"""Client for the AnkiConnect HTTP API."""

import base64
import dataclasses
import json
import logging
import typing as ty
import urllib.request

LOG = logging.getLogger(__name__)

_DEFAULT_URL = "http://127.0.0.1:8765"

CardState = ty.Literal["new", "learn", "review"]


@dataclasses.dataclass(frozen=True, slots=True)
class DeckStats:
    """Statistics for a single Anki deck."""

    name: str
    total: int
    new: int
    learn: int
    review: int


@dataclasses.dataclass(frozen=True, slots=True)
class CardInfo:
    """Rendered card content from Anki's scheduler."""

    card_id: int
    note_id: int
    question: str
    answer: str
    css: str
    buttons: list[int]
    next_reviews: list[str]
    is_marked: bool
    state: CardState


class AnkiClient:
    """Typed wrapper around the AnkiConnect JSON API.

    Args:
        url: AnkiConnect server URL.

    """

    def __init__(self, url: str = _DEFAULT_URL) -> None:
        if not url.startswith(("http:", "https:")):
            msg = "URL must start with 'http:' or 'https:'"
            raise ValueError(msg)
        self._url = url

    def _invoke(self, action: str, **params: ty.Any) -> ty.Any:  # noqa: ANN401
        """Send a raw request to AnkiConnect and return the result.

        Raises:
            RuntimeError: If AnkiConnect returns an error.

        """
        LOG.debug("AnkiConnect request: action=%s params=%s", action, params)
        body = {"action": action, "version": 6, "params": params}
        payload = json.dumps(body).encode()
        request = urllib.request.Request(  # noqa: S310
            self._url,
            payload,
        )
        response = json.load(
            urllib.request.urlopen(request),  # noqa: S310
        )
        if response["error"] is not None:
            LOG.debug("AnkiConnect error: %s", response["error"])
            raise RuntimeError(response["error"])
        LOG.debug("AnkiConnect result: %.200s", response["result"])
        return response["result"]

    # --- High-level API ---

    def deck_names(self) -> list[str]:
        """Return the names of all decks."""
        result: list[str] = self._invoke("deckNames")
        LOG.info("Found %d decks", len(result))
        return result

    def count_cards(self, deck: str = "Default") -> int:
        """Return the number of cards in *deck*."""
        cards: list[int] = self._invoke(
            "findCards",
            query=f"deck:{deck}",
        )
        LOG.info("Deck '%s': %d cards", deck, len(cards))
        return len(cards)

    def deck_stats(self) -> list[DeckStats]:
        """Return stats (new, learn, review, total) for all decks."""
        names = self.deck_names()
        raw: dict[str, ty.Any] = self._invoke(
            "getDeckStats",
            decks=names,
        )
        return [
            DeckStats(
                name=info["name"],
                total=info["total_in_deck"],
                new=info["new_count"],
                learn=info["learn_count"],
                review=info["review_count"],
            )
            for info in raw.values()
        ]

    def start_review(self, deck: str) -> bool:
        """Start a review session for *deck* using Anki's scheduler."""
        result: bool = self._invoke("guiDeckReview", name=deck)
        LOG.info("Started review for deck '%s': %s", deck, result)
        return result

    def current_card(self) -> CardInfo | None:
        """Return the current card from Anki's scheduler, or None if done."""
        try:
            result: dict[str, ty.Any] | None = self._invoke("guiCurrentCard")
        except RuntimeError:
            LOG.debug("guiCurrentCard failed (review not active)")
            return None
        if result is None:
            LOG.info("No current card (review complete)")
            return None
        self._invoke("guiStartCardTimer")

        card_id = result["cardId"]
        note_id = self._note_id_for_card(card_id)
        is_marked = self._is_marked(note_id)
        state = self._card_state(card_id)

        card = CardInfo(
            card_id=card_id,
            note_id=note_id,
            question=result["question"],
            answer=result["answer"],
            css=result.get("css", ""),
            buttons=result.get("buttons", [1, 2, 3]),
            next_reviews=result.get("nextReviews", []),
            is_marked=is_marked,
            state=state,
        )
        LOG.info(
            "Current card: %d (note: %d, marked: %s, state: %s)",
            card.card_id,
            note_id,
            is_marked,
            state,
        )
        return card

    def _note_id_for_card(self, card_id: int) -> int:
        """Map a card ID to its parent note ID."""
        note_ids: list[int] = self._invoke("cardsToNotes", cards=[card_id])
        return note_ids[0]

    def _card_state(self, card_id: int) -> CardState:
        """Return 'new', 'learn', or 'review' for the given card.

        Uses AnkiConnect's ``cardsInfo`` ``type`` field:
        0=new, 1=learning, 2=review, 3=relearning. Unknown values fall
        back to ``"review"`` (matches how Anki itself buckets odd states).
        """
        info: list[dict[str, ty.Any]] = self._invoke("cardsInfo", cards=[card_id])
        card_type = info[0].get("type")
        if card_type == 0:
            return "new"
        if card_type in (1, 3):
            return "learn"
        return "review"

    def _is_marked(self, note_id: int) -> bool:
        """Check whether a note has the 'marked' tag."""
        tags: list[str] = self._invoke("getNoteTags", note=note_id)
        return any(t.lower() == "marked" for t in tags)

    def toggle_mark(self, note_id: int) -> bool:
        """Toggle the 'marked' tag on a note. Returns the new marked state."""
        if self._is_marked(note_id):
            self._invoke("removeTags", notes=[note_id], tags="marked")
            LOG.info("Unmarked note %d", note_id)
            return False
        self._invoke("addTags", notes=[note_id], tags="marked")
        LOG.info("Marked note %d", note_id)
        return True

    def answer_card(self, ease: int) -> bool:
        """Answer the current card via Anki's scheduler.

        Args:
            ease: 1=Again, 2=Hard, 3=Good, 4=Easy.

        Returns:
            True if answered successfully.

        """
        self._invoke("guiShowAnswer")
        result: bool = self._invoke("guiAnswerCard", ease=ease)
        LOG.info("Answered current card with ease=%d: %s", ease, result)
        return result

    def undo(self) -> bool:
        """Undo the last action (e.g. a card answer).

        Returns:
            True if undo succeeded.

        """
        result: bool = self._invoke("guiUndo")
        LOG.info("Undo: %s", result)
        return result

    def suspend_card(self, card_id: int) -> bool:
        """Suspend a single card until the user manually unsuspends it."""
        result: bool = self._invoke("suspend", cards=[card_id])
        LOG.info("Suspended card %d: %s", card_id, result)
        return result

    def suspend_note(self, note_id: int) -> bool:
        """Suspend every card belonging to a note."""
        card_ids: list[int] = self._invoke("findCards", query=f"nid:{note_id}")
        if not card_ids:
            LOG.info("Suspend note %d: no cards found", note_id)
            return False
        result: bool = self._invoke("suspend", cards=card_ids)
        LOG.info("Suspended note %d (%d cards): %s", note_id, len(card_ids), result)
        return result

    def sync(self) -> None:
        """Sync the Anki collection with AnkiWeb."""
        self._invoke("sync")
        LOG.info("Sync complete")

    def retrieve_media_file(self, filename: str) -> bytes | None:
        """Fetch a file from Anki's ``collection.media`` folder.

        Returns ``None`` if Anki doesn't have the file.
        """
        result: str | bool = self._invoke(
            "retrieveMediaFile",
            filename=filename,
        )
        if result is False:
            LOG.debug("Media file not found: %s", filename)
            return None
        if not isinstance(result, str):
            msg = f"Unexpected retrieveMediaFile response: {type(result).__name__}"
            raise TypeError(msg)
        data = base64.b64decode(result)
        LOG.info("Retrieved media file '%s' (%d bytes)", filename, len(data))
        return data

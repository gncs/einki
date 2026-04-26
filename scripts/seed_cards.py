#!/usr/bin/env python3
"""Seed the Default deck with sample flashcards via AnkiConnect."""

import argparse
import base64
import pathlib
import sys
import typing as ty

from einki._anki_client import AnkiClient

_DECK = "Default"

CARDS = [
    ("What is the capital of France?", "Paris"),
    ("What is the chemical symbol for water?", "H₂O"),
    ("Who wrote 'Hamlet'?", "William Shakespeare"),
    ("What is the speed of light?", "Approx. 3 x 10^8 m/s"),
    ("What planet is known as the Red Planet?", "Mars"),
    ("What is the powerhouse of the cell?", "The mitochondria"),
    ("In what year did World War II end?", "1945"),
    ("What is the square root of 144?", "12"),
    ("What gas do plants absorb from the atmosphere?", "Carbon dioxide (CO₂)"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
]

# One extra card that embeds an image, so we can verify whether images
# rendered by Anki show up in the einki web UI.
_IMAGE_SOURCE = pathlib.Path(__file__).parent / "seed_image_dice.png"
_IMAGE_MEDIA_NAME = "einki_sample_dice.png"
_IMAGE_CARD = (
    f'How many dots? <br><img src="{_IMAGE_MEDIA_NAME}">',
    "It depends on the die.",
)


def _upload_image(client: AnkiClient) -> None:
    """Upload the sample image into Anki's media folder."""
    data = base64.b64encode(_IMAGE_SOURCE.read_bytes()).decode("ascii")
    client._invoke(  # noqa: SLF001
        "storeMediaFile",
        filename=_IMAGE_MEDIA_NAME,
        data=data,
    )
    print(f"Uploaded media: {_IMAGE_MEDIA_NAME} (from {_IMAGE_SOURCE.name})")


def _wipe_deck(client: AnkiClient, deck: str) -> None:
    """Delete every note in *deck* after an interactive confirmation."""
    note_ids: list[int] = client._invoke(  # noqa: SLF001
        "findNotes",
        query=f"deck:{deck}",
    )
    if not note_ids:
        print(f"Deck '{deck}' is already empty.")
        return

    card_ids: list[int] = client._invoke(  # noqa: SLF001
        "findCards",
        query=f"deck:{deck}",
    )
    sample_count = min(3, len(note_ids))
    samples: list[dict[str, ty.Any]] = client._invoke(  # noqa: SLF001
        "notesInfo",
        notes=note_ids[:sample_count],
    )

    print(f"Deck:    {deck}")
    print(f"Notes:   {len(note_ids)}")
    print(f"Cards:   {len(card_ids)}")
    if samples:
        print("Sample first fields:")
        for note in samples:
            fields = note.get("fields", {})
            first_field_name = next(iter(fields), None)
            value = fields[first_field_name]["value"] if first_field_name else "<empty>"
            print(f"  - {value[:80]!r}")
        if len(note_ids) > sample_count:
            print(f"  ... and {len(note_ids) - sample_count} more.")

    answer = input("Type 'yes' to confirm deletion: ").strip().lower()
    if answer != "yes":
        print("Aborted; no notes were deleted.")
        sys.exit(1)

    client._invoke("deleteNotes", notes=note_ids)  # noqa: SLF001
    print(f"Deleted {len(note_ids)} notes from '{deck}'.")


def main() -> None:
    """Add sample notes to the Default deck."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wipe",
        action="store_true",
        help=(
            f"Delete all notes in the '{_DECK}' deck before seeding "
            "(asks for confirmation)."
        ),
    )
    args = parser.parse_args()

    client = AnkiClient()

    if args.wipe:
        _wipe_deck(client, _DECK)

    _upload_image(client)

    all_cards = [_IMAGE_CARD, *CARDS]
    for front, back in all_cards:
        client._invoke(  # noqa: SLF001
            "addNote",
            note={
                "deckName": _DECK,
                "modelName": "Basic",
                "fields": {"Front": front, "Back": back},
                "options": {"allowDuplicate": True},
            },
        )
        print(f"Added: {front}")

    print(f"\nDone — added {len(all_cards)} cards to {_DECK} deck.")
    print(f"Total cards: {client.count_cards(_DECK)}")


if __name__ == "__main__":
    main()

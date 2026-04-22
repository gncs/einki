"""Flask application factory."""

import dataclasses
import datetime
import logging
import mimetypes
import os
import re
import secrets
import urllib.parse

import flask
import flask_login
import werkzeug

from einki._anki_client import AnkiClient
from einki._sync import sync_state, trigger_sync

LOG = logging.getLogger(__name__)

_IMG_SRC_RE = re.compile(
    r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)\2',
    re.IGNORECASE,
)
_ABSOLUTE_URL_PREFIXES = ("http:", "https:", "data:", "//", "/media/")


def _rewrite_media_urls(html: str) -> str:
    """Prefix bare ``<img src="...">`` filenames with ``/media/``.

    Absolute URLs (``http:``, ``https:``, ``data:``, protocol-relative
    ``//...``) and already-prefixed ``/media/...`` values are left
    untouched. Filenames are URL-encoded so spaces and non-ASCII
    characters survive.
    """

    def replace(match: re.Match[str]) -> str:
        prefix, quote, value = match.group(1), match.group(2), match.group(3)
        if value.startswith(_ABSOLUTE_URL_PREFIXES):
            return match.group(0)
        quoted = urllib.parse.quote(value, safe="/")
        return f"{prefix}{quote}/media/{quoted}{quote}"

    return _IMG_SRC_RE.sub(replace, html)


class _User(flask_login.UserMixin):  # type: ignore[misc]
    """A minimal user for flask-login. Only one user is supported."""

    def __init__(self, user_id: str) -> None:
        self.id = user_id


def _register_auth(
    app: flask.Flask,
    *,
    username: str,
    password: str,
) -> None:
    """Set up flask-login with a single-user login/logout flow."""
    login_manager = flask_login.LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader  # type: ignore[untyped-decorator]
    def load_user(user_id: str) -> _User | None:
        """Load a user by ID. Returns the user if the ID matches."""
        if user_id == username:
            return _User(user_id)
        return None

    @app.route("/login", methods=["GET", "POST"])
    def login() -> str | werkzeug.Response:
        """Show the login form or process login credentials."""
        if flask.request.method == "POST":
            provided_username = flask.request.form.get("username", "")
            provided_password = flask.request.form.get("password", "")

            if provided_username == username and provided_password == password:
                user = _User(provided_username)
                flask_login.login_user(user, remember=True)
                return flask.redirect(flask.url_for("decks"))

            return flask.render_template("login.html", error="Invalid credentials.")

        return flask.render_template("login.html", error=None)

    @app.route("/logout")
    def logout() -> werkzeug.Response:
        """Log out the current user and redirect to login."""
        flask_login.logout_user()
        return flask.redirect(flask.url_for("login"))


def _register_anki_routes(  # noqa: C901
    app: flask.Flask,
    anki_client: AnkiClient | None,
) -> None:
    """Register routes that interact with AnkiConnect."""

    @app.route("/")
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def index() -> werkzeug.Response:
        """Redirect to the decks overview."""
        return flask.redirect(flask.url_for("decks"))

    @app.route("/decks")
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def decks() -> str:
        """Show deck names and card counts from Anki."""
        if anki_client is None:
            return flask.render_template(
                "decks.html",
                error="AnkiConnect is not configured.",
                decks=[],
            )
        trigger_sync(anki_client)
        try:
            deck_info = anki_client.deck_stats()
        except Exception:
            LOG.exception("Failed to query AnkiConnect")
            return flask.render_template(
                "decks.html",
                error="Could not connect to AnkiConnect.",
                decks=[],
            )
        return flask.render_template(
            "decks.html",
            error=None,
            decks=deck_info,
        )

    @app.route("/study/<path:deck>")
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def study(deck: str) -> str:
        """Show the next due card from *deck*."""
        answer_shown = flask.request.args.get("answer_shown") == "1"
        return _render_study(anki_client, deck, answer_shown=answer_shown)

    @app.route("/answer_card", methods=["POST"])
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def answer_card() -> str | werkzeug.Response:
        """Submit a review answer and show the next card."""
        return _handle_answer(anki_client)

    @app.route("/undo", methods=["POST"])
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def undo() -> str | werkzeug.Response:
        """Undo the last card answer."""
        return _handle_undo(anki_client)

    @app.route("/sync", methods=["POST"])
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def sync() -> werkzeug.Response:
        """Trigger a sync and redirect back, preserving answer-shown state."""
        if anki_client is not None:
            trigger_sync(anki_client)
        redirect = flask.request.form.get("next", "/decks")
        if flask.request.form.get("answer_shown") == "1":
            separator = "&" if "?" in redirect else "?"
            redirect = f"{redirect}{separator}answer_shown=1"
        return flask.redirect(redirect)

    @app.route("/mark_card", methods=["POST"])
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def mark_card() -> werkzeug.Response:
        """Toggle the 'marked' tag on the current card's note."""
        return _handle_mark(anki_client)

    @app.route("/media/<path:filename>")
    @flask_login.login_required  # type: ignore[untyped-decorator]
    def media(filename: str) -> werkzeug.Response:
        """Serve a file from Anki's ``collection.media`` folder."""
        return _serve_media(anki_client, filename)


def _serve_media(
    anki_client: AnkiClient | None,
    filename: str,
) -> werkzeug.Response:
    """Fetch a media file via AnkiConnect and return it to the browser."""
    if anki_client is None:
        flask.abort(404)
    parts = filename.split("/")
    if any(part in ("", "..") for part in parts):
        flask.abort(404)
    try:
        data = anki_client.retrieve_media_file(filename)
    except Exception:
        LOG.exception("Failed to retrieve media '%s'", filename)
        flask.abort(404)
    if data is None:
        flask.abort(404)
    mimetype, _ = mimetypes.guess_type(filename)
    response = flask.Response(data, mimetype=mimetype or "application/octet-stream")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


def _handle_mark(anki_client: AnkiClient | None) -> werkzeug.Response:
    """Toggle the 'marked' tag on the current card's note."""
    deck = flask.request.form["deck"]
    note_id = int(flask.request.form["note_id"])
    answer_shown = flask.request.form.get("answer_shown") == "1"
    if anki_client is not None:
        anki_client.toggle_mark(note_id)
    return flask.redirect(
        flask.url_for("study", deck=deck, answer_shown="1" if answer_shown else None),
    )


def _handle_undo(anki_client: AnkiClient | None) -> str | werkzeug.Response:
    """Attempt undo, showing a banner if nothing to undo."""
    deck = flask.request.form["deck"]
    success = False
    if anki_client is not None:
        success = anki_client.undo()
    if success:
        return flask.redirect(flask.url_for("study", deck=deck))
    return flask.render_template(
        "study.html",
        error=None,
        card=None,
        deck=deck,
        undo_failed=True,
        stats=None,
    )


def _handle_answer(anki_client: AnkiClient | None) -> str | werkzeug.Response:
    """Process a card answer, guarding against stale cards."""
    ease = int(flask.request.form["ease"])
    deck = flask.request.form["deck"]
    expected_card_id = int(flask.request.form["card_id"])
    if anki_client is not None:
        current = anki_client.current_card()
        if current is not None and current.card_id == expected_card_id:
            anki_client.answer_card(ease)
            return flask.redirect(flask.url_for("study", deck=deck))

        LOG.warning(
            "Stale answer: expected card %d but current is %s",
            expected_card_id,
            current.card_id if current else None,
        )
        return flask.render_template(
            "study.html",
            error=None,
            card=None,
            deck=deck,
            stale=True,
            stats=None,
        )
    return flask.redirect(flask.url_for("study", deck=deck))


def _render_study(
    anki_client: AnkiClient | None,
    deck: str,
    *,
    answer_shown: bool = False,
) -> str:
    """Start a review session and render the next card."""
    if anki_client is None:
        return flask.render_template(
            "study.html",
            error="AnkiConnect is not configured.",
            card=None,
            deck=deck,
            stats=None,
            answer_shown=answer_shown,
        )
    try:
        anki_client.start_review(deck)
        card = anki_client.current_card()
        if card is not None:
            card = dataclasses.replace(
                card,
                question=_rewrite_media_urls(card.question),
                answer=_rewrite_media_urls(card.answer),
            )
        all_stats = anki_client.deck_stats()
        stats = next((s for s in all_stats if s.name == deck), None)
        if card is None:
            trigger_sync(anki_client)
            return flask.render_template(
                "study.html",
                error=None,
                card=None,
                deck=deck,
                done=True,
                stats=stats,
                answer_shown=False,
            )
    except Exception:
        LOG.exception("Failed to fetch card from AnkiConnect")
        return flask.render_template(
            "study.html",
            error="Could not connect to AnkiConnect.",
            card=None,
            deck=deck,
            stats=None,
            answer_shown=False,
        )
    return flask.render_template(
        "study.html",
        error=None,
        card=card,
        deck=deck,
        stats=stats,
        answer_shown=answer_shown,
    )


def create_app(
    *,
    username: str,
    password: str,
    anki_client: AnkiClient | None = None,
) -> flask.Flask:
    """Create and configure the Flask application.

    Args:
        username: Username for session-based auth.
        password: Password for session-based auth.
        anki_client: Optional AnkiConnect client for live deck info.

    """
    app = flask.Flask(__name__)
    app.secret_key = os.environ.get(
        "EINKI_SECRET_KEY",
        secrets.token_hex(32),
    )

    # Keep login sessions alive indefinitely (10 years).
    # The Kindle browser doesn't support re-login gracefully, so we
    # never want the session to expire while the server is running.
    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=3650)
    app.config["REMEMBER_COOKIE_DURATION"] = datetime.timedelta(days=3650)

    @app.context_processor
    def _inject_sync_status() -> dict[str, bool]:
        """Make sync_failed available in all templates."""
        return {"sync_failed": sync_state.consume_failure()}

    _register_auth(app, username=username, password=password)
    _register_anki_routes(app, anki_client)

    return app

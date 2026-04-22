"""Tests for the einki server."""

import flask
import flask.testing

from einki._app import create_app

_USERNAME = "testuser"
_PASSWORD = "testpass"  # noqa: S105


def _make_client() -> flask.testing.FlaskClient:
    """Create a Flask test client configured with test credentials."""
    app = create_app(
        username=_USERNAME,
        password=_PASSWORD,
    )
    app.config["TESTING"] = True
    return app.test_client()


def _login(client: flask.testing.FlaskClient) -> None:
    """Log in via the login form."""
    client.post(
        "/login",
        data={"username": _USERNAME, "password": _PASSWORD},
        follow_redirects=True,
    )


def test_unauthenticated_redirects_to_login() -> None:
    """Requests without a session should redirect to /login."""
    client = _make_client()
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_wrong_credentials_shows_error() -> None:
    """Login with wrong credentials should show an error message."""
    client = _make_client()
    response = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong"},
    )

    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_login_redirects_to_decks() -> None:
    """Successful login should redirect to the decks page."""
    client = _make_client()
    response = client.post(
        "/login",
        data={"username": _USERNAME, "password": _PASSWORD},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/decks"


def test_index_redirects_to_decks() -> None:
    """Authenticated GET / should redirect to /decks."""
    client = _make_client()
    _login(client)

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/decks"


def test_decks_page_accessible() -> None:
    """GET /decks should render (with AnkiConnect error since none configured)."""
    client = _make_client()
    _login(client)

    response = client.get("/decks")

    assert response.status_code == 200
    assert b"AnkiConnect is not configured" in response.data


def test_study_page_without_anki() -> None:
    """GET /study/Default should show error when AnkiConnect is not configured."""
    client = _make_client()
    _login(client)

    response = client.get("/study/Default")

    assert response.status_code == 200
    assert b"AnkiConnect is not configured" in response.data


def test_logout_clears_session() -> None:
    """Logging out should clear the session and redirect to login."""
    client = _make_client()
    _login(client)

    response = client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_suspend_requires_login() -> None:
    """POST /suspend without a session should redirect to /login."""
    client = _make_client()

    response = client.post(
        "/suspend",
        data={"deck": "Default", "scope": "card", "card_id": "1"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_suspend_card_without_anki_redirects() -> None:
    """POST /suspend (scope=card) with no AnkiClient redirects to /study/<deck>."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/suspend",
        data={"deck": "Default", "scope": "card", "card_id": "1"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default"


def test_suspend_note_without_anki_redirects() -> None:
    """POST /suspend (scope=note) with no AnkiClient redirects to /study/<deck>."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/suspend",
        data={"deck": "Default", "scope": "note", "note_id": "1"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default"


def test_suspend_unknown_scope_redirects() -> None:
    """An unknown scope must not raise — just redirect back."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/suspend",
        data={"deck": "Default", "scope": "garbage"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default"

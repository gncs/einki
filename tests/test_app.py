"""Tests for the einki server."""

import flask
import flask.testing

from einki._app import _rewrite_media_urls, create_app

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


def test_rewrite_media_urls_basic() -> None:
    """Bare filenames should be prefixed with /media/."""
    assert _rewrite_media_urls('<img src="foo.png">') == '<img src="/media/foo.png">'


def test_rewrite_media_urls_single_quotes() -> None:
    """Single-quoted src attributes should be rewritten too."""
    assert _rewrite_media_urls("<img src='foo.png'>") == "<img src='/media/foo.png'>"


def test_rewrite_media_urls_absolute_untouched() -> None:
    """Absolute URLs must not be rewritten."""
    for src in (
        "http://example.com/foo.png",
        "https://example.com/foo.png",
        "data:image/png;base64,abc",
        "//cdn.example.com/foo.png",
    ):
        html = f'<img src="{src}">'
        assert _rewrite_media_urls(html) == html


def test_rewrite_media_urls_already_prefixed() -> None:
    """Already-prefixed /media/ URLs should be left alone (idempotent)."""
    html = '<img src="/media/foo.png">'
    assert _rewrite_media_urls(html) == html
    assert _rewrite_media_urls(_rewrite_media_urls(html)) == html


def test_rewrite_media_urls_special_chars() -> None:
    """Filenames with spaces or non-ASCII must be URL-encoded."""
    result = _rewrite_media_urls('<img src="my file.png">')
    assert result == '<img src="/media/my%20file.png">'

    result = _rewrite_media_urls('<img src="café.png">')
    assert result == '<img src="/media/caf%C3%A9.png">'


def test_rewrite_media_urls_multiple_imgs() -> None:
    """Each <img> tag in the HTML should be rewritten independently."""
    html = '<p><img src="a.png"> and <img class="x" src="b.jpg" alt="b"></p>'
    expected = (
        '<p><img src="/media/a.png"> and <img class="x" src="/media/b.jpg" alt="b"></p>'
    )
    assert _rewrite_media_urls(html) == expected


def test_media_route_without_anki() -> None:
    """GET /media/<file> returns 404 when AnkiConnect is not configured."""
    client = _make_client()
    _login(client)

    response = client.get("/media/foo.png")

    assert response.status_code == 404


def test_media_route_rejects_traversal() -> None:
    """GET /media/../etc/passwd must be rejected as 404."""
    client = _make_client()
    _login(client)

    response = client.get("/media/../etc/passwd")

    assert response.status_code == 404


def test_media_route_requires_login() -> None:
    """GET /media/<file> without a session should redirect to /login."""
    client = _make_client()

    response = client.get("/media/foo.png")

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


def test_set_flag_requires_login() -> None:
    """POST /set_flag without a session should redirect to /login."""
    client = _make_client()

    response = client.post(
        "/set_flag",
        data={"deck": "Default", "card_id": "1", "flag": "1"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_set_flag_without_anki_redirects() -> None:
    """POST /set_flag with no AnkiClient redirects to /study/<deck>."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/set_flag",
        data={"deck": "Default", "card_id": "1", "flag": "3"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default"


def test_set_flag_preserves_answer_shown() -> None:
    """answer_shown=1 should round-trip through the redirect."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/set_flag",
        data={
            "deck": "Default",
            "card_id": "1",
            "flag": "0",
            "answer_shown": "1",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default?answer_shown=1"


def test_set_flag_invalid_value_redirects() -> None:
    """Out-of-range flag values must not raise — just redirect back."""
    client = _make_client()
    _login(client)

    response = client.post(
        "/set_flag",
        data={"deck": "Default", "card_id": "1", "flag": "99"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/study/Default"

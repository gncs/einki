"""Guard against committing sync credentials to the bundled Anki profile.

``docker/anki-headless/data/prefs21.db`` is baked into the image. A
developer who sets up sync locally risks accidentally committing their
AnkiWeb ``syncKey`` (and possibly ``syncUser``) to the repository. This
test fails loudly if that happens.

The schema is ``profiles(name TEXT PRIMARY KEY, data BLOB)`` where
``data`` is a pickled ``dict``. We unpickle trusted local data (the
file is in our own repo), scan the user profiles, and assert that no
credential-shaped values are present.
"""

import contextlib
import pathlib
import pickle
import re
import sqlite3
import typing as ty

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PREFS_PATH = _REPO_ROOT / "docker" / "anki-headless" / "data" / "prefs21.db"

_REQUIRED_EMPTY_KEYS: ty.Final = ("syncKey",)
_OPTIONAL_EMPTY_KEYS: ty.Final = ("syncUser", "hostNum")

_EMAIL_RE: ty.Final = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TOKEN_RE: ty.Final = re.compile(r"\b[a-f0-9]{32,}\b", re.IGNORECASE)


def _load_profiles() -> dict[str, dict[str, ty.Any]]:
    """Unpickled user profiles from the prefs db (excludes ``_global``)."""
    assert _PREFS_PATH.is_file(), f"expected prefs db at {_PREFS_PATH}"

    profiles: dict[str, dict[str, ty.Any]] = {}
    with contextlib.closing(sqlite3.connect(_PREFS_PATH)) as conn:
        for name, blob in conn.execute("SELECT name, data FROM profiles"):
            if name == "_global":
                continue
            # Trusted local file under version control in this repo.
            profiles[name] = pickle.loads(blob)  # noqa: S301

    return profiles


def test_prefs_db_has_user_profiles() -> None:
    """The bundled prefs file should contain at least one user profile."""
    profiles = _load_profiles()
    assert profiles, "no user profiles found in prefs21.db"


@pytest.mark.parametrize("key", _REQUIRED_EMPTY_KEYS)
def test_required_sync_key_is_empty(key: str) -> None:
    """Required keys must be present and falsy; absence means Anki's format changed."""
    profiles = _load_profiles()
    for name, data in profiles.items():
        assert key in data, (
            f"profile {name!r} is missing expected key {key!r} (Anki format changed?)"
        )
        assert not data[key], f"profile {name!r} has non-empty {key!r} = {data[key]!r}"


@pytest.mark.parametrize("key", _OPTIONAL_EMPTY_KEYS)
def test_optional_sync_key_is_empty_if_present(key: str) -> None:
    """Optional keys may be absent, but if present must be falsy."""
    profiles = _load_profiles()
    for name, data in profiles.items():
        if key in data:
            assert not data[key], (
                f"profile {name!r} has non-empty {key!r} = {data[key]!r}"
            )


def test_no_credential_shaped_values() -> None:
    """Belt-and-braces: no email addresses or long hex tokens in user profiles."""
    profiles = _load_profiles()
    for name, data in profiles.items():
        for key, value in data.items():
            if not isinstance(value, str):
                continue
            assert not _EMAIL_RE.search(value), (
                f"profile {name!r} key {key!r} contains email-shaped value: {value!r}"
            )
            assert not _TOKEN_RE.search(value), (
                f"profile {name!r} key {key!r} contains token-shaped value: {value!r}"
            )

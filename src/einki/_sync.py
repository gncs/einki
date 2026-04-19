"""Background sync scheduler for AnkiConnect."""

import logging
import threading
from enum import Enum

from einki._anki_client import AnkiClient

LOG = logging.getLogger(__name__)

_SYNC_INTERVAL = 5 * 60  # seconds  # copilot-todo: add unit of time to variable name


class SyncStatus(Enum):
    """Result of the last sync attempt."""

    OK = "ok"
    FAILED = "failed"
    PENDING = "pending"


class SyncState:
    """Thread-safe container for the last sync result."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = SyncStatus.PENDING
        self._seen = True  # don't show banner before first sync

    @property
    def status(self) -> SyncStatus:
        """Return the current sync status."""
        with self._lock:
            return self._status

    def set(self, status: SyncStatus) -> None:
        """Update the sync status and mark it as unseen."""
        with self._lock:
            self._status = status
            self._seen = False

    def consume_failure(self) -> bool:
        """Return True (once) if the last sync failed.

        After returning True, the failure is marked as seen so the
        banner only shows once.
        """
        with self._lock:
            if self._status == SyncStatus.FAILED and not self._seen:
                self._seen = True
                return True
            return False


# Module-level singleton — shared across threads.
sync_state = SyncState()


def _do_sync(client: AnkiClient) -> None:
    """Run sync, updating shared state."""
    try:
        client.sync()
        sync_state.set(SyncStatus.OK)
    except Exception:
        LOG.exception("Background sync failed")
        sync_state.set(SyncStatus.FAILED)


def trigger_sync(client: AnkiClient) -> None:
    """Fire off a sync in a background thread."""
    threading.Thread(target=_do_sync, args=(client,), daemon=True).start()


def start_periodic_sync(client: AnkiClient) -> None:
    """Start a repeating timer that syncs every ``_SYNC_INTERVAL`` seconds."""

    def _tick() -> None:
        _do_sync(client)
        timer = threading.Timer(_SYNC_INTERVAL, _tick)
        timer.daemon = True
        timer.start()

    timer = threading.Timer(_SYNC_INTERVAL, _tick)
    timer.daemon = True
    timer.start()
    LOG.info("Periodic sync started (every %ds)", _SYNC_INTERVAL)

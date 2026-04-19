"""CLI entry point for the einki server."""

import argparse
import logging
import os

from einki._anki_client import AnkiClient
from einki._app import create_app
from einki._sync import start_periodic_sync

LOG = logging.getLogger(__name__)


def main() -> None:
    """Run the einki Flask server."""
    parser = argparse.ArgumentParser(description="Run the einki server.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("EINKI_USERNAME"),
        help="Auth username (env: EINKI_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("EINKI_PASSWORD"),
        help="Auth password (env: EINKI_PASSWORD)",
    )
    parser.add_argument(
        "--anki-url",
        default=os.environ.get("ANKI_URL", "http://127.0.0.1:8765"),
        help="AnkiConnect URL (default: http://127.0.0.1:8765)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run Flask in debug mode (auto-reload, debugger)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    anki_client = AnkiClient(url=args.anki_url)

    missing = []
    if not args.username:
        missing.append("EINKI_USERNAME (or --username)")
    if not args.password:
        missing.append("EINKI_PASSWORD (or --password)")
    if missing:
        parser.error(f"Required: {', '.join(missing)}")

    LOG.info(
        "Starting einki on %s:%d (AnkiConnect: %s)",
        args.host,
        args.port,
        args.anki_url,
    )

    # Flask's debug-mode reloader runs this process twice: a parent watcher
    # and a child server. Both execute main() up to app.run(), so starting
    # the sync thread unconditionally would spawn two threads pinging
    # AnkiConnect on independent schedules. Werkzeug sets WERKZEUG_RUN_MAIN
    # to "true" only in the serving child, so we gate on that in debug mode.
    # Without --debug there is no reloader and we always start the thread.
    if not args.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_periodic_sync(anki_client)

    app = create_app(
        username=args.username,
        password=args.password,
        anki_client=anki_client,
    )
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()

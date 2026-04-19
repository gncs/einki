#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# debug_anki.sh — inspect Anki data volume for sync/auth issues
# ---------------------------------------------------------------------------
set -euo pipefail

echo "=== Files in /data/ ==="
docker compose exec anki ls -la /data/

echo ""
echo "=== Files in /data/addons21/ ==="
docker compose exec anki ls -la /data/addons21/ 2>/dev/null || echo "(not found)"

echo ""
echo "=== prefs21.db file info ==="
docker compose exec anki ls -la /data/prefs21.db

echo ""
echo "=== Anki sync state ==="
# Pull the DB from the container and inspect with Python on the host.
# The sync key and user are stored as pickled Python objects in prefs21.db.
docker compose exec anki cat /data/prefs21.db | python3 -c "
import sys, sqlite3, pickle, tempfile, os
data = sys.stdin.buffer.read()
f = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
f.write(data); f.close()
conn = sqlite3.connect(f.name)
for name, blob in conn.execute('SELECT name, data FROM profiles'):
    d = pickle.loads(blob)
    if name == '_global':
        print(f'Profile: {name}')
        print(f'  firstRun: {d.get(\"firstRun\")}')
        print(f'  last_loaded_profile: {d.get(\"last_loaded_profile_name\")}')
    else:
        print(f'Profile: {name}')
        print(f'  syncKey: {d.get(\"syncKey\")}')
        print(f'  syncUser: {d.get(\"syncUser\", \"(not set)\")}')
        print(f'  autoSync: {d.get(\"autoSync\")}')
        print(f'  syncMedia: {d.get(\"syncMedia\")}')
conn.close()
os.unlink(f.name)
"

echo ""
echo "=== Collection exists? ==="
docker compose exec anki ls -la /data/User\ 1/ 2>/dev/null || echo "(User 1 directory not found)"

#!/usr/bin/env bash
# Apply search-related RSS feeds into remote sruqy server/index.ts feedSources.
# Usage:
#   SRUQY_SSH_PASS='***' ./scripts/apply_search_feeds.sh
#   # or: ssh already configured with key
#   ./scripts/apply_search_feeds.sh
set -euo pipefail

HOST="${SRUQY_SSH_HOST:-116.198.229.83}"
USER="${SRUQY_SSH_USER:-jinlei72}"
REMOTE_DIR="${SRUQY_REMOTE_DIR:-/mnt/data4/jinlei72/sruqy}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FEEDS_JSON="${SCRIPT_DIR}/../search_feeds_to_add.json"

if [[ ! -f "$FEEDS_JSON" ]]; then
  echo "missing $FEEDS_JSON" >&2
  exit 1
fi

ssh_cmd() {
  if [[ -n "${SRUQY_SSH_PASS:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    sshpass -e ssh -o StrictHostKeyChecking=accept-new "$@"
  else
    ssh -o StrictHostKeyChecking=accept-new "$@"
  fi
}

export SSHPASS="${SRUQY_SSH_PASS:-}"

echo "==> uploading feeds json"
ssh_cmd "${USER}@${HOST}" "mkdir -p /tmp/sruqy-feed-patch"
scp -o StrictHostKeyChecking=accept-new "$FEEDS_JSON" "${USER}@${HOST}:/tmp/sruqy-feed-patch/feeds.json" 2>/dev/null || \
  sshpass -e scp -o StrictHostKeyChecking=accept-new "$FEEDS_JSON" "${USER}@${HOST}:/tmp/sruqy-feed-patch/feeds.json"

echo "==> patching feedSources on remote"
ssh_cmd "${USER}@${HOST}" "REMOTE_DIR='$REMOTE_DIR' python3" <<'PY'
import json, os, re, subprocess, time
from pathlib import Path

remote_dir = Path(os.environ["REMOTE_DIR"])
index = remote_dir / "server" / "index.ts"
feeds = json.loads(Path("/tmp/sruqy-feed-patch/feeds.json").read_text())

text = index.read_text()
backup = index.with_suffix(f".ts.bak.searchfeeds.{int(time.time())}")
backup.write_text(text)
print("backup:", backup)

# Collect existing feedUrl values
existing = set(re.findall(r'feedUrl:\s*"([^"]+)"', text))
existing |= set(re.findall(r"feedUrl:\s*'([^']+)'", text))

def ts_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def to_ts(entry: dict) -> str:
    cov = ", ".join(f'"{ts_escape(c)}"' for c in entry["coverage"])
    return (
        "  {\n"
        f'    name: "{ts_escape(entry["name"])}",\n'
        f'    feedUrl: "{ts_escape(entry["feedUrl"])}",\n'
        f'    type: "{ts_escape(entry["type"])}",\n'
        f"    coverage: [{cov}],\n"
        f'    limit: {int(entry["limit"])},\n'
        "  },\n"
    )

to_add = []
for e in feeds:
    if e["feedUrl"] in existing:
        print("skip existing:", e["name"])
        continue
    to_add.append(e)

if not to_add:
    print("nothing to add")
    raise SystemExit(0)

# Find feedSources array end: look for last known feed then closing ]
# Prefer insert before the closing of feedSources = [ ... ]
m = re.search(r"(feedSources\s*(?::\s*\w+\s*)?=\s*\[)", text)
if not m:
    # alternative: const feedSources = [
    m = re.search(r"(const\s+feedSources\s*=\s*\[)", text)
if not m:
    raise SystemExit("cannot find feedSources array in server/index.ts")

start = m.end()
# find matching closing bracket at depth 1 from start
depth = 1
i = start
while i < len(text) and depth > 0:
    ch = text[i]
    if ch == "[":
        depth += 1
    elif ch == "]":
        depth -= 1
    i += 1
if depth != 0:
    raise SystemExit("failed to find end of feedSources array")
end_bracket = i - 1

block = "".join(to_ts(e) for e in to_add)
# ensure previous entry has comma if needed
before = text[:end_bracket].rstrip()
if before and not before.endswith(",") and not before.endswith("["):
    # last non-ws char should be }, already with comma usually
    pass
if not before.endswith("\n"):
    before += "\n"
new_text = before + block + text[end_bracket:]
index.write_text(new_text)
print(f"added {len(to_add)} feeds:")
for e in to_add:
    print(" +", e["name"], e["feedUrl"])

# rebuild backend if docker compose present
compose = remote_dir / "docker-compose.yml"
compose2 = remote_dir / "compose.yml"
if compose.exists() or compose2.exists():
    cwd = str(remote_dir)
    # prefer rebuild backend service
    for svc in ("sruqy-backend", "backend", "server"):
        r = subprocess.run(
            ["docker", "compose", "ps", "-q", svc],
            cwd=cwd, capture_output=True, text=True
        )
        if r.returncode == 0 and r.stdout.strip():
            print("rebuilding", svc)
            subprocess.check_call(["docker", "compose", "up", "-d", "--build", svc], cwd=cwd)
            break
    else:
        print("docker compose present but backend service name unknown; please rebuild manually")
else:
    print("no compose file; please restart backend manually")
PY

echo "==> verifying /api/health source count"
sleep 3
curl -sS "http://${HOST}:9986/api/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("sources", len(d.get("sources",[])));
names=[s["name"] for s in d.get("sources",[])];
want=["arXiv cs.IR","Elastic Blog","OpenSearch Blog","Weaviate Blog","Vespa Blog","Apache Solr","ClickHouse Blog","LlamaIndex Blog","deepset / Haystack","Lilian Weng","Sebastian Ruder","SIGIR","Google Research Blog","HN Search IR","arXiv cs.AI"];
for n in want: print(("OK" if n in names else "MISSING"), n)'

#!/bin/sh
# Build a reports index from the mounted private volume (read-only OK).
set -eu
DATA_DIR="${DATA_DIR:-/data}"
RAPPORTS_DIR="$DATA_DIR/rapports"
CACHE_DIR="/var/cache/asclepios"
INDEX="$CACHE_DIR/rapports-index.json"

mkdir -p "$CACHE_DIR"
echo '[' > "$INDEX"
first=1
if [ -d "$RAPPORTS_DIR" ]; then
  for f in "$RAPPORTS_DIR"/*.md; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    case "$base" in
      [Rr][Ee][Aa][Dd][Mm][Ee].md) continue ;;
    esac
    id=${base%.md}
    if [ "$first" -eq 1 ]; then
      first=0
    else
      echo ',' >> "$INDEX"
    fi
    printf '{"id":"%s","file":"%s"}' "$id" "$base" >> "$INDEX"
  done
fi
echo ']' >> "$INDEX"

exec nginx -g 'daemon off;'

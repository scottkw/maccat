#!/usr/bin/env bash
# build-pyz.sh — builds dist/maccat.pyz from src/
#
# Source MUST be src/ (not src/maccat/) — see Phase 16 research Pitfall 1.
# Using src/ ensures maccat/ appears as a top-level directory inside the
# archive, making `import maccat` resolve correctly at runtime.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"
DIST_DIR="$SCRIPT_DIR/../dist"
OUTPUT="$DIST_DIR/maccat.pyz"

mkdir -p "$DIST_DIR"

# Remove __pycache__ for a clean archive (avoids including stale .pyc files)
find "$SRC_DIR" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# CORRECT: src/ as source so maccat/ appears as a top-level dir in the archive.
# WRONG:   python3 -m zipapp src/maccat ... → import maccat fails (no maccat/ dir).
python3 -m zipapp "$SRC_DIR" \
    --output "$OUTPUT" \
    --python "/usr/bin/env python3" \
    --main "maccat.__main__:main" \
    --compress

echo "Built: $OUTPUT"

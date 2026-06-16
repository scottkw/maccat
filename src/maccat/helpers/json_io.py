from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_get(file: Path, key: str, default: str = "") -> str:
    """
    Extract a scalar value from a JSON file by dotted key path.
    Returns default on any error (missing file, parse error, missing key, wrong type).
    Never raises. Mirrors the zsh json_get contract exactly.

    Examples:
        json_get(path, "name")            -> top-level "name" field
        json_get(path, "author.name")     -> nested traversal: data["author"]["name"]
        json_get(path, "count")           -> int leaf converted to str: "42"

    IMPORTANT: Do NOT use this for VS Code NLS key lookup — package.nls.json uses
    flat keys that may contain literal dots (e.g. "extension.title"). Dotted-path
    traversal here would split "extension.title" into data["extension"]["title"],
    which fails because the key is actually a flat top-level entry. Use
    json.loads() + .get(key) directly in vsc_name.py for NLS lookups.
    """
    if not file.is_file():
        return default
    if not key:
        return default
    try:
        data: Any = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return default
    parts = key.split(".")
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return str(cur) if cur is not None else default

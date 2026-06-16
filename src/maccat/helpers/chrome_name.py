from __future__ import annotations

import json
from pathlib import Path

from maccat.helpers.json_io import json_get


def chrome_ext_name(manifest_path: Path) -> str:
    """
    Resolve Chrome extension display name from manifest.json.

    Handles __MSG_<key>__ placeholder names via case-insensitive lookup in
    _locales/<default_locale>/messages.json. Returns ext_id (grandparent dir
    basename) as fallback — never blank, never raw placeholder.

    Mirrors the fallback chain from update-list.sh:1148-1214 (chrome_ext_name):
      1. Plain name → return name (or ext_id if empty)
      2. __MSG_key__ → look in _locales/<locale>/messages.json (case-insensitive)
      3. messages.json not found → return ext_id
      4. Key absent in messages.json → return ext_id
      5. Key found → return resolved message string
    """
    ext_id = manifest_path.parent.parent.name  # grandparent of manifest.json is the 32-char ID

    name = json_get(manifest_path, "name")

    # Plain name — most common case (zsh: [[ "$name" != __MSG_?*__ ]])
    # len(name) > len("__MSG__") ensures at least one char between prefix and suffix
    if not (name.startswith("__MSG_") and name.endswith("__") and len(name) > len("__MSG__")):
        return name if name else ext_id

    # Extract key: strip __MSG_ prefix and __ suffix
    msg_key = name[len("__MSG_") : -len("__")]

    locale = json_get(manifest_path, "default_locale") or "en"
    messages_file = manifest_path.parent / "_locales" / locale / "messages.json"

    if not messages_file.is_file():
        return ext_id

    try:
        messages = json.loads(messages_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return ext_id

    # A messages.json that is valid JSON but not an object (array, string,
    # number, ...) has no .items(). The zsh reference routes this through
    # `jq ... 2>/dev/null`, which yields nothing and degrades to ext_id —
    # so we must NOT let messages.items() raise AttributeError and abort the
    # entire catalog run. (See REVIEW.md CR-01 / graceful-degradation constraint.)
    if not isinstance(messages, dict):
        return ext_id

    # Case-insensitive lookup mirroring the zsh reference
    #   jq 'to_entries[] | select(.key | ascii_downcase == $k) | .value.message' | head -1
    #
    # Two parity details:
    #   1. head -1 keeps the FIRST case-insensitive match in file (JSON) order.
    #      A lowercase-keyed dict comprehension would keep the LAST colliding
    #      key, diverging on case-colliding keys. Iterate in insertion order
    #      (== jq input order) and stop at the first match.
    #   2. .value.message must be a plain string. A non-string message would
    #      make jq -r emit multi-line JSON whose first line head -1 captures;
    #      str(value) cannot reproduce that, so degrade to ext_id instead of
    #      emitting a Python repr. The first match wins even if unusable.
    # (See REVIEW.md WR-02 / byte-parity constraint.)
    key_lower = msg_key.lower()
    for k, v in messages.items():  # insertion order == jq input order
        if k.lower() == key_lower:
            if isinstance(v, dict):
                resolved = v.get("message", "")
                if isinstance(resolved, str) and resolved:
                    return resolved
            return ext_id  # first match wins, even if unusable

    return ext_id

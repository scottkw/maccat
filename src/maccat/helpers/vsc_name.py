from __future__ import annotations

import json
from pathlib import Path

from maccat.helpers.json_io import json_get


def resolve_vsc_ext_name(pkg_json: Path, ext_id: str) -> str:
    """
    Resolve VS Code / Cursor extension display name via NLS placeholder resolution.

    Returns ext_id as fallback — never blank, never raw %key% placeholder.

    Mirrors the fallback chain from update-list.sh:1316-1367 (resolve_vsc_ext_name):
      1. No displayName → return ext_id
      2. Plain displayName (no %%) → return displayName
      3. %key% placeholder → look in package.nls.json (flat key lookup)
      4. package.nls.json not found → return ext_id
      5. Key absent in NLS file → return ext_id
      6. Key found → return resolved string

    CRITICAL: NLS lookup uses json.loads().get(nls_key) directly — NOT json_get().
    package.nls.json stores flat keys that may contain literal dots (e.g.
    "extension.title"). json_get's dotted-path traversal would split that key
    and fail to find it. Use direct .get() only (see RESEARCH.md Pitfall 3).
    """
    dn = json_get(pkg_json, "displayName")
    if not dn:
        return ext_id

    # Plain string — most extensions (zsh: [[ "$dn" != %?*% ]])
    # len(dn) > 2 ensures at least one char between the two % characters
    if not (dn.startswith("%") and dn.endswith("%") and len(dn) > 2):
        return dn

    nls_key = dn[1:-1]  # strip leading % and trailing %
    nls_file = pkg_json.parent / "package.nls.json"

    if not nls_file.is_file():
        return ext_id

    try:
        nls = json.loads(nls_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return ext_id

    # A package.nls.json that is valid JSON but not an object (array, string,
    # number, ...) has no .get(). The zsh reference uses `jq '.[$k] // ""'
    # 2>/dev/null`, which degrades to ext_id — so we must NOT let nls.get()
    # raise AttributeError and abort the entire catalog run.
    # (See REVIEW.md CR-02 / graceful-degradation constraint.)
    if not isinstance(nls, dict):
        return ext_id

    # FLAT key lookup — .get(nls_key) not json_get dotted traversal
    # Keys like "extension.title" are top-level flat keys, not nested paths
    #
    # NLS values are meant to be flat strings. The VS Code NLS v2 form stores
    # an object ({"message": "...", "comment": [...]}) for a key. The zsh
    # reference (`jq -r '.[$k] // ""'`) emits pretty-printed multi-line JSON for
    # such a value, which str(dict) would NOT reproduce (it gives a Python dict
    # repr). Rather than emit a divergent repr, degrade a non-string (or empty)
    # resolved value to ext_id — only a plain string is a usable display name.
    # (See REVIEW.md WR-01 / byte-parity constraint.)
    resolved = nls.get(nls_key, "")
    if not isinstance(resolved, str) or not resolved:
        return ext_id
    return resolved

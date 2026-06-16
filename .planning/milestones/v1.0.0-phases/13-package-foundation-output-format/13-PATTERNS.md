# Phase 13: Package Foundation + Output Format - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 12 (new — no existing Python in repo)
**Analogs found:** 12 / 12 (all from zsh reference; Python codebase does not yet exist)

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `pyproject.toml` | config | — | `update-list.sh` lines 1–45 (project metadata conventions) | config-match |
| `.python-version` | config | — | `update-list.sh` line 1 shebang (interpreter pin) | config-match |
| `src/maccat/__init__.py` | package root | — | `update-list.sh` lines 1–45 (version constant pattern) | role-match |
| `src/maccat/__main__.py` | entrypoint | request-response | `update-list.sh` lines 1–55 (interpreter guard + main orchestration) | role-match |
| `src/maccat/catalog/__init__.py` | package init | — | zsh sub-section structure | structural |
| `src/maccat/catalog/format.py` | utility | transform | `update-list.sh:1243–1297` (`emit_item`, `flush_section`) | exact |
| `src/maccat/catalog/writer.py` | utility | file-I/O | `update-list.sh:1075–1078` (`write_section`) + output file handling | exact |
| `src/maccat/helpers/__init__.py` | package init | — | zsh helper function grouping | structural |
| `src/maccat/helpers/json_io.py` | utility | file-I/O | `update-list.sh:1099–1121` (`json_get`) | exact |
| `src/maccat/helpers/chrome_name.py` | utility | transform | `update-list.sh:1148–1214` (`chrome_ext_name`) | exact |
| `src/maccat/helpers/vsc_name.py` | utility | transform | `update-list.sh:1316–1367` (`resolve_vsc_ext_name`) | exact |
| `tests/test_format.py` | test | — | `update-list.sh:1243–1297` (behavior spec for emit_item + flush_section) | behavior-match |
| `tests/test_helpers.py` | test | — | `update-list.sh:1099–1367` (behavior spec for json_get + name helpers) | behavior-match |
| `tests/test_writer.py` | test | — | `update-list.sh:1075–1078` + hex dump (byte-level spec) | behavior-match |
| `tests/conftest.py` | test config | — | pytest conventions | role-match |

---

## Pattern Assignments

### `pyproject.toml` (config)

**Analog:** `update-list.sh` lines 40–55 (global constants block)

**Project metadata pattern** — name is locked to `maccat`; zero runtime deps; build backend `hatchling`:
```toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "maccat"
version = "1.0.0"
description = "Catalog every piece of software on your Mac — apps, extensions, plugins, MCP servers."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
# No [project.dependencies] — zero runtime deps; stdlib only

[project.scripts]
maccat = "maccat.__main__:main"

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "ruff>=0.15",
    "mypy>=1.10",
]

[tool.hatchling.build.targets.wheel]
packages = ["src/maccat"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
src = ["src"]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
strict = true
python_version = "3.11"
```

**Key constraints:**
- `requires-python = ">=3.11"` — matches PKG-02 version floor
- No `[project.dependencies]` section — PKG-01 stdlib-only enforcement
- `packages = ["src/maccat"]` — PEP 517 `src/` layout; zipapp-compatible (Phase 16 can pass `src/maccat` directly to `zipapp`)

---

### `src/maccat/__init__.py` (package root)

**Analog:** `update-list.sh` lines 40–45 (global constants block)

**Pattern:** Single `__version__` constant; no imports; no side effects.

```python
# src/maccat/__init__.py
"""maccat — Mac software catalog generator."""

__version__ = "1.0.0"
```

**Key constraint:** Must not import from sub-packages at module level (circular import risk when `__main__.py` guards before importing `maccat.*`).

---

### `src/maccat/__main__.py` (entrypoint)

**Analog:** `update-list.sh` lines 1–55 (shebang + interpreter constraint + main block orchestration)

**Version guard pattern** (PKG-02) — `import sys` FIRST; guard fires before any `maccat.*` import:

```python
# src/maccat/__main__.py
# VERSION GUARD — must be first executable code; no package imports before this check
import sys

if sys.version_info < (3, 11):
    sys.exit(
        f"maccat requires Python 3.11 or later.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.\n"
        f"\n"
        f"Install a supported version:\n"
        f"  Homebrew: brew install python@3.11\n"
        f"  Direct:   https://python.org/downloads/\n"
        f"\n"
        f"Note: /usr/bin/python3 on macOS is Python 3.9 (EOL). Use Homebrew Python."
    )

# Only import from the package AFTER the version check
def main() -> None:
    from maccat.cli import run   # Phase 16
    run()

if __name__ == "__main__":
    main()
```

**Key constraints:**
- `sys.exit(str)` — prints to stderr + exits 1 in one call; never use `print()` + `sys.exit(1)` separately
- All `from maccat.*` imports must be INSIDE `main()` or deferred functions, never at module top level
- Phase 13 stub: `main()` body can just `pass` or print a placeholder; the structure must be correct

---

### `src/maccat/catalog/format.py` (utility, transform)

**Analog:** `update-list.sh:1243–1297` (`emit_item` + `flush_section`)

**Imports pattern:**
```python
from __future__ import annotations

import os
import subprocess
```

**`emit_item` core pattern** — direct Python translation of `update-list.sh:1243–1269`:

Zsh reference (`update-list.sh:1243–1269`):
```zsh
emit_item() {
    local name="$1"
    local version="$2"
    local id="$3"
    local line=""

    # Name unresolvable: use ID as name and suppress bracket duplication
    if [[ -z "$name" && -n "$id" ]]; then
        name="$id"
        id=""
    fi

    # Build line per FMT-01 rules
    if [[ -n "$name" && -n "$version" && -n "$id" ]]; then
        line="${name} (${version}) [${id}]"
    elif [[ -n "$name" && -n "$version" ]]; then
        line="${name} (${version})"
    elif [[ -n "$name" && -n "$id" ]]; then
        line="${name} [${id}]"
    elif [[ -n "$name" ]]; then
        line="$name"
    else
        return  # all fields empty — nothing to emit
    fi

    _section_lines+=("$line")
}
```

Python translation:
```python
def emit_item(name: str, version: str, id_: str) -> str | None:
    """
    FMT-01 degradation rules. Returns None for all-empty input — caller skips None results.

    name + version + id  →  "name (version) [id]"
    name + version       →  "name (version)"
    name + id            →  "name [id]"
    name only            →  "name"
    id only (no name)    →  "id"           (id promoted; brackets suppressed)
    id + version         →  "id (version)" (id promoted; brackets suppressed)
    all empty            →  None
    """
    if not name and id_:
        name, id_ = id_, ""   # id-as-name: suppress bracket duplication
    if name and version and id_:
        return f"{name} ({version}) [{id_}]"
    elif name and version:
        return f"{name} ({version})"
    elif name and id_:
        return f"{name} [{id_}]"
    elif name:
        return name
    return None
```

**`flush_section` core pattern** — direct Python translation of `update-list.sh:1290–1297`:

Zsh reference (`update-list.sh:1290–1297`):
```zsh
flush_section() {
    if [[ ${#_section_lines[@]} -eq 0 ]]; then
        echo "  (none found)" >> "$OUTPUT_FILE"
    else
        printf "%s\n" "${_section_lines[@]}" | LC_ALL=C sort -f -u >> "$OUTPUT_FILE"
    fi
    _section_lines=()
}
```

Python translation:
```python
def flush_section(lines: list[str]) -> list[str]:
    """
    Sort + dedup via LC_ALL=C sort -f -u. Returns ['  (none found)'] if empty.

    NEVER use Python sorted() — it diverges from LC_ALL=C sort -f for mixed-case
    and non-ASCII names. The subprocess call is mandatory for byte parity.
    """
    if not lines:
        return ["  (none found)"]
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-f", "-u"],
        input="\n".join(lines) + "\n",   # mirrors: printf "%s\n" "${lines[@]}"
        capture_output=True,
        text=True,
        env=env,
    )
    # rstrip("\n").split("\n") → no trailing empty string; matches zsh output exactly
    return result.stdout.rstrip("\n").split("\n")
```

**`version_sort_tail` pattern** (for Chrome version directory selection, CAT-03):

Zsh reference (`update-list.sh:2121`):
```zsh
ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | grep -E '^[0-9]' | sort -V | tail -1)
```

Python translation:
```python
def version_sort_tail(candidates: list[str]) -> str | None:
    """Return highest version string using sort -V (numeric version sort, not lexicographic)."""
    if not candidates:
        return None
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-V"],
        input="\n".join(candidates) + "\n",
        capture_output=True,
        text=True,
        env=env,
    )
    lines = result.stdout.rstrip("\n").split("\n")
    return lines[-1] if lines and lines[-1] else None
```

**Critical constraints for `format.py`:**
- `subprocess.run(["sort", ...], shell=False)` — shell=False is the default; never use shell=True (no shell injection risk; also matches security note in RESEARCH.md)
- Empty section writes two-space prefix: `"  (none found)"` — verified from `update-list.sh:1292`
- `flush_section` returns a list of strings WITHOUT trailing newlines; `write_lines` (in writer.py) adds `\n` per line

---

### `src/maccat/catalog/writer.py` (utility, file-I/O)

**Analog:** `update-list.sh:1075–1078` (`write_section`) + global `OUTPUT_FILE` append pattern

**`write_section` reference** (`update-list.sh:1075–1078`):
```zsh
write_section() {
    echo "\n$1" >> "$OUTPUT_FILE"
    echo "------------------------------------" >> "$OUTPUT_FILE"
}
```

In zsh, `echo "\n$1"` emits: `0x0a` + title bytes + `0x0a`. The separator is exactly 36 ASCII dashes.

**Byte-exact output for `write_section("Homebrew Packages")`:**
```
0a 48 6f 6d 65 62 72 65 77 20 50 61 63 6b 61 67
65 73 0a 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 0a
```
(Verified from real catalog file `mac-software-list-[computer-one.local]-20260612130331.txt`)

**Python `CatalogWriter` pattern:**
```python
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType


class CatalogWriter:
    """
    Context manager that writes a catalog file atomically (tmp + rename).
    Mirrors the global OUTPUT_FILE append pattern in update-list.sh.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fh = None  # set in __enter__
        self._tmp_path: Path | None = None

    def __enter__(self) -> "CatalogWriter":
        fd, tmp = tempfile.mkstemp(
            dir=self._path.parent, prefix=".maccat-", suffix=".tmp"
        )
        self._tmp_path = Path(tmp)
        self._fh = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._fh:
            self._fh.close()
        if exc_type is None and self._tmp_path:
            self._tmp_path.rename(self._path)
        elif self._tmp_path and self._tmp_path.exists():
            self._tmp_path.unlink()

    def write_section(self, title: str) -> None:
        """
        Byte-exact equivalent of update-list.sh write_section().
        Emits: \n + title + \n + ("-" * 36) + \n
        The leading \n produces the blank line between sections.
        """
        assert self._fh is not None
        self._fh.write(f"\n{title}\n")
        self._fh.write("-" * 36 + "\n")

    def write_lines(self, lines: list[str]) -> None:
        """Append sorted lines (from flush_section) — each line gets exactly one trailing \n."""
        assert self._fh is not None
        for line in lines:
            self._fh.write(line + "\n")
```

**Critical constraints:**
- Separator is `"-" * 36` — exactly 36 dashes, `0x2d × 36`. Never use a different count.
- `newline="\n"` in `open()` — prevents `\r\n` on any non-macOS run.
- Atomic write via `tempfile.mkstemp` + `rename` — prevents partial catalog on crash.
- `write_lines` adds `\n` per line; `flush_section` returns lines WITHOUT trailing newlines; these two are the only `\n` sources for item lines.
- The file STARTS with `0x0a` because `write_section` is the first write call (leading `\n`).

**Section boundary invariant:**
```
...last_item_of_prev_section\n   ← from write_lines
\nNext Section Title\n            ← from write_section (leading \n = blank line)
------------------------------------\n
```
ONE blank line between sections. No extra `\n` anywhere else.

---

### `src/maccat/helpers/json_io.py` (utility, file-I/O)

**Analog:** `update-list.sh:1099–1121` (`json_get`)

**Zsh reference** (`update-list.sh:1099–1121`):
```zsh
json_get() {
    local file="$1"
    local key="$2"
    local value=""

    [[ -f "$file" ]] || { echo ""; return; }
    [[ -n "$key" ]] || { echo ""; return; }

    if command -v jq &>/dev/null; then
        value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null) || value=""
    else
        value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
    fi

    echo "$value"
}
```

**Python translation** — replaces the jq/plutil subprocess chain entirely with `json.loads()`:
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_get(file: Path, key: str, default: str = "") -> str:
    """
    Extract a scalar value from a JSON file by dotted key path.
    Returns default on any error (missing file, parse error, missing key, wrong type).
    Never raises. Mirrors the zsh json_get contract exactly.

    IMPORTANT: Do NOT use this for VS Code NLS key lookup — package.nls.json uses
    flat keys that may contain literal dots (e.g. "extension.title"). Use
    json.loads() + .get(key) directly in vsc_name.py.
    """
    if not file.is_file():
        return default
    if not key:
        return default
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
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
```

**Key constraints:**
- Dotted-path traversal (`key.split(".")`) mirrors jq `getpath($k | split("."))` — correct for manifest.json, NOT for NLS files.
- `encoding="utf-8"` — extension manifests may contain non-ASCII in description fields.
- `except (json.JSONDecodeError, OSError, UnicodeDecodeError)` — mirrors `|| value=""` fallback in zsh; never raises.

---

### `src/maccat/helpers/chrome_name.py` (utility, transform)

**Analog:** `update-list.sh:1148–1214` (`chrome_ext_name`)

**Zsh reference** (`update-list.sh:1148–1214`):
```zsh
chrome_ext_name() {
    local manifest="$1"
    ...
    ext_id=$(basename "$(dirname "$(dirname "$manifest")")")
    name=$(json_get "$manifest" "name")

    if [[ "$name" != __MSG_?*__ ]]; then
        [[ -n "$name" ]] && echo "$name" || echo "$ext_id"
        return
    fi

    msg_key="${name#__MSG_}"
    msg_key="${msg_key%__}"

    locale=$(json_get "$manifest" "default_locale")
    [[ -z "$locale" ]] && locale="en"

    messages_file="$(dirname "$manifest")/_locales/${locale}/messages.json"
    [[ ! -f "$messages_file" ]] && { echo "$ext_id"; return; }

    # Case-insensitive lookup (jq: ascii_downcase on both key sides)
    resolved=$(jq -r --arg k "${msg_key:l}" \
        'to_entries[] | select(.key | ascii_downcase == $k) | .value.message' \
        "$messages_file" 2>/dev/null | head -1)
    [[ -n "$resolved" ]] && { echo "$resolved"; return; }

    echo "$ext_id"
}
```

**Python translation:**
```python
from __future__ import annotations

import json
from pathlib import Path

from maccat.helpers.json_io import json_get


def chrome_ext_name(manifest_path: Path) -> str:
    """
    Resolve Chrome extension display name from manifest.json.
    Handles __MSG_<key>__ placeholder names via case-insensitive messages.json lookup.
    Returns ext_id (grandparent dir basename) as fallback — never blank, never raw placeholder.
    """
    ext_id = manifest_path.parent.parent.name   # grandparent of manifest.json is the 32-char ID

    name = json_get(manifest_path, "name")

    # Plain name — most common case (zsh: [[ "$name" != __MSG_?*__ ]])
    if not (name.startswith("__MSG_") and name.endswith("__") and len(name) > len("__MSG__")):
        return name if name else ext_id

    # Extract key: strip __MSG_ prefix and __ suffix
    msg_key = name[len("__MSG_"):-len("__")]

    locale = json_get(manifest_path, "default_locale") or "en"
    messages_file = manifest_path.parent / "_locales" / locale / "messages.json"

    if not messages_file.is_file():
        return ext_id

    try:
        messages = json.loads(messages_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ext_id

    # Case-insensitive: build lowercase-keyed lookup dict (mirrors zsh ascii_downcase)
    lowered = {k.lower(): v for k, v in messages.items()}
    entry = lowered.get(msg_key.lower())
    if entry and isinstance(entry, dict):
        resolved = entry.get("message", "")
        if resolved:
            return resolved

    return ext_id
```

**Key constraints:**
- `manifest_path.parent.parent.name` — grandparent of manifest.json is the extension ID (not parent)
- Case-insensitive lookup via `{k.lower(): v for k, v in messages.items()}` — mirrors `ascii_downcase` in jq
- Chrome messages.json values are `{"message": "...", "description": "..."}` objects — must extract `.get("message")`
- `len(name) > len("__MSG__")` guards non-empty key (zsh `?*` pattern requires at least one char)

---

### `src/maccat/helpers/vsc_name.py` (utility, transform)

**Analog:** `update-list.sh:1316–1367` (`resolve_vsc_ext_name`)

**Zsh reference** (`update-list.sh:1316–1367`):
```zsh
resolve_vsc_ext_name() {
    local pkg_json="$1"
    local ext_id="$2"
    ...
    dn=$(json_get "$pkg_json" "displayName")
    [[ -z "$dn" ]] && { echo "$ext_id"; return; }

    if [[ "$dn" != %?*% ]]; then
        echo "$dn"; return
    fi

    nls_key="${dn#%}"
    nls_key="${nls_key%\%}"

    nls_file="$(dirname "$pkg_json")/package.nls.json"
    [[ ! -f "$nls_file" ]] && { echo "$ext_id"; return; }

    # jq: .[$k] treats key as flat top-level — NOT getpath (handles dots in key)
    resolved=$(jq -r --arg k "$nls_key" '.[$k] // ""' "$nls_file" 2>/dev/null)
    [[ -n "$resolved" ]] && { echo "$resolved"; return; }

    echo "$ext_id"
}
```

**Python translation:**
```python
from __future__ import annotations

import json
from pathlib import Path

from maccat.helpers.json_io import json_get


def resolve_vsc_ext_name(pkg_json: Path, ext_id: str) -> str:
    """
    Resolve VS Code / Cursor extension display name via NLS placeholder resolution.
    Returns ext_id as fallback — never blank, never raw %key%.

    CRITICAL: NLS lookup uses json.loads().get(key) directly — NOT json_get().
    package.nls.json has flat keys like "extension.title" that json_get's dotted-path
    traversal would misinterpret.
    """
    dn = json_get(pkg_json, "displayName")
    if not dn:
        return ext_id

    # Plain string — most extensions (zsh: [[ "$dn" != %?*% ]])
    if not (dn.startswith("%") and dn.endswith("%") and len(dn) > 2):
        return dn

    nls_key = dn[1:-1]   # strip leading % and trailing %
    nls_file = pkg_json.parent / "package.nls.json"

    if not nls_file.is_file():
        return ext_id

    try:
        nls = json.loads(nls_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ext_id

    # FLAT key lookup — .get(nls_key) not json_get dotted traversal
    # Keys like "extension.title" are top-level flat keys, not nested paths
    resolved = nls.get(nls_key, "")
    return resolved if resolved else ext_id
```

**Key constraints:**
- `nls.get(nls_key)` — flat lookup, NEVER `json_get(nls_file, nls_key)` (dotted-path split breaks keys containing literal dots)
- VS Code NLS values are plain strings, NOT `{"message": ...}` objects (unlike Chrome)
- `len(dn) > 2` ensures key is non-empty (zsh `?*` = at least 1 char between `%` and `%`)
- Case-sensitive: zsh uses the key exactly as extracted (`nls_key`) — no `.lower()` here

---

### `tests/conftest.py` (test config)

**Pattern:** Minimal conftest providing shared fixtures for path-based tests. No analog in existing codebase.

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_json(tmp_path: Path):
    """Factory fixture: write a dict as JSON to a temp file, return the Path."""
    def _write(data: dict, filename: str = "test.json") -> Path:
        p = tmp_path / filename
        p.write_text(json.dumps(data), encoding="utf-8")
        return p
    return _write
```

---

### `tests/test_format.py` (test)

**Pattern:** Unit tests for `emit_item` (pure function, no I/O) and `flush_section` (subprocess sort).

**FMT-01 cases to cover** (from `update-list.sh:1229–1236` docstring):
```
name + version + id  →  "name (version) [id]"
name + version       →  "name (version)"
name + id            →  "name [id]"
name only            →  "name"
id only (no name)    →  "id"
id + version         →  "id (version)"
all empty            →  None
```

**flush_section cases to cover:**
- Empty list → `["  (none found)"]`
- Mixed-case dedup: `["1password", "Bitwarden", "zed", "Adobe Acrobat", "bitwarden"]` → `["1password", "Adobe Acrobat", "Bitwarden", "zed"]`

---

### `tests/test_writer.py` (test)

**Pattern:** Byte-level verification of `CatalogWriter.write_section()` output.

**Key assertion:** After `write_section("Homebrew Packages")`, file bytes at position 0 must be:
```
0a 48 6f 6d 65 62 72 65 77 20 50 61 63 6b 61 67
65 73 0a 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 0a
```

**Section boundary assertion:** After `write_section` + `write_lines(sorted_items)` + `write_section`, file must contain exactly one blank line between sections (no double blank lines).

---

### `tests/test_helpers.py` (test)

**Pattern:** Unit tests for `json_get`, `chrome_ext_name`, and `resolve_vsc_ext_name`.

**json_get cases:**
- Missing file → `""`
- Empty key → `""`
- Nested key `"author.name"` → traversal
- Non-string leaf → `str(value)`
- Malformed JSON → `""`

**chrome_ext_name cases:**
- Plain name → returned as-is
- `__MSG_extName__` → resolved from `_locales/en/messages.json` (case-insensitive)
- Missing messages.json → returns ext_id
- Missing key in messages.json → returns ext_id

**resolve_vsc_ext_name cases:**
- Plain displayName → returned as-is
- `%extension.title%` → flat key lookup in `package.nls.json`
- Same key via `json_get` (dotted path) → empty string (demonstrates why flat lookup is required)
- Missing NLS file → returns ext_id

---

## Shared Patterns

### Error Handling (all helper modules)
**Source:** `update-list.sh:1105–1107` (guard + fallback pattern)
**Apply to:** All `helpers/*.py` and `catalog/format.py`

```python
# Pattern: return default on any error; never raise from utility functions
try:
    data = json.loads(file.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError, UnicodeDecodeError):
    return default
```

This mirrors the zsh pattern:
```zsh
[[ -f "$file" ]] || { echo ""; return; }
value=$(jq ... "$file" 2>/dev/null) || value=""
```

### Tool Availability Check
**Source:** `update-list.sh:59–63` (`command -v` pattern)
**Apply to:** Any future collector that probes for optional tools (Phase 15)

```zsh
# Zsh reference:
if command -v brew &>/dev/null; then
    ...
else
    echo "  WARNING: Homebrew not found." >> "$OUTPUT_FILE"
fi
```

Python equivalent (for Phase 15 reference):
```python
import shutil
if shutil.which("brew"):
    ...
else:
    writer.write_lines(["  WARNING: Homebrew not found."])
```

### subprocess Safety
**Source:** RESEARCH.md security domain note
**Apply to:** `catalog/format.py` (`flush_section`, `version_sort_tail`)

```python
# Always: shell=False (default), env override only LC_ALL
env = {**os.environ, "LC_ALL": "C"}
result = subprocess.run(
    ["sort", "-f", "-u"],   # list form, not string — no shell injection possible
    input=data,
    capture_output=True,
    text=True,
    env=env,
    # shell=False is the default; never set shell=True
)
```

### Python Conventions (CLAUDE.md)
**Apply to:** All `.py` files

- 4-space indentation
- `snake_case` functions and variables
- Type hints on all function signatures
- `from __future__ import annotations` at top of every module (enables `X | Y` union syntax on 3.10+ too, though 3.11+ is the floor)
- Docstrings on all public functions

---

## No Analog Found

No files in this phase lack an analog. All files map to either:
1. An exact zsh function in `update-list.sh` (format.py, writer.py, json_io.py, chrome_name.py, vsc_name.py), or
2. Standard Python project conventions (pyproject.toml, __init__.py, __main__.py, test files).

---

## Critical Anti-Patterns (do NOT copy these)

| Anti-Pattern | Where It Fails | Correct Pattern |
|---|---|---|
| `sorted(lines, key=str.casefold)` | `flush_section` | `subprocess.run(["sort", "-f", "-u"], env={"LC_ALL": "C"})` |
| `"-" * 34` or `"-" * 40` | `write_section` | `"-" * 36` (verified by hex dump) |
| `json_get(nls_file, "extension.title")` | `resolve_vsc_ext_name` | `nls_data.get("extension.title")` |
| Extra `\n` after `write_lines` | `CatalogWriter` | `write_section` provides the blank line; `write_lines` adds only one `\n` per item |
| `from maccat.catalog import ...` at top of `__main__.py` | `__main__.py` | All `maccat.*` imports inside `main()` body, after version guard |
| `shell=True` in subprocess | `flush_section` | `shell=False` (default); pass command as list |

---

## Metadata

**Analog search scope:** `update-list.sh` (primary reference, read sections 1075–1367, 2121); `.planning/codebase/CONVENTIONS.md`
**Files scanned:** 2 source files (no existing Python)
**Zsh functions extracted:** `write_section` (line 1075), `json_get` (line 1099), `chrome_ext_name` (line 1148), `emit_item` (line 1243), `flush_section` (line 1290), `resolve_vsc_ext_name` (line 1316)
**Pattern extraction date:** 2026-06-14

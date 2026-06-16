# Phase 13: Package Foundation + Output Format - Research

**Researched:** 2026-06-14
**Domain:** Python package skeleton + byte-exact output format layer (stdlib only, macOS)
**Confidence:** HIGH — all formatting claims verified against live zsh source + real catalog
files; all Python patterns verified by live execution.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (from PROJECT.md and CONTEXT.md)

- **Package name:** `maccat` — used as import name (`src/maccat/`, `import maccat`), CLI
  command, `.pyz` artifact name, and config dir (`~/.config/maccat/`). The prior research
  docs use `maclist`/`mac_software_list`; those names are stale and must NOT be used.
- **Layout:** `src/` layout — `src/maccat/` package directory (PEP 517); success criteria
  explicitly requires `python -c "import maccat"` to succeed.
- **Zero runtime deps:** Standard library only — no third-party packages in the runtime
  package. Phase 13 installs zero third-party packages at runtime.
- **Sort must shell out:** `flush_section()` MUST call `LC_ALL=C sort -f -u` via subprocess.
  Never Python `sorted()`. This is a requirement in both CONTEXT.md and ROADMAP.md success
  criteria.
- **Python 3.11+ floor:** The version guard runs before any `tomllib` or package imports.
- **zsh is the untouched parity reference:** `update-list.sh` is never modified. Every
  formatting decision is dictated by matching its output byte-for-byte.

### Claude's Discretion

All internal structure choices (module file names, class names, function signatures, type
annotations, file organisation within `src/maccat/`) are at Claude's discretion, constrained
by the byte-parity requirement and CLAUDE.md conventions (Python: 4 spaces, `snake_case`, type
hints, `black`/`ruff`/`mypy`; virtual environment mandatory).

### Deferred Ideas (OUT OF SCOPE for Phase 13)

- Config layer, `tomllib` usage — Phase 14
- Any collector — Phase 15
- Git operations, CLI wiring, zipapp packaging — Phase 16
- Parity test suite (golden fixtures) — Phase 17
- pipx / PyPI distribution — v1.1 (PKG-04)
- `tests/golden/` infrastructure (deferred from STATE.md pending todo — the scaffolding may
  be created here but the golden fixtures are Phase 17's job)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-01 | Zero third-party runtime deps (stdlib only) | Verified: all Phase 13 modules use only `json`, `subprocess`, `os`, `pathlib`, `sys`, `re` — no pip installs at runtime |
| PKG-02 | Python 3.11+ with fail-fast version guard that never hangs on macOS CLT dialog | Verified: `sys.version_info` guard in `__main__.py` before any `tomllib`/package imports; `#!/usr/bin/env python3` shebang avoids `/usr/bin/python3` stub |
| CAT-02 | `name (version) [id]` format with FMT-01 degradation rules | Verified: exact conditionals extracted from `emit_item` (update-list.sh:1243–1269) |
| CAT-03 | Shell out to `LC_ALL=C sort -f -u` (and `sort -V` for Chrome) — never Python `sorted()` | Verified: subprocess invocation pattern confirmed working; `sort -V` also subprocess |
| CAT-04 | Chrome `__MSG_…__` and VS Code `%nls%` placeholder resolution with ID/displayName fallbacks | Verified: exact fallback chains extracted from `chrome_ext_name` (line 1148) and `resolve_vsc_ext_name` (line 1316) |
| CAT-07 | Section titles, order, and `------` separators byte-identical to zsh catalog | Verified: 36 ASCII dashes (0x2d × 36); exact byte layout captured from real catalog file |

</phase_requirements>

---

## Summary

Phase 13 creates the byte-exact foundation that every downstream phase builds on. The zsh
reference (`update-list.sh`) is the unambiguous specification: three key functions —
`write_section`, `emit_item`, and `flush_section` — plus the `chrome_ext_name` and
`resolve_vsc_ext_name` helpers define the complete output contract. All of these have been read
from the zsh source and their exact byte behavior confirmed against live catalog files.

The central implementation choices are:

1. The `flush_section` must shell out to `LC_ALL=C sort -f -u` via `subprocess.run`. Python
   `sorted()` diverges for mixed-case names (confirmed by live testing). This is the one
   subprocess call in the format layer — everything else is pure Python.

2. `CatalogWriter.write_section()` must emit exactly `\n{title}\n{"–"*36}\n` — verified byte
   by byte against real catalog files. The leading `\n` produces the blank line between
   sections; the separator is exactly 36 ASCII dashes (`-`, 0x2d).

3. The package skeleton uses `src/maccat/` layout with a `pyproject.toml` that locks the name
   to `maccat` and canonicalises `requires-python = ">=3.11"`. The `__main__.py` version guard
   fires before any package-internal imports.

4. The name-resolution helpers (`chrome_ext_name`, `resolve_vsc_ext_name`) are pure Python
   replacements for the zsh `json_get` + `jq/plutil` chain. They work directly with `json`
   module — no subprocess.

**Primary recommendation:** Build in this order: `pyproject.toml` → `src/maccat/__init__.py`
+ `__main__.py` (version guard only) → `src/maccat/catalog/format.py` (`emit_item`,
`flush_section`) → `src/maccat/catalog/writer.py` (`CatalogWriter`) → `src/maccat/helpers/`
(`json_get`, `chrome_ext_name`, `resolve_vsc_ext_name`) → pytest smoke tests. Each layer is
independently testable before the next is built.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Package import, version guard | Python package (`__main__.py`) | — | Entry point; version check must fire before any stdlib 3.11+ import |
| Section header formatting | `catalog/format.py` or `catalog/writer.py` | — | Pure formatting; no collectors depend on I/O yet |
| Item line formatting (FMT-01) | `catalog/format.py` | — | Pure function; zero I/O; independently testable |
| Sort + dedup via LC_ALL=C | `catalog/format.py` (subprocess shell-out) | OS `sort` binary | subprocess call to `/usr/bin/sort` with LC_ALL=C; not replaceable with Python sorted() |
| Output file write (atomic) | `catalog/writer.py` | — | CatalogWriter context manager; tmp+rename guarantees no partial files |
| Chrome `__MSG_` resolution | `helpers/chrome_name.py` | `helpers/json_io.py` | Pure Python JSON; no subprocess; case-insensitive dict lookup |
| VS Code `%nls%` resolution | `helpers/vsc_name.py` | `helpers/json_io.py` | Pure Python JSON; flat-key lookup (NOT dotted path) |
| JSON file extraction | `helpers/json_io.py` | — | Replaces jq+plutil chain entirely; `json.loads()` is always available |

---

## Standard Stack

### Core (runtime — all stdlib)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `subprocess` (stdlib) | — | `LC_ALL=C sort -f -u` and `sort -V` shell-outs | Only way to produce byte-identical sort output to zsh reference |
| `json` (stdlib) | — | Parse manifest.json / extensions.json / messages.json | Direct replacement for jq + plutil chain; always reliable |
| `pathlib` (stdlib) | — | All path operations | Cleaner than `os.path`; available since 3.4 |
| `os` (stdlib) | — | `os.environ`, `os.fdopen`, `tempfile` interop | Needed for env override in subprocess calls |
| `sys` (stdlib) | — | `sys.version_info` version guard, `sys.exit` | Must be imported before any other maccat module |
| `re` (stdlib) | — | VS Code `%nls%` placeholder detection | Pattern is `%?*%` — simple regex suffices |

### Dev / test only (NOT in runtime package)

| Library | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=9.0 (current: 9.1.0) [VERIFIED: pip registry] | Test runner |
| `ruff` | >=0.15 (current: 0.15.17) [VERIFIED: pip registry] | Lint + format (replaces black+isort+flake8) |
| `mypy` | >=1.10 [ASSUMED] | Type checking |
| `uv` | >=0.5 [ASSUMED] | Virtual env management (preferred per CLAUDE.md) |

### No packages to audit for legitimacy

Phase 13 installs zero third-party runtime packages. The dev tools (pytest, ruff, mypy, uv) are
installed into a development venv only — they never ship inside the `.pyz` artifact.

---

## Package Legitimacy Audit

No third-party packages are installed by Phase 13. This section is N/A.

**Packages removed due to slopcheck verdict:** none
**Packages flagged:** none

---

## Architecture Patterns

### System Architecture Diagram

```
python -c "import maccat"
  │
  └─ src/maccat/__init__.py (package root; exposes version)

python3 maccat.pyz  (future: Phase 16)
  │
  └─ src/maccat/__main__.py
       │
       1. sys.version_info check (< 3.11 → clear error + exit)
       2. from maccat.cli import main   [Phase 16]
       └─ main()

CatalogWriter (context manager)
  │
  ├─ write_section(title)
  │     └─ writes: \n + title + \n + "----"×36 + \n
  │
  └─ write_lines(sorted_lines)
        └─ each line + \n

flush_section(lines: list[str]) → list[str]
  │
  ├─ empty input → ["  (none found)"]
  │
  └─ non-empty → subprocess.run(["sort", "-f", "-u"], env=LC_ALL=C)
                       └─ stdout split back to list

emit_item(name, version, id_) → str | None
  │  FMT-01 rules (pure function)
  └─ returns formatted line or None

helpers/json_get(file, key) → str
  │
  └─ json.loads() with dotted-key path traversal; returns "" on any error

helpers/chrome_ext_name(manifest_path) → str
  │
  ├─ read name from manifest.json via json_get
  ├─ if __MSG_<key>__: lookup in _locales/<default_locale>/messages.json
  │     └─ case-insensitive: {k.lower(): v for k, v in messages.items()}
  └─ fallback chain: resolved name → ext_id (grandparent dir basename)

helpers/resolve_vsc_ext_name(pkg_json, ext_id) → str
  │
  ├─ read displayName from package.json via json_get
  ├─ if %<key>%: lookup in package.nls.json (FLAT key, NOT dotted)
  │     └─ .get(nls_key, "") — case-sensitive (zsh uses exact key)
  └─ fallback chain: resolved name → ext_id
```

### Recommended Project Structure

```
mac-software-list/          ← existing repo root
├── update-list.sh          ← untouched zsh reference
├── machine-labels.tsv      ← existing
├── personal/               ← existing catalog folders
├── office/                 ← existing catalog folders
│
├── src/
│   └── maccat/             ← NEW: Python package (Phase 13)
│       ├── __init__.py     ← __version__ = "1.0.0"
│       ├── __main__.py     ← version guard (Phase 13); main() wiring (Phase 16)
│       ├── catalog/
│       │   ├── __init__.py
│       │   ├── format.py   ← emit_item(), flush_section()
│       │   └── writer.py   ← CatalogWriter (context manager)
│       └── helpers/
│           ├── __init__.py
│           ├── json_io.py      ← json_get()
│           ├── chrome_name.py  ← chrome_ext_name()
│           └── vsc_name.py     ← resolve_vsc_ext_name()
│
├── tests/                  ← NEW (Phase 13 scaffolds this)
│   ├── __init__.py
│   ├── conftest.py
│   ├── golden/             ← fixture dir (populated Phase 17)
│   └── test_format.py      ← emit_item + flush_section unit tests
│   └── test_helpers.py     ← json_get + chrome_ext_name + vsc_name unit tests
│   └── test_writer.py      ← CatalogWriter byte-level tests
│
├── pyproject.toml          ← NEW (Phase 13)
└── .python-version         ← optional: "3.11" pin for pyenv users
```

**Key layout decisions:**
- `src/` layout (PEP 517): prevents accidental imports of the uninstalled package during test runs
- `catalog/` sub-package: separates format (pure, no I/O) from writer (I/O); `format.py` is
  trivially unit-testable with zero mocking
- `helpers/` as a sibling to `catalog/`: shared by multiple future collectors; avoids circular
  imports if placed inside `catalog/`
- Phase 16 fills in `cli.py`, `config.py`, `gitops.py`, etc. — the structure above only shows
  Phase 13 deliverables

---

## Exact Byte Format (Critical Reference)

### Section header

From `update-list.sh:1075–1078`:
```zsh
write_section() {
    echo "\n$1" >> "$OUTPUT_FILE"
    echo "------------------------------------" >> "$OUTPUT_FILE"
}
```

In zsh, `echo "\n$1"` emits: `0x0a` + title bytes + `0x0a` (zsh `echo` interprets `\n`).
Then `echo "----..."` emits: 36 × `0x2d` + `0x0a`.

**Exact byte output of write_section("Homebrew Packages"):**
```
0a 48 6f 6d 65 62 72 65 77 20 50 61 63 6b 61 67
65 73 0a 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d 2d
2d 2d 2d 2d 2d 2d 2d 0a
```

Verified against real catalog file (`xxd` of bytes 28–84 in the 20260612 catalog).

**Python `write_section` equivalent:**
```python
def write_section(self, title: str) -> None:
    self._fh.write(f"\n{title}\n")
    self._fh.write("-" * 36 + "\n")
```

**Key facts:**
- Separator is **exactly 36 ASCII dashes** (U+002D, `0x2d`). Verified by counting from hex dump.
- The leading `\n` in `write_section` is what produces the blank line between sections.
- The file STARTS with `0x0a` because `write_section` is the very first write call.
- Between two sections: last item's trailing `\n` (from sort output) + next section's leading `\n`
  from `write_section` = one blank line visible in the file.

### flush_section output

From `update-list.sh:1290–1296`:
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

**Key facts:**
- Empty buffer writes: `  (none found)\n` (TWO spaces before the parenthesis — verified from zsh source)
- Non-empty: `printf "%s\n"` ensures each line gets exactly one trailing `\n` before pipe to sort
- `LC_ALL=C sort -f -u` produces: sorted lines each ending with `\n`, NO trailing blank line
- The `sort` output ends with `\n` on the last item (confirmed by live subprocess test)
- `flush_section` does NOT add a trailing `\n` after the last line — the next `write_section`
  call adds the leading `\n` separator

**Verified Python equivalent:**
```python
def flush_section(lines: list[str]) -> list[str]:
    """Sort + dedup via LC_ALL=C sort -f -u. Returns ['  (none found)'] if empty."""
    if not lines:
        return ["  (none found)"]
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-f", "-u"],
        input="\n".join(lines) + "\n",   # printf "%s\n" equivalent
        capture_output=True,
        text=True,
        env=env,
    )
    # rstrip("\n").split("\n") matches the zsh output: no trailing empty string
    return result.stdout.rstrip("\n").split("\n")
```

Confirmed working by live test: `["1password", "Bitwarden", "zed", "Adobe Acrobat", "bitwarden"]`
→ `["1password", "Adobe Acrobat", "Bitwarden", "zed"]` (bitwarden deduped with Bitwarden).

### CatalogWriter.write_lines

The format layer returns sorted lines from `flush_section`. The writer appends each line + `\n`:
```python
def write_lines(self, lines: list[str]) -> None:
    for line in lines:
        self._fh.write(line + "\n")
```

**Full section body for empty section:**
```
\nSection Title\n------------------------------------\n  (none found)\n
```

**Full section body for non-empty section (e.g. items ["1password","Bitwarden","zed"]):**
```
\nSection Title\n------------------------------------\n1password\nBitwarden\nzed\n
```

### emit_item FMT-01 rules

From `update-list.sh:1243–1269` (verified by live zsh execution):

```
name + version + id  →  "name (version) [id]"
name + version       →  "name (version)"
name + id            →  "name [id]"
name only            →  "name"
id only (name empty) →  "id"          ← id promoted to name; brackets suppressed
id + version (name empty) → "id (version)"  ← id promoted; brackets suppressed
all empty            →  nothing emitted (function returns; nothing appended)
```

**Python implementation:**
```python
def emit_item(name: str, version: str, id_: str) -> str | None:
    """FMT-01 rules. Returns None for all-empty input — caller skips None results."""
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

---

## Section Titles and Order (CAT-07)

Canonical section titles extracted from all `write_section` calls in `update-list.sh`:

| # | Section Title | zsh source line |
|---|--------------|----------------|
| 1 | `Installed Mac Software List` | 2226 |
| 2 | `Homebrew Packages` | 2233 |
| 3 | `App Store Applications` | 2249 |
| 4 | `Setapp Applications` | 2267 |
| 5 | `Web-installed Applications` | 2281 |
| 6 | `Claude Code Plugins` | 1598 |
| 7 | `Claude Code MCP Servers` | 1642 |
| 8 | `Claude Code Skills & Agents` | 1697 |
| 9 | `Codex MCP Servers` | 1752 |
| 10 | `OpenCode Plugins` | 1806 |
| 11 | `OpenCode MCP Servers` | 1865 |
| 12 | `OpenCode Agents` | 1934 |
| 13 | `Gemini CLI Extensions` | 1974 |
| 14 | `Gemini CLI MCP Servers` | 2020 |
| 15 | `VS Code Extensions` | 1393 |
| 16 | `Cursor Extensions` | 1500 |
| 17 | `Google Chrome Extensions` | 2078 |
| 18 | `Firefox Extensions` | 2159 |

**Important note on Phase 13 scope:** Phase 13 only implements the format layer and name
resolution helpers. Sections 6–18 are produced by collectors (Phase 15). The section title
strings are defined here for reference and must be spelled exactly as shown (case, spaces,
ampersand in "Skills & Agents").

Sections 1–5 use direct file writes (not `emit_item`/`flush_section`) in the zsh script.
The Python collectors for these sections (Phase 15) will also use `CatalogWriter` directly.

---

## Chrome `__MSG_…__` Resolution (CAT-04)

From `update-list.sh:1148–1214`:

**Algorithm:**
1. Read `name` field from manifest.json via `json_get`
2. If `name` does NOT match `__MSG_?*__` pattern: return name (or ext_id if name is empty)
3. Extract key: strip `__MSG_` prefix and `__` suffix → `msg_key`
4. Read `default_locale` from manifest.json; default to `"en"` if absent
5. Construct messages file path: `<ext_version_dir>/_locales/<default_locale>/messages.json`
6. If messages file absent: return `ext_id`
7. **Case-insensitive key lookup:** zsh uses `${msg_key:l}` (lowercase) + jq `ascii_downcase`
8. Look up `messages[key.lower()].message` (Chrome messages.json value is `{message: "...", description: "..."}`)
9. If resolved: return resolved name
10. If not found: return `ext_id`

**Python implementation:**
```python
def chrome_ext_name(manifest_path: Path) -> str:
    """Resolve Chrome extension display name. Returns ext_id as fallback."""
    ext_id = manifest_path.parent.parent.name   # grandparent of manifest.json
    name = json_get(manifest_path, "name")

    if not name.startswith("__MSG_") or not name.endswith("__"):
        return name if name else ext_id

    msg_key = name[len("__MSG_"):-len("__")]
    locale = json_get(manifest_path, "default_locale") or "en"
    messages_file = manifest_path.parent / "_locales" / locale / "messages.json"

    if not messages_file.is_file():
        return ext_id

    try:
        messages = json.loads(messages_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ext_id

    # Case-insensitive: build lowercase-keyed lookup dict
    lowered = {k.lower(): v for k, v in messages.items()}
    entry = lowered.get(msg_key.lower())
    if entry and isinstance(entry, dict):
        resolved = entry.get("message", "")
        if resolved:
            return resolved

    return ext_id
```

**Pattern match:** `?*` in zsh glob = at least one character between `__MSG_` and `__`. The
Python equivalent is `len(name) > len("__MSG__")` (i.e., key is non-empty).

---

## VS Code `%nls%` Resolution (CAT-04)

From `update-list.sh:1316–1366`:

**Algorithm:**
1. Read `displayName` from package.json via `json_get`
2. If absent: return `ext_id`
3. If `displayName` does NOT match `%?*%` pattern: return `displayName` (most extensions)
4. Extract key: strip leading and trailing `%` → `nls_key`
5. Construct NLS file: `<ext_dir>/package.nls.json` (same directory as package.json)
6. If NLS file absent: return `ext_id`
7. **FLAT key lookup** (CRITICAL: NOT dotted path — keys may contain literal dots like
   `"extension.title"`)
8. `nls_data.get(nls_key, "")` — case-sensitive (zsh uses the key exactly as extracted)
9. If resolved: return resolved string
10. If not found: return `ext_id`

**Python implementation:**
```python
def resolve_vsc_ext_name(pkg_json: Path, ext_id: str) -> str:
    """Resolve VS Code/Cursor extension display name via NLS. Returns ext_id as fallback."""
    dn = json_get(pkg_json, "displayName")
    if not dn:
        return ext_id

    if not (dn.startswith("%") and dn.endswith("%") and len(dn) > 2):
        return dn   # plain string (most common case)

    nls_key = dn[1:-1]   # strip leading/trailing %
    nls_file = pkg_json.parent / "package.nls.json"

    if not nls_file.is_file():
        return ext_id

    try:
        nls = json.loads(nls_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ext_id

    # FLAT string values (not {message:...} objects like Chrome)
    # Keys may contain literal dots (e.g. "extension.title") — use .get(), NOT getpath
    resolved = nls.get(nls_key, "")
    return resolved if resolved else ext_id
```

**Critical difference from Chrome:** `package.nls.json` stores flat string values like
`{"extension.title": "My Extension"}`, NOT objects like `{"extName": {"message": "...", "description": "..."}}`.
The `json_get` dotted-key path traversal must NOT be used here. Direct `.get(nls_key)` only.

---

## json_get Helper

From `update-list.sh:1099–1121` (the Python replacement is simpler — no jq/plutil chain):

```python
# helpers/json_io.py
import json
from pathlib import Path
from typing import Any

def json_get(file: Path, key: str, default: str = "") -> str:
    """
    Extract a scalar value from a JSON file by dotted key path.
    Returns default on any error (missing file, parse error, missing key).
    Never raises. Mirrors the zsh json_get contract exactly.
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
        cur = cur.get(part, None)
        if cur is None:
            return default
    return str(cur) if cur is not None else default
```

**Note:** The VS Code NLS resolver must NOT use `json_get` for NLS lookups — it must call
`json.loads` directly and use `.get(nls_key)` to avoid the dotted-path split misinterpreting
literal dots in NLS keys like `"extension.title"`.

---

## pyproject.toml (Phase 13 creates this)

Per STATE.md pending todo: "Phase 13 planning: decide Python import package name and canonicalize
in pyproject.toml at the start."

The `maccat` name is locked in PROJECT.md. Create `pyproject.toml` at repo root in Phase 13:

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

**Note on PKG-03 (zipapp) compatibility:** The `src/maccat/` layout is directly usable as
the zipapp source directory in Phase 16:
```bash
python3 -m zipapp src/maccat -o dist/maccat.pyz -p "/usr/bin/env python3" \
    -m "maccat.__main__:main" -c
```
No structural change needed between Phase 13 and Phase 16.

---

## Python 3.11+ Version Guard (PKG-02)

The guard must be in `__main__.py` as the FIRST executable code — before any `import maccat.*`
statement, before `import tomllib`, before any other stdlib call that might behave differently
on 3.9 vs 3.11.

```python
# src/maccat/__main__.py
# VERSION GUARD — must be first; no package imports before this check
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

**Why `sys.exit(message)` and not `print` + `sys.exit(1)`:** `sys.exit(str)` prints to stderr
and exits with code 1 in one call — correct for user-facing error messages.

**The CLT dialog concern:** If a user on a clean macOS without CLT runs `python3 maccat.pyz`,
the shebang `#!/usr/bin/env python3` resolves to `/usr/bin/python3` (the CLT stub) IF no real
Python is in PATH. The stub will pop the GUI dialog — that behaviour is outside our control. The
documentation should tell users to install Homebrew Python first. The key thing Phase 13 ensures:
once Python 3 actually runs (any Python 3), the version guard fires immediately before any
blocking or complex work.

---

## sort -V for Chrome Version Directories (CAT-03)

From `update-list.sh:2121–2122`:
```zsh
ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | grep -E '^[0-9]' | sort -V | tail -1)
```

`sort -V` is version sort: numeric segments compared numerically. `14.0.0_0 > 9.0.0_0 > 2.10.0_0`.
Python lexicographic sort gets this wrong (`9 > 14` lexicographically).

**Python equivalent — shell out to `sort -V`:**
```python
import subprocess, os

def version_sort_tail(candidates: list[str]) -> str | None:
    """Return the highest version string using sort -V (numeric version sort)."""
    if not candidates:
        return None
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-V"],
        input="\n".join(candidates) + "\n",
        capture_output=True, text=True, env=env,
    )
    lines = result.stdout.rstrip("\n").split("\n")
    return lines[-1] if lines else None
```

This is used in the Chrome collector (Phase 15), but the helper belongs in `helpers/` or
`catalog/format.py` since it is a sort utility. Phase 13 can scaffold it.

**Alternative (pure Python):** Only use if subprocess is a concern for this specific call:
```python
import re
def _version_key(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.split(r'[._-]', s) if x.isdigit())

def version_sort_tail(candidates: list[str]) -> str | None:
    if not candidates:
        return None
    return max(candidates, key=_version_key)
```

Tested on `["2.0.0_0", "14.0.0_0", "3.5.1_0", "2026.5.1_0"]` — both approaches return
`"2026.5.1_0"`. The subprocess approach guarantees byte-identical selection to zsh.
**Recommendation: use subprocess for correctness; document pure-Python as fallback.**

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sort items by name (case-insensitive, dedup) | Python `sorted()` + `set()` | `subprocess.run(["sort", "-f", "-u"], env={"LC_ALL": "C"})` | Python sort diverges from `LC_ALL=C sort -f` for mixed-case, non-ASCII, punctuation |
| JSON file key extraction | Subprocess `jq` or `plutil` | `json.loads()` + dict traversal | Python has a built-in JSON parser; no subprocess needed; more reliable than the jq/plutil chain |
| NLS key lookup in package.nls.json | `json_get(nls_file, nls_key)` (dotted path) | `json.loads(...).get(nls_key)` (direct flat lookup) | Dotted-path split in `json_get` breaks keys with literal dots like `"extension.title"` |
| Version directory selection | Python `sorted(dirs, key=str)` | `sort -V` via subprocess (or `_version_key` tuple) | Lexicographic sort gets `9.x > 14.x` wrong |
| Atomic file write | `open(path, "w")` direct | `CatalogWriter` (tmp + rename) | Crash mid-write leaves partial catalog; git stages corrupt file |

---

## Common Pitfalls

### Pitfall 1: Python `sorted()` diverges from `LC_ALL=C sort -f -u`

**What goes wrong:** `sorted(lines, key=str.lower)` produces different output than `LC_ALL=C
sort -f -u` for mixed-case names. `A` and `a` sort differently under C locale vs Unicode locale.
The catalog will look plausible but fail byte-parity tests.

**Why it happens:** Developer uses Python sort for convenience; tests pass on ASCII-only fixtures.

**How to avoid:** Only use `subprocess.run(["sort", "-f", "-u"], env={..., "LC_ALL": "C"})`.
The zsh sort is the reference; the Python implementation must call the same binary.

**Warning signs:** Parity tests pass on simple fixtures but fail on real catalogs with
`1Password`, `Bitwarden`, etc.

### Pitfall 2: Wrong separator length

**What goes wrong:** Using 34 or 40 dashes instead of exactly 36.

**Why it happens:** Developer counts visually rather than reading the source.

**How to avoid:** Use `"-" * 36`. Verified count: the string in update-list.sh line 1077 is
`"------------------------------------"` which is exactly 36 dashes (confirmed by hex dump).

### Pitfall 3: VS Code NLS dotted-key confusion

**What goes wrong:** `json_get(nls_file, "extension.title")` splits on `.` and traverses
`data["extension"]["title"]`, but `package.nls.json` has `{"extension.title": "My Extension"}`
as a flat top-level key. The traversal returns empty string.

**Why it happens:** `json_get` is designed for dotted-path traversal (Chrome manifest.json),
but VS Code NLS files use flat keys that look like dotted paths.

**How to avoid:** The VS Code NLS lookup must bypass `json_get` and use direct
`nls_data.get(nls_key)`. Never call `json_get` for NLS lookups.

### Pitfall 4: Trailing newline asymmetry at section boundaries

**What goes wrong:** Adding an extra `\n` after `flush_section` output creates `\n\n` before
the next section title instead of the expected single `\n`. Every section boundary shifts one
byte; all parity tests fail.

**Why it happens:** `subprocess.stdout` from sort ends with `\n`; developer's `write_lines`
also adds `\n`; the `write_section` leading `\n` is a third newline.

**How to avoid:** `flush_section` returns a list of strings (WITHOUT trailing newline);
`write_lines` adds exactly one `\n` per line; `write_section` adds the blank line via its
leading `\n`. The only newline after the last item is from `write_lines`.

**Verification:** After writing one section and before writing the next, the file must contain:
`...last_item\n\nNext Section Title\n----...` — exactly ONE blank line between sections.

### Pitfall 5: `__main__.py` imports from `maccat` before version guard

**What goes wrong:** If `from maccat.catalog.format import flush_section` appears before the
`sys.version_info` check in `__main__.py`, a Python 3.9 user gets an `ImportError` (3.11+
syntax like `X | Y` union types will fail) rather than the helpful version error message.

**How to avoid:** The version guard must be the FIRST executable code in `__main__.py`. All
`from maccat.*` imports must be inside `main()` or deferred until after the guard.

### Pitfall 6: Using `src/maccat` path instead of `maccat` for zipapp entry point

**What goes wrong:** `python -m zipapp src/maccat -m "src.maccat.__main__:main"` — the module
path includes `src.` which doesn't exist inside the zip archive.

**Why it happens:** Developer includes `src/` in the module path because it's in the filesystem
path.

**How to avoid:** The zipapp archive contains the `maccat/` directory directly (extracted from
`src/maccat/`). The entry point is `maccat.__main__:main`, not `src.maccat.__main__:main`.

---

## Code Examples

### Verified: complete write_section + flush_section interaction (zsh)

```zsh
# Source: update-list.sh:1075–1296 — verified by live zsh execution
write_section "Test Section"
_section_lines=()
flush_section
# Output bytes: \nTest Section\n------------------------------------\n  (none found)\n

write_section "Test Section With Items"
_section_lines=("zed" "Bitwarden" "1password")
flush_section
# Output bytes: \nTest Section With Items\n------------------------------------\n1password\nBitwarden\nzed\n
```

### Verified: Python subprocess sort (live test)

```python
# Verified by live execution on this machine (Python 3.14.6, macOS)
import subprocess, os

lines = ["1password", "Bitwarden", "zed", "Adobe Acrobat", "bitwarden"]
env = {**os.environ, "LC_ALL": "C"}
result = subprocess.run(
    ["sort", "-f", "-u"],
    input="\n".join(lines) + "\n",
    capture_output=True, text=True, env=env,
)
# result.stdout = "1password\nAdobe Acrobat\nBitwarden\nzed\n"
# "bitwarden" deduplicated against "Bitwarden" by -u (case-folded comparison)
```

### Verified: Chrome `__MSG_` resolution fallback chain

```zsh
# Source: update-list.sh:1160–1213 — fallback chain:
# 1. name is NOT __MSG_*__ → return name (or ext_id if empty)
# 2. name IS __MSG_key__ → look in _locales/<default_locale>/messages.json
# 3. messages.json not found → return ext_id
# 4. key not in messages.json → return ext_id
# 5. key.message found → return resolved name
```

### Verified: VS Code NLS flat-key vs dotted-path

```json
// package.nls.json example (flat keys):
{"extension.title": "My Extension", "extension.description": "Does stuff"}

// WRONG — json_get splits on "." and traverses:
json_get(nls_file, "extension.title")  // → "" (traversal fails)

// CORRECT — direct flat key lookup:
data = json.loads(nls_file.read_text())
data.get("extension.title")  // → "My Extension"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jq + plutil fallback chain in zsh | `json.loads()` in Python | Phase 13 (this phase) | Eliminates two subprocess calls per manifest read; more reliable |
| `python3` in jq fallback chain | Removed (python3 = CLT stub risk) | update-list.sh prior art | json_get comment at line 1096: "python3 NOT in the chain — on a clean macOS it is an xcrun stub" |
| `sorted()` for catalog ordering | `LC_ALL=C sort -f -u` subprocess | Zsh original; Python must match | Byte-identical ordering across locales |
| Names `maclist` / `mac_software_list` | `maccat` | PROJECT.md decision 2026-06-14 | All prior research docs use old names; canonicalise in pyproject.toml |

**Deprecated/outdated:**
- Old research docs STACK.md and ARCHITECTURE.md (`.planning/research/`) use `maclist` and
  `mac_software_list` — these names are stale. Use `maccat` everywhere.
- ARCHITECTURE.md §4 "Matching LC_ALL=C sort" section contradicts itself: it first shows
  `sorted(lines, key=str.casefold)` as a code example, then correctly identifies in
  Anti-Pattern 3 that subprocess is required. Use subprocess. The casefold example is wrong.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `hatchling >= 1.26` is the correct build backend version floor | pyproject.toml section | Build fails; pin lower if needed |
| A2 | `mypy >= 1.10` works with `strict = true` on Python 3.11 | Standard Stack | Type check failures; adjust strict settings |
| A3 | The `sort -V` subprocess approach works identically to the zsh `ls | grep | sort -V | tail -1` pipeline | sort -V section | Chrome version selection may pick wrong dir; test with a multi-version fixture |
| A4 | `hatchling` is the correct build backend for this project (vs `flit_core`) | pyproject.toml | build fails; switch backend; both are fine |

**Verified claims (not assumed):**
- Separator is 36 dashes [VERIFIED: hex dump of real catalog file]
- Leading `\n` in write_section [VERIFIED: zsh source + hex dump]
- `flush_section` empty → `"  (none found)"` with TWO spaces [VERIFIED: zsh source line 1292]
- FMT-01 degradation rules [VERIFIED: zsh source lines 1243–1269 + live execution]
- Chrome `__MSG_` resolution algorithm [VERIFIED: zsh source lines 1148–1214]
- VS Code `%nls%` resolution algorithm [VERIFIED: zsh source lines 1316–1366]
- LC_ALL=C sort -f -u via subprocess produces correct output [VERIFIED: live Python test]
- `pytest 9.1.0`, `ruff 0.15.17` current versions [VERIFIED: pip registry]
- `python -c "import maccat"` requires `src/` in `sys.path` [VERIFIED: live test]

---

## Open Questions

1. **Encoding for catalog output file**
   - What we know: zsh `echo` writes bytes in the system locale (UTF-8 on macOS). The Python
     `subprocess sort` returns UTF-8 text when `text=True`. Extension names may contain non-ASCII.
   - What's unclear: Should `CatalogWriter` open the file as `"w"` with `encoding="utf-8"`, or
     `"wb"` with explicit encode? The zsh reference writes bytes directly; the catalog consumer
     (git diff, text editors) expects UTF-8.
   - Recommendation: Use `"w"` + `encoding="utf-8"` + `newline="\n"` (prevents `\r\n` on any
     hypothetical non-macOS run). This matches zsh's implicit UTF-8 byte output.

2. **`tests/golden/` scaffolding in Phase 13 vs Phase 17**
   - STATE.md says "scaffold tests/golden/ and normalize_catalog_body() utility in this phase"
   - CONTEXT.md defers all golden fixture population to Phase 17
   - Recommendation: Create `tests/golden/` directory + `normalize_catalog_body()` utility
     (strips volatile timestamp/hostname fields) in Phase 13. Populating golden files is Phase 17.
     This lets Phase 13's own unit tests use the normalizer without waiting for Phase 17.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | ✓ | 3.14.6 (Homebrew) | Must install Homebrew Python |
| `/usr/bin/sort` | `flush_section` subprocess | ✓ | macOS BSD sort | None — required |
| `sort -V` flag | Chrome version selection | ✓ | macOS BSD sort supports `-V` | Pure-Python version_key fallback |
| `uv` | Dev env management | [ASSUMED] | — | `python3 -m venv` + `pip` |
| `git` | Required by project (not Phase 13) | ✓ | macOS/Xcode CLT | N/A |

**Missing dependencies with no fallback:** None for Phase 13 itself.

**Note:** `/usr/bin/sort` is always present on macOS (POSIX). The `-f` and `-V` flags are
supported by macOS BSD sort. No installation required.

---

## Validation Architecture

> `nyquist_validation` is `false` in config.json — this section is skipped.

---

## Security Domain

> This is a pure infrastructure/format layer phase with no user input, no authentication,
> no network calls, and no file writes beyond the output catalog. ASVS categories V2–V6
> do not apply to Phase 13 deliverables.
>
> The one security-relevant pattern: `subprocess.run(["sort", ...], input=..., ...)` passes
> data through stdin (not shell=True), so no shell injection is possible. Use `shell=False`
> (the default) always.

---

## Sources

### Primary (HIGH confidence)

- `update-list.sh` (live read) — `write_section` (line 1075), `emit_item` (line 1243),
  `flush_section` (line 1290), `chrome_ext_name` (line 1148), `resolve_vsc_ext_name` (line 1316),
  `generate_catalog` (line 2220), all section title strings (lines 1393–2281)
- Real catalog file `mac-software-list-[computer-one.local]-20260612130331.txt` —
  hex dump verified: 36 dashes, leading `\n`, section boundary format
- Live zsh execution: `write_section` + `flush_section` byte output confirmed
- Live Python subprocess: `sort -f -u` with `LC_ALL=C` confirmed correct output

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` (2026-06-14) — RunContext pattern, collector ABC,
  CatalogWriter pattern — note: uses stale name `maclist`; patterns are valid
- `.planning/research/PITFALLS.md` (2026-06-14) — Pitfalls 1–5 confirmed by code reading
- `.planning/research/STACK.md` (2026-06-14) — stdlib sufficiency analysis, version floor
  rationale — note: uses stale name `mac_software_list`; analysis is valid
- `pip index versions pytest` / `pip index versions ruff` — version verification (live)

### Tertiary (LOW confidence)

- None in this phase.

---

## Metadata

**Confidence breakdown:**
- Byte format details: HIGH — verified from zsh source + hex dump of real files
- FMT-01 rules: HIGH — read directly from zsh source + live execution
- Sort subprocess pattern: HIGH — verified by live Python test
- Chrome/VS Code resolution: HIGH — read directly from zsh source
- pyproject.toml structure: MEDIUM — build backend version floor is assumed
- Dev tool versions: MEDIUM — pytest/ruff verified via pip registry; mypy/uv assumed

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable stdlib; zsh source is locked; sort behavior won't change)

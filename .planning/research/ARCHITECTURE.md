# Architecture Research

**Domain:** Python port of a macOS single-file Zsh cataloger — modular package, external catalog repo, `.pyz`/pipx distribution
**Researched:** 2026-06-14
**Confidence:** HIGH

## Summary

Re-implementing `update-list.sh` (~2,500-line Zsh) as a modular Python package at byte-parity
output. The central architectural constraints:

1. **Exact output fidelity** — every section title, line format, sort order, and graceful-
   degradation message must match the Zsh output byte-for-byte so golden-output parity tests pass.
2. **SCRIPT_DIR must die** — the Zsh script assumes the catalog repo lives next to the script.
   The Python package lives in a `.pyz`/pipx installation; the catalog repo is user-configured.
3. **No globals** — the Zsh anti-pattern of globals-as-parameters must not carry over.
4. **Collector contract** — 17 independent collectors must be individually testable; a uniform
   interface lets the registry compose them without knowing their internals.
5. **Distribution** — the package must run as a self-contained `.pyz` zipapp and install via `pipx`;
   standard library only unless a dependency is universally available (subprocess, pathlib, json,
   plistlib, datetime, shutil, os, sys).

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  maclist/__main__.py                                                  │
│  Entry point: parse args, load config, build RunContext, dispatch    │
│  --rename → rename_mode()   |   normal run → catalog_mode()         │
└──────────────────┬──────────────────────────────────────────────────┘
                   │  RunContext (immutable dataclass, replaces globals)
         ┌─────────▼─────────────────────────────────────────────┐
         │  maclist/cli.py                                         │
         │  Argument parsing (argparse), config loading,          │
         │  computer-folder menu (select_computer),               │
         │  archive-retention prompt, produces RunContext          │
         └─────────┬─────────────────────────────────────────────┘
                   │
         ┌─────────▼─────────────────────────────────────────────┐
         │  maclist/identity.py                                    │
         │  select_computer(), validate_computer_name(),          │
         │  upsert_machine_label() — all take catalog_repo Path   │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/gitops.py                                       │
         │  git_pull(repo), git_commit_and_push(repo, ctx),       │
         │  rename_commit(repo, old, new)                          │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/catalog/                                        │
         │  ┌──────────────┐  ┌──────────────────┐               │
         │  │ writer.py    │  │ format.py         │               │
         │  │ CatalogWriter│  │ emit_item()       │               │
         │  │ write_section│  │ flush_section()   │               │
         │  │ atomic write │  │ Item dataclass    │               │
         │  └──────────────┘  └──────────────────┘               │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/collectors/                                     │
         │  __init__.py  (REGISTRY: ordered list of Collector)     │
         │  base.py      (abstract Collector, CollectorResult)     │
         │  homebrew.py  vscode.py    chrome.py    codex.py        │
         │  mas.py       cursor.py    firefox.py   opencode.py     │
         │  setapp.py    claude.py    gemini.py                    │
         │  webapps.py                                              │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/helpers/                                        │
         │  json_io.py    (json_get — plistlib/json fallback)      │
         │  chrome_name.py (chrome_ext_name — __MSG_ resolution)  │
         │  vsc_name.py   (resolve_vsc_ext_name — NLS)            │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/config.py                                       │
         │  load_config(Path?) → Config                            │
         │  resolve_catalog_repo(flag_val, config) → Path         │
         │  Config dataclass (catalog_repo, default_computer, …)  │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/retention.py                                    │
         │  retain_newest_per_host(target_dir: Path, …)           │
         │  prune_old_archives(archive_dir: Path, age_days: int)  │
         └─────────────────────────────────────────────────────────┘
                   │
         ┌─────────▼──────────────────────────────────────────────┐
         │  maclist/naming.py                                       │
         │  parse_catalog_filename(filename) → CatalogFilename    │
         │  make_catalog_filename(machine, ts) → str              │
         │  CatalogFilename dataclass (machine, timestamp, stem)  │
         └─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Key boundary |
|-----------|----------------|--------------|
| `__main__.py` | Entry point; wires config → RunContext → dispatch | No business logic; only orchestration |
| `cli.py` | argparse, interactive menus (select_computer, archive-days prompt), TTY guards | Produces RunContext; no I/O after that |
| `config.py` | Load `~/.config/maclist/config.toml`, resolve catalog_repo path | Pure data; no side effects |
| `identity.py` | Computer-folder selection, validate_computer_name, upsert_machine_label | Takes catalog_repo Path; no globals |
| `naming.py` | `mac-software-list-[label]-YYYYMMDDHHMMSS.txt` parse + generate | Pure functions; no I/O |
| `retention.py` | retain_newest_per_host, prune_old_archives | Takes Path args; no globals |
| `gitops.py` | git pull/commit/push via subprocess; rename commit | Takes repo Path; no globals |
| `catalog/writer.py` | CatalogWriter context manager; atomic write (tmp + rename) | Owns the output file lifetime |
| `catalog/format.py` | Item dataclass, emit_item, flush_section (sort + dedup) | Pure formatting, no file I/O |
| `collectors/base.py` | Abstract Collector, CollectorResult protocol | Contract only; no logic |
| `collectors/__init__.py` | REGISTRY: ordered list of Collector instances | Fixed section order matches Zsh |
| `collectors/*.py` | One file per source; each implements Collector | Each independently testable |
| `helpers/json_io.py` | json_get(file, key) — json/plistlib only, stdlib | No subprocess; pure Python |
| `helpers/chrome_name.py` | chrome_ext_name(manifest_path) — __MSG_ resolution | Wraps json_io |
| `helpers/vsc_name.py` | resolve_vsc_ext_name(pkg_json, ext_id) — NLS | Wraps json_io |

---

## Recommended Project Structure

```
mac-software-list/          ← existing repo root (catalog repo when running locally)
├── update-list.sh          ← untouched; stays here forever
├── machine-labels.tsv      ← also lives here (or in the user's catalog repo)
├── personal/               ← existing catalog folders
├── office/                 ← existing catalog folders
│
└── maclist/                ← NEW: Python package source tree
    ├── __init__.py
    ├── __main__.py         ← `python -m maclist` / zipapp entry
    ├── cli.py              ← argparse + interactive menus + RunContext builder
    ├── config.py           ← Config dataclass + config file loader
    ├── identity.py         ← computer-folder selection + TSV map
    ├── naming.py           ← filename parse/generate (pure)
    ├── retention.py        ← retain_newest_per_host + prune_old_archives
    ├── gitops.py           ← git pull/commit/push via subprocess
    │
    ├── catalog/
    │   ├── __init__.py
    │   ├── writer.py       ← CatalogWriter (context manager, atomic output)
    │   └── format.py       ← Item, emit_item, flush_section, write_section
    │
    ├── collectors/
    │   ├── __init__.py     ← REGISTRY (ordered list); register() decorator
    │   ├── base.py         ← Collector ABC, CollectorResult
    │   ├── homebrew.py
    │   ├── mas.py
    │   ├── setapp.py
    │   ├── webapps.py
    │   ├── claude.py       ← plugins + MCP + skills/agents (3 sections)
    │   ├── codex.py        ← MCP only (no plugins in v0.46)
    │   ├── opencode.py     ← plugins + MCP + agents
    │   ├── gemini.py       ← extensions + MCP
    │   ├── vscode.py
    │   ├── cursor.py
    │   ├── chrome.py
    │   └── firefox.py
    │
    └── helpers/
        ├── __init__.py
        ├── json_io.py      ← json_get() using json/plistlib (no subprocess)
        ├── chrome_name.py  ← chrome_ext_name()
        └── vsc_name.py     ← resolve_vsc_ext_name()

tests/
├── golden/
│   └── fixtures/           ← per-section fixture files for parity tests
├── unit/
│   ├── test_naming.py
│   ├── test_format.py
│   ├── test_retention.py
│   └── collectors/
│       └── test_*.py       ← one test file per collector
└── integration/
    └── test_parity.py      ← golden-output comparisons

pyproject.toml              ← project metadata, build system (flit or setuptools)
build-pyz.sh                ← zipapp build script
```

### Structure Rationale

- **`maclist/` at repo root alongside `update-list.sh`:** both implementations coexist in the same
  repo without confusion; the Python package does not overwrite any Zsh outputs.
- **`catalog/` sub-package:** keeps format and I/O concerns separated; `format.py` has no file I/O
  (pure Item/line logic) which makes it trivially testable with zero mocking.
- **`collectors/` as a sub-package with a registry:** the fixed section order lives in one
  authoritative place (`REGISTRY` in `__init__.py`); adding a new source is one file + one registry
  entry, nothing else to wire.
- **`helpers/` not inside `collectors/`:** json_io, chrome_name, and vsc_name are shared across
  multiple collectors; placing them in a sibling package avoids circular imports.
- **`tests/golden/`:** fixture files checked into the repo; parity tests diff Python output against
  captured Zsh section bodies.

---

## Architectural Patterns

### Pattern 1: RunContext — immutable parameter bundle (replaces Zsh globals)

**What:** A frozen dataclass passed top-down from `__main__` through every function call. No module-
level mutable state.

**When to use:** Everywhere. Every function that previously read a global (`TARGET_LOCATION`,
`SCRIPT_DIR`, `ARCHIVE_AGE_DAYS`, etc.) now takes a `RunContext` or one of its fields.

**Trade-offs:** Slightly more verbose function signatures; eliminates entire class of test
difficulties (no global-reset boilerplate).

```python
# maclist/cli.py
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True)
class RunContext:
    catalog_repo: Path          # replaces SCRIPT_DIR
    computer:     str           # replaces TARGET_LOCATION / CURRENT_MACHINE
    archive_days: int           # replaces ARCHIVE_AGE_DAYS
    auto_commit:  bool          # replaces AUTO_COMMIT
    timestamp:    str           # YYYYMMDDHHMMSS, set once at startup
    output_file:  Path          # derived: catalog_repo / computer / filename
```

The `output_file` is derived, not stored separately; `naming.make_catalog_filename(computer,
timestamp)` produces the filename, and `catalog_repo / computer / filename` is the full path.

### Pattern 2: Collector ABC — uniform pluggable interface

**What:** An abstract base class with a `collect()` method that returns a `CollectorResult`. Each
source is one concrete subclass. The registry is an ordered list of instances.

**When to use:** For all 17 sources. The contract is designed so the orchestrator calls collectors
without knowing anything about their internals.

**Trade-offs:** Slightly more structure than bare functions; pays off immediately in testability
(mock a collector, swap one, test ordering independently of data).

```python
# maclist/collectors/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence

@dataclass
class Section:
    title:  str
    items:  list[str]   # pre-formatted lines (emit_item output, NOT yet sorted)
    note:   str = ""    # graceful-degradation message when items is empty

@dataclass
class CollectorResult:
    sections: list[Section]     # one collector may yield multiple sections
    warnings: list[str] = field(default_factory=list)

class Collector:
    """Abstract. Subclasses implement collect()."""
    def collect(self) -> CollectorResult:
        raise NotImplementedError

    def available(self) -> bool:
        """Override to gate on tool presence or directory existence."""
        return True

    def degraded_result(self, title: str, note: str) -> CollectorResult:
        """Return the standard '(none found)' result for a missing source."""
        return CollectorResult(sections=[Section(title=title, items=[], note=note)])
```

Each collector's `collect()` builds `Section` objects whose `items` list will be sorted and
deduplicated by `flush_section` in `catalog/format.py` before writing. The `note` field holds
the graceful-degradation text (e.g. `"Homebrew is not installed."`).

### Pattern 3: CatalogWriter — context manager for atomic output

**What:** A context manager that writes the catalog to a temp file in the same directory, then
renames it to the final path on `__exit__`. Guarantees the output file is never partial.

**When to use:** Whenever writing the catalog file. Never write directly to the final path.

**Trade-offs:** Two file ops instead of one; negligible cost, eliminates corrupted-on-crash files.

```python
# maclist/catalog/writer.py
from pathlib import Path
import tempfile, os

class CatalogWriter:
    def __init__(self, output_path: Path):
        self._path = output_path
        self._tmp  = None
        self._fh   = None

    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        self._tmp = Path(tmp)
        self._fh  = os.fdopen(fd, "w", encoding="utf-8")
        return self

    def write_section(self, title: str) -> None:
        self._fh.write(f"\n{title}\n")
        self._fh.write("------------------------------------\n")

    def write_lines(self, lines: list[str]) -> None:
        for line in lines:
            self._fh.write(line + "\n")

    def __exit__(self, *_):
        self._fh.close()
        self._tmp.rename(self._path)   # atomic on POSIX
```

### Pattern 4: json_get — stdlib-only JSON/plist extraction (replaces jq + plutil chain)

**What:** The Python port can use `json` and `plistlib` from the standard library directly, with
no subprocess calls. This is strictly better than the Zsh jq → plutil fallback chain.

**When to use:** Everywhere a JSON file must be read. The Zsh `json_get` is a Zsh-specific
workaround for the absence of a built-in JSON library; in Python there is no workaround needed.

**Trade-offs:** None. Python's `json.load()` handles the same files `jq` handles.

```python
# maclist/helpers/json_io.py
import json
from pathlib import Path
from typing import Any

def json_get(file: Path, key: str, default: str = "") -> str:
    """
    Extract a scalar value from a JSON file by dotted key path.
    Returns default on any error (missing file, parse error, missing key).
    Never raises. Mirrors the Zsh json_get contract exactly.
    """
    if not file.is_file():
        return default
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default
    parts = key.split(".")
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part, default)
        if cur == default:
            return default
    return str(cur) if cur is not None else default
```

For plist files (e.g. if plutil-formatted JSON appears), `plistlib.loads()` handles them. The
`json_io` helper is the single gateway; callers never import `json` directly.

### Pattern 5: emit_item + flush_section — exact FMT-01 format with LC_ALL=C sort

**What:** `emit_item(name, version, id)` builds one formatted line per the FMT-01 rules; lines
are accumulated in a list and written via `flush_section()` which sorts with `locale.strxfrm`
under `LC_ALL=C` semantics and deduplicates.

**When to use:** In every collector for every item. Never format lines manually.

**Matching LC_ALL=C sort -f -u in Python:**
The Zsh `LC_ALL=C sort -f -u` is byte-value ordering after Unicode case-folding. Python's
`sorted()` with `key=str.casefold` is NOT byte-identical to LC_ALL=C on non-ASCII input. The
safest match is to call `subprocess.run(["sort", "-f", "-u"], ...)` with `LC_ALL=C` in the
environment. This is the one subprocess call that must remain for correct parity.

```python
# maclist/catalog/format.py
import subprocess, os
from dataclasses import dataclass

@dataclass
class Item:
    name:    str
    version: str
    id:      str

def emit_item(name: str, version: str, id_: str) -> str | None:
    """
    Builds one catalog line per FMT-01 rules. Returns None for all-empty input.
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
    return None   # all empty → nothing

def flush_section(lines: list[str]) -> list[str]:
    """
    Sort lines with LC_ALL=C sort -f -u (byte-stable, case-insensitive, deduplicated).
    Returns ["  (none found)"] when lines is empty.
    Preserves exact Zsh FMT-04 output.
    """
    if not lines:
        return ["  (none found)"]
    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-f", "-u"],
        input="\n".join(lines) + "\n",
        capture_output=True, text=True, env=env,
    )
    return result.stdout.rstrip("\n").split("\n")
```

---

## Catalog-Repo Path Threading (SCRIPT_DIR replacement)

### The problem

The Zsh script uses `SCRIPT_DIR="${0:A:h}"` as its working root for everything: catalog output,
`machine-labels.tsv`, `archive/` subdirectories, and git operations. This works because the script
lives in the catalog repo. The Python package lives in a `.pyz`/pipx installation — it has no
meaningful `__file__` path relative to any catalog.

### The solution: Config-resolved `catalog_repo` Path

1. **Config file** (`~/.config/maclist/config.toml`) holds `catalog_repo = "/path/to/repo"`.
2. **`--catalog-repo` flag** overrides it at runtime.
3. `config.py` resolves the final path:

```python
# maclist/config.py
import tomllib   # Python 3.11+ stdlib; or tomli backport for 3.10
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    catalog_repo: Path | None = None

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "maclist" / "config.toml"

def load_config(config_path: Path | None = None) -> Config:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.is_file():
        return Config()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    repo_str = raw.get("catalog_repo")
    return Config(catalog_repo=Path(repo_str).expanduser() if repo_str else None)

def resolve_catalog_repo(flag_val: str | None, config: Config) -> Path:
    """
    Flag overrides config; config overrides cwd fallback.
    Raises SystemExit with actionable message when nothing is configured.
    """
    if flag_val:
        return Path(flag_val).expanduser().resolve()
    if config.catalog_repo:
        return config.catalog_repo.expanduser().resolve()
    # Last resort: current working directory (useful for local dev in the repo itself)
    cwd = Path.cwd()
    if (cwd / "machine-labels.tsv").exists() or (cwd / "update-list.sh").exists():
        return cwd
    raise SystemExit(
        "ERROR: catalog_repo not configured. "
        "Run with --catalog-repo /path/to/repo or set catalog_repo in "
        "~/.config/maclist/config.toml"
    )
```

4. `catalog_repo` is stored in `RunContext` and passed as a `Path` argument to every function
   that needs it — `identity.py`, `retention.py`, `gitops.py`, `CatalogWriter`. No module-level
   state stores it.

### Functions that formerly used SCRIPT_DIR

| Zsh function | Python equivalent | Receives catalog_repo via |
|---|---|---|
| `select_computer` | `identity.select_computer(catalog_repo, ...)` | argument |
| `upsert_machine_label` | `identity.upsert_machine_label(catalog_repo, computer)` | argument |
| `retain_newest_per_host` | `retention.retain_newest_per_host(catalog_repo / computer)` | argument |
| `prune_old_archives` | `retention.prune_old_archives(catalog_repo / computer / "archive", days)` | argument |
| `git_pull` | `gitops.git_pull(catalog_repo)` | argument |
| `git_commit_and_push` | `gitops.git_commit_and_push(catalog_repo, ctx)` | argument |
| `rename_machine` | `identity.rename_machine(catalog_repo, ...)` | argument |
| Main output file | `CatalogWriter(catalog_repo / computer / filename)` | argument |

---

## Faithful Reproduction of Subtle Bits

### 1. jq → plutil → grep collapses to json + plistlib

The Zsh chain exists because Zsh has no JSON library. Python does. Every `json_get` call becomes
`json.loads(file.read_text())`. The `plutil` fallback was needed for `.plist` files; `plistlib`
handles those. The `grep` fallback was a last resort for when both tools were absent — not needed
in Python. The entire Zsh backend chain reduces to:

```python
def _load_json_or_plist(file: Path) -> dict:
    text = file.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import plistlib
        return plistlib.loads(text.encode())   # handles XML and binary plist
```

This is strictly more reliable than the Zsh chain because `plutil` on macOS 12+ silently changed
some behaviors for edge-case JSON; `json.loads` is always canonical.

### 2. BSD date -v cutoff math → datetime

```python
# maclist/retention.py
from datetime import datetime, timedelta

def cutoff_date(archive_days: int) -> str:
    """Returns YYYYMMDD string matching `date -v-{N}d +%Y%m%d`."""
    return (datetime.now() - timedelta(days=archive_days)).strftime("%Y%m%d")
```

This is a straightforward replacement. `datetime.now()` is local time, same as `date -v` uses.

### 3. Atomic TSV writes (tmp + rename)

The Zsh `upsert_machine_label` already uses tmp+rename for the TSV. Python matches it:

```python
# maclist/identity.py
import tempfile, os
from pathlib import Path

def _atomic_write_tsv(path: Path, lines: list[str]) -> None:
    """Write lines to path atomically via tmp + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    Path(tmp).rename(path)
```

Key: `newline="\n"` prevents Windows-style `\r\n` even on a hypothetical cross-platform build.

### 4. Filename parsing — 14-digit timestamp + [label]

```python
# maclist/naming.py
import re
from dataclasses import dataclass

_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

@dataclass(frozen=True)
class CatalogFilename:
    machine:   str
    timestamp: str   # YYYYMMDDHHMMSS
    filename:  str

def parse_catalog_filename(filename: str) -> CatalogFilename | None:
    """Returns None (not raises) for non-matching filenames — same as Zsh warn-and-continue."""
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    return CatalogFilename(
        machine=m.group("machine"),
        timestamp=m.group("ts"),
        filename=filename,
    )

def make_catalog_filename(machine: str, timestamp: str) -> str:
    return f"mac-software-list-[{machine}]-{timestamp}.txt"
```

The regex matches exactly what the Zsh filename convention produces. `machine` matches
`[^\[\]]+` — no brackets allowed inside (enforced by `validate_computer_name`).

### 5. Graceful degradation — exact messages

The Zsh script has two message registers: `NOTE:` for "tool simply not installed" and `WARNING:`
for "expected but failed". The Python port reproduces both verbatim:

```
NOTE: Google Chrome not installed.
NOTE: VS Code not installed or no extensions found.
WARNING: code CLI returned empty list. Falling back to extensions.json.
WARNING: Could not parse timestamp from: <filename> — skipping
```

The exact strings are tested in the parity suite. Any string mismatch between Zsh and Python
output is a test failure.

### 6. Source-guard for testability

The Zsh script has `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0` to make it sourceable for
isolated tests. Python modules are already importable without executing anything — `__main__.py`
guards its top-level code:

```python
# maclist/__main__.py
if __name__ == "__main__":
    from maclist.cli import main
    main()
```

Individual modules have no top-level side effects, so any function can be imported and called in
isolation.

---

## Data Flow

### Normal Catalog Run

```
argv
  │
  ▼
cli.parse_args() + load_config()
  │  validates --computer, --archive-days, --catalog-repo
  ▼
identity.select_computer(catalog_repo)
  │  TTY menu or --computer flag; calls upsert_machine_label
  ▼
RunContext(catalog_repo, computer, archive_days, auto_commit, timestamp, output_file)
  │
  ▼
gitops.git_pull(catalog_repo)           [warn-and-continue on failure]
  │
  ▼
CatalogWriter(output_file).__enter__()  [opens tmp file]
  │
  ├─ for collector in REGISTRY:
  │     result = collector.collect()
  │     for section in result.sections:
  │         writer.write_section(section.title)
  │         writer.write_lines(flush_section(section.items))
  │
  ▼
CatalogWriter.__exit__()                [tmp → final path, atomic]
  │
  ▼
retention.retain_newest_per_host(catalog_repo / computer)
  │
  ▼
retention.prune_old_archives(catalog_repo / computer / "archive", archive_days)
  │
  ▼
gitops.git_commit_and_push(catalog_repo, ctx)  [warn-and-continue on failure]
```

### Rename Run

```
argv --rename
  │
  ▼
gitops.git_pull(catalog_repo)
  │
  ▼
identity.rename_machine(catalog_repo, auto_commit)
  │  TTY menu → old/new names → mv folder → rewrite filenames → update TSV → commit
  ▼
exit 0
```

### Collector Execution

```
collector.available() → False
    │
    └─ return CollectorResult(sections=[Section(title, items=[], note="<tool> not installed.")])

collector.available() → True
    │
    ▼
collector.collect()
    │  subprocess call OR file parse
    ▼
list of Item(name, version, id_)
    │
    ▼
[emit_item(item.name, item.version, item.id_) for item in items]
    │ → list of formatted strings
    ▼
CollectorResult(sections=[Section(title, items=formatted_lines)])
    │
    ▼  (in CatalogWriter loop)
flush_section(section.items) → sorted + deduped lines
    │
    ▼
writer.write_lines(lines)
```

---

## Package Layout: Coexistence + Build

### Coexistence with update-list.sh

Both live in the same repo root. The Python package is a new `maclist/` directory alongside the
existing Zsh outputs. `update-list.sh` is never modified. The Python package writes catalogs to
the same `<catalog_repo>/<computer>/` paths, so both tools produce files that git can commit and
compare.

When the Python tool is run against the same catalog repo, the retention and archive logic operate
on the same files regardless of which tool created them — the filename convention is identical.

### pyproject.toml (minimal, stdlib-only)

```toml
[build-system]
requires = ["flit_core>=3.2"]
build-backend = "flit_core.buildapi"

[project]
name = "maclist"
version = "1.0.0"
description = "Mac software catalog generator"
requires-python = ">=3.11"
# No runtime dependencies — stdlib only

[project.scripts]
maclist = "maclist.__main__:main"
```

`tomllib` is stdlib in Python 3.11+. If 3.10 support is needed, add `tomli` as the only
dependency and guard: `try: import tomllib except ImportError: import tomli as tomllib`.

### .pyz Zipapp Build

```bash
# build-pyz.sh
python -m zipapp maclist \
  --output maclist.pyz \
  --python "/usr/bin/env python3" \
  --main "maclist.__main__:main"
```

The `.pyz` is a self-contained archive of the `maclist/` directory. It runs with any Python 3.11+
on the user's machine. No installation required beyond having python3.

For pipx:

```bash
pipx install git+https://github.com/<user>/mac-software-list.git#subdirectory=maclist
# or once published to PyPI:
pipx install maclist
```

### Build Order (dependency-respecting phases)

| Phase | Modules | Depends on | Rationale |
|-------|---------|------------|-----------|
| **Phase 1: Foundation** | `naming.py`, `catalog/format.py`, `catalog/writer.py`, `helpers/json_io.py` | nothing | Pure functions/classes; no external state; unit tests can run immediately |
| **Phase 2: Helpers** | `helpers/chrome_name.py`, `helpers/vsc_name.py` | `json_io` | Wrap json_io; needed by collectors |
| **Phase 3: Config + Identity** | `config.py`, `identity.py`, `retention.py` | `naming.py` | catalog_repo threading; TSV map; retention logic; all take Path args |
| **Phase 4: Collectors** | `collectors/base.py`, then each `collectors/*.py` | `format.py`, `json_io`, `chrome_name`, `vsc_name` | Independent per source; can be built in parallel after Phase 2 |
| **Phase 5: Git + CLI** | `gitops.py`, `cli.py`, `__main__.py` | everything above | Wires the pipeline; interactive menus; RunContext construction |
| **Phase 6: Distribution** | `pyproject.toml`, `build-pyz.sh` | complete package | Package metadata; zipapp build |
| **Phase 7: Parity Tests** | `tests/integration/test_parity.py` | all collectors + Zsh | Golden-output comparison; requires both tools runnable in test env |

Within Phase 4, each collector file is independent — vscode.py can be built and tested before
chrome.py. The registry in `collectors/__init__.py` is assembled last in Phase 4.

---

## Anti-Patterns

### Anti-Pattern 1: Carrying Zsh globals forward as Python module-level state

**What people do:** Put `TARGET_LOCATION`, `OUTPUT_FILE`, etc. as module-level variables in
`maclist/__init__.py` and mutate them in each function (faithfully reproducing the Zsh approach).
**Why it's wrong:** Makes every function untestable without side effects; breaks if two tests run
concurrently; obscures data flow.
**Do this instead:** `RunContext` frozen dataclass, passed as an argument. Construct it once in
`__main__.py` after arg parsing.

### Anti-Pattern 2: Reimplementing json_get with subprocess jq

**What people do:** Call `subprocess.run(["jq", "-r", ...])` to preserve the exact Zsh backend.
**Why it's wrong:** Defeats the purpose of using Python; adds a hard dependency on jq; slower.
**Do this instead:** `json.loads()` in `helpers/json_io.py`. Python's stdlib JSON parser is faster
and more reliable than routing through jq.

### Anti-Pattern 3: Using Python's `locale` module to reproduce LC_ALL=C sort

**What people do:** `sorted(lines, key=locale.strxfrm)` after calling `locale.setlocale(LC_ALL, "C")`.
**Why it's wrong:** `locale.setlocale` is process-global and thread-unsafe; behavior differs across
Python versions and macOS updates.
**Do this instead:** `subprocess.run(["sort", "-f", "-u"], env={**os.environ, "LC_ALL": "C"})` —
same binary the Zsh script calls; byte-identical output guaranteed.

### Anti-Pattern 4: Writing the catalog file directly (no atomic tmp+rename)

**What people do:** `output_path.open("w")` and write directly.
**Why it's wrong:** A crash mid-write leaves a partial catalog file at the final path; git will
stage a corrupt snapshot.
**Do this instead:** `CatalogWriter` context manager always writes to a `.tmp` sibling and renames
on close.

### Anti-Pattern 5: Making collectors write to a file instead of returning data

**What people do:** Pass `output_file` into each collector and have it append directly, mirroring
the Zsh `>> "$OUTPUT_FILE"` pattern.
**Why it's wrong:** Makes collectors impossible to unit-test without filesystem setup; prevents
the flush_section sort from running after the collector finishes.
**Do this instead:** Collectors return `CollectorResult`; the orchestrator calls `flush_section`
and writes via `CatalogWriter`. This is the key architectural inversion from Zsh → Python.

### Anti-Pattern 6: One Python module for all collectors

**What people do:** Put all 17 `collect_*` functions in a single `collectors.py` file to mirror
the single Zsh file.
**Why it's wrong:** Makes the file ~1500 lines; a change to `chrome.py` logic re-runs all collector
tests; individual sections can't be developed/tested in isolation.
**Do this instead:** One file per source in `collectors/`; the registry assembles them in order.

---

## Integration Points

### External Tool Boundaries

| Tool | How Python calls it | Notes |
|------|-------------------|-------|
| `brew` | `subprocess.run(["brew", "list", "--formula"])` | stdout captured; stderr suppressed |
| `mas` | `subprocess.run(["mas", "list"])` | awk equivalent in Python (split/format) |
| `claude` | `subprocess.run(["claude", "plugin", "list", "--json"])` | JSON parsed by json module |
| `code`/`cursor` | `subprocess.run(["code", "--list-extensions", "--show-versions"])` | fall back to extensions.json |
| `sort` | `subprocess.run(["sort", "-f", "-u"], env=LC_ALL=C)` | parity-critical; do not replace |
| `git` | `subprocess.run(["git", ...], cwd=catalog_repo)` | cwd kwarg replaces `cd "$SCRIPT_DIR"` |

### File System Boundaries

| Path | Owner | Notes |
|------|-------|-------|
| `~/.config/maclist/config.toml` | config.py | Tool config; not in catalog repo |
| `<catalog_repo>/machine-labels.tsv` | identity.py | Shared with Zsh tool; same format |
| `<catalog_repo>/<computer>/*.txt` | CatalogWriter | Output; shared with Zsh tool |
| `<catalog_repo>/<computer>/archive/*.txt` | retention.py | Shared with Zsh tool |
| `~/.claude/`, `~/.codex/`, etc. | collectors | Read-only; never written |
| `~/Library/Application Support/Google/Chrome/` | chrome.py | Read-only |

### Internal Module Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| cli → identity | function call, returns computer str | identity never imports cli |
| cli → config | function call, returns Config | config has no imports from maclist |
| collectors → helpers | function call, returns str | helpers have no imports from collectors |
| collectors → format | function call, returns str | format has no imports from collectors |
| __main__ → catalog/writer | context manager | writer never imports __main__ |
| gitops → RunContext | receives as argument | gitops does not import cli |

All dependencies flow downward (toward the leaf modules). No circular imports.

---

## Sources

- `/Users/ken/dev/mac-software-list/update-list.sh` — full read of all functions; behavioral
  source of truth for format, degradation rules, sort, retention math, filename convention
- `/Users/ken/dev/mac-software-list/.planning/PROJECT.md` — confirmed decisions (modular Python,
  config-file catalog-repo, `.pyz`/pipx, golden parity tests, `update-list.sh` untouched)
- `.planning/codebase/ARCHITECTURE.md` — existing system overview and globals-as-params analysis
- Python 3.11 stdlib docs — `tomllib`, `json`, `plistlib`, `zipapp`, `dataclasses`, `pathlib`
- Prior `.planning/research/` files (STACK, FEATURES, PITFALLS, SUMMARY) — collector inventory,
  FMT-01/FMT-04 rules, LC_ALL=C sort requirement, secret-exclusion policy

---

*Architecture research for: v1.0.0 Python port of mac-software-list*
*Researched: 2026-06-14*

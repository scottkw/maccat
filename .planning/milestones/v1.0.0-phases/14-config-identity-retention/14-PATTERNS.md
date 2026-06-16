# Phase 14: Config, Identity & Retention - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 10 (4 implementation + 4 test + 2 conftest additions)
**Analogs found:** 10 / 10 (all files map to zsh behavioral analog + Phase 13 Python structural analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Zsh Behavioral Analog | Phase 13 Python Structural Analog | Match Quality |
|---|---|---|---|---|---|
| `src/maccat/naming.py` | utility | transform | `update-list.sh` filename convention (all retention/rename functions) | `src/maccat/helpers/json_io.py` (pure-function module, returns None on parse failure) | exact |
| `src/maccat/config.py` | service | request-response | `update-list.sh` lines 511–541 (`resolve_archive_retention`) + config init is new | `src/maccat/catalog/writer.py` (atomic write + dataclass-owning module) | role-match |
| `src/maccat/identity.py` | service | request-response + file-I/O | `update-list.sh` lines 308–606 (`select_computer`, `upsert_machine_label`, `validate_computer_name*`) | `src/maccat/helpers/chrome_name.py` (multi-function module, graceful fallbacks) | exact |
| `src/maccat/retention.py` | service | file-I/O | `update-list.sh` lines 637–923, 942–1064 (`rename_machine`, `retain_newest_per_host`, `prune_old_archives`) | `src/maccat/catalog/writer.py` (tempfile atomic pattern, OSError handling) | exact |
| `tests/test_naming.py` | test | — | `update-list.sh` filename convention | `tests/test_format.py` (class-per-function, pure-function unit tests) | role-match |
| `tests/test_retention.py` | test | — | `update-list.sh` lines 942–1064 (TDD — write before impl) | `tests/test_writer.py` (tmp_path fixtures, file-state assertions) | role-match |
| `tests/test_identity.py` | test | — | `update-list.sh` lines 308–606 | `tests/test_helpers.py` (monkeypatch + multi-scenario classes) | role-match |
| `tests/test_config.py` | test | — | `update-list.sh` lines 511–541 + new UX | `tests/test_helpers.py` (env-patch pattern, error-path coverage) | role-match |
| `tests/conftest.py` | test config | — | `update-list.sh` git repo fixture need | `tests/conftest.py` (factory fixture pattern — extend, do NOT replace) | exact |

---

## Pattern Assignments

### `src/maccat/naming.py` (utility, transform)

**Zsh behavioral analog:** `update-list.sh` — filename convention used throughout (retention lines 957–985, rename lines 791–826, prune lines 1040–1048)

**Phase 13 structural analog:** `src/maccat/helpers/json_io.py`

**Imports pattern** — mirrors json_io.py: stdlib-only, `from __future__ import annotations`:
```python
from __future__ import annotations

import re
from dataclasses import dataclass
```

**Core pattern** — frozen dataclass + pure parse function returning `None` on failure (mirrors `json_get` returning `""` on any error):
```python
_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

@dataclass(frozen=True)
class CatalogFilename:
    machine: str    # folder label without brackets
    timestamp: str  # 14-digit YYYYMMDDHHMMSS string
    filename: str   # full filename

def parse_catalog_filename(filename: str) -> CatalogFilename | None:
    """Returns None (never raises) for non-matching names — mirrors zsh warn-and-continue."""
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

**Zsh reference for regex derivation** (`update-list.sh` lines 964–965, 982–983):
```zsh
local tmp="${filename#*\[}"
local host="${tmp%\]-*}"    # host = text between [ and first ]-
local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
```
The Python regex `\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$` is the exact equivalent: `[^\[\]]+` prevents brackets inside the host label (which `validate_computer_name` also rejects), and `\d{14}` matches the 14-digit timestamp.

**Error handling pattern** — identical to `json_io.py`: return `None`, never raise, caller warns-and-continues.

**Key constraints:**
- `frozen=True` dataclass — immutable, hashable, safe as dict key
- `parse_catalog_filename` returns `None` not raises — every caller must check for `None` before using
- `make_catalog_filename` has NO validation — validation belongs in `validate_computer_name` (caller's job)

---

### `src/maccat/config.py` (service, request-response)

**Zsh behavioral analog:** `update-list.sh` lines 511–541 (`resolve_archive_retention` — non-TTY default, interactive prompt, validation); config init/show is new (no zsh equivalent)

**Phase 13 structural analog:** `src/maccat/catalog/writer.py` (owns atomic write; `src/maccat/__main__.py` for `sys.exit(str)` error pattern)

**Imports pattern:**
```python
from __future__ import annotations

import os
import tempfile
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
```

**Config dataclass pattern** — plain dataclass, single field, `None` means unconfigured:
```python
@dataclass
class Config:
    catalog_dir: Path | None = None
```

**XDG path construction pattern** — direct construction, never `platformdirs` (CFG-02 locked):
```python
def _default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "maccat" / "config.toml"
```

**Config file load pattern** — stdlib `tomllib` (binary open required), returns empty Config on missing file:
```python
def load_config(config_path: Path | None = None) -> Config:
    path = config_path or _default_config_path()
    if not path.is_file():
        return Config()
    with path.open("rb") as f:      # tomllib requires binary mode
        raw = tomllib.load(f)
    raw_dir = raw.get("catalog_dir")
    return Config(catalog_dir=Path(raw_dir).expanduser() if raw_dir else None)
```

**Precedence resolution pattern** — CFG-01 locked; `SystemExit` (not `raise Exception`) on unconfigured:
```python
def resolve_catalog_repo(flag_val: str | None, config: Config) -> Path:
    """Precedence: --catalog-dir flag > MACCAT_CATALOG_DIR env > config file > error."""
    if flag_val:
        return Path(flag_val).expanduser().resolve()
    env_val = os.environ.get("MACCAT_CATALOG_DIR")
    if env_val:
        return Path(env_val).expanduser().resolve()
    if config.catalog_dir:
        return config.catalog_dir.expanduser().resolve()
    raise SystemExit(
        "ERROR: Catalog repo not configured.\n"
        "Options:\n"
        "  1. Run: maccat config init\n"
        "  2. Pass: --catalog-dir /path/to/repo\n"
        "  3. Set:  MACCAT_CATALOG_DIR=/path/to/repo"
    )
```

**Git repo validation pattern** — CFG-06; `subprocess.run` list form (no shell injection), warn-and-continue on missing remote:
```python
def is_git_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True,
    )
    return result.returncode == 0

def validate_catalog_repo(catalog_repo: Path) -> None:
    """Fail fast on missing dir or non-git-repo. Warn-and-continue on missing remote."""
    if not catalog_repo.is_dir():
        raise SystemExit(
            f"ERROR: Catalog directory not found: {catalog_repo}\n"
            f"Run `maccat config init` to configure a valid catalog repo."
        )
    if not is_git_repo(catalog_repo):
        raise SystemExit(
            f"ERROR: {catalog_repo} is not a git repository.\n"
            f"Run `maccat config init` to configure a valid catalog repo."
        )
    result = subprocess.run(["git", "remote"], cwd=catalog_repo, capture_output=True, text=True)
    if not (result.returncode == 0 and result.stdout.strip()):
        print(f"  WARNING: No git remote configured in {catalog_repo}. Changes will not be pushed.")
```

**TOML atomic write pattern** — mirrors `CatalogWriter.__enter__`/`__exit__` tmpfile+rename; TOML basic string escaping:
```python
def _toml_string(s: str) -> str:
    """Escape a string for TOML basic string (double-quoted). Handles \ and " in path."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def write_config(config_path: Path, catalog_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"catalog_dir = {_toml_string(str(catalog_dir))}\n"
    fd, tmp = tempfile.mkstemp(dir=config_path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    Path(tmp).rename(config_path)
```

**`config init` interactive loop pattern** — TTY guard + loop + validate + write; mirrors `resolve_archive_retention` (update-list.sh lines 519–540):
```python
def config_init(config_path: Path | None = None) -> None:
    import sys
    if not sys.stdin.isatty():
        raise SystemExit("ERROR: `maccat config init` requires an interactive terminal.")
    path = config_path or _default_config_path()
    print(f"Config file: {path}")
    while True:
        try:
            raw = input("Enter the path to your catalog repository: ").strip()
        except EOFError:
            raise SystemExit("\nAborted.")
        candidate = Path(raw).expanduser().resolve()
        if not candidate.is_dir():
            print(f"  ERROR: Directory not found: {candidate}")
            continue
        if not is_git_repo(candidate):
            print(f"  ERROR: Not a git repository: {candidate}")
            continue
        write_config(path, candidate)
        print(f"Config written to: {path}")
        break
```

**`config show` output pattern** — print resolved source with precedence label:
```python
# Precedence source labels (exact strings):
# "[from: --catalog-dir flag]"
# "[from: MACCAT_CATALOG_DIR env var]"
# "[from: config file]"
# "(not configured)" when none
```

**Key constraints:**
- `tomllib.load()` requires binary file open (`"rb"`)  — `open("rb")` not `open("r")`
- `--catalog-dir` is NEVER written back to the config file (CFG-03)
- All `subprocess.run` calls use list form, `shell=False` (default) — no shell injection
- `sys.exit(str)` for fatal errors — prints to stderr in one call (matches `__main__.py` pattern)

---

### `src/maccat/identity.py` (service, request-response + file-I/O)

**Zsh behavioral analog:** `update-list.sh` lines 117–175 (`validate_computer_name`, `validate_computer_name_quiet`), lines 308–490 (`select_computer`), lines 557–606 (`upsert_machine_label`), lines 637–923 (`rename_machine`)

**Phase 13 structural analog:** `src/maccat/helpers/chrome_name.py` (multi-function module, each function gracefully degrades, imports at top)

**Imports pattern:**
```python
from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path
```

**Validation pattern** — two variants matching zsh exactly (update-list.sh lines 117–175):
```python
def validate_computer_name(val: str) -> None:
    """Fatal variant — raises SystemExit(1). Used for --computer flag at parse time."""
    if not val:
        raise SystemExit("ERROR: computer name must not be empty")
    if val != val.strip():
        raise SystemExit(
            f"ERROR: computer name must not have leading or trailing whitespace (got '{val}')"
        )
    if any(c in val for c in "/[]"):
        raise SystemExit(
            f"ERROR: computer name must not contain /, [, or ] (got '{val}')"
        )
    if "\t" in val or "\n" in val:
        raise SystemExit("ERROR: computer name must not contain tab or newline characters")


def validate_computer_name_quiet(val: str) -> str | None:
    """Non-fatal variant — returns error string or None if valid. Used in re-prompt loops."""
    if not val:
        return "ERROR: computer name must not be empty"
    if val != val.strip():
        return f"ERROR: computer name must not have leading or trailing whitespace (got '{val}')"
    if any(c in val for c in "/[]"):
        return f"ERROR: computer name must not contain /, [, or ] (got '{val}')"
    if "\t" in val or "\n" in val:
        return "ERROR: computer name must not contain tab or newline characters"
    return None
```

**Folder discovery pattern** — shared between `select_computer` and `rename_machine` (update-list.sh lines 344–394, 644–686); extract as helper:
```python
def discover_computer_folders(catalog_repo: Path) -> list[str]:
    """Union of catalog-bearing dirs and TSV values, deduplicated, alphabetically sorted."""
    seen: set[str] = set()
    computers: list[str] = []

    # Source a: top-level dirs with at least one catalog file
    for d in sorted(catalog_repo.iterdir()):
        if not d.is_dir():
            continue
        if any(d.glob("mac-software-list-*.txt")):
            if d.name not in seen:
                computers.append(d.name)
                seen.add(d.name)

    # Source b: TSV values (folders not yet on disk are still listed)
    map_file = catalog_repo / "machine-labels.tsv"
    if map_file.is_file():
        for line in map_file.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "\t" not in line:
                continue
            label = line.split("\t", 1)[1]
            if label and label not in seen:
                computers.append(label)
                seen.add(label)

    return sorted(computers)
```

**TTY guard + EOF pattern** — must wrap ALL `input()` calls (update-list.sh lines 337–340, 425–427):
```python
# TTY guard — always check BEFORE input(); non-TTY must fail-fast, not hang.
if not sys.stdin.isatty():
    raise SystemExit(
        'ERROR: No computer selected and stdin is not a TTY. Pass --computer "Name".'
    )

# EOF/Ctrl-D handling — NEVER use `except EOFError: continue` (infinite loop regression)
try:
    choice = input("Enter your choice [...]: ")
except EOFError:
    return None   # clean quit — no traceback
```

**`select_computer` menu display exact strings** (update-list.sh lines 401–413):
```
Select a computer:

  1) FolderName   (this machine — default)   ← THREE spaces before paren; only for saved_folder
  2) AnotherFolder
  N) Create new computer
  N+1) Quit
```
Exact strings: `"Select a computer:"`, `"  (this machine — default)"` (three spaces before paren), `"Create new computer"`, `"Quit"`, `"No catalog written."`, `"No default for this machine — please enter a number."`, `"Computer: {name}"`.

**`select_computer` saved-default guard** (update-list.sh lines 447–450) — let it crash, no silent fallback:
```python
# If saved_folder was promoted to position 0 but then not found in computers list:
if saved_folder and saved_folder not in computers:
    raise SystemExit(
        f"ERROR: saved default '{saved_folder}' is not in the computer list."
    )
```

**`upsert_machine_label` atomic write pattern** (update-list.sh lines 557–606) — mirrors `CatalogWriter` tmp+rename:
```python
def upsert_machine_label(catalog_repo: Path, folder: str) -> None:
    map_file = catalog_repo / "machine-labels.tsv"
    current_host = socket.gethostname()

    # Create with header if absent (exact header text from zsh lines 564–567)
    if not map_file.exists():
        map_file.write_text(
            "# Mac Software List — hostname to computer-folder map\n"
            "# Format: hostname\tcomputer-folder\n"
            "# One entry per line. Lines beginning with # and blank lines are ignored.\n",
            encoding="utf-8",
        )

    lines = map_file.read_text(encoding="utf-8").splitlines(keepends=True)
    found = False
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped == "":
            out.append("\n")
        elif stripped.startswith("#"):
            out.append(line if line.endswith("\n") else line + "\n")
        else:
            host = stripped.split("\t", 1)[0]
            if host == current_host:
                out.append(f"{current_host}\t{folder}\n")
                found = True
            else:
                out.append(line if line.endswith("\n") else line + "\n")
    if not found:
        out.append(f"{current_host}\t{folder}\n")

    # Atomic write — same pattern as CatalogWriter (tempfile.mkstemp + rename)
    fd, tmp = tempfile.mkstemp(dir=catalog_repo, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)
    Path(tmp).rename(map_file)
    print(f"  Saved computer folder mapping: {current_host} -> {folder}")
```

**`rename_machine` guards** (update-list.sh lines 747–766) — refuse-clobber is HARD (exit 1, not warning):
```python
# Guard order (update-list.sh lines 748–766):
# 1. No-op guard
if new_name == old_name:
    print(f"WARNING: New name is the same as the old name ('{old_name}'). Nothing renamed.")
    return  # exit 0

# 2. Folder-not-found guard
old_dir = catalog_repo / old_name
if not old_dir.is_dir():
    print(f"WARNING: Computer folder '{old_name}' not found in {catalog_repo}. Nothing renamed.")
    return  # exit 0

# 3. Refuse-clobber (HARD — exit 1, not warning)
new_dir = catalog_repo / new_name
if new_dir.exists():
    raise SystemExit(
        f"ERROR: A computer named '{new_name}' already exists. "
        f"Refusing to merge. Nothing renamed."
    )
```

**`rename_machine` opt-out filename rewrite** (update-list.sh lines 773–826) — default is YES (empty input = yes):
```python
# Rewrite prompt — default is yes (update-list.sh lines 698–703)
try:
    ans = input(f"Rewrite all existing catalogs in '{new_name}' to '[{new_name}]'? [Y/n]: ").strip().lower()
except EOFError:
    ans = ""  # EOF = accept default (yes)
rewrite = ans in ("", "y", "yes")

# Rewrite scope: new_dir/ AND new_dir/archive/ only
# Per-file: only rewrite if label == old_name (skip mixed-label transition files)
# Collision guard: if destination already exists, warn and skip (never overwrite)
```

**Key constraints:**
- `socket.gethostname()` for hostname — matches zsh `$(hostname)` on macOS
- `saved_folder` found but not in list → `SystemExit` (let it crash), never silent fallback (update-list.sh line 447)
- `rename_machine` git-commit wiring is Phase 16; Phase 14 accepts `auto_commit: bool = False` parameter
- Archive subfolder moves with parent via single `old_dir.rename(new_dir)` (same as zsh `mv "$old_dir" "$new_dir"`)

---

### `src/maccat/retention.py` (service, file-I/O)

**Zsh behavioral analog:** `update-list.sh` lines 942–1004 (`retain_newest_per_host`), lines 1022–1064 (`prune_old_archives`)

**Phase 13 structural analog:** `src/maccat/catalog/writer.py` (file-I/O module, OSError handling, `tempfile` pattern established)

**Imports pattern:**
```python
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from maccat.naming import parse_catalog_filename
```

**Two-pass retention pattern** (update-list.sh lines 942–1004) — TDD first:
```python
def retain_newest_per_host(target_dir: Path) -> None:
    archive_dir = target_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Pass 1: find max timestamp per host (update-list.sh lines 957–973)
    newest: dict[str, str] = {}
    for f in target_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            print(f"  WARNING: Could not parse hostname/timestamp from: {f.name}")
            continue
        if cf.machine not in newest or cf.timestamp > newest[cf.machine]:
            newest[cf.machine] = cf.timestamp

    # Pass 2: archive non-newest; tied-newest BOTH kept (update-list.sh lines 976–996)
    moved = 0
    for f in target_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue   # already warned in pass 1
        if cf.timestamp == newest.get(cf.machine, ""):
            continue   # keep (includes tied-newest — both share the max ts)
        try:
            f.rename(archive_dir / f.name)
            moved += 1
        except OSError:
            print(f"  WARNING: Could not archive: {f.name} — leaving in place")
```

**Prune cutoff pattern** (update-list.sh line 1036) — `datetime.now() - timedelta` replaces BSD `date -v-Nd`:
```python
def cutoff_yyyymmdd(archive_days: int) -> str:
    """YYYYMMDD string matching BSD `date -v-{N}d +%Y%m%d`. Uses local time."""
    return (datetime.now() - timedelta(days=archive_days)).strftime("%Y%m%d")
```

**Prune algorithm** (update-list.sh lines 1040–1057) — string comparison is correct for YYYYMMDD:
```python
def prune_old_archives(archive_dir: Path, archive_days: int) -> None:
    if not archive_dir.is_dir():
        print("  No archive directory found — nothing to prune.")
        return

    cutoff = cutoff_yyyymmdd(archive_days)
    pruned = 0
    for f in archive_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            # Unparseable: NEVER delete (update-list.sh lines 1044–1048)
            print(f"  WARNING: Could not parse timestamp from: {f.name} — skipping")
            continue
        file_yyyymmdd = cf.timestamp[:8]   # first 8 chars = YYYYMMDD
        if file_yyyymmdd < cutoff:          # string comparison is correct: YYYYMMDD is lexicographically ordered
            f.unlink()
            pruned += 1
```

**Critical invariants:**
- Two-pass algorithm is mandatory — single-pass with `max()` loses tied-newest files (pitfall 4)
- Unparseable filenames: warn and `continue`, NEVER move or delete (pitfall 3)
- `prune_old_archives` operates ONLY in `archive/` — never touches the main computer folder
- String comparison `<` on YYYYMMDD is correct and intentional (zero-padded ISO date: lexicographic = numeric)
- `archive_dir.mkdir(exist_ok=True)` at the top of `retain_newest_per_host` — create if absent

---

### `tests/conftest.py` (test config — extend, do NOT replace)

**Existing file:** `tests/conftest.py` — `tmp_json` factory fixture (keep this)

**Add two new fixtures** (from RESEARCH.md testing architecture):
```python
# Add after the existing tmp_json fixture

@pytest.fixture
def git_repo(tmp_path: Path):
    """Disposable git repo (no remote) for catalog operations.
    All retention/identity/config tests MUST use this — never the real personal/office dirs."""
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True
    )
    return tmp_path


@pytest.fixture
def catalog_repo(git_repo: Path):
    """Git repo pre-populated with a personal/ computer folder containing one catalog file."""
    from maccat.naming import make_catalog_filename
    computer_dir = git_repo / "personal"
    computer_dir.mkdir()
    ts = "20260614120000"
    catalog = computer_dir / make_catalog_filename("personal", ts)
    catalog.write_text("test catalog", encoding="utf-8")
    return git_repo
```

**Key constraint:** Both new fixtures build on pytest's built-in `tmp_path` — isolation is guaranteed. The existing `tmp_json` fixture must NOT be removed or modified.

---

### `tests/test_naming.py` (test)

**Analog:** `tests/test_format.py` — class-per-function, pure-function unit tests, no fixtures needed

**Test class structure pattern** (mirrors `TestEmitItem` in test_format.py):
```python
from __future__ import annotations

import pytest

from maccat.naming import CatalogFilename, make_catalog_filename, parse_catalog_filename


class TestParseCatalogFilename:
    def test_valid_filename_returns_dataclass(self) -> None: ...
    def test_non_matching_name_returns_none(self) -> None: ...
    def test_brackets_in_machine_name_returns_none(self) -> None: ...  # validate_computer_name blocks these
    def test_13_digit_timestamp_returns_none(self) -> None: ...
    def test_15_digit_timestamp_returns_none(self) -> None: ...
    def test_machine_field_populated_correctly(self) -> None: ...
    def test_timestamp_field_populated_correctly(self) -> None: ...
    def test_gitkeep_not_matched(self) -> None: ...


class TestMakeCatalogFilename:
    def test_round_trip(self) -> None: ...  # make then parse → same machine/ts
    def test_output_format(self) -> None: ...
```

**Import pattern** (matches test_format.py):
```python
from __future__ import annotations
# No pytest import needed for class-based tests unless using pytest.mark or raises
from maccat.naming import CatalogFilename, make_catalog_filename, parse_catalog_filename
```

---

### `tests/test_retention.py` (test — TDD: write before implementation)

**Analog:** `tests/test_writer.py` — `tmp_path`-based file-state assertions; `tests/test_format.py` for class structure

**Fixture usage pattern** — use `catalog_repo` + `make_catalog_filename` from conftest:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.naming import make_catalog_filename
from maccat.retention import prune_old_archives, retain_newest_per_host


class TestRetainNewestPerHost:
    def test_single_file_stays_in_main(self, tmp_path: Path) -> None: ...
    def test_older_file_moved_to_archive(self, tmp_path: Path) -> None: ...
    def test_tied_newest_both_kept(self, tmp_path: Path) -> None: ...
    def test_unparseable_filename_never_moved(self, tmp_path: Path) -> None: ...
    def test_non_catalog_txt_file_untouched(self, tmp_path: Path) -> None: ...
    def test_archive_dir_created_if_absent(self, tmp_path: Path) -> None: ...
    def test_multiple_hosts_independent(self, tmp_path: Path) -> None: ...


class TestPruneOldArchives:
    def test_old_file_deleted(self, tmp_path: Path) -> None: ...
    def test_recent_file_kept(self, tmp_path: Path) -> None: ...
    def test_unparseable_filename_never_deleted(self, tmp_path: Path) -> None: ...
    def test_missing_archive_dir_no_error(self, tmp_path: Path) -> None: ...
    def test_boundary_date_kept(self, tmp_path: Path) -> None: ...  # exactly N days: kept
```

**Key test assertion patterns:**
- `assert (computer_dir / f.name).exists()` for kept files
- `assert (archive_dir / f.name).exists()` for moved files
- `assert not (computer_dir / unparseable_name).exists()` — but unparseable should still exist where it was
- Use `make_catalog_filename()` to create fixture filenames — never hardcode raw strings

---

### `tests/test_identity.py` (test)

**Analog:** `tests/test_helpers.py` — monkeypatch + `unittest.mock.patch`, class-per-function grouping

**Import + mock pattern** (mirrors test_helpers.py deferred imports):
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.identity import (
    discover_computer_folders,
    upsert_machine_label,
    validate_computer_name,
    validate_computer_name_quiet,
)


class TestValidateComputerName:
    def test_valid_name_no_raise(self) -> None: ...
    def test_empty_raises_systemexit(self) -> None: ...
    def test_leading_whitespace_raises(self) -> None: ...
    def test_trailing_whitespace_raises(self) -> None: ...
    def test_slash_raises(self) -> None: ...
    def test_open_bracket_raises(self) -> None: ...
    def test_close_bracket_raises(self) -> None: ...
    def test_tab_raises(self) -> None: ...
    def test_newline_raises(self) -> None: ...


class TestSelectComputer:
    def test_non_tty_exits_with_error(self, tmp_path: Path, monkeypatch) -> None:
        """stdin not a TTY → immediate SystemExit with actionable message."""
        import sys
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        ...

    def test_ctrl_d_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        """EOF on first input → clean return (no traceback)."""
        import sys
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with patch("builtins.input", side_effect=EOFError):
            ...

    def test_enter_with_saved_folder_returns_saved(self, catalog_repo: Path, monkeypatch) -> None:
        """Empty input when saved_folder is set → returns saved_folder."""
        ...


class TestRenameMachine:
    def test_refuse_clobber_exits_1(self, tmp_path: Path, monkeypatch) -> None:
        """Renaming to existing folder name → SystemExit(1), both folders intact."""
        ...
    def test_noop_on_same_name(self, tmp_path: Path) -> None: ...
    def test_folder_not_found_warns_and_returns(self, tmp_path: Path) -> None: ...


class TestUpsertMachineLabel:
    def test_creates_file_with_header_if_absent(self, tmp_path: Path) -> None: ...
    def test_appends_new_host(self, tmp_path: Path) -> None: ...
    def test_updates_existing_host(self, tmp_path: Path) -> None: ...
    def test_preserves_comments_and_blank_lines(self, tmp_path: Path) -> None: ...
    def test_atomic_write_tmp_gone_after(self, tmp_path: Path) -> None: ...
```

---

### `tests/test_config.py` (test)

**Analog:** `tests/test_helpers.py` — env-patch + tmp_path, deferred imports per class

**Pattern:**
```python
from __future__ import annotations

import os
from pathlib import Path

import pytest

from maccat.config import Config, load_config, resolve_catalog_repo


class TestResolveConfigPath:
    def test_default_path_uses_home_config(self, monkeypatch) -> None: ...
    def test_xdg_config_home_override(self, monkeypatch) -> None: ...


class TestLoadConfig:
    def test_missing_file_returns_empty_config(self, tmp_path: Path) -> None: ...
    def test_valid_toml_populates_catalog_dir(self, tmp_path: Path) -> None: ...
    def test_malformed_toml_raises(self, tmp_path: Path) -> None: ...
    def test_missing_catalog_dir_key_returns_none(self, tmp_path: Path) -> None: ...


class TestResolveCatalogRepo:
    def test_flag_wins_over_env_and_config(self, tmp_path: Path, monkeypatch) -> None: ...
    def test_env_wins_over_config(self, tmp_path: Path, monkeypatch) -> None: ...
    def test_config_used_when_no_flag_or_env(self, tmp_path: Path) -> None: ...
    def test_all_absent_raises_systemexit(self) -> None: ...
    def test_flag_not_written_back_to_config(self, tmp_path: Path) -> None: ...  # CFG-03


class TestValidateCatalogRepo:
    def test_missing_dir_raises(self, tmp_path: Path) -> None: ...
    def test_non_git_dir_raises(self, tmp_path: Path) -> None: ...
    def test_valid_git_repo_no_remote_warns(self, git_repo: Path, capsys) -> None: ...
    def test_valid_git_repo_with_remote_no_warn(self, git_repo: Path) -> None: ...
```

---

## Shared Patterns

### Atomic Write (applies to `config.py` and `identity.py`)

**Source:** `src/maccat/catalog/writer.py` (`CatalogWriter.__enter__`/`__exit__` pattern) + `update-list.sh` lines 575–604

Every file write that must be POSIX-atomic uses `tempfile.mkstemp` + `os.fdopen` + `Path.rename`:

```python
fd, tmp = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(out_lines)
Path(tmp).rename(target_path)   # atomic on POSIX/macOS
```

Apply to: `write_config()` in `config.py`, `upsert_machine_label()` in `identity.py`.

### TTY Guard + EOF Clean Exit (applies to `identity.py`, `config.py`)

**Source:** `update-list.sh` lines 337–340 (non-TTY guard) + lines 425–427 (EOF clean quit)

```python
# Guard — check BEFORE any input() call
if not sys.stdin.isatty():
    raise SystemExit("ERROR: ... Pass --computer to run non-interactively.")

# EOF handling — NEVER `except EOFError: continue`
try:
    value = input("prompt: ")
except EOFError:
    return None   # or raise SystemExit("..."), never continue
```

Apply to: `select_computer()`, `rename_machine()`, `config_init()` in respective modules.

### SystemExit for Fatal Errors (all modules)

**Source:** `src/maccat/__main__.py` lines 7–15 (`sys.exit(str)` pattern) + `update-list.sh` line 121 (`exit 1`)

```python
# Pattern: raise SystemExit(message_string) not print + sys.exit(1)
raise SystemExit("ERROR: actionable message\nHint: what to do next")
```

Apply to: all functions in `config.py`, `identity.py`, `retention.py` that detect fatal errors.

### Warn-and-Continue for Non-Fatal Failures (retention.py, config.py)

**Source:** `update-list.sh` lines 966–970 (unparseable file skip), lines 1044–1048 (prune skip)

```python
# Pattern: print warning, continue loop — never move/delete on parse failure
cf = parse_catalog_filename(f.name)
if cf is None:
    print(f"  WARNING: Could not parse hostname/timestamp from: {f.name}")
    continue
```

Apply to: `retain_newest_per_host()`, `prune_old_archives()`, and any caller iterating catalog filenames.

### Module Header Convention (all new `.py` files)

**Source:** `src/maccat/helpers/json_io.py` lines 1–6, `src/maccat/catalog/writer.py` lines 1–10

```python
from __future__ import annotations
# (module docstring as file-level docstring if complex; one-liner if simple)
# stdlib imports only — no third-party
```

Apply to: all four new implementation modules.

### subprocess Safety (config.py git validation)

**Source:** `src/maccat/catalog/format.py` (`flush_section` subprocess pattern) + RESEARCH.md security domain

```python
# Always list form, shell=False (default), capture_output=True
result = subprocess.run(
    ["git", "rev-parse", "--git-dir"],
    cwd=path,
    capture_output=True,   # suppress stdout/stderr to caller's terminal
)
```

Apply to: all `subprocess.run` calls in `config.py`.

---

## No Analog Found

All files in this phase have both a zsh behavioral analog AND a Phase 13 Python structural analog. No file lacks a pattern reference.

The only genuinely new UX (no zsh analog) is `config init` and `config show` — but these follow the existing `resolve_archive_retention` interactive-prompt pattern from `update-list.sh` lines 511–541 for the loop structure, and the `CatalogWriter` atomic-write pattern for the file-write.

---

## Critical Anti-Patterns (do NOT copy these)

| Anti-Pattern | Where It Fails | Correct Pattern |
|---|---|---|
| `except EOFError: continue` in input loop | `select_computer`, `rename_machine`, `config_init` | `except EOFError: return None` (v0.49.0 infinite-loop regression) |
| `input()` without prior `sys.stdin.isatty()` guard | Any interactive function | Always gate with `if not sys.stdin.isatty(): raise SystemExit(...)` first |
| `shutil.move(old_dir, new_dir)` without `new_dir.exists()` check | `rename_machine` | Explicit `if new_dir.exists(): raise SystemExit("ERROR: ... Refusing to merge.")` |
| Single-pass retention with `max()` | `retain_newest_per_host` | Two-pass algorithm; tied-newest must be kept |
| `f.unlink()` after failed `parse_catalog_filename` | `prune_old_archives` | Skip with warning, never delete unparseable files |
| `Path(__file__).parent` or `os.getcwd()` as catalog root | `config.py`, any module | Always resolve from `resolve_catalog_repo()` result |
| `platformdirs` for config path | `config.py` | Direct construction via `Path.home() / ".config" / "maccat" / "config.toml"` with `XDG_CONFIG_HOME` override |
| `open(map_file, "w")` direct write | `upsert_machine_label` | `tempfile.mkstemp` + `Path.rename` (atomic) |
| `tomllib.load(open(path, "r"))` | `load_config` | `tomllib` requires binary mode: `open(path, "rb")` |
| Writing `--catalog-dir` value back to config file | `config.py` | `--catalog-dir` is run-only override; NEVER persisted (CFG-03) |

---

## Metadata

**Analog search scope:** `update-list.sh` (lines 117–1064 read directly), `src/maccat/` (all files), `tests/` (all files)
**Files scanned:** 9 Python source files, `update-list.sh` (relevant sections), 3 test files
**Zsh functions extracted:** `validate_computer_name` (line 117), `validate_computer_name_quiet` (line 156), `parse_arguments` (line 189), `select_computer` (line 308), `resolve_archive_retention` (line 511), `upsert_machine_label` (line 557), `rename_machine` (line 608), `retain_newest_per_host` (line 942), `prune_old_archives` (line 1022)
**Pattern extraction date:** 2026-06-14

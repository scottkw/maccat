# Phase 14: Config, Identity & Retention - Research

**Researched:** 2026-06-14
**Domain:** Python config resolution, interactive CLI menus (argparse + input()), atomic filesystem writes, filename-based retention/prune logic
**Confidence:** HIGH — all behavioral claims derive from direct reading of `update-list.sh` with line-number citations; no speculation.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Environment variable name:** `MACCAT_CATALOG_DIR` (matches the locked `maccat` name used for
  the package, CLI, and `~/.config/maccat/` dir — consistency over the research draft `MAC_CATALOG_DIR`).
- **config.toml schema:** flat top-level key `catalog_dir = "/abs/path"` (not a `[catalog]` table) —
  simplest for a single-value config; easy to extend later. Read with stdlib `tomllib` (3.11+),
  read-only (no toml writer needed beyond `config init`'s own simple emit).
- **Precedence (CFG-01, locked by requirement):** `--catalog-dir` flag > `MACCAT_CATALOG_DIR` env >
  config file `catalog_dir` > clear actionable error. `--catalog-dir` overrides for the run only and
  is NEVER written back to the config file (CFG-03).
- **Config path (CFG-02, locked):** `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml`,
  constructed directly via `Path.home()/".config"/"maccat"/"config.toml"` with `XDG_CONFIG_HOME`
  override — do NOT rely on `platformdirs` (returns `~/Library/Application Support` on macOS).
- **Validation (CFG-06):** before any catalog operation, validate the resolved dir exists AND is a
  git repo (`git rev-parse --git-dir` or equivalent); fail fast with a remediation hint
  (e.g. "Run `maccat config init`"). Absent git remote → warn-and-continue, not fatal.

### Parity-Determined (Claude's Discretion to match the zsh reference exactly)
- The selection menu, `--computer`/aliases + mutual-exclusion, retention two-pass + tied-newest +
  unparseable-skip, prune cutoff, atomic TSV writes, rename refuse-clobber + opt-out rewrite, and
  all interactive-safety behaviors must reproduce the zsh `update-list.sh` behavior.

### Claude's Discretion
- CLI parser library: stdlib `argparse` (research-recommended; zero-dep constraint)
- Exact wording of new error/guidance messages, as long as they are clear and actionable.

### Deferred Ideas (OUT OF SCOPE)
- Named config profiles (multi-catalog-repo)
- The actual git pull/commit/push wiring and generate-then-sweep ordering — Phase 16
- pipx/PyPI distribution channel — v1.1 (PKG-04 deferred)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | Catalog-repo location resolved by precedence: CLI flag > env var > config file > clear error | Section: Config Resolution |
| CFG-02 | Config stored at `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml` | Section: Config Resolution |
| CFG-03 | `--catalog-dir` overrides at runtime without writing back to config file | Section: Config Resolution |
| CFG-04 | `config init` (interactive capture + validate + write) and `config show` (print resolved effective config) | Section: config init / config show |
| CFG-05 | App repo separated from catalog repo — never assumes catalog lives next to executable | Section: Config Resolution |
| CFG-06 | Fail fast when catalog dir missing or not git repo; warn-and-continue on absent remote | Section: Git Repo Validation |
| OPS-01 | Always-shown computer-folder selection menu (existing folders + create-new + Quit, remembered folder as Enter default), TTY-guarded | Section: select_computer — exact behavior |
| OPS-02 | `--computer "Name"` with `--personal`/`--office`/`--machine` aliases and mutual-exclusion | Section: Flag semantics |
| OPS-03 | Newest-per-machine retention: two-pass per-host max-timestamp; tied-newest kept; unparseable-timestamp files skipped | Section: retain_newest_per_host |
| OPS-04 | Archive prune at N days with `--archive-days N` flag (or prompt), correct generate-then-sweep ordering | Section: prune_old_archives |
| OPS-05 | `machine-labels.tsv` hostname→folder map: atomic (tmp + rename) writes, preserving comments/blank lines | Section: upsert_machine_label |
| OPS-07 | `--rename` renames computer folder + archive with opt-out-gated filename rewrite, hard refuse-clobber guard, single-commit map update | Section: rename_machine |
| OPS-08 | Non-TTY runs never hang; EOF/Ctrl-D exits cleanly; invalid input re-prompts | Section: Interactive Safety |
</phase_requirements>

---

## Summary

Phase 14 ports the config-resolution, computer-folder identity, machine-label map, retention/prune, and rename-machine behaviors from `update-list.sh` into the `src/maccat/` package. Phase 13 delivered the package skeleton, `CatalogWriter`, `format.py`, and `helpers/`; Phase 14 adds `config.py`, `identity.py`, `naming.py`, and `retention.py` — the architectural backbone that all later phases thread `catalog_repo` through.

Every behavioral requirement in this phase is directly specified by zsh functions that have been read line-by-line. The behavioral spec does NOT need to be inferred — it is quoted with line numbers throughout this document. The only genuinely new UX this phase adds (that doesn't exist in zsh at all) is `config init` / `config show`: the zsh tool had no config file because it used `SCRIPT_DIR`. The Python implementation needs an interactive first-run setup flow to capture and validate the catalog repo path, and a `config show` to print the resolved effective config.

**Primary recommendation:** Build `naming.py` first (pure functions, no I/O, needed by both `identity.py` and `retention.py`), then `retention.py` (TDD — write tests before implementation, safety-critical), then `identity.py` (interactive menus + atomic TSV), then `config.py` (XDG path, tomllib, TOML writer). The module dependency order within this phase is: naming → retention → identity → config.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config resolution (XDG path, precedence chain) | `config.py` | `cli.py` (consumes) | Pure data resolution; no I/O except file read |
| Config init / config show subcommands | `cli.py` (dispatch) | `config.py` (writes) | CLI parses subcommand; config.py does path logic |
| Computer-folder selection menu | `identity.py` | `cli.py` (calls it) | All menu logic, TTY guard, TSV read belongs here |
| Machine-label TSV read/write | `identity.py` | — | Atomic write owns the file lifetime |
| Catalog filename parse/generate | `naming.py` | — | Pure functions; depended on by identity + retention |
| Retention (two-pass per-host) | `retention.py` | — | Operates on catalog_repo/computer/ path |
| Archive prune (N-day cutoff) | `retention.py` | — | Operates on catalog_repo/computer/archive/ |
| Rename machine folder + files | `identity.py` | — | Closely coupled to TSV update and folder discovery |
| Git repo validation (CFG-06) | `config.py` | — | Runs before any catalog operation; pure check |

---

## Standard Stack

### Core (all stdlib — zero new deps)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `tomllib` | Python 3.11+ stdlib | Read `config.toml` | Locked by PKG-02 / Phase 13 floor; no backport needed |
| `pathlib.Path` | stdlib | All path operations | Already used throughout Phase 13 code |
| `os.replace()` | stdlib | Atomic TSV/config writes | POSIX-atomic: single syscall, never partial file |
| `tempfile.mkstemp()` | stdlib | Temp file for atomic writes | Already pattern-established in `CatalogWriter` |
| `re` | stdlib | Catalog filename parsing | 14-digit timestamp + `[label]` extraction |
| `subprocess.run()` | stdlib | `git rev-parse --git-dir` validation | Already used for sort subprocess in Phase 13 |
| `argparse` | stdlib | CLI flag parsing + mutually-exclusive groups | Locked decision from CONTEXT.md |
| `sys.stdin.isatty()` | stdlib | TTY guard | Direct equivalent of zsh `[[ ! -t 0 ]]` |
| `datetime.timedelta` | stdlib | Prune day-cutoff arithmetic | Replaces BSD `date -v-Nd` |

### No New Third-Party Packages

This phase adds zero new runtime dependencies. All capabilities are stdlib. [VERIFIED: direct inspection of pyproject.toml + Python 3.11 stdlib docs]

### Installation

```bash
# No new packages — everything is stdlib
# Dev tools already installed via Phase 13's pyproject.toml dev extras
./venv/bin/pip install -e ".[dev]"  # already done in Phase 13
```

---

## Package Legitimacy Audit

No external packages are installed in this phase. All code uses Python stdlib only.

| Package | Registry | Notes | Disposition |
|---------|----------|-------|-------------|
| (none) | — | Phase 14 is stdlib-only | N/A |

---

## Architecture Patterns

### Recommended Project Structure (additions this phase)

```
src/maccat/
├── __init__.py          # already exists (Phase 13)
├── __main__.py          # already exists (Phase 13) — stub only
├── catalog/             # already exists (Phase 13)
├── helpers/             # already exists (Phase 13)
│
├── naming.py            # NEW: parse_catalog_filename, make_catalog_filename
├── config.py            # NEW: Config dataclass, load_config, resolve_catalog_repo,
│                        #      validate_catalog_repo, config_init, config_show
├── identity.py          # NEW: select_computer, validate_computer_name,
│                        #      validate_computer_name_quiet, upsert_machine_label,
│                        #      rename_machine
└── retention.py         # NEW: retain_newest_per_host, prune_old_archives

tests/
├── conftest.py          # already exists — add git_repo_fixture and catalog_repo_fixture
├── test_naming.py       # NEW: unit tests for naming.py
├── test_retention.py    # NEW: TDD tests — write before implementing retention.py
├── test_identity.py     # NEW: unit tests (monkeypatch input) for identity functions
└── test_config.py       # NEW: unit tests for config.py (config init/show/resolve)
```

---

## Detailed Behavioral Spec (from zsh source)

This is the authoritative spec section. All findings are [VERIFIED: direct source read of update-list.sh].

---

### 1. `validate_computer_name` and `validate_computer_name_quiet`

**Lines 117–175 of `update-list.sh`.**

Four validation rules (both variants share the same rules):

1. Must be non-empty (`[[ -z "$val" ]]` → error)
2. Must not have leading or trailing whitespace (`[[ "$val" =~ ^[[:space:]] ]] || [[ "$val" =~ [[:space:]]$ ]]`)
3. Must not contain `/`, `[`, or `]` (`[[ "$val" =~ '[][/]' ]]`)
4. Must not contain TAB or newline (`[[ "$val" == *$'\t'* || "$val" == *$'\n'* ]]`)

Difference between the two variants:
- `validate_computer_name` (line 117): calls `exit 1` — used when a flag value fails at parse time
- `validate_computer_name_quiet` (line 156): calls `return 1` and echoes the error reason to stdout — used inside interactive re-prompt loops where you catch the error and loop

Python equivalents:

```python
# [VERIFIED: update-list.sh lines 117-175]

def validate_computer_name(val: str) -> None:
    """Fatal variant — raises SystemExit(1) with actionable message. Used for --computer flag."""
    if not val:
        raise SystemExit("ERROR: computer name must not be empty")
    if val != val.strip():
        raise SystemExit(f"ERROR: computer name must not have leading or trailing whitespace (got '{val}')")
    if any(c in val for c in "/[]"):
        raise SystemExit(f"ERROR: computer name must not contain /, [, or ] (got '{val}')")
    if "\t" in val or "\n" in val:
        raise SystemExit("ERROR: computer name must not contain tab or newline characters")


def validate_computer_name_quiet(val: str) -> str | None:
    """Non-fatal variant — returns error message string, or None if valid. Used in re-prompt loops."""
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

---

### 2. `select_computer` — exact behavior

**Lines 308–490 of `update-list.sh`.** This is the most complex interactive function. Read every detail carefully.

#### 2a. Flag path (lines 310–317)

```zsh
if [[ -n "$TARGET_LOCATION" ]]; then
    mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"   # select-or-create semantics
    upsert_machine_label
    echo "Computer: ${TARGET_LOCATION} (from command-line argument)"
    return
fi
```

When `--computer`/`--personal`/`--office`/`--machine` is set:
1. `mkdir -p` the folder (select-or-create — the folder may not exist yet)
2. `upsert_machine_label` to remember the choice
3. Print `"Computer: {name} (from command-line argument)"`
4. Return immediately — NO menu shown

#### 2b. Map lookup for remembered default (lines 319–334)

```zsh
local current_host=$(hostname)
local saved_folder=""
if [[ -f "$map_file" ]]; then
    while IFS=$'\t' read -r map_host map_label || [[ -n "$map_host" ]]; do
        [[ "$map_host" =~ ^# ]] && continue    # skip comment lines
        [[ -z "$map_host" ]] && continue        # skip blank lines
        if [[ "$map_host" == "$current_host" ]]; then
            saved_folder="$map_label"
            break
        fi
    done < "$map_file"
fi
```

Key: `saved_folder` is the remembered folder for THIS machine's hostname. When set, it shows `"  (this machine — default)"` next to that entry and enables the Enter-default. When not set, Enter without typing a number re-prompts with `"No default for this machine — please enter a number."`.

**The menu is ALWAYS shown** — a found `saved_folder` does NOT fast-exit. It only marks the default.

#### 2c. Non-TTY guard (lines 337–340)

```zsh
if [[ ! -t 0 ]]; then
    echo "ERROR: No computer selected and stdin is not a TTY. Pass --computer \"Name\"."
    exit 1
fi
```

Python equivalent: `if not sys.stdin.isatty(): sys.exit("ERROR: ...")`

#### 2d. Folder discovery (lines 343–394)

Two sources, merged and deduplicated:

**Source a** (lines 360–370): Top-level dirs in `SCRIPT_DIR` that contain at least one `mac-software-list-*.txt` file. Note the `local f=""` assignment — bare `local f` in a loop causes zsh to echo `f=<value>` to stdout (typeset-query behavior), leaking paths into the menu. In Python this is not a concern; just use `Path.glob()`.

**Source b** (lines 373–379): Machine-labels.tsv values (even for folders not yet on disk). Skip comment lines, blank lines, and entries where either column is empty.

**Ordering** (lines 382–394):
1. Sort alphabetically
2. If `saved_folder` is in the list, promote it to index 1 (position 0 in Python)

The promotion guard at line 391 (`if _name_in_list "$saved_folder"`): only promote if `saved_folder` is in the discovered list. If it's not found, no promotion.

#### 2e. Numbered menu display (lines 397–414)

```
(blank line)
Select a computer:
(blank line)
  1) FolderName   (this machine — default)   ← only if this is saved_folder
  2) AnotherFolder
  N) Create new computer
  N+1) Quit
(blank line)
```

Exact text strings:
- `"Select a computer:"` (line 401)
- `"  ${i}) ${computers[$i]}   (this machine — default)"` (line 406) — note THREE spaces before the paren
- `"  ${create_new_idx}) Create new computer"` (line 412)
- `"  ${quit_idx}) Quit"` (line 413)

Indices: `create_new_idx = len(computers) + 1`, `quit_idx = len(computers) + 2`. Both are 1-based.

#### 2f. Input loop (lines 419–460)

Prompt text (lines 421–425):
```zsh
if [[ -n "$saved_folder" ]]; then
    printf "Enter your choice [1-${quit_idx}, or Enter for the default]: "
else
    printf "Enter your choice [1-${quit_idx}]: "
fi
```

EOF/Ctrl-D handling (line 425–427):
```zsh
if ! read -r choice; then        # EOF (Ctrl-D / closed stdin) -> clean quit
    choice="$quit_idx"
fi
```
In Python: `except EOFError: return QuitSelection()` — NOT `continue`, not `raise`.

`q`/`quit` alias (lines 429–431): case-insensitive check; map to `quit_idx`.

Empty input (lines 433–455):
- If `saved_folder` is set: resolve to that folder's index. If `saved_folder` is not found in `computers[]` (edge case), fail loudly: `"ERROR: saved default '${saved_folder}' is not in the computer list."` and `exit 1`. This is the "let it crash" policy — no silent fallback.
- If `saved_folder` is NOT set: re-prompt with `"No default for this machine — please enter a number."`

Invalid input (line 459): `"ERROR: Invalid choice '${choice}'. Please enter 1-${quit_idx}."`

#### 2g. Branch on choice (lines 463–489)

- `quit_idx`: print `"No catalog written."`, `exit 0` — clean quit, no traceback
- `create_new_idx`: enter create-new re-prompt loop:
  ```
  printf "Enter a name for the new computer: "
  EOF -> "No catalog written." + exit 0
  validate_computer_name_quiet → re-prompt on failure
  ```
- Any valid index: `TARGET_LOCATION = computers[choice - 1]` (Python 0-indexed)

After any non-quit branch: print `"Computer: {TARGET_LOCATION}"` and call `upsert_machine_label`.

---

### 3. Flag semantics and mutual-exclusion (`--computer`/`--personal`/`--office`/`--machine`)

**Lines 189–278 of `update-list.sh`.**

All four flags write the same `TARGET_LOCATION` global. The script counts `selecting_flags_seen`:

```zsh
if (( selecting_flags_seen > 1 )); then
    echo "ERROR: --personal, --office, --computer, and --machine are mutually exclusive."
    exit 1
fi
```

- `--personal` → `TARGET_LOCATION="personal"`
- `--office` → `TARGET_LOCATION="office"`
- `--computer "Name"` → validate + set `TARGET_LOCATION="Name"`
- `--machine "Name"` → silent back-compat alias, same as `--computer`

The `--computer` and `--machine` flags require a non-empty value that doesn't start with `--`:
```zsh
if [[ -z "$2" || "$2" == --* ]]; then
    echo "ERROR: --computer requires a value"
    exit 1
fi
```

`--rename` cannot be combined with any selecting flag (line 274–277):
```zsh
if [[ "$RENAME_MODE" == "true" && -n "$TARGET_LOCATION" ]]; then
    echo "ERROR: --rename cannot be combined with a computer-selecting flag ..."
    exit 1
fi
```

`--archive-days N` validates `N` is a positive integer ≥ 1 (lines 230–236).

**Python argparse pattern** (matches ARCHITECTURE.md research):
```python
# [VERIFIED: update-list.sh lines 189-278]
import argparse

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="maccat", add_help=True)
    computer = p.add_mutually_exclusive_group()
    computer.add_argument("--computer", metavar="NAME")
    computer.add_argument("--personal", action="store_const", const="personal", dest="computer")
    computer.add_argument("--office", action="store_const", const="office", dest="computer")
    computer.add_argument("--machine", metavar="NAME", dest="computer")  # silent back-compat
    p.add_argument("--catalog-dir", metavar="PATH", default=None)
    p.add_argument("--no-commit", action="store_true")
    p.add_argument("--archive-days", type=int, default=30, metavar="N")
    p.add_argument("--rename", action="store_true")
    p.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    # config subcommands
    sub = p.add_subparsers(dest="subcommand")
    sub.add_parser("config").add_subparsers(dest="config_cmd")
    return p
```

Note: argparse `add_mutually_exclusive_group()` handles the mutual-exclusion error natively. The `--rename` + selecting-flag check must be done manually after parsing (argparse can't express that constraint natively).

---

### 4. `upsert_machine_label` — TSV format and atomic write

**Lines 557–606 of `update-list.sh`.**

#### TSV format

File path: `${SCRIPT_DIR}/machine-labels.tsv` → in Python: `catalog_repo / "machine-labels.tsv"`

Header created if file doesn't exist (lines 564–568):
```
# Mac Software List — hostname to computer-folder map
# Format: hostname\tcomputer-folder
# One entry per line. Lines beginning with # and blank lines are ignored.
```

Data line format: `hostname\tcomputer-folder\n` (tab-delimited, LF terminated)

#### Atomic write algorithm (lines 575–604)

The key insight from lines 574–576:
```zsh
# Use ': >' not bare '>': a bare redirect runs zsh NULLCMD (cat), which reads
# stdin and hangs on an interactive TTY. ': >' truncates without reading stdin.
: > "$tmp_file"
```
This is the zsh NULLCMD pitfall — not relevant in Python, but worth understanding why the zsh code looks the way it does.

Algorithm:
1. Create tmp file at `{map_file}.tmp`
2. Read original map line-by-line:
   - Blank lines: preserve verbatim (write `\n`)
   - Comment lines (`^#`): preserve verbatim
   - Data lines: split on first TAB, get `map_host = line.split('\t', 1)[0]`
     - If `map_host == current_host`: write `current_host\tcurrent_folder\n`, set `found = True`
     - Otherwise: write original line verbatim
3. If `found` is still False after the loop: append `current_host\tcurrent_folder\n`
4. `mv tmp_file map_file` (Python: `Path(tmp).rename(map_file)`)
5. Print: `"  Saved computer folder mapping: {hostname} -> {folder}"`

Python pattern:
```python
# [VERIFIED: update-list.sh lines 557-606]
import os, tempfile, socket
from pathlib import Path

def upsert_machine_label(catalog_repo: Path, folder: str) -> None:
    map_file = catalog_repo / "machine-labels.tsv"
    current_host = socket.gethostname()

    # Create with header if absent
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
        if stripped == "":           # blank line
            out.append("\n")
        elif stripped.startswith("#"):   # comment
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

    # Atomic write
    fd, tmp = tempfile.mkstemp(dir=catalog_repo, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)
    Path(tmp).rename(map_file)
    print(f"  Saved computer folder mapping: {current_host} -> {folder}")
```

---

### 5. `retain_newest_per_host` — exact retention algorithm

**Lines 942–1004 of `update-list.sh`.**

#### Filename timestamp extraction

The zsh extraction (lines 965, 983):
```zsh
local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
```
This extracts the 14-digit timestamp from the END of the filename before `.txt`. The host label is extracted (lines 964, 982):
```zsh
local tmp="${filename#*\[}"
local host="${tmp%\]-*}"    # strips everything from the first "]-" onward
```

Both host and ts are checked for emptiness; if either fails, a warning is printed and the file is **skipped** (never moved/deleted).

#### Algorithm

**Pass 1** (lines 957–973): For each `mac-software-list-*.txt` in the main folder:
- Parse `host` and `ts`
- If unparseable: warn and `continue` — never delete
- Update `newest_ts[host]` if `ts > newest_ts[host]`

**Pass 2** (lines 976–996): For each file again:
- If unparseable: `continue` (already warned in pass 1)
- If `ts == newest_ts[host]`: `continue` (keep — **includes tied-newest**)
- Otherwise: `mv "$file" "${archive_path}/"` (move to archive)

Python pattern:
```python
# [VERIFIED: update-list.sh lines 942-1004]
from pathlib import Path
import re

_CATALOG_RE = re.compile(r"^mac-software-list-\[(?P<host>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$")

def _parse(filename: str) -> tuple[str, str] | None:
    """Returns (host, ts) or None if unparseable."""
    m = _CATALOG_RE.match(filename)
    if not m:
        return None
    return m.group("host"), m.group("ts")

def retain_newest_per_host(target_dir: Path) -> None:
    archive_dir = target_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Pass 1: find max timestamp per host
    newest: dict[str, str] = {}
    for f in target_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        parsed = _parse(f.name)
        if parsed is None:
            print(f"  WARNING: Could not parse hostname/timestamp from: {f.name}")
            continue
        host, ts = parsed
        if host not in newest or ts > newest[host]:
            newest[host] = ts

    # Pass 2: archive non-newest
    moved = 0
    for f in target_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        parsed = _parse(f.name)
        if parsed is None:
            continue  # already warned in pass 1
        host, ts = parsed
        if ts == newest[host]:  # includes tied-newest
            continue
        try:
            f.rename(archive_dir / f.name)
            print(f"  Archived: {f.name}")
            moved += 1
        except OSError:
            print(f"  WARNING: Could not archive: {f.name} — leaving in place")
    ...
```

**Tied-newest invariant**: Two files for the same host with identical timestamps will both have `ts == newest[host]` in pass 2 → both skipped → both kept. This is the correct two-pass algorithm.

---

### 6. `prune_old_archives` — exact prune algorithm

**Lines 1022–1064 of `update-list.sh`.**

#### Cutoff date computation (line 1036)

```zsh
local cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")
```

BSD `date -v-Nd` subtracts N days from today and formats as `YYYYMMDD`. Python equivalent:
```python
# [VERIFIED: update-list.sh line 1036]
from datetime import datetime, timedelta

def cutoff_yyyymmdd(archive_days: int) -> str:
    """Returns YYYYMMDD string matching BSD `date -v-{N}d +%Y%m%d`."""
    return (datetime.now() - timedelta(days=archive_days)).strftime("%Y%m%d")
```

`datetime.now()` uses local time (same as `date -v`). This is a direct replacement.

#### Prune algorithm (lines 1040–1057)

For each `mac-software-list-*.txt` in `archive/`:
1. Extract timestamp via the same grep/cut pattern as retention (but only 8 digits: `cut -c1-8`)
2. If timestamp empty: print `"  WARNING: Could not parse timestamp from: {filename} — skipping"` and `continue` — **never delete**
3. Compare as strings: `if [[ "$timestamp" -lt "$cutoff_date" ]]` (zsh numeric comparison on YYYYMMDD integers, which works because the format is zero-padded and lexicographic order = numeric order)
4. If old: `rm "$file"`, print `"  Pruned: {filename}"`

Python pattern:
```python
# [VERIFIED: update-list.sh lines 1022-1064]
def prune_old_archives(archive_dir: Path, archive_days: int) -> None:
    if not archive_dir.is_dir():
        print("  No archive directory found — nothing to prune.")
        return

    cutoff = cutoff_yyyymmdd(archive_days)
    pruned = 0
    for f in archive_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        m = re.search(r"(\d{14})\.txt$", f.name)
        if not m:
            print(f"  WARNING: Could not parse timestamp from: {f.name} — skipping")
            continue
        file_yyyymmdd = m.group(1)[:8]  # first 8 digits = YYYYMMDD
        if file_yyyymmdd < cutoff:      # string comparison is correct: YYYYMMDD is lexicographically ordered
            f.unlink()
            print(f"  Pruned: {f.name}")
            pruned += 1
    ...
```

**Critical invariant**: The `prune_old_archives` function only touches files in `archive/`, never in the main computer folder. Files with unparseable timestamps are NEVER deleted.

---

### 7. `rename_machine` — exact behavior

**Lines 637–923 of `update-list.sh`.**

#### TTY guard (lines 638–641)
```zsh
if [[ ! -t 0 ]]; then
    echo "ERROR: --rename requires an interactive terminal (stdin is not a TTY)."
    exit 1
fi
```

#### Folder discovery (lines 644–686)

Same algorithm as `select_computer` but WITHOUT the remembered-default promotion. Returns alphabetically sorted union of (catalog-bearing dirs) ∪ (TSV values).

Empty-list guard (lines 689–692): if no computers found, print `"No computers found. Nothing to rename."` and `exit 0`.

#### Numbered picker (lines 695–727)

```
(blank line)
Select the computer to rename:
(blank line)
  1) FolderName
  ...
  N) Quit
(blank line)
```

- NO `Create new computer` option (rename picker only)
- NO Enter-default (rename picker only)
- `q`/`quit`/EOF → `exit 0` with `"Nothing renamed."` message

#### New name prompt (lines 730–745)

```
Enter new name for '{old_name}': 
EOF -> "Nothing renamed." + exit 0
validate_computer_name_quiet → re-prompt on error
```

#### Guards (lines 747–766)

1. **No-op guard** (lines 748–750): `if new == old: print("WARNING: New name is the same...") + exit 0`
2. **Folder-not-found guard** (lines 758–761): `if ! -d old_dir: print("WARNING: ... not found.") + exit 0`
3. **Refuse-clobber (HARD)** (lines 763–766): `if -e new_dir: print("ERROR: A computer named '...' already exists. Refusing to merge. Nothing renamed.") + exit 1`

#### Folder move (lines 769–771)

```zsh
mv "$old_dir" "$new_dir"
echo "  Renamed folder: ${old_name}/ -> ${new_name}/"
```

Single `mv` — the `archive/` subfolder moves with it.

#### Opt-out-gated filename rewrite (lines 773–826)

```zsh
printf "Rewrite all existing catalogs in '${new_name}' to '[${new_name}]'? [Y/n]: "
read -r rewrite_ans
local lc_ans="${rewrite_ans:l}"
if [[ -z "$lc_ans" || "$lc_ans" == "y" || "$lc_ans" == "yes" ]]; then
    # rewrite filenames
fi
# else: opt-out — filenames keep old [label]; map still updates + commits
```

Default is **yes** (empty input = yes). `n`/`no` opts out.

Rewrite scope: `new_dir/` AND `new_dir/archive/` only.

For each file:
1. Extract `[label]` from filename
2. Only rewrite if `label == old_name` (skip mixed-label transition files)
3. Extract 14-digit timestamp via parameter expansion
4. Construct new filename: `mac-software-list-[{new_name}]-{ts}.txt`
5. Collision guard: if destination already exists, print warning and skip (never overwrite)
6. `mv old_filename new_filename`

#### Map update (lines 833–864)

Unconditional — runs in BOTH rewrite and opt-out modes.

```zsh
if [[ "$line" == *$'\t'* && "${line#*$'\t'}" == "$old_name" ]]; then
    printf '%s\t%s\n' "${line%%$'\t'*}" "$new_name" >> "$tmp_file"
```

Key: only rewrite lines that actually contain a TAB AND whose second column equals `old_name` exactly. Lines without a TAB (hand-edited bare hostname) are preserved verbatim.

#### Git commit (Phase 16 concern — lines 871–918)

This phase implements the rename logic and guards. The actual git add/commit/push wiring is Phase 16. For Phase 14, the function should perform folder move + filename rewrite + TSV update and then stub out the git section (or accept an `auto_commit: bool` parameter and skip the git section when False, matching the `--no-commit` flag).

---

### 8. Config init / config show (new — no zsh equivalent)

These subcommands are genuinely new. The zsh tool had no config file. The Python tool needs them because the catalog repo is no longer inferred from `SCRIPT_DIR`.

#### config init behavior

1. Display current config path: `~/.config/maccat/config.toml`
2. Prompt for catalog repo path:
   ```
   Enter the path to your catalog repository: 
   ```
3. Expand `~`: `Path(input).expanduser().resolve()`
4. Validate:
   - Path exists and is a directory
   - Is a git repo: `subprocess.run(["git", "rev-parse", "--git-dir"], cwd=path, capture_output=True).returncode == 0`
5. If invalid: print error and re-prompt (loop)
6. Write config file:
   ```toml
   catalog_dir = "/absolute/path/to/catalog-repo"
   ```
7. Print: `"Config written to: ~/.config/maccat/config.toml"`

**TOML writing without a toml writer**: Since `tomllib` is read-only, `config init` hand-emits the TOML. The config is a single key-value pair — no quoting ambiguity as long as the path is properly escaped. For a path value, wrap in double quotes and escape any embedded `"` and `\`:

```python
# [ASSUMED] — config init is new; this pattern is based on TOML spec for basic strings
def _toml_string(s: str) -> str:
    """Escape a string for TOML basic string value (double-quoted)."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def write_config(config_path: Path, catalog_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"catalog_dir = {_toml_string(str(catalog_dir))}\n"
    # Atomic write
    fd, tmp = tempfile.mkstemp(dir=config_path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    Path(tmp).rename(config_path)
```

TOML basic string escaping requirements: `\` → `\\`, `"` → `\"`. macOS paths rarely contain these characters, but the code must handle them correctly. [VERIFIED: TOML spec v1.0 — basic strings use backslash escaping]

#### config show behavior

Print the resolved effective config with precedence winner:

```
Catalog repo: /path/to/repo   [from: --catalog-dir flag]
Config file:  ~/.config/maccat/config.toml
```

Or if no source provides a value:
```
Catalog repo: (not configured)
Config file:  ~/.config/maccat/config.toml
  Run `maccat config init` to configure.
```

Precedence source labels:
- `[from: --catalog-dir flag]`
- `[from: MACCAT_CATALOG_DIR env var]`
- `[from: config file]`
- `(not configured)` when none

---

### 9. Git repo validation (CFG-06)

```python
# [VERIFIED: update-list.sh lines 2340, 2387 — pattern used in both git_pull and git_commit_and_push]
import subprocess
from pathlib import Path

def is_git_repo(path: Path) -> bool:
    """Returns True if path is inside a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True,
    )
    return result.returncode == 0

def has_git_remote(path: Path) -> bool:
    """Returns True if the repo has at least one remote configured."""
    result = subprocess.run(
        ["git", "remote"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())

def validate_catalog_repo(catalog_repo: Path) -> None:
    """Fail fast if catalog_repo is missing or not a git repo (CFG-06).
    Warn-and-continue if no remote configured.
    """
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
    if not has_git_remote(catalog_repo):
        print(f"  WARNING: No git remote configured in {catalog_repo}. "
              f"Changes will not be pushed.")
```

---

### 10. `resolve_archive_retention` — non-TTY default

**Lines 511–541 of `update-list.sh`.**

When `--archive-days` was NOT passed AND stdin is not a TTY:
```zsh
if [[ ! -t 0 ]]; then
    echo "Archive retention: ${ARCHIVE_AGE_DAYS} days (non-interactive, using default)"
    return
fi
```
The default (30) is used silently without prompting. This is the correct non-TTY behavior for `--archive-days`.

The interactive prompt is:
```
Archive retention period in days [30]: 
```
Empty → keep default. Non-empty → validate positive integer ≥ 1.

---

### 11. `naming.py` — catalog filename parse/generate

This is a pure module with no I/O. Derived from the filename convention throughout `update-list.sh`.

```python
# [VERIFIED: update-list.sh multiple locations — filename convention is central to the tool]
import re
from dataclasses import dataclass

_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

@dataclass(frozen=True)
class CatalogFilename:
    machine: str    # the folder/label without brackets
    timestamp: str  # 14-digit YYYYMMDDHHMMSS
    filename: str   # full filename

def parse_catalog_filename(filename: str) -> CatalogFilename | None:
    """Returns None (not raises) for non-matching names — mirrors zsh warn-and-continue."""
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

---

## Architecture Patterns

### Pattern 1: Two-level `prompt()` wrapper

All interactive input must go through a wrapper that enforces the TTY guard and handles EOF:

```python
# [VERIFIED: update-list.sh select_computer + PITFALLS.md Pitfall 14/15]
import sys
from typing import Callable

def prompt(msg: str, *, default: str | None = None) -> str:
    """Issue a prompt and return user input.

    Raises SystemExit if stdin is not a TTY (non-interactive context).
    Returns QuitSignal sentinel on EOF (Ctrl-D).
    Never loops — the caller's loop handles re-prompting.
    """
    if not sys.stdin.isatty():
        raise SystemExit(
            "ERROR: Interactive prompt required but stdin is not a TTY. "
            "Pass --computer to run non-interactively."
        )
    try:
        return input(msg)
    except EOFError:
        raise  # caller catches EOFError and returns QuitSelection()
```

The caller's loop then does:
```python
while True:
    try:
        choice = prompt("Enter your choice [1-N]: ")
    except EOFError:
        return None  # clean quit
    # validate choice...
```

This pattern ensures: (1) non-TTY fails fast before blocking, (2) EOF exits cleanly without traceback, (3) `continue` in the except branch is NEVER used.

### Pattern 2: Folder discovery (shared between select_computer and rename_machine)

Both functions use the same two-source discovery algorithm. Extract into a shared helper:

```python
# [VERIFIED: update-list.sh lines 344-394, 644-686]
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

    # Source b: TSV values
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

### Pattern 3: Atomic write utility (established in Phase 13, extend here)

Phase 13 established `CatalogWriter` with atomic tmp+rename. Phase 14 adds the same pattern for `machine-labels.tsv` and `config.toml`. Extract as a shared utility:

```python
# [VERIFIED: update-list.sh upsert_machine_label lines 575-604 + PITFALLS.md Pitfall 10]
import os, tempfile
from pathlib import Path

def atomic_write_text(path: Path, content: str) -> None:
    """Write content to path atomically via tmp + rename (POSIX-atomic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    Path(tmp).rename(path)
```

### Anti-Patterns to Avoid

- **`except EOFError: continue`** in any input loop — this recreates the v0.49.0 infinite-loop regression. Use `except EOFError: return None` (or a `QuitSelection` sentinel) instead. [VERIFIED: update-list.sh line 425-427, PITFALLS.md Pitfall 15]
- **`input()` without TTY guard** — hangs in cron/pipe. ALL `input()` calls must be gated behind `sys.stdin.isatty()`. [VERIFIED: update-list.sh line 337-340, PITFALLS.md Pitfall 14]
- **`Path.rename()` or `shutil.move()` without clobber check** — use `if new_dir.exists(): raise` before any move in `rename_machine`. [VERIFIED: update-list.sh lines 763-766, PITFALLS.md Pitfall 11]
- **Deleting files with unparseable timestamps** — skip with warning, never delete. [VERIFIED: update-list.sh lines 966-970, 1044-1048]
- **`open(map_file, "w")`** for direct write — always use tmp+rename atomic pattern. [VERIFIED: PITFALLS.md Pitfall 10]
- **`Path(__file__).parent` or `os.getcwd()`** as catalog root — always resolve from config. [VERIFIED: PITFALLS.md Pitfall 9]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mutual-exclusion CLI flags | Custom flag conflict detection | `argparse.add_mutually_exclusive_group()` | stdlib, works correctly, produces standard error messages |
| TOML parsing | Custom TOML parser | `tomllib` (Python 3.11+ stdlib) | Already decided in Phase 13 / PKG-02 |
| Atomic file write | Manual open/write/rename | `tempfile.mkstemp` + `os.fdopen` + `Path.rename()` | Already pattern in Phase 13; POSIX-atomic on macOS |
| Date cutoff arithmetic | Reimplementing BSD `date -v` | `datetime.now() - timedelta(days=N)` | stdlib, correct, no macOS-specific behavior |
| Git repo detection | Parsing `.git` directory | `subprocess.run(["git", "rev-parse", "--git-dir"])` | Standard git plumbing, same as zsh reference |
| Hostname | `socket.gethostname()` alternatives | `socket.gethostname()` | stdlib, matches what `hostname` command returns |

**Key insight:** Every piece of "infrastructure" in this phase has a well-worn stdlib equivalent. The custom logic is in the business rules: two-pass retention, tied-newest handling, comment-preserving TSV rewrite, refuse-clobber guard. Don't let infrastructure choices crowd out time for the business logic.

---

## Testing Architecture (Phase 14 specific)

Since `nyquist_validation` is disabled in config.json, no formal validation section is required. However, the phase has two **safety-critical** functions that must be TDD'd:

### Safety-Critical Tests (write BEFORE implementation)

#### `retain_newest_per_host` tests

```python
# tests/test_retention.py

def test_single_file_stays_in_main(tmp_catalog_dir):
    """One file per host — stays in main folder."""

def test_older_file_moved_to_archive(tmp_catalog_dir):
    """Older file moved to archive/; newer stays in main."""

def test_tied_newest_both_kept(tmp_catalog_dir):
    """Two same-host files with identical timestamps: BOTH must stay in main."""

def test_unparseable_filename_never_moved(tmp_catalog_dir):
    """A .txt file with non-matching name is never moved."""

def test_non_catalog_file_untouched(tmp_catalog_dir):
    """.gitkeep or README.md in the folder is never touched."""

def test_archive_dir_created_if_absent(tmp_catalog_dir):
    """archive/ is created if it doesn't exist."""
```

#### `prune_old_archives` tests

```python
def test_old_file_deleted(tmp_archive_dir):
    """File with timestamp older than cutoff is deleted."""

def test_recent_file_kept(tmp_archive_dir):
    """File with timestamp within cutoff is kept."""

def test_unparseable_filename_never_deleted(tmp_archive_dir):
    """File with unparseable name is skipped, not deleted."""

def test_missing_archive_dir_no_error(tmp_catalog_dir):
    """No archive/ directory — returns early, no error."""
```

### Interactive Menu Tests (monkeypatch)

```python
# tests/test_identity.py
from unittest.mock import patch, MagicMock

def test_select_computer_non_tty_exits_fast(tmp_catalog_dir, monkeypatch):
    """stdin not a TTY → immediate exit with error."""
    monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: False))
    with pytest.raises(SystemExit):
        select_computer(tmp_catalog_dir)

def test_select_computer_ctrl_d_clean_quit(tmp_catalog_dir, monkeypatch):
    """EOF (Ctrl-D) → clean exit, no traceback."""
    monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))
    with patch("builtins.input", side_effect=EOFError):
        result = select_computer(tmp_catalog_dir)
    assert result is None  # or a QuitSelection sentinel

def test_select_computer_returns_saved_folder_on_enter(tmp_catalog_dir, monkeypatch):
    """Enter with saved_folder set → returns saved_folder."""
    # setup TSV with current hostname → "personal"
    # patch input to return ""
    ...

def test_rename_machine_refuse_clobber(tmp_catalog_dir, monkeypatch):
    """Renaming to an existing folder name → exit 1 + both folders intact."""
    ...
```

### Disposable Fixtures

All tests MUST use `tmp_path` (pytest's built-in) or `git_repo_fixture` (a new fixture to add to conftest.py):

```python
# tests/conftest.py addition
@pytest.fixture
def git_repo(tmp_path):
    """Create a disposable git repo (no remote) for catalog operations."""
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    return tmp_path
```

This ensures tests never touch the real `personal/`/`office/` folders.

---

## Common Pitfalls

### Pitfall 1: EOF as `continue` in input loop

**What goes wrong:** `except EOFError: continue` recreates the v0.49.0 infinite-loop bug.
**Why it happens:** Looks like "graceful handling" but is wrong — the loop spins forever on closed stdin.
**How to avoid:** `except EOFError: return None` (or a `QuitSelection` sentinel). Test with `input` patched to `side_effect=EOFError`.
**Warning signs:** `except EOFError: continue` anywhere in the codebase.
**Source:** [VERIFIED: update-list.sh line 425-427, PITFALLS.md Pitfall 15, v0.49.0 UAT defect record]

### Pitfall 2: Non-TTY hang

**What goes wrong:** `input()` blocks when stdin is an open-but-non-TTY pipe.
**Why it happens:** `input()` blocks on non-EOF non-TTY stdin.
**How to avoid:** Gate ALL `input()` calls with `sys.stdin.isatty()`. The TTY check must happen BEFORE the `input()` call, not after.
**Warning signs:** Direct `input()` anywhere outside the `prompt()` wrapper.
**Source:** [VERIFIED: update-list.sh line 337-340, PITFALLS.md Pitfall 14]

### Pitfall 3: Prune deleting unparseable files

**What goes wrong:** A non-catalog `.txt` file in `archive/` gets deleted.
**Why it happens:** Matching `*.txt` and treating parse failure as "file is old".
**How to avoid:** Parse failure → skip with warning, NEVER delete. Only delete files that successfully parse AND have a timestamp older than cutoff.
**Warning signs:** Any `file.unlink()` inside an `except` or after a failed parse.
**Source:** [VERIFIED: update-list.sh lines 1044-1048, PITFALLS.md Pitfall 7]

### Pitfall 4: Single-pass retention loses tied-newest files

**What goes wrong:** Using `max()` and archiving everything else in one pass → tied files are lost.
**Why it happens:** `max()` returns a single value; "keep the max" sounds correct.
**How to avoid:** Two-pass algorithm. Pass 1 builds `newest: dict[str, str]`; Pass 2 keeps only files with `ts == newest[host]`.
**Warning signs:** Single loop with `if ts < current_max: archive`.
**Source:** [VERIFIED: update-list.sh lines 942-1004, PITFALLS.md Pitfall 8]

### Pitfall 5: `rename_machine` missing refuse-clobber check

**What goes wrong:** `shutil.move(old_dir, new_dir)` without checking `new_dir.exists()` first — merges two computer folders irreversibly.
**Why it happens:** `shutil.move` "works" on some filesystems without raising.
**How to avoid:** Explicit `if new_dir.exists(): raise SystemExit("ERROR: ...")` before ANY move operation.
**Warning signs:** Any `shutil.move` or `Path.rename()` in `rename_machine` without a prior `.exists()` check.
**Source:** [VERIFIED: update-list.sh lines 763-766, PITFALLS.md Pitfall 11]

### Pitfall 6: Saved default not found in computer list → corrupt output

**What goes wrong:** The zsh tool has an explicit guard (line 447): if `saved_folder` is not in `computers[]`, fail loudly instead of silently using index 0.
**Why it happens:** After a rename or manual TSV edit, the saved folder may no longer exist.
**How to avoid:** After resolving empty-input to saved_folder, verify the folder is still in the list. Raise with `"ERROR: saved default '{saved_folder}' is not in the computer list."` — do NOT silently fall through.
**Source:** [VERIFIED: update-list.sh lines 447-451]

### Pitfall 7: TOML writing with untrusted path content

**What goes wrong:** A catalog path containing `"` or `\` breaks the hand-emitted TOML.
**Why it happens:** macOS paths rarely contain these, so testing with `/Users/ken/dev/catalog` never exercises the edge case.
**How to avoid:** Always escape `\` → `\\` and `"` → `\"` in the TOML basic string.
**Source:** [ASSUMED — TOML spec requirement; macOS paths don't contain these characters in practice but the code must be correct]

---

## Code Examples

### Filename parsing (naming.py)
```python
# [VERIFIED: update-list.sh filename convention used throughout]
import re
from dataclasses import dataclass

_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

@dataclass(frozen=True)
class CatalogFilename:
    machine: str
    timestamp: str
    filename: str

def parse_catalog_filename(filename: str) -> "CatalogFilename | None":
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    return CatalogFilename(machine=m.group("machine"), timestamp=m.group("ts"), filename=filename)

def make_catalog_filename(machine: str, timestamp: str) -> str:
    return f"mac-software-list-[{machine}]-{timestamp}.txt"
```

### Config resolution (config.py)
```python
# [VERIFIED: CONTEXT.md locked decisions + tomllib stdlib docs]
import os, tomllib
from dataclasses import dataclass
from pathlib import Path

def _default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "maccat" / "config.toml"

@dataclass
class Config:
    catalog_dir: Path | None = None

def load_config(config_path: Path | None = None) -> Config:
    path = config_path or _default_config_path()
    if not path.is_file():
        return Config()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    raw_dir = raw.get("catalog_dir")
    return Config(catalog_dir=Path(raw_dir).expanduser() if raw_dir else None)

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

### Two-pass retention (retention.py)
```python
# [VERIFIED: update-list.sh lines 942-1004]
from pathlib import Path
from maccat.naming import parse_catalog_filename

def retain_newest_per_host(target_dir: Path) -> None:
    archive_dir = target_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Pass 1: max timestamp per host
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

    # Pass 2: archive non-newest (keep tied-newest)
    moved = 0
    for f in target_dir.glob("mac-software-list-*.txt"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue  # already warned
        if cf.timestamp == newest.get(cf.machine, ""):
            continue  # keep (includes tied-newest)
        try:
            f.rename(archive_dir / f.name)
            print(f"  Archived: {f.name}")
            moved += 1
        except OSError:
            print(f"  WARNING: Could not archive: {f.name} — leaving in place")
    if moved == 0:
        print("  No older catalogs to archive.")
    else:
        print(f"  Archived {moved} catalog(s) to {target_dir.name}/archive/")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SCRIPT_DIR` as catalog root | Config-resolved `catalog_repo: Path` | v1.0.0 (this milestone) | Enables pipx/zipapp distribution; app repo ≠ catalog repo |
| `date -v-Nd` BSD date arithmetic | `datetime.now() - timedelta(days=N)` | v1.0.0 (this phase) | Cross-platform, timezone-safe, no subprocess |
| jq + plutil subprocess chain for JSON | `tomllib` (stdlib) for TOML | v1.0.0 | Zero external dep; faster; correct |
| Zsh globals as parameters | `Config` + `RunContext` frozen dataclass | v1.0.0 | Testable, no global state, clear data flow |
| `[[ ! -t 0 ]]` TTY guard | `sys.stdin.isatty()` | v1.0.0 | Direct equivalent; same semantics |
| `: > file` (NULLCMD guard) | `tempfile.mkstemp()` | v1.0.0 | No zsh NULLCMD concern in Python; still atomic |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `config init` hand-emits TOML with `\` and `"` escaping; TOML basic string escaping is correct | Config init / config show | Config file unreadable by `tomllib` on paths with backslash/quote (macOS paths don't contain these in practice) |
| A2 | `config show` output format (precedence winner labels and layout) — no zsh equivalent to compare against | Config init / config show | UX only — easy to adjust after planner review |
| A3 | `socket.gethostname()` returns the same value as the zsh `$(hostname)` call | upsert_machine_label | TSV entry uses wrong key → menu won't show saved default |

**A3 note:** On macOS, `socket.gethostname()` and `hostname` both return the machine's local hostname (e.g., `computer-one.local`). [ASSUMED — matches typical macOS behavior but should be verified in early testing with `python3 -c "import socket; print(socket.gethostname())"` vs `hostname` on the dev machine.]

---

## Open Questions

1. **`socket.gethostname()` vs `hostname` command output**
   - What we know: Both should return the same short hostname on macOS
   - What's unclear: Edge cases on machines with custom FQDN or when the hostname contains dots
   - Recommendation: Add a test early: `assert socket.gethostname() == subprocess.check_output(["hostname"]).decode().strip()`; if they differ, use `subprocess.run(["hostname"])` for exact parity

2. **`rename_machine` git commit in Phase 14 vs Phase 16**
   - What we know: The CONTEXT.md says the rename logic + guards land in Phase 14; the actual git commit wires in Phase 16
   - What's unclear: Should `rename_machine` in Phase 14 accept an `auto_commit: bool` parameter and call a stub, or should the git section simply not exist in Phase 14?
   - Recommendation: Implement `rename_machine` with a `auto_commit: bool = False` parameter; the git section is either a stub or a pass-through to an injected `git_commit_fn`; Phase 16 fills it in

3. **`--archive-days` interactive prompt in Phase 14 vs Phase 16**
   - What we know: `resolve_archive_retention` is interactive (prompts when not set and stdin is TTY)
   - What's unclear: Does this interactive prompt belong in `identity.py` or `cli.py`?
   - Recommendation: Keep it in `cli.py` dispatch since it's argument resolution, not identity/folder logic

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code (tomllib) | ✓ | 3.14 (see pycache) | None — hard requirement |
| `git` CLI | CFG-06 validation, rename commit | ✓ | Built-in macOS | None — tool requires git repo |
| `pytest` | Test suite | ✓ | 9.1.0 (pycache evidence) | None |
| `ruff` | Linting | ✓ | ≥0.15 (pyproject.toml) | None |
| `socket` | `gethostname()` | ✓ | stdlib | `subprocess.run(["hostname"])` |

**Missing dependencies with no fallback:** None.

---

## Security Domain

The `security_enforcement` key is not set in `.planning/config.json`, so security review is enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user authentication in CLI tool |
| V3 Session Management | No | Stateless CLI |
| V4 Access Control | No | Single-user personal tool |
| V5 Input Validation | Yes | `validate_computer_name` / `validate_computer_name_quiet` |
| V6 Cryptography | No | No secrets handled |

### Known Threat Patterns for this Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--catalog-dir` or computer name | Tampering | `Path.resolve()` on `catalog_dir`; `validate_computer_name` rejects `/` |
| Shell injection via computer folder name in git subprocess | Tampering | `subprocess.run([...list...], shell=False)` — already established pattern; pass `--` before pathspec |
| Partial TSV write corrupts machine-labels.tsv | Tampering | Atomic tmp+rename; never open TSV directly for write |
| Config file world-readable exposes catalog repo path | Information Disclosure | `config.toml` created with default umask (0o644); acceptable for path-only config on a personal macOS machine |

---

## Sources

### Primary (HIGH confidence)
- `update-list.sh` lines 117–1064, 2316–2431 — direct read of all Phase 14 behavioral functions with line-number citations
- `src/maccat/` Phase 13 output — direct inspection of existing package structure, `__main__.py`, `catalog/writer.py`, `catalog/format.py`, `helpers/`
- `pyproject.toml` — confirmed: `requires-python = ">=3.11"`, zero runtime deps, `maccat` package name
- `tests/conftest.py` — confirmed existing fixture infrastructure (`tmp_json`)
- `.planning/phases/14-config-identity-retention/14-CONTEXT.md` — locked decisions
- Python 3.11 stdlib docs: `tomllib`, `pathlib`, `argparse`, `tempfile`, `os.replace`, `subprocess`, `socket`, `datetime` [ASSUMED — standard stdlib, well-documented]

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — Config dataclass pattern, `resolve_catalog_repo` design (uses stale names `maclist`/`MAC_CATALOG_DIR` — translated)
- `.planning/research/PITFALLS.md` — Pitfalls 7, 8, 9, 10, 11, 14, 15 all directly relevant to this phase
- `.planning/research/SUMMARY.md` — `datetime.timedelta` as BSD date replacement (confirmed)

---

## Metadata

**Confidence breakdown:**
- Behavioral spec (select_computer, retention, prune, rename): HIGH — all from direct zsh source reading with line citations
- Python implementation patterns: HIGH — all stdlib, well-established, matches Phase 13 patterns
- config init/show UX: MEDIUM — new behavior, no zsh reference; output format is at Claude's discretion

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable domain — Python stdlib + zsh behavior spec; no fast-moving dependencies)

# Phase 26: Picker + CLI Wiring + Integration - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 4 (2 new modules, 1 modified, 1 new test)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/maccat/reinstall/picker.py` | utility | request-response | `src/maccat/retention.py` (pass-1 loop) + `src/maccat/identity.py` (select_computer) | role-match (composite) |
| `src/maccat/reinstall/cli.py` | service/orchestrator | request-response | `src/maccat/cli.py` run() dispatch shape + reinstall/emitter.py conventions | role-match |
| `src/maccat/cli.py` (modify) | controller/entry-point | request-response | itself — existing `_build_parser()` config subparser block + run() step 4 | exact (self-analog) |
| `tests/reinstall/test_reinstall_cli.py` | test | request-response | `tests/test_cli.py` (TestConfigDispatch + helpers) | exact |

---

## Pattern Assignments

### `src/maccat/reinstall/picker.py` (utility, request-response)

**Analogs:** `src/maccat/retention.py` (lines 62-72) + `src/maccat/identity.py` (lines 80-99, 260-293)

**Imports pattern** — mirror retention.py line 1 + identity.py line 1:
```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from maccat.naming import parse_catalog_filename
```
Note: `maccat.identity` imports are deferred inside the picker-branch body (PKG-03 lazy import pattern mirroring cli.py lines 129-148).

**Core pattern — `_find_newest_catalog` helper** (mirrors retention.py lines 62-72, pass 1 loop):
```python
# src/maccat/retention.py lines 62-72
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
```
Picker variant scans a single folder for a single machine: replace `newest: dict` with `best_ts: str | None` + `best_path: Path | None`; drop the `print` warning (no machine dict, just skip). Lexicographic `>` on `cf.timestamp` (14-digit YYYYMMDDHHMMSS) is correct — same as retention.py.

**Core pattern — resolve flow** (mirrors identity.py lines 80-99 and cli.py lines 215-219):
```python
# src/maccat/identity.py lines 80-99 — resolve_computer_selection
def resolve_computer_selection(*, computer: str | None) -> str | None:
    if not computer:
        return None
    validate_computer_name(computer)
    return computer

# src/maccat/cli.py lines 215-219 — None-quit guard
computer_pre = resolve_computer_selection(computer=args.computer)
computer = select_computer(catalog_repo, computer_name=computer_pre)
if computer is None:
    # User chose Quit — no catalog written, no git ops
    return
```
`resolve_catalog_path` replicates the two-call chain (`resolve_computer_selection` → `select_computer`) and must include the `if computer is None` guard. Return `None` on quit; caller (`run_reinstall`) handles it with a clean `return` (same as cli.py line 219).

**Error handling pattern** — `sys.exit(f"ERROR: ...")` for fatal validation failures:
```python
# src/maccat/identity.py lines 42-43, 48-50 — validate_computer_name fatal pattern
if not val:
    raise SystemExit("ERROR: computer name must not be empty")
...
if any(c in val for c in "/[]"):
    raise SystemExit(f"ERROR: computer name must not contain /, [, or ] (got '{val}')")
```
For picker.py: use `sys.exit(f"ERROR: ...")` (not `raise SystemExit`) — matches cli.py style at lines 166-168, 189-191.

---

### `src/maccat/reinstall/cli.py` (orchestrator, request-response)

**Analogs:** `src/maccat/cli.py` run() orchestration (lines 108-283) + `src/maccat/reinstall/emitter.py` conventions

**Imports pattern** — deferred maccat.* imports inside function body (mirrors cli.py lines 129-148):
```python
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path
```
All `maccat.reinstall.*` imports go INSIDE `run_reinstall()` body, not at module level. This mirrors:
```python
# src/maccat/cli.py lines 129-148
def run() -> None:
    from maccat import gitops
    from maccat.catalog.format import flush_section
    from maccat.catalog.writer import CatalogWriter
    from maccat.collectors import get_registry
    from maccat.config import (...)
    from maccat.identity import (...)
    from maccat.naming import make_catalog_filename
    from maccat.retention import prune_old_archives, retain_newest_per_host
```

**Core pattern — pipeline orchestration** (mirrors cli.py steps 9-13 structure):
```python
# PIPELINE inside run_reinstall:
# 1. resolve  → catalog_path
# 2. parse    → catalog object
# 3. emit     → script string
# 4. write    → file at 0o644
# 5. print    → absolute path

# File write + chmod (stdlib idiom):
output_path = Path.cwd() / "reinstall.sh"
output_path.write_text(script, encoding="utf-8")
os.chmod(output_path, 0o644)
print(str(output_path.resolve()))
```
`Path.cwd()` is called INSIDE `run_reinstall()` body — never at module level (see Pitfall 6 in RESEARCH.md).

**Provenance values pattern** — date as `YYYY-MM-DD`:
```python
generated = date.today().strftime("%Y-%m-%d")
source_name = catalog_path.name   # bare filename, not full path
```
Matches `emit_reinstall_script` contract (emitter.py lines 253-256): `source_name` is the human-readable catalog basename; `generated` is the date string.

**Error handling pattern** — clean return on picker-quit (mirrors cli.py lines 217-219):
```python
catalog_path = resolve_catalog_path(args, catalog_repo=catalog_repo)
if catalog_path is None:
    return   # user quit picker — no file written, exit 0
```

---

### `src/maccat/cli.py` — Modifications (controller, request-response)

**Analog:** itself — `_build_parser()` lines 95-105 and `run()` lines 194-210

**Subparser addition pattern** (lines 95-103 — add after line 103):
```python
# src/maccat/cli.py lines 95-103 — existing config subparser block
subparsers = parser.add_subparsers(dest="subcommand")
config_parser = subparsers.add_parser(
    "config",
    help="Configuration management subcommands",
)
config_sub = config_parser.add_subparsers(dest="config_subcommand")
config_sub.add_parser("init", help="Interactive first-run setup")
config_sub.add_parser("show", help="Print effective configuration")
```
Add immediately after line 103, before `return parser`:
```python
reinstall_parser = subparsers.add_parser(
    "reinstall",
    help="Generate reinstall.sh from a catalog",
)
reinstall_parser.add_argument(
    "--from",
    metavar="PATH",
    dest="from_path",     # MUST use dest= — "from" is a Python keyword
    default=None,
    help="Explicit catalog file path (skips computer picker)",
)
```

**Dispatch insertion — step 4 split** (lines 197-210 — the exact neighborhood to modify):
```python
# src/maccat/cli.py lines 197-210 — current monolithic step 4
cfg = load_config()
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
validate_catalog_repo(catalog_repo)

auto_commit = not args.no_commit

# ------------------------------------------------------------------
# 5. --rename short-circuit (update-list.sh:2447-2451)
# ------------------------------------------------------------------
if args.rename:
    gitops.git_pull(catalog_repo)
    rename_machine(catalog_repo, auto_commit=auto_commit)
    return
```
Replace with split 4a/4b/4c/4d:
```python
# 4a. Config load
cfg = load_config()

# 4b. Reinstall --from dispatch (before resolve_catalog_repo — no repo needed)
if args.subcommand == "reinstall" and args.from_path is not None:
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args)
    return

# 4c. Resolve + validate catalog repo (all remaining paths need it)
catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
validate_catalog_repo(catalog_repo)
auto_commit = not args.no_commit

# 4d. Reinstall picker dispatch (after repo validated — picker needs catalog_repo)
if args.subcommand == "reinstall":
    if args.rename:
        sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo=catalog_repo)
    return

# 5. --rename short-circuit (UNCHANGED — lines 207-210)
if args.rename:
    ...
```

**Config dispatch guard pattern** (lines 159-168 — template for the reinstall guard):
```python
# src/maccat/cli.py lines 159-168 — config subcommand guard
if args.subcommand == "config":
    if any([args.rename, args.computer]):
        sys.exit(
            "ERROR: --rename and --computer cannot be combined with the 'config' subcommand."
        )
```
The reinstall guard checks only `args.rename` (not `args.computer` — `--computer` flows through legitimately for picker mode).

**Deferred import pattern** (lines 129-148, 595-596 — both models for the reinstall import):
```python
# src/maccat/cli.py lines 129-148 — bulk deferred import at top of run()
from maccat import gitops
...

# src/maccat/identity.py lines 595-596 — conditional deferred import inside branch
if auto_commit:
    from maccat import gitops
    gitops.git_commit_rename(catalog_repo, old_name, new_name)
```
The reinstall dispatch uses the second model: `from maccat.reinstall.cli import run_reinstall` lives INSIDE the `if args.subcommand == "reinstall":` block. NOT at the top of `run()`. Appears twice (4b and 4d blocks) — both are valid; only one branch executes per invocation.

---

### `tests/reinstall/test_reinstall_cli.py` (test, request-response)

**Analog:** `tests/test_cli.py` (lines 1-473) + `tests/conftest.py` (lines 1-56)

**File header + imports pattern** (mirrors test_cli.py lines 1-13):
```python
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
```

**Fixture catalog pattern** — write a minimal valid catalog to `tmp_path`:
```python
# Pattern from conftest.py lines 43-55 — catalog_repo fixture
@pytest.fixture()
def catalog_repo(git_repo: Path) -> Path:
    from maccat.naming import make_catalog_filename
    computer_dir = git_repo / "personal"
    computer_dir.mkdir()
    catalog = computer_dir / make_catalog_filename("personal", "20260614120000")
    catalog.write_text("test catalog", encoding="utf-8")
    return git_repo
```
Phase 26 test variant: write to `tmp_path` directly (no git repo needed for `--from` mode). Filename must match the `mac-software-list-[{machine}]-{timestamp}.txt` convention (naming.py line 19) so `parse_catalog_filename` can parse it.

**In-process test invocation pattern** (mirrors test_cli.py lines 135-140, 203-210):
```python
# src/tests/test_cli.py lines 135-140
monkeypatch.setattr(sys, "argv", ["maccat", "--rename", "--computer", "box"])
from maccat.cli import run
with pytest.raises(SystemExit) as exc:
    run()
assert exc.value.code != 0

# src/tests/test_cli.py lines 203-210
monkeypatch.setenv("MACCAT_CATALOG_DIR", str(catalog_repo))
monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])
from maccat.cli import run
run()
mocks["git_commit_and_push"].assert_not_called()
```
For reinstall `--from` mode: no `MACCAT_CATALOG_DIR` env needed (the whole point of the `--from` branch is no repo required). Use `monkeypatch.chdir(tmp_path)` so `Path.cwd() / "reinstall.sh"` lands in `tmp_path`.

**chdir + cwd pattern** — test isolation:
```python
monkeypatch.chdir(tmp_path)   # pytest 3.9+ — restores cwd after test
# then:
output = tmp_path / "reinstall.sh"
assert output.exists()
```

**Mode assertion pattern** (CONTEXT.md specifics):
```python
assert oct(output.stat().st_mode & 0o777) == "0o644"
```

**Side-effect mock pattern** (mirrors test_cli.py lines 163-185 `_patch_run_dependencies`):
```python
# For reinstall tests: mock git_pull to prove it is NOT called
mock_pull = MagicMock()
monkeypatch.setattr("maccat.gitops.git_pull", mock_pull)
# ...
mock_pull.assert_not_called()   # reinstall returns before any git ops
```

**Exit-code pattern** (mirrors test_cli.py lines 405-410):
```python
# Non-zero exit:
with pytest.raises(SystemExit) as exc:
    run()
assert exc.value.code != 0

# Exit 0 (success): no SystemExit raised — assert run() returns normally
run()  # no pytest.raises wrapping = success assertion
```

**Gen-path non-trigger assertion** (mirrors test_cli.py lines 289-298):
```python
# No mac-software-list-*.txt written anywhere (reinstall dispatches before gen path)
txt_files = list(tmp_path.glob("mac-software-list-*.txt"))
assert len(txt_files) == 0
# The fixture catalog itself is named mac-software-list-*.txt — do NOT glob there;
# check that no NEW catalog was created in the cwd or catalog_repo dirs.
```

---

## Shared Patterns

### Deferred maccat.* Imports (PKG-03)
**Source:** `src/maccat/cli.py` lines 129-148 and identity.py lines 594-596
**Apply to:** `src/maccat/reinstall/picker.py` (identity imports), `src/maccat/reinstall/cli.py` (all reinstall.* imports), modified `src/maccat/cli.py` dispatch blocks

All `maccat.*` module imports in `cli.py::run()` and in any new orchestrator live INSIDE function bodies. Top-level imports in new modules are stdlib-only (`argparse`, `os`, `pathlib`, `datetime`, `sys`). Deferred `maccat.*` imports live in the function body closest to their first use.

### Error Handling — sys.exit("ERROR: ...")
**Source:** `src/maccat/cli.py` lines 166-168, 189-191
**Apply to:** `src/maccat/reinstall/picker.py`, `src/maccat/reinstall/cli.py`, modified `cli.py` dispatch blocks

```python
# src/maccat/cli.py lines 166-168 — canonical pattern
sys.exit(
    "ERROR: --rename and --computer cannot be combined with the 'config' subcommand."
)
```
All fatal user-facing errors use `sys.exit("ERROR: ...")`. Never bare `raise SystemExit` in cli-layer code (that form is for validators like `validate_computer_name`).

### from __future__ import annotations (line 1)
**Source:** every existing `src/maccat/*.py` module
**Apply to:** all new files

Every new file starts with `from __future__ import annotations` as line 1, before any other imports. This is a project-wide invariant in all maccat Python modules.

### Null-Glob Guard
**Source:** `src/maccat/retention.py` lines 64-65
**Apply to:** `src/maccat/reinstall/picker.py::_find_newest_catalog`

```python
for f in target_dir.glob("mac-software-list-*.txt"):
    if not f.is_file():
        continue
```
Always check `f.is_file()` inside glob loops — symlinks, dirs, or race-created entries can match the glob pattern.

### Test Class + Fixture Organization
**Source:** `tests/test_cli.py` lines 35-124 (TestArgparse), 194-260 (TestNoCommit)
**Apply to:** `tests/reinstall/test_reinstall_cli.py`

Each logical concern gets its own `class Test*:` block. Shared fixtures are `@pytest.fixture()` methods on the class. The module-level `_patch_run_dependencies` helper in `test_cli.py` (lines 149-186) shows the shared-mock-wiring pattern for multi-test classes.

---

## No Analog Found

All four files have analogs. No entries.

---

## Metadata

**Analog search scope:** `src/maccat/`, `src/maccat/reinstall/`, `tests/`, `tests/reinstall/`
**Files read:** 10 source files
**Pattern extraction date:** 2026-06-16

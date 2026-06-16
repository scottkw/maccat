---
phase: 26-picker-cli-wiring-integration
plan: "01"
subsystem: reinstall
tags: [cli, reinstall, picker, integration, tdd]
dependency_graph:
  requires: [24-01, 25-01]
  provides: [maccat-reinstall-subcommand]
  affects: [src/maccat/cli.py, src/maccat/reinstall/]
tech_stack:
  added: []
  patterns: [deferred-imports-PKG-03, two-point-dispatch, tdd-red-green]
key_files:
  created:
    - src/maccat/reinstall/picker.py
    - src/maccat/reinstall/cli.py
    - tests/reinstall/test_reinstall_cli.py
    - tests/reinstall/test_picker_and_reinstall_cli.py
  modified:
    - src/maccat/cli.py
decisions:
  - "Two-point dispatch in cli.py run(): 4b before resolve_catalog_repo (--from mode, repo-agnostic) and 4d after validate_catalog_repo (picker mode, repo required)"
  - "resolve_catalog_path returns None on picker-quit (not sys.exit); run_reinstall handles with clean return matching existing cli.py lines 217-219 pattern"
  - "dest='from_path' explicit on --from argument to avoid Python keyword conflict and trailing-underscore confusion"
  - "Deferred maccat.* imports inside each if-block per PKG-03 (appears twice, only one branch executes per run)"
metrics:
  duration: "~30 min"
  completed: "2026-06-16"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 1
---

# Phase 26 Plan 01: Picker + CLI Wiring + Integration Summary

Closed the v2.1.0 milestone by wiring Phase 24 parser + Phase 25 emitter into a working `maccat reinstall` subcommand — explicit `--from PATH` or interactive computer picker, writes `reinstall.sh` mode 0o644 to cwd, prints absolute path, never auto-executes.

## What Was Built

### src/maccat/reinstall/picker.py

- `_find_newest_catalog(folder: Path) -> Path | None`: globs `mac-software-list-*.txt`, applies null-file guard, uses `parse_catalog_filename` + lexicographic 14-digit timestamp comparison (same algorithm as `retention.py` pass-1 loop — NOT mtime).
- `resolve_catalog_path(args, catalog_repo=None) -> Path | None`: `--from PATH` branch validates via `Path.expanduser().resolve()` + `is_file()` guard; picker branch defers identity imports per PKG-03, calls `resolve_computer_selection` + `select_computer`, returns `None` on picker-quit.

### src/maccat/reinstall/cli.py

- `run_reinstall(args, catalog_repo=None) -> None`: full pipeline — `resolve_catalog_path` → None-check (clean return) → `parse_catalog` → `emit_reinstall_script(source_name=catalog_path.name, generated=date.today().strftime("%Y-%m-%d"))` → `Path.cwd() / "reinstall.sh"` write_text → `os.chmod(0o644)` (explicit, not relying on umask) → `print(str(output_path.resolve()))`. All maccat.* imports deferred inside function body.

### src/maccat/cli.py (surgical addition — ~47 lines)

Two edits only:

1. `_build_parser()`: added `reinstall` subparser with `--from PATH` argument (`dest="from_path"`). Updated docstring Subcommands block.

2. `run()`: split monolithic step 4 into 4a/4b/4c/4d:
   - **4a**: `load_config()` (always runs)
   - **4b**: `--from` dispatch before `resolve_catalog_repo` — `--from` mode is repo-agnostic; includes `--rename` mutual-exclusion guard
   - **4c**: `resolve_catalog_repo` + `validate_catalog_repo` + `auto_commit` (unchanged logic)
   - **4d**: picker dispatch after repo validated; before `--rename` step 5; includes same guard

   Steps 6-13 (gen path) are byte-behavior identical.

### tests/reinstall/test_reinstall_cli.py (7 tests)

Full in-process integration tests (mirrors `test_cli.py` style):
- `test_from_path_writes_reinstall_sh`: mode `0o644`, shebang, provenance header
- `test_reinstall_sh_contains_generated_on_header`
- `test_rename_guard_does_not_fire`: `git_pull.assert_not_called()`
- `test_gen_path_not_triggered_by_reinstall`: no `mac-software-list-*.txt` in output cwd
- `test_reinstall_rename_mutual_exclusion`: SystemExit non-zero
- `test_missing_from_path_errors`: SystemExit non-zero
- `test_non_reinstall_invocation_unchanged`: `git_pull` called (step 8 reached)

### tests/reinstall/test_picker_and_reinstall_cli.py (16 unit tests)

TDD unit tests for `_find_newest_catalog`, `resolve_catalog_path`, and `run_reinstall`.

## Verification Results

| Check | Result |
|-------|--------|
| Full test suite (540 tests) | PASS |
| mypy --strict (picker.py + reinstall/cli.py + src/maccat/cli.py) | PASS |
| ruff check (all new/modified files) | PASS |
| Subparser registration | PASS |
| gen path invariant (steps 6-13 unchanged) | PASS |
| mode 0o644 assertion | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree missing Phase 24/25 reinstall package**

- **Found during:** Pre-task setup
- **Issue:** The worktree was spawned from commit `a507b4c` (before Phase 24/25 merge). `src/maccat/reinstall/` and `tests/reinstall/` existed only in `main`, not in this worktree.
- **Fix:** Cherry-picked `__init__.py`, `parser.py`, `emitter.py` from `main:src/maccat/reinstall/` and `__init__.py`, `test_emitter.py`, `test_parser_contract.py` from `main:tests/reinstall/`. Committed as `chore(26-01): bring Phase 24/25 reinstall package into worktree`.
- **Files modified:** `src/maccat/reinstall/` (created), `tests/reinstall/` (pre-populated)
- **Commit:** 879f220

**2. [Rule 1 - Bug] ruff import-sort in picker.py**

- **Found during:** Task 1 post-implementation lint check
- **Issue:** `ruff check` reported `I001` (import block unsorted) — `from maccat.naming import parse_catalog_filename` needs to follow a blank line after stdlib imports.
- **Fix:** `ruff check --fix` applied automatically.
- **Commit:** Folded into Task 1 commit (53a4581)

## TDD Gate Compliance

- RED gate: `test(26-01)` commit 04cdce6 — 16 failing tests (ModuleNotFoundError)
- GREEN gate: `feat(26-01)` commit 53a4581 — 16 passing tests

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 879f220 | chore | bring Phase 24/25 reinstall package into worktree |
| 04cdce6 | test | add failing unit tests for picker.py and reinstall/cli.py (RED) |
| 53a4581 | feat | implement reinstall/picker.py and reinstall/cli.py (GREEN) |
| 6b40888 | feat | wire reinstall subparser + two-point dispatch into cli.py |
| 441bd2a | feat | add integration tests for maccat reinstall subcommand |

## Known Stubs

None.

## Threat Flags

None — all new surface was pre-analyzed in the plan's threat model (T-26-01 through T-26-SC). No new trust boundaries introduced beyond what was modeled.

## Self-Check: PASSED

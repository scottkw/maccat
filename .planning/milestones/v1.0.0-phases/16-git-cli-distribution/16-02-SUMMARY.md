---
phase: 16-git-cli-distribution
plan: "02"
subsystem: cli
tags: [argparse, orchestration, cli, end-to-end]
dependency_graph:
  requires: [16-01, 15-01, 15-02, 15-03, 15-04, 15-05, 15-06, 15-07, 15-08, 14-01, 14-02, 14-03, 14-04, 13-01, 13-02, 13-03]
  provides: [maccat.cli._build_parser, maccat.cli.run]
  affects: [src/maccat/__main__.py]
tech_stack:
  added: []
  patterns: [deferred-import-inside-function, argparse-subparsers, generate-then-sweep-invariant]
key_files:
  created: [src/maccat/cli.py, tests/test_cli.py]
  modified: [src/maccat/__main__.py]
decisions:
  - "--machine kept as separate dest='machine' (not aliased to computer) to preserve resolve_computer_selection(machine=...) call signature"
  - "All maccat.* imports deferred inside function bodies (PKG-03 / mirrors collectors/__init__.py lazy pattern)"
  - "Timestamp captured AFTER git_pull returns — generate-then-sweep invariant ensures just-written catalog survives retention sweep"
  - "--rename × selecting-flag guard placed in cli.py only (identity.py:99-101 explicitly excludes it)"
metrics:
  duration_minutes: 8
  completed: "2026-06-15"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 16 Plan 02: CLI Argparse + End-to-End Orchestration Summary

**One-liner:** argparse CLI with mutually-exclusive selecting flags, config subcommands, rename short-circuit, and NON-NEGOTIABLE generate-then-sweep orchestration order wiring all phases 13-16 modules.

## What Was Built

### src/maccat/cli.py (new)

Two public names: `_build_parser()` and `run()`.

`_build_parser()` constructs the ArgumentParser:
- `--version` / `--help` (PKG-05)
- `--catalog-dir PATH` (CFG-03: flag override never written back)
- Mutually exclusive group: `--personal`, `--office`, `--computer NAME`, `--machine NAME` (separate `dest="machine"` kept for `resolve_computer_selection(machine=...)` call signature)
- `--rename` (short-circuit flag)
- `--archive-days N`
- `--no-commit`
- Subparser: `config` with `config init` and `config show`

`run()` executes the NON-NEGOTIABLE orchestration order mirroring update-list.sh:2443-2505:
1. Parse args
2. Config subcommand dispatch (`config init` / `config show` / bare exits 1)
3. `--rename` × selecting-flag guard (cli.py only — identity.py:99-101 excludes it)
4. `load_config` → `resolve_catalog_repo(flag, cfg)` → `validate_catalog_repo`
5. `--rename` short-circuit: `git_pull` → `rename_machine(auto_commit=...)` → `return`
6. `resolve_computer_selection` → `select_computer` (interactive fallback; returns `None` → clean return)
7. `resolve_archive_days`
8. `git_pull`
9. Capture `timestamp = datetime.now().strftime(...)` **AFTER** `git_pull` (generate-then-sweep invariant)
10. `make_catalog_filename` → `mkdir(parents=True, exist_ok=True)` → `CatalogWriter`: write "Installed Mac Software List" header, then iterate `get_registry()` — `raw=True` → `write_lines(items)`, else → `write_lines(flush_section(items))`
11. `retain_newest_per_host(catalog_repo / computer)`
12. `prune_old_archives(catalog_repo / computer / "archive", archive_days)`
13. `git_commit_and_push` if `auto_commit` else print manual-commit hint

All maccat.* imports are deferred inside the function body (never at module top).

### src/maccat/__main__.py (modified)

Lines 19-21 replaced: `NotImplementedError("Phase 16")` stub removed. Now:
```python
def main() -> None:
    from maccat.cli import run
    run()
```
Version guard (lines 3-15) unchanged.

**Result:** `mypy --strict src/maccat` now reports 0 errors across 29 source files. The long-standing `import-untyped` stub error for `maccat.cli` is resolved.

### tests/test_cli.py (new, 28 tests)

- `TestArgparse` (14): `--version`/`--help` exit codes, mutual-exclusion exits 2, `--machine` separate dest, `--no-commit`/`--archive-days` defaults, bare `subcommand=None`
- `TestRenameFlag` (4): `--rename` × `{--personal, --office, --computer, --machine}` all raise `SystemExit`
- `TestNoCommit` (4): `git_commit_and_push` NOT called; `git_pull` IS called; catalog `.txt` written; with-commit path calls `git_commit_and_push`
- `TestGenerateThenSweep` (2): just-written catalog not in `archive/`; timestamp captured after `git_pull` (call-order side-effect verification)
- `TestConfigDispatch` (3): `config init`/`show` dispatch; bare `config` exits non-zero
- `TestSelectComputerQuit` (1): `select_computer(None)` causes clean return without writing catalog

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond those specified in the plan's threat model (T-16-05 through T-16-SC all addressed).

## Known Stubs

None.

## Self-Check: PASSED

Files exist:
- FOUND: src/maccat/cli.py
- FOUND: src/maccat/__main__.py
- FOUND: tests/test_cli.py

Commits exist:
- 4f2de44: feat(16-02): implement cli.py argparse parser + run orchestration; fill __main__.py stub
- 73c66b1: test(16-02): add tests/test_cli.py

Verification:
- `PYTHONPATH=src ./venv/bin/python -m maccat --version` → `maccat 1.0.0` (exit 0)
- `PYTHONPATH=src ./venv/bin/python -m maccat --help` → usage text (exit 0)
- `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` → Success: no issues found in 29 source files
- `PYTHONPATH=src ./venv/bin/ruff check src/maccat tests/test_cli.py` → All checks passed
- `PYTHONPATH=src ./venv/bin/pytest -x -q` → 389 passed

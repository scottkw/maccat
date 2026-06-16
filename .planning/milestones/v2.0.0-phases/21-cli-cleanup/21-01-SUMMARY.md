---
phase: 21-cli-cleanup
plan: "01"
subsystem: cli
tags: [refactor, cli, identity, argparse]
dependency_graph:
  requires: []
  provides: [simplified-resolve-computer-selection, cli-parser-single-selector]
  affects: [src/maccat/identity.py, src/maccat/cli.py]
tech_stack:
  added: []
  patterns: [argparse-single-flag, keyword-only-function-signature]
key_files:
  created: []
  modified:
    - src/maccat/identity.py
    - src/maccat/cli.py
    - src/maccat/gitops.py
    - src/maccat/retention.py
    - src/maccat/catalog/writer.py
    - src/maccat/naming.py
decisions:
  - "Kept the mutually-exclusive group in _build_parser with a single --computer member (Claude's discretion from CONTEXT.md — keeps group for future extensibility, no behavior change)"
  - "resolve_computer_selection kept as a named function rather than inlined (preserves unit-testability per existing test structure)"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-16"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 6
---

# Phase 21 Plan 01: CLI Cleanup — Remove Legacy Selecting Flags — Summary

**One-liner:** Removed --personal/--office/--machine from argparse parser and resolve_computer_selection; collapsed four-way flag resolver to single --computer validator with docstring scrub across six files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Simplify resolve_computer_selection in identity.py | 112f26e | src/maccat/identity.py |
| 2 | Update cli.py — parser, guards, call site, module docstring | 42c9a34 | src/maccat/cli.py |
| 3 | Scrub docstring examples in gitops.py, retention.py, writer.py, naming.py | 3c8a5d0 | src/maccat/gitops.py, src/maccat/retention.py, src/maccat/catalog/writer.py, src/maccat/naming.py |

## What Was Built

**Task 1 — identity.py:**
- `resolve_computer_selection` rewritten from `(*, computer, personal, office, machine) -> str | None` to `(*, computer: str | None) -> str | None`
- Body collapsed to: `if not computer: return None; validate_computer_name(computer); return computer`
- Removed: `count = sum([...])` block, `count > 1` SystemExit, `personal → "personal"` and `office → "office"` literal branches, `machine` parameter and its validate/return branch
- Docstring updated to reflect single-flag semantics; removed mutual-exclusion rules and zsh analog line reference

**Task 2 — cli.py:**
- Module docstring Flags section: removed `--personal`, `--office`, `--machine` lines
- `_build_parser()`: removed three `group.add_argument` blocks for `--personal`, `--office`, `--machine`; kept mutually-exclusive group with single `--computer` member
- Config subcommand guard: `any([args.rename, args.computer])` (was `any([args.rename, args.personal, args.office, args.computer, args.machine])`)
- Config guard error message: `"--rename and --computer cannot be combined with the 'config' subcommand."`
- Rename guard: `args.rename and bool(args.computer)` (was `args.rename and any([args.personal, args.office, args.computer, args.machine])`)
- Rename guard error message: `"--rename cannot be combined with --computer."`
- Call site: `resolve_computer_selection(computer=args.computer)` (was four-argument call)

**Task 3 — docstring examples:**
- gitops.py: `e.g. "personal", "office"` → `e.g. "MyMac", "WorkLaptop"`
- retention.py: `catalog_repo / "personal"` → `catalog_repo / "MyMac"`
- catalog/writer.py: `Path("personal/catalog-2026.txt")` → `Path("MyMac/catalog-2026.txt")`
- naming.py: `[personal]-20260614120000.txt` → `[MyMac]-20260614120000.txt`

## Verification Results

All four plan-level acceptance checks passed:
1. `ruff check` on all six modified files — 0 errors
2. `mypy --strict src/maccat/identity.py src/maccat/cli.py` — 0 errors
3. `grep args.personal/args.office/args.machine src/maccat/cli.py` — no output
4. `grep personal=/office=/machine= src/maccat/identity.py` — no output

Parser introspection: `_build_parser().parse_args(['--computer', 'Laptop']).computer == 'Laptop'` — OK
Signature introspection: `inspect.signature(resolve_computer_selection).parameters == ['computer']` — OK

## Deviations from Plan

None — plan executed exactly as written.

The venv was absent from the repo (`.gitignore`d) and was created as part of the execution environment setup. This is expected behavior, not a deviation.

## Known Stubs

None — this is a pure refactor with no new stubs introduced.

## Threat Flags

None — removing flags reduces CLI attack surface; no new trust surface introduced.

## Self-Check: PASSED

- src/maccat/identity.py — exists, modified
- src/maccat/cli.py — exists, modified
- src/maccat/gitops.py — exists, modified
- src/maccat/retention.py — exists, modified
- src/maccat/catalog/writer.py — exists, modified
- src/maccat/naming.py — exists, modified
- Commit 112f26e — exists (Task 1)
- Commit 42c9a34 — exists (Task 2)
- Commit 3c8a5d0 — exists (Task 3)

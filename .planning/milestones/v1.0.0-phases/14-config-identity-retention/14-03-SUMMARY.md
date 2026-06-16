---
phase: 14-config-identity-retention
plan: "03"
subsystem: identity
tags: [identity, flag-resolver, interactive-menu, tsv, rename, tdd]
dependency_graph:
  requires: [14-01]
  provides: [identity.py]
  affects: [16-cli-git-distribution]
tech_stack:
  added: []
  patterns:
    - "atomic-write: tempfile.mkstemp + os.fdopen + Path.rename (upsert_machine_label, rename_machine TSV update)"
    - "TTY guard: sys.stdin.isatty() checked BEFORE any input() call"
    - "EOF safe: except EOFError: return None — never continue (prevents infinite-loop regression)"
    - "discover_computer_folders: sorted union of catalog-bearing dirs + TSV values"
    - "resolve_computer_selection: pure SC3 flag-alias resolver, no argparse, no TTY"
key_files:
  created:
    - src/maccat/identity.py
    - tests/test_identity.py
  modified: []
decisions:
  - "resolve_computer_selection is a pure function (no argparse, no TTY) — makes SC3 unit-testable in Phase 14; Phase 16 wires argparse dispatch to call it"
  - "rename_machine refuses clobber via SystemExit (not warning) — irreversible merge is catastrophic; hard fail matches update-list.sh lines 763-766"
  - "empty-string computer/machine treated as not-set in resolve_computer_selection — bool('') is False so empty flag value never counts toward selecting-flag count"
  - "auto_commit parameter exists with default False; git-commit block is comment stub only — Phase 16 wires the actual commit"
metrics:
  duration_minutes: 4
  completed_date: "2026-06-14"
  tasks_completed: 1
  files_created: 2
  tests_written: 40
  tests_passing: 40
---

# Phase 14 Plan 03: identity.py — Selection Menu, Machine-Labels TSV, Rename, Flag Resolver Summary

**One-liner:** Pure flag resolver (SC3), always-shown computer-folder menu with TTY/EOF safety, atomic TSV upsert, and hard-refuse-clobber rename — all derived from zsh update-list.sh lines 117–923.

## What Was Built

### src/maccat/identity.py

Seven functions implementing the computer-identity layer:

**`validate_computer_name(val: str) -> None`**
Fatal validator (SystemExit). Four rules from update-list.sh lines 117–141:
1. Non-empty. 2. No leading/trailing whitespace. 3. No `/`, `[`, `]`. 4. No TAB/newline.

**`validate_computer_name_quiet(val: str) -> str | None`**
Non-fatal variant (returns error string or None). Same four rules. Used in interactive re-prompt loops.

**`resolve_computer_selection(*, computer, personal, office, machine) -> str | None`**
Pure SC3 function — no argparse, no TTY. Counts how many selecting flags are "set" (truthy; empty strings treated as not-set). Zero flags → None (interactive fallback). Exactly one → resolve alias (personal→"personal", office→"office", --computer/--machine → validate then return value). More than one → SystemExit with exact mutual-exclusion message from update-list.sh lines 265–267.

Phase 16 note: the `--rename × selecting-flag` guard (update-list.sh lines 270–277) is NOT here — it depends on RENAME_MODE parser state and belongs to Phase 16's argparse dispatch.

**`discover_computer_folders(catalog_repo: Path) -> list[str]`**
Sorted, deduplicated union of (a) dirs containing `mac-software-list-*.txt` files and (b) second-column values from machine-labels.tsv (skipping comment/blank/tab-less lines). Used by both `select_computer` and `rename_machine`.

**`upsert_machine_label(catalog_repo: Path, folder: str) -> None`**
Creates machine-labels.tsv with 3-line header if absent. Reads existing lines, preserving comments and blank lines verbatim; replaces current host's entry or appends if not found. Writes atomically via `tempfile.mkstemp + os.fdopen + Path.rename`.

**`select_computer(catalog_repo: Path, *, computer_name: str | None = None) -> str | None`**
Flag path (computer_name not None): mkdir, upsert, announce, return. Interactive path: non-TTY guard → TSV saved-folder lookup → discover+promote saved_folder to position 0 → always-shown menu → input loop with EOF=None, q/quit=Quit, Enter=saved-default or re-prompt, invalid=re-prompt → Quit/Create-new/Existing branches.

**`rename_machine(catalog_repo: Path, *, auto_commit: bool = False) -> None`**
TTY guard → discover (no saved-default promotion) → picker menu → new-name prompt → three guards in order (1. same-name warn+return, 2. folder-not-found warn+return, 3. refuse-clobber SystemExit) → folder move → opt-out filename rewrite prompt (default YES, EOF=YES, collision guard per file) → unconditional TSV atomic update → Phase 16 git stub comment.

### tests/test_identity.py

40 tests across 5 classes:

- **TestValidateComputerName** (13): all four rules for both variants (fatal + quiet)
- **TestResolveComputerSelection** (11): all four aliases, zero-flag None, two pairs of mutual-exclusion, invalid name via validate, empty-string-as-None
- **TestSelectComputer** (6): non-TTY fast-fail, EOF clean quit, saved-folder Enter, flag-path mkdir/upsert, quit/q returns None
- **TestRenameMachine** (5): refuse-clobber SystemExit + both folders intact, same-name warning, folder-not-found warning, non-TTY exit, happy-path rename
- **TestUpsertMachineLabel** (5): creates with header, appends new host, updates existing host, preserves comments+blank lines, no .tmp file after write

## Deviations from Plan

None — plan executed exactly as written.

The `discover_computer_folders` import was initially included in the test module but was unused; ruff's F401 auto-fix removed it cleanly.

## TDD Gate Compliance

RED commit `7585548`: failing tests for identity.py (import error — module not yet created).
GREEN commit `2e192bf`: implementation; all 40 tests pass.
REFACTOR: no structural changes needed after GREEN.

## Threat Mitigations Applied

All four T-14 threat mitigations from the plan's threat register were implemented:

| Threat ID | Mitigation |
|-----------|------------|
| T-14-06 | validate_computer_name rejects /, [, ], leading/trailing whitespace, tab, newline |
| T-14-06b | resolve_computer_selection: count > 1 → SystemExit before any folder/TSV mutation |
| T-14-07 | rename_machine: `if new_dir.exists(): raise SystemExit(...)` before any rename call |
| T-14-08 | upsert_machine_label: tempfile.mkstemp + Path.rename; never open(map_file, "w") |
| T-14-09 | select_computer: sys.stdin.isatty() checked before any input(); EOF → return None |
| T-14-10 | rename_machine filename rewrite: per-file collision check; never overwrite |

## Success Criteria Status

- [x] All tasks executed; committed individually (RED: 7585548, GREEN: 2e192bf)
- [x] SC3 (OPS-02): resolve_computer_selection maps --personal/--office/--machine/--computer correctly
- [x] SC3: raises SystemExit (message contains "mutually exclusive") when 2+ selecting flags
- [x] SC3: returns None for zero flags (interactive fallback)
- [x] SC3: invalid --computer/--machine value raises SystemExit via validate_computer_name
- [x] Non-TTY test: SystemExit raised immediately (no hang)
- [x] EOF test: select_computer returns None, no traceback
- [x] Refuse-clobber test: rename_machine raises SystemExit; both folders intact after call
- [x] upsert_machine_label: comments and blank lines preserved verbatim
- [x] rename_machine auto_commit parameter exists; git commit section is comment stub only
- [x] ruff clean: 0 errors on identity.py and test_identity.py
- [x] mypy --strict clean: 0 issues on identity.py
- [x] 137 total tests pass (40 new + 97 pre-existing)

## Self-Check: PASSED

Files created:
- src/maccat/identity.py — FOUND
- tests/test_identity.py — FOUND

Commits:
- 7585548 (test RED) — FOUND
- 2e192bf (feat GREEN) — FOUND

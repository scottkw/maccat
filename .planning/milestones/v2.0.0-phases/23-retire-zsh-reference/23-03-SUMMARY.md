---
phase: 23-retire-zsh-reference
plan: "03"
subsystem: docs
tags: [docs, cleanup, zsh-retirement, readme]
dependency_graph:
  requires: [23-02]
  provides: [ZSH-04]
  affects: [README.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - README.md
decisions:
  - "Placed the one-sentence history note (v1.0.0 port) immediately above ## Troubleshooting — natural location, not buried in Overview"
  - "Removed entire ## Zsh Reference Script section rather than repurposing it"
  - "Updated --personal --no-commit example to --no-commit only (flag is sufficient; --computer is optional)"
  - "docs/superpowers/specs/2026-06-14-computer-folder-model-design.md left untouched — it is a historical design spec, not operational documentation"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-16"
  tasks_completed: 2
  files_changed: 1
---

# Phase 23 Plan 03: Scrub README Zsh References Summary

README describes maccat as the standalone Python tool with one-sentence lineage note; CLI docs updated to --computer; stale --personal/--office/--machine flags removed; all quality gates green.

## What Was Built

README.md was surgically updated to remove all operational references to `update-list.sh` and the Zsh implementation:

1. **Removed "## Zsh Reference Script" section** — replaced the entire heading + paragraph (which framed `update-list.sh` as a live parity reference) with a single history sentence placed above `## Troubleshooting`:
   > "maccat was originally implemented as a Zsh script and ported to Python in v1.0.0."

2. **Updated Usage section** — removed the three stale examples using `--personal`, `--office`, and `--personal --no-commit`; replaced with a single example showing `--computer MyMac`.

3. **Updated Options table** — dropped `--personal`, `--office`, and `--machine "Label"` rows; added `--computer NAME` row with description.

4. **Updated Machine Identity section** — replaced every `--machine "Label"` reference with `--computer NAME`; updated the non-interactive run paragraph.

5. **Fixed "The script generates"** — replaced with "maccat generates" (removes implicit `update-list.sh` referent).

6. **Fixed Disabling Auto-commit example** — removed orphaned `--personal` flag from the `--no-commit` example.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update README.md — remove zsh reference section; fix CLI docs | 2d608f6 | README.md |
| 2 | Final full suite gate | (validation only) | — |

## Verification Results

- `grep -c "update-list\.sh\|Zsh Reference\|parity reference\|--personal\|--office\|--machine"` → 0
- `grep -c "v1\.0\.0\|originally"` → 1 (history note present)
- `grep -c "\-\-computer"` → 4 (usage example, options table, Machine Identity x2)
- `ruff check src tests` → All checks passed
- `mypy --strict src/maccat` → Success: no issues found in 30 source files
- `pytest -x -q` → 421 passed, 5 skipped in 3.07s

## Deviations from Plan

None — plan executed exactly as written.

The docs/superpowers/specs/ design document was inspected and intentionally left untouched: it is a historical design spec predating the Python port, not operational user-facing documentation, and the plan scope is README.md only.

## Known Stubs

None.

## Threat Flags

None — documentation-only change, no new execution surface introduced.

## Self-Check: PASSED

- README.md exists and was modified: confirmed
- Commit 2d608f6 exists: confirmed
- All prohibited terms absent from README: confirmed
- History note present: confirmed
- --computer flag documented: confirmed
- Full test suite green: confirmed (421 passed)

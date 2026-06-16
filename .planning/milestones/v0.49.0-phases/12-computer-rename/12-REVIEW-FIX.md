---
phase: 12-computer-rename
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/12-computer-rename/12-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/12-computer-rename/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (CR-01, WR-01 — Info findings IN-01..03 explicitly out of scope)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### CR-01: New-name prompt loops infinitely on EOF (Ctrl-D)

**Files modified:** `update-list.sh`
**Commit:** 450fcf3
**Applied fix:** Wrapped the `read -r new_name` in the new-name re-prompt loop
(line ~732) in an `if ! read -r ...; then` EOF guard, mirroring the sibling
loops at lines 423, 469, and 707. On EOF (Ctrl-D / closed stdin) the loop now
prints `Nothing renamed.` and `exit 0` with nothing moved, no map edit, and no
commit — consistent with the phase's Quit/EOF clean-abort semantics. The prior
unguarded `read` spun forever because an empty `new_name` failed the validator,
re-prompted, and immediately hit EOF again. `zsh -n` passes.

### WR-01: Folder name beginning with `-` breaks `git add` staging (silent partial commit)

**Files modified:** `update-list.sh`
**Commit:** f98d74b
**Applied fix:** Added the `--` end-of-options separator to the auto-commit
staging calls — `git add -A -- "${old_name}/"`, `git add -A -- "${new_name}/"`,
`git add -- machine-labels.tsv` (lines ~878-880) — and to the printed
`--no-commit` manual instructions (line ~907). This prevents a leading-dash
folder name (e.g. `-foo`) from being parsed as a git option, which previously
caused staging to silently fail under `2>/dev/null || true` and produce an
inconsistent commit (map updated, folder move unstaged). Expanded the inline
comment to explain the marker. `zsh -n` passes.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

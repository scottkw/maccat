---
phase: 09-machine-rename
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/09-machine-rename/09-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/09-machine-rename/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, CR-02, WR-01, WR-02, WR-03)
- Fixed: 5
- Skipped: 0

All fixes applied to `update-list.sh` and verified with `zsh -n` (syntax). The
WR-01 tab-split logic was additionally exercised in an isolated Zsh harness to
confirm the no-tab pass-through behavior. CR-02 is a logic-gating change and is
flagged below for human verification of the guard semantics.

## Fixed Issues

### CR-01: `git add -A personal/ office/` aborts (exit 128) when one directory is absent

**Files modified:** `update-list.sh`
**Commit:** 5d42e12
**Applied fix:** Replaced the single `git add -A personal/ office/` with a loop
that stages each location directory only when it exists
(`for loc in personal office; do [[ -d "${SCRIPT_DIR}/${loc}" ]] && git add -A "${loc}/"; done`),
followed by `git add machine-labels.tsv`. This prevents the fatal exit-128 abort
on single-location machines that would otherwise leave renames unstaged while the
map update got committed alone (a corrupt, inconsistent commit). Matches the
defensive single-directory staging already used by `git_commit_and_push`.

### CR-02: Collision-only rename rewrites the map and commits despite zero files moved

**Files modified:** `update-list.sh`
**Commit:** c14c8cd
**Applied fix:** Replaced the `renamed_count == 0 && skipped_count == 0` no-match
guard with a strict `renamed_count == 0` no-effect guard. A collision-only run
(`renamed_count == 0`, `skipped_count > 0`) now warns and `exit 0`s WITHOUT
mutating `machine-labels.tsv` or committing. The branch distinguishes the
collision-only message from the no-files-found message. This subsumes the prior
guard since `renamed_count` is the only signal that on-disk state changed.
**Note: requires human verification** — this is a logic-gating change; confirm the
guard semantics (collision-only must produce no map mutation and no commit) match
the intended SC#5 contract.

### WR-01: Map rewrite mislabels a no-tab data line whose hostname equals the OLD label

**Files modified:** `update-list.sh`
**Commit:** f48c97c
**Applied fix:** Guarded the data-line match on the presence of an actual tab:
`if [[ "$line" == *$'\t'* && "${line#*$'\t'}" == "$old_label" ]]`. No-tab lines
(bare hostnames, hand-edited entries) now pass through verbatim instead of
falling back to `${line#*\t}` returning the whole line and wrongly matching a
hostname equal to `old_label`. Verified in an isolated Zsh harness: bare
`OldName` → passthrough; `host1<TAB>OldName` → rewrite; `host2<TAB>Other` →
passthrough.

### WR-02: `git push` failure in rename mode lacks resync guidance about moved files

**Files modified:** `update-list.sh`
**Commit:** a6c2eab
**Applied fix:** Expanded the push-failure warning to state that the catalog
files were ALREADY renamed on disk (with the `${renamed_count}` count), warn
against re-running `--rename` before resolving the push, and give explicit
recovery steps (`git pull --rebase && git push`, then manual reconciliation on
conflict). No behavioral change beyond the message; consistent with the script's
warn-and-continue policy.

### WR-03: `--rename` combined with `--machine "X"` silently discards the label

**Files modified:** `update-list.sh`
**Commit:** 2bd8ecc
**Applied fix:** Added a guard after the `parse_arguments` while loop that
errors out and `exit 1`s when both `RENAME_MODE == "true"` and `MACHINE_LABEL`
is non-empty, with a clear message that `--rename` is interactive and cannot be
combined with `--machine`. Matches the fail-fast convention and prevents the
confusing silent no-op.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

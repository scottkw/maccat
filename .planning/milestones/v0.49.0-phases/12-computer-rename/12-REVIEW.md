---
phase: 12-computer-rename
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
resolved:
  - CR-01  # fixed in 450fcf3 (EOF guard on new-name prompt), re-verified iteration 2
  - WR-01  # fixed in f98d74b (-- separator in git add pathspecs), re-verified iteration 2
---

# Phase 12: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Status:** clean

## Summary

Re-review iteration 2 of the `rename_machine()` fix loop. Both prior findings are
confirmed resolved and introduce no regressions. `zsh -n` passes.

**CR-01 (BLOCKER) — RESOLVED.** The new-name re-prompt loop (lines 730-741) now
guards `read -r new_name` with `if ! read -r new_name; then echo "Nothing renamed."; exit 0; fi`
(lines 732-735). The guard fires on EOF BEFORE the validator call (736), the
no-op `new==old` guard (744), the `mv` (766), the map edit (829-860), and the
commit (866-913) — so nothing is moved or committed on the EOF path. Verified by
isolated fixture across three cases: (a) immediate EOF exits 0 with "Nothing
renamed." and no loop; (b) an invalid-but-nonempty name still re-prompts (the
guard does not catch validator failures); (c) a normal valid name proceeds
immediately. The pattern matches the three sibling EOF guards (lines 423, 469, 707).

**WR-01 (WARNING) — RESOLVED.** All three auto-commit staging calls now carry the
`--` end-of-options separator: `git add -A -- "${old_name}/"` (881),
`git add -A -- "${new_name}/"` (882), `git add -- machine-labels.tsv` (883). The
`--no-commit` manual instructions at line 910 were updated to match. Verified in a
throwaway git repo: without `--`, a leading-dash folder (`-foo/`) fails staging
with `error: unknown switch` (the original silent-partial-commit bug); with `--`
it stages correctly as a pathspec, and normal non-dash folder names plus the TSV
still stage correctly.

No new Critical or Warning issues were introduced by either diff. The three
pre-existing Info findings (IN-01..IN-03) are unchanged and do not block clean
status. Note: the normal-catalog path `git_commit_and_push` at line 2390 still
omits `--`, but that is outside the scope of these two diffs and not a regression
introduced here; it can be considered separately if dash-leading names ever flow
through `TARGET_LOCATION`.

## Info

### IN-01: Apostrophe in folder name produces broken copy-paste manual instructions

**File:** `update-list.sh:910-911`
**Issue:** The `--no-commit` manual instructions wrap paths in single quotes:
`git add -A -- '${old_name}/'`. For a name containing an apostrophe (e.g. `Ken's Mac`),
the emitted line has unbalanced quotes that break if the user copy-pastes it. This is
display-only; the script's own auto-commit `git add` (lines 881-882) uses correct zsh
quoting and is unaffected. The commit message on line 911 has the same fragility.
**Fix:** Note in the instructions that names with apostrophes must be hand-quoted,
or emit the paths with escaped quoting. Low impact given the auto-commit path is the
common one.

### IN-02: Redundant `cd "$SCRIPT_DIR"` in rename commit block

**File:** `update-list.sh:867`
**Issue:** The main block calls `git_pull` immediately before `rename_machine`, and
`git_pull` already `cd`s to `SCRIPT_DIR`. The `cd "$SCRIPT_DIR"` at line 867 is
therefore redundant on the normal path. Harmless (it is also a correct defensive
guard if `rename_machine` is ever called standalone), but worth noting.
**Fix:** No change required; optionally add a comment that it is a defensive re-`cd`.

### IN-03: Discovery + `_name_in_list` helper duplicated between `select_computer` and `rename_machine`

**File:** `update-list.sh:345-377` and `update-list.sh:647-679`
**Issue:** The folder-discovery block (null-glob dir scan + map-value union + the
nested `_name_in_list` helper) is duplicated nearly verbatim in `select_computer`
and `rename_machine`, differing only in the dropped remembered-default promotion.
Per CLAUDE.md's "3 real examples before abstracting" rule this is 2 copies — at the
threshold, not over it — so extracting a shared helper is a judgment call, not a
requirement. Flagging for maintainability only.
**Fix:** Optional: extract a `discover_computers` function that fills a passed array
name, called by both. Defer unless a third caller appears.

---

_Reviewed: 2026-06-14 (iteration 2)_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

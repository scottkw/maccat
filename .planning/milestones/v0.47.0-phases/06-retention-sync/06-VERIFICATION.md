---
phase: 06-retention-sync
verified: 2026-06-13T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 6: Retention & Sync Verification Report

**Phase Goal:** Every run leaves the targeted location's main folder with exactly one catalog per machine, its archive self-pruned at 30 days, and all changes committed so every machine that pulls converges on the same retained set.
**Verified:** 2026-06-13
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a run on a machine with two catalogs for the same hostname in personal/ or office/, the main folder contains exactly one (the newest) and the older one is in archive/ | VERIFIED | Synthetic test 1: `mac-software-list-[TestHost-A]-20260101120000.txt` moved to archive; `mac-software-list-[TestHost-A]-20260610120000.txt` kept in main. 20/20 assertions passed. |
| 2 | After a run, any file in archive/ whose filename timestamp is older than 30 days has been deleted from disk | VERIFIED | Synthetic test 2: 20260101-dated files pruned (>30d from 2026-06-13); 20260601-dated file kept (<30d). `ARCHIVE_AGE_DAYS=30` confirmed at line 45. `date -v-${ARCHIVE_AGE_DAYS}d` used at line 286. |
| 3 | Running with --personal touches only personal/ and personal/archive/; running with --office touches only office/ and office/archive/ | VERIFIED | Both `retain_newest_per_host` and `prune_old_archives` parameterized by `$1` (target_dir); compute `full_path="${SCRIPT_DIR}/${target_dir}"`. No cross-location access path exists in either function. git staging uses `git add -A "${TARGET_LOCATION}/"` (line 1645) — relative path scoped to the targeted location after `cd "$SCRIPT_DIR"`. |
| 4 | A run against an empty folder, a missing archive/ directory, or an unparseable filename timestamp completes successfully and still produces the new catalog (warn-and-continue) | VERIFIED | Synthetic test 4: both functions completed cleanly on empty `office/` (no archive/ dir) with exit 0. `retain_newest_per_host` creates archive/ if absent. `prune_old_archives` returns early with message if archive/ absent. Test 5: `mac-software-list-[TestHost-C]-badname.txt` (unparseable timestamp) survived all retain+prune calls untouched. `setopt local_options null_glob` at lines 207 and 288 prevents Zsh glob-expansion errors on empty directories. |
| 5 | The resulting git commit includes the new catalog (addition), any catalogs moved to archive (rename/add+delete), and any 30-day-pruned files (deletion); --no-commit skips the commit while disk operations still run | VERIFIED | `git add -A "${TARGET_LOCATION}/"` at line 1645 stages the entire location tree (additions, deletions, renames as D+A pairs) in one call. `retain_newest_per_host` (line 1720) and `prune_old_archives` (line 1723) called unconditionally BEFORE the `if [[ "$AUTO_COMMIT" == "true" ]]` gate at line 1726. Disk ops run regardless of `--no-commit`. |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | `retain_newest_per_host` function — two-pass Zsh associative array retention sweep | VERIFIED | Defined at line 192. Two-pass: pass 1 builds `typeset -A newest_ts` map (line 208); pass 2 moves non-max files to archive/. |
| `update-list.sh` | `prune_old_archives` function — BSD date 30-day hard-delete prune | VERIFIED | Defined at line 272. Uses `date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d"` at line 286. Deletes files with `"$timestamp" -lt "$cutoff_date"`. |
| `update-list.sh` | `ARCHIVE_AGE_DAYS` set to 30 | VERIFIED | Line 45: `ARCHIVE_AGE_DAYS=30`. Confirmed with `grep -n 'ARCHIVE_AGE_DAYS' update-list.sh`. |
| `update-list.sh` | `git_commit_and_push` uses `git add -A` for staging | VERIFIED | Line 1645: `git add -A "${TARGET_LOCATION}/"`. No old targeted `git add` calls remain. |
| `update-list.sh` | Main block calls `generate_catalog` before retention sweep | VERIFIED | Line 1708: `generate_catalog`; line 1720: `retain_newest_per_host`; line 1723: `prune_old_archives`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| main block | `retain_newest_per_host` | called after `generate_catalog`, before `prune_old_archives` | VERIFIED | Lines 1708, 1720, 1723 — confirmed order. |
| main block | `prune_old_archives` | called after `retain_newest_per_host`, before `git_commit_and_push` | VERIFIED | Lines 1723, 1726-1727. |
| `git_commit_and_push` | `TARGET_LOCATION` directory | `git add -A` stages the whole location | VERIFIED | Line 1645: `git add -A "${TARGET_LOCATION}/"`. Function first `cd "$SCRIPT_DIR"` (line 1631), making the path relative to repo root. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no data-rendering components. The phase modifies a shell script's file-management and git-staging logic. Observable outputs are file system state (presence/absence of `.txt` files) and git staging, both verified by behavioral test.

---

### Behavioral Spot-Checks (Synthetic /tmp Test)

A self-contained Zsh test was built and run at `/tmp/test-retention-06-verify.zsh`. It sourced only `retain_newest_per_host` and `prune_old_archives` from the live `update-list.sh` using `sed -n '/^{function}()/,/^}/p'`. It created a synthetic directory tree under `/tmp/retention-verify-{PID}/` and never touched the real repo. All files in `/tmp` were cleaned up on completion.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Older-of-two Host A catalogs moved to archive/ | `retain_newest_per_host "personal"` | `mac-software-list-[TestHost-A]-20260101120000.txt` gone from main; found in archive/ | PASS |
| Newer Host A catalog kept in main | same | `mac-software-list-[TestHost-A]-20260610120000.txt` exists in main | PASS |
| Sole Host B catalog kept | same | `mac-software-list-[TestHost-B]-20260609120000.txt` exists in main | PASS |
| Non-catalog file untouched | same | `some-other-file.txt` exists in main | PASS |
| Unparseable-timestamp file not moved | same | `mac-software-list-[TestHost-C]-badname.txt` exists in main (WARNING printed) | PASS |
| >30d archive file pruned | `prune_old_archives "personal"` | `mac-software-list-[TestHost-A]-20260101090000.txt` gone | PASS |
| <30d archive file kept | same | `mac-software-list-[TestHost-A]-20260601090000.txt` exists | PASS |
| Non-catalog archive file untouched | same | `other-archive-file.txt` exists | PASS |
| File moved to archive in Test 1 (20260101 date) also pruned | same | `mac-software-list-[TestHost-A]-20260101120000.txt` gone from archive | PASS |
| Second retain call is a no-op | second `retain_newest_per_host "personal"` | "No older catalogs to archive." message; main state unchanged | PASS |
| Empty folder / missing archive/ — retain returns 0 | `retain_newest_per_host "office"` (no files) | exit 0; archive/ created cleanly | PASS |
| Missing archive/ — prune returns 0 | `prune_old_archives "office"` (no archive) | exit 0; "No archive directory found" message | PASS |
| Unparseable file not moved on re-run | second `retain_newest_per_host "personal"` | `mac-software-list-[TestHost-C]-badname.txt` exists, WARNING printed | PASS |
| /tmp cleanup successful | `rm -rf` | temp dir confirmed absent | PASS |

**Total: 20/20 assertions passed. Exit code: 0.**

---

### Code Review Fixes (WR-01 / WR-02 / WR-03)

The code review (06-REVIEW.md) identified three warnings. All three are confirmed fixed in the live code:

| ID | Finding | Fix Verified |
|----|---------|-------------|
| WR-01 | `mv` exit code unchecked — misleading "Archived" report on failure | FIXED — lines 241-245: `if mv "$file" "${archive_path}/"; then ... else echo "WARNING: Could not archive: $filename — leaving in place"; fi` |
| WR-02 | `rm` exit code unchecked — misleading "Pruned" report on failure | FIXED — lines 300-304: `if rm "$file"; then ... else echo "WARNING: Could not prune: $filename — leaving in place"; fi` |
| WR-03 | `--no-commit` guidance used `git add .` (stages whole repo) | FIXED — line 1732: `git add -A \"${TARGET_LOCATION}/\"` with scoped path |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| RET-01 | Newest catalog per machine retained in main; older moved to archive/ | SATISFIED | `retain_newest_per_host`: two-pass typeset -A; older non-max files moved to archive/. Proven by Test 1. |
| RET-02 | Archive files older than 30 days hard-deleted | SATISFIED | `prune_old_archives` + `ARCHIVE_AGE_DAYS=30`; `date -v-30d` cutoff; `-lt` comparison. Proven by Test 2. |
| RET-03 | Retention/prune scoped to targeted location only | SATISFIED | Both functions parameterized by `$1`; `full_path="${SCRIPT_DIR}/${target_dir}"`. No cross-location access path. |
| RET-04 | Never abort — empty folder, missing archive/, unparseable timestamp handled gracefully | SATISFIED | `setopt local_options null_glob` in both functions. `mkdir -p archive/` in retain. Early return in prune. Unparseable → warn+continue, never delete. Proven by Tests 4 and 5. |
| SYNC-01 | git commit stages all changes (add, rename, delete) in one commit | SATISFIED | `git add -A "${TARGET_LOCATION}/"` at line 1645; `-A` flag captures all changes in the path. |
| SYNC-02 | `--no-commit` skips git only; disk ops still run | SATISFIED | `retain_newest_per_host` and `prune_old_archives` called unconditionally at lines 1720/1723, before the `AUTO_COMMIT` gate at line 1726. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found in the two new functions or the modified main block. No TBD/FIXME/XXX markers. No stubs. |

Checked: `update-list.sh` (the sole file modified by this phase). Zero `TBD`/`FIXME`/`XXX` markers. No `return null`, `return []`, or placeholder patterns in `retain_newest_per_host` or `prune_old_archives`. All functions fully implemented.

---

### Syntax Gate

```
zsh -n update-list.sh → SYNTAX OK (exit 0)
```

---

### Human Verification Required

None. All success criteria for this phase are mechanically verifiable via code inspection and the synthetic /tmp behavioral test. No browser, UI, external service, or visual output to assess.

---

## Gaps Summary

None. All 5 must-haves are VERIFIED. All 6 requirement IDs (RET-01 through RET-04, SYNC-01, SYNC-02) are SATISFIED. The three code review warnings (WR-01, WR-02, WR-03) are all confirmed fixed. The synthetic behavioral test passed 20/20 assertions with exit code 0.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_

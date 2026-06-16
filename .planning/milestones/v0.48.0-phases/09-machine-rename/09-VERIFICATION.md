---
phase: 09-machine-rename
verified: 2026-06-14T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 9: Machine Rename Verification Report

**Phase Goal:** Users can rename a machine label everywhere it appears — all catalog files in both locations — in a single self-committing operation so other machines converge on pull.
**Verified:** 2026-06-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--rename` presents a numbered menu of known labels (from TSV union filename segments), accepts OLD+NEW, renames every matching file in all 4 dirs | VERIFIED | `rename_machine()` at line 518: 4-dir array (line 550), null-glob loops (lines 555, 634), `[segment]` label-parse idiom (lines 561-562, 640-641), numbered menu (lines 586-600). Behavioral fixture test confirmed both cryptic hostnames extracted correctly from filenames. |
| 2 | After rename, every machine-labels.tsv entry whose label equals OLD is updated to NEW | VERIFIED | Atomic TSV rewrite at lines 678-704: tab-gated data-line check (`"$line" == *$'\t'*`), replaces label column for all matching entries, `.tmp + mv` pattern preserves comments/blanks verbatim. |
| 3 | All file moves + updated TSV staged and pushed in ONE commit; `git pull` runs first | VERIFIED | Main block: `git_pull` at line 2287 before `rename_machine` at line 2288. Per-dir loop stages `personal/` and `office/` (lines 724-726) + `git add machine-labels.tsv` (line 727). Single `git commit` (line 733) + `git push` (line 740). Commit message includes "Rename machine label:" (line 732). |
| 4 | Cryptic pre-map machines (computer-one.local, computer-two.local) appear in candidate menu | VERIFIED | Filename-segment scanning in step 2b (lines 549-575) uses same `${filename#*\[}` / `${tmp%\]-*}` idiom as `retain_newest_per_host`. Throwaway-fixture behavioral test confirmed both labels extracted from dummy filenames. These machines predate the map and have no TSV entry — the filename-scan path is the only route they enter the menu. |
| 5 | No matching files → clear warning, exit WITHOUT modifying map or creating commit | VERIFIED | Guard at line 668: `if (( renamed_count == 0 ))` exits at line 674 with "WARNING: No catalog files found for label..." (line 672). Map write is at line 678; git operations start at line 709 — both strictly after the guard's `exit 0`. A collision-only run (renamed=0, skipped>0) also triggers the guard (line 669-670), satisfying the no-mutation contract in both cases. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `update-list.sh` | `rename_machine` function + `--rename` flag + `RENAME_MODE` global + `display_usage` update + main block short-circuit | VERIFIED | File exists, 2349 lines. All components present and wired. |
| `machine-labels.tsv` | Hostname-to-label map read and rewritten during rename | VERIFIED | File referenced at `SCRIPT_DIR}/machine-labels.tsv` (line 525). Read in step 2a (lines 531-546); atomically rewritten in step 7 (lines 678-704). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `parse_arguments --rename)` case | `RENAME_MODE=true` global | `case` statement assignment, line 197 | WIRED | `--rename)` case sets `RENAME_MODE=true` then `shift` (lines 196-199). `*)` error message updated to include `--rename` (line 202). |
| Main block `RENAME_MODE` check | `rename_machine` function | `if [[ "$RENAME_MODE" == "true" ]]` at line 2286 | WIRED | Short-circuit at lines 2286-2290: `git_pull; rename_machine; exit 0`. Positioned after `parse_arguments "$@"` (line 2282) and before `get_target_location` (line 2293). Ordering confirmed: 2282 < 2286 < 2293. |
| `rename_machine` candidate enumeration | `machine-labels.tsv` + four directory globs | TSV read loop (lines 531-546) + `setopt local_options null_glob` glob loops (lines 552-575) | WIRED | Both sources contribute to the `labels` array. Deduplication applied to both paths. |
| `rename_machine` map update | `machine-labels.tsv` atomic rewrite | `.tmp + mv` pattern at lines 678-704 | WIRED | `local tmp_file="${map_file}.tmp"` (line 678); written then `mv "$tmp_file" "$map_file"` (line 704). Consistent with `upsert_machine_label` pattern (lines 341, 382). |

### Data-Flow Trace (Level 4)

Not applicable — `rename_machine` is a mutation function (mv + TSV rewrite + git), not a rendering component. No data display to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `zsh -n` syntax check | `zsh -n update-list.sh` | exit 0 | PASS |
| Cryptic hostname label extraction from filenames | Zsh idiom `${filename#*\[}` / `${tmp%\]-*}` run against throwaway fixture files | `computer-one.local` and `computer-two.local` correctly extracted | PASS |
| No-match guard precedes map write | Line ordering check: guard at 668, map write at 677, git at 708 | Guard exits before both mutation points | PASS |
| Main block short-circuit ordering | `grep -n` line numbers: `parse_arguments` at 2282, `RENAME_MODE` check at 2286, `get_target_location` at 2293 | 2282 < 2286 < 2293 | PASS |
| Function placement ordering | `resolve_machine_label` definition at 405, `rename_machine` at 518, `retain_newest_per_host` at 785 | 405 < 518 < 785 | PASS |

### Probe Execution

No phase-declared probes. No `scripts/*/tests/probe-*.sh` conventional probes exist for this project.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REN-01 | 09-01-PLAN.md | User can rename a machine label, rewriting it across every catalog file in both locations | SATISFIED | `rename_machine` iterates `dirs=("personal" "personal/archive" "office" "office/archive")` (line 550), renames all matching files. Candidate enumeration includes filename-segment scanning so pre-map machines are renamable. |
| REN-02 | 09-01-PLAN.md | A rename updates the hostname-to-label map and stages all renames in a single git commit/push | SATISFIED | Atomic TSV rewrite (lines 678-704) updates all map entries with `old_label`. Per-dir git staging (lines 723-726) + `git add machine-labels.tsv` (line 727) + single commit (line 733) + push (line 740). |

No orphaned requirements — both REN-01 and REN-02 are fully covered.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned `update-list.sh` for `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, `PLACEHOLDER`, `return null`, `return {}`, `return []`, `=> {}`. No blockers found. The REVIEW.md (iteration 2) documents 2 INFO-level items (duplicated enumeration logic, redundant `cd`) — neither is a functional defect.

### Notable Implementation Deviations (Non-Blocking)

**Per-dir staging loop vs. single `git add -A personal/ office/`**

The plan and PLAN grep assertion (`grep -c "git add -A personal/ office/" = 1`) expected a single invocation. The actual code uses `for loc in personal office; do [[ -d ... ]] && git add -A "${loc}/"; done` (lines 723-726). This is strictly safer — `git add -A personal/ office/` exits 128 and stages nothing when one directory is absent (documented in the REVIEW and the code comment at line 718). The per-dir loop achieves the same goal with correct behavior on single-location machines. The `git add -A personal/ office/` form only appears as an echo string in the `--no-commit` manual instructions (line 758) — never executed.

The functional requirement (all four dirs staged in one commit) is fully met by the loop pattern.

**`map_file\.tmp` grep assertion**

The plan's grep `map_file\.tmp` expected >= 2 matches. The actual source uses `"${map_file}.tmp"` — the `}` brace makes the literal string `map_file.tmp` absent. The atomic `.tmp + mv` pattern IS present at lines 341/382 (`upsert_machine_label`) and lines 678/704 (`rename_machine`). Functionally satisfied; plan's grep pattern was a false negative.

### Human Verification Required

None. All success criteria are verifiable through source inspection and static analysis.

### Gaps Summary

No gaps. All 5 must-haves are VERIFIED against `update-list.sh`. Both REN-01 and REN-02 are satisfied. The script passes `zsh -n`. The implementation deviations from the plan (per-dir staging loop, `map_file.tmp` grep pattern) are plan-artifact false negatives, not implementation defects — the code is functionally correct and the REVIEW (iteration 2, status: clean) confirms all prior BLOCKER/WARNING findings were resolved.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_

---
phase: 07-archive-retention-control
reviewed: 2026-06-14T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: issues_found
---

# Phase 7: Code Review Report (Iteration 2)

**Reviewed:** 2026-06-14
**Depth:** standard
**Status:** issues_found (info-only; no BLOCKER or WARNING)

## Summary

Iteration 2 re-review of the Phase 7 archive-retention-control surface in `update-list.sh`,
focused on verifying that the three prior warnings (WR-01/WR-02/WR-03) are genuinely
resolved and that the fixes introduced no regressions. Scope reviewed: the `--archive-days`
case in `parse_arguments` (lines 122-135), `resolve_archive_retention()` (lines 220-250),
the `ARCHIVE_DAYS_SET` sentinel (line 48), the new TTY guard in `get_target_location`
(lines 168-171), and the main-block wiring (lines 1763-1803).

**All three prior warnings are confirmed fixed:**

- **WR-01 (misleading flag-named error on the prompt path) — RESOLVED.** Line 244 now emits
  `ERROR: Archive retention must be a positive integer (got '${input}')`, a path-appropriate
  message that no longer cites a flag the user did not invoke. Verified by source inspection
  (commit `35cbc54`).
- **WR-02 (`read` without `-r`) — RESOLVED.** Line 236 now uses `read -r input`, eliminating
  the backslash-mangling anti-pattern in the retention prompt (commit `85b7325`).
- **WR-03 (no TTY guard in `get_target_location`) — RESOLVED.** Lines 168-171 add
  `[[ ! -t 0 ]]` → actionable error + `exit 1` before the location prompt, mirroring the
  retention guard. The front-loaded-prompt non-interactive invariant now holds for the very
  first prompt, so a piped/cron run with no location flag fails loud instead of falling
  through to the invalid-choice branch (commit `141944c`).

**Regression checks (no regressions found).** `zsh -n` parses clean. Runtime verification
confirmed: `--archive-days abc` still rejects and exits 1; `--archive-days` with no value
exits 1 via the `[[ -z "$2" ]]` guard; `--archive-days --personal` rejects `--personal` as a
non-integer (fails loud rather than silently consuming a flag — acceptable); boundary inputs
`0` and `-5` are rejected; the non-TTY `get_target_location` guard fires under piped stdin
and exits 1 without prompting. The `local val` inside the `case` branch and the main-block
call ordering (`parse_arguments` → `get_target_location` → `resolve_archive_retention` →
... → `prune_old_archives "$TARGET_LOCATION"`) feeding the resolved `ARCHIVE_AGE_DAYS` into
`date -v-${ARCHIVE_AGE_DAYS}d` are all intact.

No BLOCKER- or WARNING-severity correctness, security, or data-loss issues remain in the
Phase 7 surface. The four pre-existing Info items below were never in fix scope and persist;
they are quality/robustness suggestions, not gating defects.

## Info

### IN-01: Validation logic duplicated across two call sites

**File:** `update-list.sh:128` and `update-list.sh:243`
**Issue:** The guard `[[ "$val" =~ ^[0-9]+$ ]] && (( val >= 1 ))` is copied verbatim into
both `parse_arguments` and `resolve_archive_retention`. Two copies of one validation rule
drift independently; if the rule changes (e.g. adding an upper bound) one site can be missed.
**Fix:** Extract a small validator and call it from both sites:
```zsh
is_positive_int() { [[ "$1" =~ ^[0-9]+$ ]] && (( $1 >= 1 )); }
# usage: if ! is_positive_int "$val"; then ...; fi
```

### IN-02: Leading-zero values accepted and echoed verbatim

**File:** `update-list.sh:128`, `update-list.sh:132`, `update-list.sh:248`
**Issue:** `--archive-days 08` (or `007`) passes `^[0-9]+$`, is stored as
`ARCHIVE_AGE_DAYS="08"`, and is echoed as `Archive retention: 08 days`. Verified safe
downstream: `date -v-08d` is decimal under BSD date and `(( val >= 1 ))` is decimal in zsh,
so there is no octal-misparse correctness bug. The only impact is the cosmetically odd echo.
The original CONTEXT stated an all-digits-and-≥1 test "is sufficient," so this is acceptable
per spec — flagged for awareness only.
**Fix (optional):** Normalize for display, e.g. `ARCHIVE_AGE_DAYS=$((10#$val))`, or document
that leading zeros are tolerated.

### IN-03: Usage banner omits `--archive-days` from the USAGE synopsis line

**File:** `update-list.sh:76` (and header comment, lines 21 + 26)
**Issue:** The OPTIONS block (line 82) and the header OPTIONS comment document
`--archive-days N`, but the one-line USAGE synopsis at line 76 still reads
`./update-list.sh [--personal | --office] [--no-commit]` and the header USAGE line (line 21)
likewise omits it. The synopsis and the options list are now inconsistent.
**Fix:** Update line 76 and the header comment (lines 21 + 26) to include `[--archive-days N]`.

### IN-04: Prompt default and empty-input echo hardcode the magic number 30

**File:** `update-list.sh:234`, `update-list.sh:240`
**Issue:** The prompt string `"Archive retention period in days [30]: "` (line 234) and the
empty-input echo `"Archive retention: 30 days"` (line 240) hardcode `30` rather than
referencing the `ARCHIVE_AGE_DAYS` default constant (line 45). If the default constant
changes, these two strings silently become wrong — the prompt would advertise `[30]` while
the real default differs. Note `display_usage` (line 86) already does this correctly via
`${ARCHIVE_AGE_DAYS}`.
**Fix:** Interpolate the constant:
```zsh
printf "Archive retention period in days [%s]: " "$ARCHIVE_AGE_DAYS"
...
echo "Archive retention: ${ARCHIVE_AGE_DAYS} days"
```

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (iteration 2)_

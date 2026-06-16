---
phase: 20-cut-over-external-catalog-verification
plan: "01"
subsystem: verification
tags: [mig-05, maccat, external-catalog, non-destructive, verification]
dependency_graph:
  requires: []
  provides: [MIG-05]
  affects: []
tech_stack:
  added: []
  patterns: [zipapp-pyz-build, external-catalog-dir, mktemp-disposable-dir]
key_files:
  created: []
  modified: []
decisions:
  - "Used local src/ tree (venv/bin/python -m zipapp) to build maccat.pyz rather than cloning github.com/scottkw/maccat — avoids network/auth dependencies and local src/ is byte-identical to the public repo"
  - "maccat.pyz required venv Python (3.14) to run since /usr/bin/python3 on this macOS is Python 3.9 (below maccat's 3.11 floor)"
metrics:
  duration: "~3 minutes"
  completed: "2026-06-16T04:54:47Z"
  tasks_completed: 2
  files_changed: 0
---

# Phase 20 Plan 01: MIG-05 External-Catalog Verification Summary

**One-liner:** maccat correctly catalogs against an isolated mktemp dir via --catalog-dir, producing a 775-line, 18-section catalog with zero commits and no impact on real catalog trees.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Obtain a runnable maccat in a disposable workspace | (verification — no files committed) | maccat.pyz built in $WORK |
| 2 | Run maccat against external mktemp catalog dir and assert structure | (verification — no files committed) | catalog produced + asserted in $CAT |

## Execution Details

### Task 1: maccat acquisition method

**Method used: venv zipapp build** (preferred path per plan).

Command:
```
/Users/ken/dev/mac-software-list/venv/bin/python -m zipapp src \
    --output $WORK/maccat.pyz \
    --python "/usr/bin/env python3" \
    --main "maccat.__main__:main" \
    --compress
```

- `WORK=/var/folders/lb/2__vrh3n2n155kwhrvz08lv80000gn/T/tmp.eGWJL4tDRG` (not inside this repo)
- `$WORK/maccat.pyz` exists and is non-empty: PASS
- `venv/bin/python $WORK/maccat.pyz --help` exits 0: PASS
- No files under `personal/` or `office/` touched: PASS

Note: System `/usr/bin/python3` on this macOS is Python 3.9 — below maccat's version guard (3.11+). The venv's Python 3.14 was used to both build and run the pyz.

### Task 2: External catalog run and assertions

**Catalog dir:** `CAT=/var/folders/lb/2__vrh3n2n155kwhrvz08lv80000gn/T/tmp.YuBSCEmwdh`
- `git init "$CAT"` — fresh repo, no remote (push impossible by design)
- Both `$WORK` and `$CAT` confirmed outside this repo before removal

**Command run:**
```
venv/bin/python $WORK/maccat.pyz --catalog-dir $CAT --computer test --no-commit
```

**Assertions:**

| Assertion | Check | Result |
|-----------|-------|--------|
| (a) Exactly one catalog file in $CAT/test/ | `ls $CAT/test/mac-software-list-*.txt \| wc -l == 1` | PASS — 1 file |
| (b) "Installed Mac Software List" header present | `grep -q '^Installed Mac Software List$'` | PASS |
| (c) "Homebrew Packages" section present | `grep -q '^Homebrew Packages$'` | PASS |
| (d) >= 5 section separators (36-dash rule) | `grep -c '^------------------------------------$' >= 5` | PASS — 18 separators |
| No commit made (--no-commit honored) | `git -C $CAT log --oneline \| wc -l == 0` | PASS — 0 commits |
| personal/ and office/ unchanged | `git status --porcelain personal office \| wc -l == 20` | PASS — 20 pre-existing D entries only, unchanged |
| $WORK removed | `test ! -e $WORK` | PASS |
| $CAT removed | `test ! -e $CAT` | PASS |

**Catalog file produced:**
- Filename: `mac-software-list-[test]-20260615235407.txt`
- Total lines: 775
- Total sections: 18 (section separators)
- Key section headers confirmed: Installed Mac Software List, Homebrew Packages, App Store Applications

**Config precedence confirmed:** `--catalog-dir` flag was the highest-precedence source, routing the catalog write to the disposable temp dir and never touching `~/.config/maccat/config.toml` or `MACCAT_CATALOG_DIR`.

## MIG-05 Satisfaction

MIG-05 is **verified**: maccat correctly catalogs against a genuinely external catalog repo resolved via `--catalog-dir` (the highest-precedence config source). The run was:
- Non-destructive: `--no-commit` honored, zero commits in temp dir
- Isolated: both temp dirs (`$WORK`, `$CAT`) were outside this repo and cleaned up
- Safe: `personal/` and `office/` byte-unchanged before and after (still only 20 pre-existing D entries from prior git state, none attributable to this run)

This is the last gate before the irreversible cut-over (Plan 20-02: MIG-04 repo strip).

## Deviations from Plan

None — plan executed exactly as written. The fallback path (PYTHONPATH=src module invocation) was not needed; the preferred zipapp build succeeded on the first attempt.

## Known Stubs

None. This plan produces no persistent artifacts and modifies no source files.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan is verification-only — no code modified, no files committed other than this SUMMARY.

## Self-Check: PASSED

- SUMMARY.md created at correct path
- Task 1 and Task 2 executed and verified
- All assertions passed (see assertions table above)
- Temp dirs cleaned up, personal/office confirmed unchanged
- No task-level commits (correct — this plan modifies no repo files)
- MIG-05 marked complete in REQUIREMENTS.md

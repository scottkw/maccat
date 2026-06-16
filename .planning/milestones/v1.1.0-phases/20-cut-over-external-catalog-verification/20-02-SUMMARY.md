---
phase: 20-cut-over-external-catalog-verification
plan: "02"
subsystem: repo-strip
tags: [mig-04, catalog-data, strip, private-remote, readme]
dependency_graph:
  requires: [20-01]
  provides: [catalog-data-only-repo]
  affects: [private-remote-origin]
tech_stack:
  added: []
  patterns: [git-rm-scoped-staging]
key_files:
  created: []
  modified:
    - README.md
decisions:
  - "Staging was scoped strictly to git rm targets + README; pre-existing D personal/*.txt churn left unstaged (per plan)"
  - "Untracked working-tree remnants (src/__pycache__, tests/golden, venv, dist) removed via rm -rf, not git rm"
  - ".planning/ left fully intact — orchestrator removes it last"
metrics:
  duration: "~5 min"
  completed: "2026-06-16"
---

# Phase 20 Plan 02: MIG-04 Repo Strip Summary

**One-liner:** Reduced mac-software-list a private Git host repo to catalog-data-only by removing 103 tracked code/tooling files via scoped git rm, rewriting README as a maccat pointer, and pushing to a private Git host — personal/, office/, machine-labels.tsv, archives, and .planning/ all preserved.

## What Was Done

### Task 1: Blocking Human-Verify Checkpoint
APPROVED by the human before execution. Prerequisites confirmed:
- Milestone v1.1.0 lifecycle ran (audit → complete-milestone → cleanup)
- Final .planning/ pushed to the maccat repo
- Real v1.1.0 release tag published to maccat with maccat.pyz attached

### Task 2: Strip Code/Tooling, Write Pointer README, Commit and Push

**Safety assertion passed:** `git remote get-url origin` → `a private catalog remote` (a private Git host confirmed; GitHub would have aborted the operation).

**Removed via `git rm -r` (103 tracked files across):**
- `src/` — full maccat Python package (27 files)
- `tests/` — test suite, golden fixtures, conftest (60+ files)
- `scripts/build-pyz.sh`
- `docs/superpowers/specs/2026-06-14-computer-folder-model-design.md`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `update-list.sh`
- `.python-version`
- `CLAUDE.md`
- `test-parse-arguments-11-02.sh`
- `test-rename-back-12-02.sh`
- `test-rename-front-12-01.sh`

**Removed from working tree only (untracked):**
- `venv/`, `dist/`, `src/__pycache__/` remnants, `tests/golden/` remnants, `tests/collectors/__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`
- `config.example.toml` — was absent (not tracked, not present)

**README.md rewritten** as a short pointer:
- Title: "# Mac Software Catalogs"
- Notes this repo holds private per-machine catalogs (data only)
- Points to https://github.com/scottkw/maccat for the tool
- Notes catalog organization (personal/, office/) and machine-labels.tsv

**Scoped staging:** Only git rm targets and README.md staged. Pre-existing ` D personal/*.txt` working-tree deletions (catalog churn from another machine) were deliberately NOT staged — they remain as unstaged deletions for the repo owner to handle separately.

**Commit:** `3e2c2ef` — `chore: reduce repo to catalog-data-only — maccat tool moved to github.com/scottkw/maccat (MIG-04)`

**Push:** Succeeded to `a private catalog remote` (`70dbec4..3e2c2ef main -> main`)

## KEEP Items Verified Intact

| Item | Status |
|------|--------|
| `personal/` | Present |
| `personal/archive/` | Present |
| `office/` | Present |
| `office/archive/` | Present |
| `machine-labels.tsv` | Present |
| `.planning/` | Present (orchestrator removes last) |
| `.git` | Present |

## Post-Strip Working Tree

After the strip, the working tree contains only:
- `README.md` (rewritten pointer)
- `machine-labels.tsv` (hostname → label map, kept)
- `personal/` (catalog data + archive)
- `office/` (catalog data + archive)
- `.git/` (repository metadata)
- `.planning/` (GSD home — pending orchestrator removal)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Untracked directory remnants after git rm**
- **Found during:** Task 2 post-strip assertions
- **Issue:** `src/` and `tests/` remained as empty/untracked directories after `git rm -r` because `__pycache__/`, `golden/`, and other compiled artifacts were not tracked by git and thus not removed by `git rm`
- **Fix:** `rm -rf src tests` on working tree (not via git rm — files were untracked)
- **Files modified:** Untracked directories only — no git history impact
- **Commit:** No additional commit needed (untracked files; post-strip assertions all passed after removal)

## Pending Orchestrator Action

`.planning/` removal is NOT part of this plan. The orchestrator performs this final irreversible step after:
1. This strip commit is confirmed pushed to a private Git host (DONE: `3e2c2ef`)
2. Milestone lifecycle (audit → complete-milestone → cleanup) completed
3. Final `.planning/` pushed to maccat repo

Orchestrator command: `git rm -r .planning && git commit -m "chore(MIG-04): remove .planning — GSD home now lives in scottkw/maccat" && git push origin HEAD`

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan only removes files — the threat mitigations T-20-03 and T-20-04 were applied:
- T-20-03: Explicit enumerated remove-list used; personal/office/machine-labels.tsv/archive never passed to git rm
- T-20-04: Origin asserted as a private Git host before push; would have aborted on GitHub

## Self-Check: PASSED

- `test ! -d src` → PASSED (gone)
- `test ! -d tests` → PASSED (gone)
- `test ! -d scripts` → PASSED (gone)
- `test ! -d docs` → PASSED (gone)
- `test ! -d .github` → PASSED (gone)
- `test ! -f update-list.sh` → PASSED (gone)
- `test ! -f pyproject.toml` → PASSED (gone)
- `test ! -f CLAUDE.md` → PASSED (gone)
- `test -d personal` → PASSED (kept)
- `test -d office` → PASSED (kept)
- `test -f machine-labels.tsv` → PASSED (kept)
- `test -d personal/archive` → PASSED (kept)
- `test -d office/archive` → PASSED (kept)
- `test -d .planning` → PASSED (kept, orchestrator removes last)
- `grep -q 'github.com/scottkw/maccat' README.md` → PASSED
- `git remote get-url origin | grep -q private-remote` → PASSED
- Strip commit `git show --stat HEAD` contains no `personal/*.txt` paths → PASSED
- Strip commit hash `3e2c2ef` exists in git log → PASSED

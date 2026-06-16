---
phase: 19-ci-build-release-pipeline
plan: "01"
subsystem: ci
tags: [github-actions, ci, build, artifact, pyz]
dependency_graph:
  requires: []
  provides: [CI-02-build-job, maccat.pyz-artifact]
  affects: [github.com/scottkw/maccat/.github/workflows/ci.yml]
tech_stack:
  added: []
  patterns: [parallel-jobs-in-workflow, upload-artifact-v4]
key_files:
  created: []
  modified:
    - /tmp/maccat-staging.AxZxJN/.github/workflows/ci.yml  # pushed to github.com/scottkw/maccat
    - .planning/REQUIREMENTS.md
decisions:
  - "Build job runs parallel to test matrix (not sequential) — avoids 3 redundant artifact uploads"
  - "Runner stays macos-latest for build (consistent with existing CI; zipapp is OS-agnostic)"
  - "if-no-files-found: error on upload-artifact ensures build failure is visible, not silently skipped"
metrics:
  duration: "~5 min (CI run: 26s wall-clock for all 4 jobs)"
  completed: "2026-06-16"
  tasks_completed: 2
  files_modified: 1
---

# Phase 19 Plan 01: CI Build Artifact (CI-02) Summary

Added a `build` job to `.github/workflows/ci.yml` in `github.com/scottkw/maccat` that runs `scripts/build-pyz.sh` and uploads `maccat.pyz` as a workflow artifact on every push/PR to `main`; confirmed by a real green Actions run (27593763334) carrying the artifact.

## What Was Done

### Task 1: Confirmed CI-01 and added build job to ci.yml

- **CI-01 confirmed:** Run 27593156990 (initial commit push, 2026-06-16T03:59:28Z) — conclusion `success`, 28s.
- Added a `build` job to `.github/workflows/ci.yml` in the maccat staging tree (`/tmp/maccat-staging.AxZxJN`):
  - `runs-on: macos-latest` (consistent with existing CI runner)
  - Steps: `actions/checkout@v4`, `actions/setup-python@v5` (3.11), `chmod +x scripts/build-pyz.sh && ./scripts/build-pyz.sh`, `actions/upload-artifact@v4` with `name: maccat.pyz` / `path: dist/maccat.pyz` / `if-no-files-found: error`
- Verified YAML valid, `upload-artifact` present, `build-pyz.sh` referenced, `dist/` untracked.

### Task 2: Pushed and observed real green run with artifact

- Committed to maccat repo: `4a914de ci: build maccat.pyz and upload as workflow artifact (CI-02)`
- Pushed to `github.com/scottkw/maccat` main.
- Run 27593763334 triggered — all 4 jobs green:
  - `build` job: 9s — `maccat.pyz` built and uploaded
  - `test (0)`: 23s
  - `test (42)`: 26s
  - `test (random)`: 18s
- Artifact confirmed: `maccat.pyz` (47,554 bytes) present on run 27593763334.
- This repo's a private Git host origin (`a private catalog remote`) was never pushed.

## Key Run IDs

| Requirement | Run ID | Conclusion | Artifact |
|-------------|--------|------------|---------|
| CI-01 | 27593156990 | success | n/a (test-only) |
| CI-02 | 27593763334 | success | maccat.pyz (47,554 bytes) |

## Run URL

https://github.com/scottkw/maccat/actions/runs/27593763334

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced beyond those already in the plan's threat model.

## Self-Check: PASSED

- ci.yml modified in maccat staging tree: confirmed (read back)
- maccat.pyz artifact on run 27593763334: confirmed via `gh api`
- CI-01 run 27593156990 conclusion=success: confirmed via `gh run list`
- This repo's origin unchanged (a private Git host): confirmed via `git remote get-url origin`
- REQUIREMENTS.md CI-01 and CI-02 marked Complete: confirmed

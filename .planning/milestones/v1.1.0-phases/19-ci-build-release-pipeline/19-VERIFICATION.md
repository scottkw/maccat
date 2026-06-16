---
phase: 19-ci-build-release-pipeline
verified: 2026-06-15T00:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
---

# Phase 19: CI Build & Release Pipeline Verification Report

**Phase Goal:** The new repo's GitHub Actions build the `.pyz` and run the existing test gates on every push/PR to `main`, and publish a versioned GitHub Release with the compiled `.pyz` attached when a version tag is pushed.
**Verified:** 2026-06-15
**Status:** passed
**Re-verification:** No — initial verification

Verification was performed against REAL GitHub state on `github.com/scottkw/maccat` via `gh api` / `gh run list` / `gh release list`, NOT against SUMMARY.md claims or the (possibly absent) local staging tree. Every workflow file was fetched from the maccat repo over the API, and run/release/tag state was queried live.

## Goal Achievement

### Observable Truths

| #   | Truth (ROADMAP SC + PLAN must-haves)                                                                                          | Status     | Evidence                                                                                                                                                                  |
| --- | --------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | CI-01: test workflow runs on push/PR to main and is green (pytest+ruff+mypy --strict+zsh -n, macos-latest, HASHSEED matrix) | ✓ VERIFIED | `ci.yml` on maccat main has `test` job: macos-latest, matrix [0,42,random], ruff/mypy --strict/pytest/`zsh -n update-list.sh`. Runs 27593156990, 27593763334, 27593889738 on main all `success`. |
| 2   | CI-02: ci.yml builds maccat.pyz via scripts/build-pyz.sh and uploads it as a downloadable artifact on push/PR              | ✓ VERIFIED | `ci.yml` `build` job invokes `./scripts/build-pyz.sh` + `actions/upload-artifact@v4` (name maccat.pyz, path dist/maccat.pyz, if-no-files-found: error). Run 27593763334 artifact `maccat.pyz` 47554 bytes; latest run 27593889738 artifact 47548 bytes. |
| 3   | CI-03: separate release.yml triggers on v*.*.* tags, builds on ubuntu-latest, publishes Release with maccat.pyz via gh release create (no 3rd-party action), contents: write | ✓ VERIFIED | `release.yml` exists: `on.push.tags ['v*.*.*']`, `permissions: contents: write`, job on `ubuntu-latest`, `gh release create "$GITHUB_REF_NAME" dist/maccat.pyz` with `GH_TOKEN: secrets.GITHUB_TOKEN`. No softprops. Run 27593897536 (tag v0.0.1-ci-test) `success`; "Publish GitHub Release" step succeeded. |
| 4   | maccat.pyz is NOT committed to the repo (dist/ gitignored)                                                                  | ✓ VERIFIED | No release asset/committed artifact; build output is workflow artifact only. Commit log shows only workflow edits (4a914de, 9b3d35e), no dist/ blob. |
| 5   | release job grants only contents: write (no broader scope)                                                                 | ✓ VERIFIED | `release.yml` top-level `permissions: contents: write` only — no other permission keys present in fetched file. |
| 6   | CLEANUP: throwaway v0.0.1-ci-test release AND tag are gone (remote)                                                          | ✓ VERIFIED | `gh release view v0.0.1-ci-test` → "release not found"; `gh api .../git/refs/tags/v0.0.1-ci-test` → 404; `gh api .../tags` → empty. |
| 7   | No real v1.1.0 release/tag exists yet (deferred to Phase 20)                                                                 | ✓ VERIFIED | `gh release list` → empty; `gh api .../git/refs/tags/v1.1.0` → 404. |
| 8   | SAFETY: this repo's origin still private-remote; no third-party action in release.yml                                                | ✓ VERIFIED | `git remote get-url origin` → `a private catalog remote`. release.yml grep for `softprops` → none. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact                                | Expected                                          | Status     | Details                                                                                                  |
| --------------------------------------- | ------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `scottkw/maccat:.github/workflows/ci.yml`      | test matrix job + build/upload-artifact step      | ✓ VERIFIED | Fetched via `gh api contents`. Contains `test` (macos-latest matrix) + `build` jobs; `build-pyz.sh` + `actions/upload-artifact@v4` present. |
| `scottkw/maccat:.github/workflows/release.yml` | tag-triggered build + gh release create publish   | ✓ VERIFIED | Fetched via `gh api contents`. `on.push.tags ['v*.*.*']`, ubuntu-latest, `gh release create`, contents:write, no softprops. |

Both artifacts live in the maccat repo (the phase's intended target), not this repo — confirmed by API fetch. This repo's local tree was not relied upon.

### Key Link Verification

| From                          | To                            | Via                                  | Status   | Details                                                              |
| ----------------------------- | ----------------------------- | ------------------------------------ | -------- | -------------------------------------------------------------------- |
| ci.yml build step             | scripts/build-pyz.sh          | `run: ./scripts/build-pyz.sh`        | ✓ WIRED  | Present in `build` job; run 27593763334 produced a real artifact, proving the script executed and emitted dist/maccat.pyz. |
| ci.yml upload step            | dist/maccat.pyz               | `actions/upload-artifact@v4`         | ✓ WIRED  | `name: maccat.pyz`, `path: dist/maccat.pyz`. Artifact present on runs 27593763334 (47554 B) and 27593889738 (47548 B). |
| release.yml trigger           | tag push v*.*.*               | `on.push.tags`                       | ✓ WIRED  | Tag `v0.0.1-ci-test` (matches v*.*.*) triggered run 27593897536. |
| release.yml publish step      | GitHub Release asset          | `gh release create ... dist/maccat.pyz` | ✓ WIRED | "Publish GitHub Release" step in run 27593897536 = success; SUMMARY recorded maccat.pyz asset 50004 B before cleanup. |

### Behavioral Spot-Checks

| Behavior                                          | Command                                                                 | Result                                  | Status |
| ------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------- | ------ |
| ci.yml runs green on push to main                 | `gh run list --repo scottkw/maccat --workflow ci.yml --branch main`     | 3 runs, all conclusion=success          | ✓ PASS |
| CI run carries maccat.pyz artifact                | `gh api .../actions/runs/27593763334/artifacts`                         | `maccat.pyz` 47554 bytes, expired=false | ✓ PASS |
| release.yml ran green for v*.*.* tag              | `gh run list --workflow release.yml` + jobs steps                       | run 27593897536 success; publish step success | ✓ PASS |
| Test release+tag cleaned up                       | `gh release view v0.0.1-ci-test` / `gh api .../tags/v0.0.1-ci-test`     | not found / 404                         | ✓ PASS |
| No real release/tag yet                           | `gh release list` / `gh api .../tags/v1.1.0`                            | empty / 404                             | ✓ PASS |
| This repo origin still private-remote                      | `git remote get-url origin`                                             | a private git host                    | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                  | Status      | Evidence                                                        |
| ----------- | ----------- | ---------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------- |
| CI-01       | 19-01       | Test workflow runs on every push/PR to main (macOS, hashseed matrix)         | ✓ SATISFIED | ci.yml test job + 3 green runs on main                          |
| CI-02       | 19-01       | CI builds .pyz via build-pyz.sh and uploads workflow artifact                | ✓ SATISFIED | ci.yml build job + maccat.pyz artifact on runs 27593763334/...889738 |
| CI-03       | 19-02       | Version-tag push creates a Release with compiled .pyz attached               | ✓ SATISFIED | release.yml + green run 27593897536 for v0.0.1-ci-test (publish step success) |

No orphaned requirements: REQUIREMENTS.md maps exactly CI-01/CI-02/CI-03 to Phase 19, all claimed by the plans.

### Anti-Patterns Found

None. Workflow files contain no debt markers, no third-party actions, no broader-than-needed permissions, and no committed build artifact. Only first-party `actions/*` (checkout@v4, setup-python@v5, upload-artifact@v4) and built-in `gh` are used.

### Human Verification Required

None — every success criterion is scriptable and was verified against live GitHub state.

### Gaps Summary

No gaps. All three ROADMAP success criteria are observably true on `github.com/scottkw/maccat`:
1. The test workflow runs on push/PR to main and reports results (3 green runs observed).
2. CI builds and uploads `maccat.pyz` as a downloadable artifact on push (artifact present on the latest two main runs).
3. A `v*.*.*` tag push triggers `release.yml` which builds on ubuntu-latest and publishes a Release with `maccat.pyz` via `gh release create` (proven by the green v0.0.1-ci-test run, then cleaned up).

Safety/cleanup invariants hold: the throwaway test release and tag are fully removed, no real v1.1.0 was cut (deferred to Phase 20), this repo's a private Git host origin is untouched, and no third-party action is used.

Note: the live Release asset for v0.0.1-ci-test was intentionally deleted as part of validation cleanup, so it cannot be re-fetched now. Its prior existence is corroborated by the release run's "Publish GitHub Release" step concluding `success` (the step IS `gh release create dist/maccat.pyz`) plus the SUMMARY-recorded asset size/SHA — and the cleanup itself is independently confirmed by the now-404 release/tag. This is expected behavior, not a gap.

---

_Verified: 2026-06-15_
_Verifier: Claude (gsd-verifier)_

---
phase: 19-ci-build-release-pipeline
plan: "02"
subsystem: ci
tags: [github-actions, release, pyz, tag-trigger, gh-cli]
dependency_graph:
  requires: [CI-02-build-job]
  provides: [CI-03-release-workflow, maccat.pyz-release-asset]
  affects: [github.com/scottkw/maccat/.github/workflows/release.yml]
tech_stack:
  added: []
  patterns: [tag-triggered-release, gh-release-create, contents-write-only]
key_files:
  created:
    - /tmp/maccat-staging.AxZxJN/.github/workflows/release.yml  # pushed to github.com/scottkw/maccat
  modified:
    - .planning/REQUIREMENTS.md
decisions:
  - "gh release create in a run step (not softprops) — no third-party action, contents:write only"
  - "Release job on ubuntu-latest (zipapp is OS-agnostic, cheaper/faster than macos-latest)"
  - "Throwaway tag v0.0.1-ci-test used for validation, fully deleted after confirming Release+asset"
metrics:
  duration: "~5 min (release run: completed in <30s wall-clock)"
  completed: "2026-06-16"
  tasks_completed: 2
  files_modified: 1
---

# Phase 19 Plan 02: Tag-Triggered Release Workflow (CI-03) Summary

Tag-triggered release workflow on ubuntu-latest using `gh release create` + `secrets.GITHUB_TOKEN` (`contents: write` only), proven by run 27593897536 for tag `v0.0.1-ci-test` which produced a GitHub Release with `maccat.pyz` (50,004 bytes) attached — then fully cleaned up.

## What Was Done

### Task 1: Create release.yml and push to maccat main

- Created `.github/workflows/release.yml` in the maccat staging tree (`/tmp/maccat-staging.AxZxJN`):
  - `name: Release`
  - `on.push.tags: ['v*.*.*']` — matches `v1.1.0` and pre-release test tags
  - `permissions: contents: write` (top-level; nothing broader)
  - Single job `release` on `runs-on: ubuntu-latest`
  - Steps: `actions/checkout@v4`, `actions/setup-python@v5` (3.11), `chmod +x scripts/build-pyz.sh && ./scripts/build-pyz.sh`, then `gh release create "${GITHUB_REF_NAME}" dist/maccat.pyz --title "${GITHUB_REF_NAME}" --generate-notes` with `env: GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`
  - No third-party action (no softprops, no marketplace release action)
- Committed: `9b3d35e ci: add tag-triggered release workflow publishing maccat.pyz (CI-03)`
- Pushed to `github.com/scottkw/maccat` main; `dist/` status clean (no artifact committed).

### Task 2: Validate CI-03, confirm Release+asset, clean up

**Validation:**
- Pushed throwaway tag: `git -C <tree> tag v0.0.1-ci-test && git push origin v0.0.1-ci-test`
- Release run triggered immediately — completed `success` in <30s:
  - **Run ID:** 27593897536
  - **Conclusion:** success
  - **Head branch:** v0.0.1-ci-test
  - **Created at:** 2026-06-16T04:20:11Z
- Release confirmed: `gh release view v0.0.1-ci-test --json assets -q '.assets[].name'` → `maccat.pyz`
- Asset details: `maccat.pyz`, 50,004 bytes, SHA-256 `94fe48fa7cd680f3f5e7d3f32bc63abead9a7a5cddacaff8b1e21597e8dbb23b`

**Cleanup (all confirmed):**
- `gh release delete v0.0.1-ci-test --repo scottkw/maccat --yes --cleanup-tag` — release deleted
- `git -C <tree> push origin :refs/tags/v0.0.1-ci-test` — remote tag deleted
- `git -C <tree> tag -d v0.0.1-ci-test` — local tag deleted
- `gh release view v0.0.1-ci-test` → not found (release gone)
- `gh api repos/scottkw/maccat/git/refs/tags/v0.0.1-ci-test` → not found (remote tag gone)
- `git tag -l v0.0.1-ci-test` → empty (local tag gone)
- `gh api repos/scottkw/maccat/git/refs/tags/v1.1.0` → not found (real v1.1.0 not created)
- This repo's origin: `a private catalog remote` (unchanged — never pushed)

## Key Run IDs

| Requirement | Run ID | Conclusion | Asset |
|-------------|--------|------------|-------|
| CI-03 | 27593897536 | success | maccat.pyz (50,004 bytes) |

## Run URL

https://github.com/scottkw/maccat/actions/runs/27593897536

## Maccat Commit

| Commit | Message | Repo |
|--------|---------|------|
| 9b3d35e | ci: add tag-triggered release workflow publishing maccat.pyz (CI-03) | github.com/scottkw/maccat |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced beyond those already in the plan's threat model. All T-19-04 through T-19-SC mitigations confirmed applied:
- T-19-04: `permissions: contents: write` only (verified by YAML parse + acceptance check)
- T-19-05: Token passed via `env: GH_TOKEN`, never echoed in logs
- T-19-06: v0.0.1-ci-test release + remote tag + local tag all deleted and confirmed gone
- T-19-07: No third-party action (`softprops` absent in workflow, confirmed by grep)

## Self-Check: PASSED

- release.yml exists at maccat commit 9b3d35e on origin/main: confirmed via `git log`
- Run 27593897536 conclusion=success: confirmed via `gh run list`
- maccat.pyz asset (50,004 bytes) on release v0.0.1-ci-test: confirmed via `gh release view`
- v0.0.1-ci-test release gone: confirmed (gh release view returns not-found)
- v0.0.1-ci-test remote tag gone: confirmed (gh api returns not-found)
- v0.0.1-ci-test local tag gone: confirmed (git tag -l returns empty)
- v1.1.0 not created: confirmed (gh api returns not-found)
- This repo's origin unchanged (a private Git host): confirmed via `git remote get-url origin`
- CI-03 marked Complete in REQUIREMENTS.md: confirmed

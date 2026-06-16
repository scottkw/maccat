# Phase 19: CI Build & Release Pipeline - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `.pyz` build step + artifact upload to the new `maccat` repo's CI on push/PR to `main`
(CI-02), and a separate tag-triggered workflow that publishes a GitHub Release with the compiled
`.pyz` attached (CI-03). CI-01 (the migrated test workflow runs on push/PR to `main`) is ALREADY
satisfied — the initial push to `github.com/scottkw/maccat` triggered a green CI run
(run 27593156990, macOS, 28s); this phase confirms it and layers build+release on top.

All deliverables land in the **`maccat` GitHub repo** (`github.com/scottkw/maccat`), NOT this repo.
This phase does NOT reduce this repo to catalog-data-only (Phase 20) and does NOT cut the real
`v1.1.0` release.

</domain>

<decisions>
## Implementation Decisions

### CI Workflow Structure & Release Mechanics
- Keep the test job in `.github/workflows/ci.yml`; add a **separate** `.github/workflows/release.yml` for the tag-triggered release (clean separation — release logic only fires on tags).
- CI-02: add a build step to `ci.yml` that runs `scripts/build-pyz.sh` and uploads `maccat.pyz` via `actions/upload-artifact` on every push/PR to `main`.
- CI-03: the release workflow uses **`gh release create` in a run step** (built-in `gh` + `GITHUB_TOKEN`) — no third-party action, matching the project's minimal-deps ethos. Requires `permissions: contents: write`.
- Release `.pyz` is built on **`ubuntu-latest`** (zipapp is OS-agnostic — faster/cheaper); the test matrix stays on `macos-latest`.

### Release Validation
- Tag pattern the release workflow matches: **`v*.*.*`** (matches `v1.1.0` and the test tag `v0.0.1-ci-test`).
- Validate the pipeline by pushing a **throwaway pre-release tag `v0.0.1-ci-test`**, confirming the Release exists with the `.pyz` asset attached, then **deleting the release AND the tag** (both remote and local). Do NOT cut the real `v1.1.0` in this phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/build-pyz.sh` — already builds `dist/maccat.pyz` via stdlib `python -m zipapp` (deterministic). The release/build jobs invoke this.
- `.github/workflows/ci.yml` (in the maccat repo) — existing test workflow: `runs-on: macos-latest`, matrix `PYTHONHASHSEED: [0, 42, random]`, steps: venv + `pip install -e .[dev]`, ruff, mypy --strict, pytest, `zsh -n update-list.sh`. Triggers on push to `main` + pull_request.
- `pyproject.toml` — hatchling, `>=3.11`, `[dev]` extras.

### Established Patterns
- The existing CI installs into a venv (`python -m venv venv && ./venv/bin/pip install -e ".[dev]"`). Build steps should mirror this style or call `scripts/build-pyz.sh` directly.

### Integration Points
- **Where the work happens:** the `maccat` GitHub repo. Work from a **fresh `git clone https://github.com/scottkw/maccat`** into a temp dir (preferred for robustness), OR the existing staging tree at `/tmp/maccat-staging.AxZxJN` (already has `origin=github.com/scottkw/maccat`). Commit + push workflow changes to `main`. Observe runs via `gh run list/watch --repo scottkw/maccat`.
- This repo's GSD `.planning/` receives the phase artifacts (CONTEXT/PLAN/SUMMARY/VERIFICATION); the maccat repo's `.planning/` snapshot is NOT updated here (reconciled at cut-over).

</code_context>

<specifics>
## Specific Ideas

- Verification should observe REAL GitHub Actions runs (not just YAML inspection): confirm a push run is green (CI-01/CI-02 with the artifact present), and that the `v0.0.1-ci-test` tag produced a Release with `maccat.pyz` attached — then clean the test tag/release up.
- `.pyz` must not be committed to the repo (it's a build artifact); `.gitignore` already excludes `dist/`.

</specifics>

<deferred>
## Deferred Ideas

- Cutting the real `v1.1.0` release — deferred (milestone completes at Phase 20 cut-over).
- PKG-04 (PyPI/pipx) — separate future milestone.
- Reducing this repo to catalog-data-only + final `.planning/` sync to the maccat repo — Phase 20 / cut-over.

</deferred>

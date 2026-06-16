# Roadmap: Mac Software List Generator

## Milestones

- ✅ **v0.46.0 Extension Cataloging** — Phases 1-5 (shipped 2026-06-13) — [archive](milestones/v0.46.0-ROADMAP.md)
- ✅ **v0.47.0 Catalog Retention & Sync** — Phase 6 (shipped 2026-06-14) — [archive](milestones/v0.47.0-ROADMAP.md)
- ✅ **v0.48.0 Machine Identity & Retention Control** — Phases 7-9 (shipped 2026-06-14) — [archive](milestones/v0.48.0-ROADMAP.md)
- ✅ **v0.49.0 Computer-Folder Model** — Phases 10-12 (shipped 2026-06-14) — [archive](milestones/v0.49.0-ROADMAP.md)
- ✅ **v1.0.0 Python Port & Distribution** — Phases 13-17 (shipped 2026-06-14) — [archive](milestones/v1.0.0-ROADMAP.md)
- 🚧 **v1.1.0 Repo Separation & CI Build** — Phases 18-20 (in progress)

## Phases

<details>
<summary>✅ v0.46.0 Extension Cataloging (Phases 1-5) — SHIPPED 2026-06-13</summary>

- [x] Phase 1: Shared Helpers Foundation (1/1 plans) — completed 2026-06-13
- [x] Phase 2: Editor Collectors (2/2 plans) — completed 2026-06-13
- [x] Phase 3: AI-CLI Collectors (4/4 plans) — completed 2026-06-13
- [x] Phase 4: Browser Collectors (3/3 plans) — completed 2026-06-13
- [x] Phase 5: Integration & Verification Gates (2/2 plans) — completed 2026-06-13

Full details: [milestones/v0.46.0-ROADMAP.md](milestones/v0.46.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.47.0 Catalog Retention & Sync (Phase 6) — SHIPPED 2026-06-14</summary>

- [x] Phase 6: Retention & Sync (1/1 plans) — completed 2026-06-14

Full details: [milestones/v0.47.0-ROADMAP.md](milestones/v0.47.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.48.0 Machine Identity & Retention Control (Phases 7-9) — SHIPPED 2026-06-14</summary>

- [x] Phase 7: Archive Retention Control (1/1 plans) — completed 2026-06-14
- [x] Phase 8: Machine Identity (1/1 plans) — completed 2026-06-14
- [x] Phase 9: Machine Rename (1/1 plans) — completed 2026-06-14

Full details: [milestones/v0.48.0-ROADMAP.md](milestones/v0.48.0-ROADMAP.md)

</details>

<details>
<summary>✅ v0.49.0 Computer-Folder Model (Phases 10-12) — SHIPPED 2026-06-14</summary>

- [x] Phase 10: Computer-Folder Identity Foundation (1/1 plans) — completed 2026-06-14
- [x] Phase 11: Computer Selection & CLI (2/2 plans) — completed 2026-06-14
- [x] Phase 12: Computer Rename (2/2 plans) — completed 2026-06-14

Full details: [milestones/v0.49.0-ROADMAP.md](milestones/v0.49.0-ROADMAP.md)

</details>

<details>
<summary>✅ v1.0.0 Python Port & Distribution (Phases 13-17) — SHIPPED 2026-06-14</summary>

Full phase detail: [milestones/v1.0.0-ROADMAP.md](milestones/v1.0.0-ROADMAP.md)

- [x] Phase 13: Package Foundation + Output Format (3/3 plans) — completed 2026-06-14
- [x] Phase 14: Config, Identity & Retention (4/4 plans) — completed 2026-06-14
- [x] Phase 15: Collectors (8/8 plans) — completed 2026-06-15
- [x] Phase 16: Git, CLI & Distribution (3/3 plans) — completed 2026-06-15
- [x] Phase 17: Parity & Safety Tests (3/3 plans) — completed 2026-06-15

</details>

### 🚧 v1.1.0 Repo Separation & CI Build (In Progress)

**Milestone Goal:** Extract `maccat` into a clean, generic **public** GitHub repo started from a
fresh git history (code + tests + build tooling + docs + the zsh reference + `.planning/`), genericize
all setup-specific content, add a GitHub Action that builds the `.pyz` and runs the existing test gates
on push/PR to `main` plus publishes a Release `.pyz` on a version tag, verify maccat against a genuinely
external catalog repo, and finally reduce **this** repo to catalog-data-only — clearing the runway for
feature development in the new repo.

This is a **brownfield infrastructure** milestone: the code, tests (`tests/`), build script
(`scripts/build-pyz.sh`), and an existing CI test workflow (`.github/workflows/ci.yml` — macOS runner,
`PYTHONHASHSEED` 0/42/random matrix, ruff/mypy/pytest/`zsh -n`) **already exist** here. This milestone
*moves* them and *adds* build+release to CI — it does not re-create the test suite from scratch.

- [ ] **Phase 18: Public Repo Migration (Genericized, Fresh History)** — Stand up the new public repo from a genericized clean tree with zero personal data and a fresh git history
- [ ] **Phase 19: CI Build & Release Pipeline** — Extend CI in the new repo to build the `.pyz` per push/PR and publish a Release `.pyz` on a version tag
- [ ] **Phase 20: Cut-Over & External-Catalog Verification** — Prove maccat runs against an external catalog repo, then reduce this repo to catalog-data-only

## Phase Details

### Phase 18: Public Repo Migration (Genericized, Fresh History)
**Goal**: A new public GitHub repo exists holding the genericized maccat code, tests, build tooling, docs, the zsh reference, and `.planning/` history — started from a fresh git history that exposes zero personal catalog data anywhere in the tree or the log.
**Depends on**: Nothing (first phase of this milestone; operates on the current maccat tree as source)
**Requirements**: MIG-01, MIG-02, MIG-03, GEN-01, GEN-02, GEN-03, GEN-04
**Success Criteria** (what must be TRUE):
  1. A new **public** GitHub repo (created via `gh`) exists and contains the maccat code (`src/`), tests, `pyproject.toml`, `scripts/build-pyz.sh`, docs, `update-list.sh`, and `.planning/` at their current state
  2. The new repo's working tree contains **no** personal catalog `.txt` files, hostnames, machine names, committed `dist/maccat.pyz` artifact, stray root throwaway test scripts (`test-parse-arguments-11-02.sh`, `test-rename-back-12-02.sh`, `test-rename-front-12-01.sh`), `venv/`, or `personal`/`office` catalog folders
  3. The new repo's **entire git log** (every commit, from the initial one) contains zero personal catalog data — confirmed by inspecting the full history, not just the tip
  4. The README documents install-from-Releases, catalog-dir configuration, and basic usage with no personal paths or values; an example/template config and an open-source LICENSE file are present
**Plans**: 2 plans
- [ ] 18-01-PLAN.md — Build genericized staging tree (copy include-list, exclude personal data, add LICENSE/.gitignore/example config, rewrite README)
- [ ] 18-02-PLAN.md — Fresh git init + privacy gate (working tree + full log scan), then create public scottkw/maccat and push

### Phase 19: CI Build & Release Pipeline
**Goal**: The new repo's GitHub Actions build the `.pyz` and run the existing test gates on every push/PR to `main`, and publish a versioned GitHub Release with the compiled `.pyz` attached when a version tag is pushed.
**Depends on**: Phase 18 (the new repo and its `.github/workflows/ci.yml` + `scripts/build-pyz.sh` must already exist there)
**Requirements**: CI-01, CI-02, CI-03
**Success Criteria** (what must be TRUE):
  1. On every push and pull request to `main` in the new repo, the test workflow runs (pytest + ruff + mypy `--strict` + `zsh -n update-list.sh`, macOS runner, `PYTHONHASHSEED` 0/42/random matrix) and reports pass/fail
  2. On every push/PR to `main`, CI builds the `.pyz` via `scripts/build-pyz.sh` and uploads it as a downloadable workflow artifact
  3. Pushing a version tag (e.g. `v1.1.0`) creates a GitHub Release with the freshly compiled `.pyz` attached as a release asset
**Plans**: TBD

### Phase 20: Cut-Over & External-Catalog Verification
**Goal**: maccat is proven to catalog correctly against a genuinely external catalog repo via its config resolution, after which this repo is reduced to catalog-data-only as the final cut-over.
**Depends on**: Phase 18 (new repo must hold the working maccat); Phase 19 (release pipeline proven before cut-over). This phase is intentionally **last** so this repo's source tree stays intact until the new repo is verified.
**Requirements**: MIG-05, MIG-04
**Success Criteria** (what must be TRUE):
  1. maccat run from the new repo correctly catalogs against an **external** catalog repo resolved via `--catalog-dir` flag, `MACCAT_CATALOG_DIR` env, and `~/.config/maccat/config.toml` (precedence order honored)
  2. Verification is performed against an isolated/disposable catalog dir (e.g. `mktemp -d`), never the user's real `personal/`/`office/` trees
  3. This repo is reduced to **catalog-data-only** — code, tests, build tooling, docs, and `.planning/` removed; catalog folders, `machine-labels.tsv`, and archives remain intact
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 18 → 19 → 20

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Shared Helpers Foundation | v0.46.0 | 1/1 | Complete | 2026-06-13 |
| 2. Editor Collectors | v0.46.0 | 2/2 | Complete | 2026-06-13 |
| 3. AI-CLI Collectors | v0.46.0 | 4/4 | Complete | 2026-06-13 |
| 4. Browser Collectors | v0.46.0 | 3/3 | Complete | 2026-06-13 |
| 5. Integration & Verification Gates | v0.46.0 | 2/2 | Complete | 2026-06-13 |
| 6. Retention & Sync | v0.47.0 | 1/1 | Complete | 2026-06-14 |
| 7. Archive Retention Control | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 8. Machine Identity | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 9. Machine Rename | v0.48.0 | 1/1 | Complete | 2026-06-14 |
| 10. Computer-Folder Identity Foundation | v0.49.0 | 1/1 | Complete | 2026-06-14 |
| 11. Computer Selection & CLI | v0.49.0 | 2/2 | Complete | 2026-06-14 |
| 12. Computer Rename | v0.49.0 | 2/2 | Complete | 2026-06-14 |
| 13. Package Foundation + Output Format | v1.0.0 | 3/3 | Complete    | 2026-06-14 |
| 14. Config, Identity & Retention | v1.0.0 | 4/4 | Complete    | 2026-06-14 |
| 15. Collectors | v1.0.0 | 8/8 | Complete    | 2026-06-15 |
| 16. Git, CLI & Distribution | v1.0.0 | 3/3 | Complete    | 2026-06-15 |
| 17. Parity & Safety Tests | v1.0.0 | 3/3 | Complete    | 2026-06-15 |
| 18. Public Repo Migration | v1.1.0 | 0/? | Not started | - |
| 19. CI Build & Release Pipeline | v1.1.0 | 0/? | Not started | - |
| 20. Cut-Over & External-Catalog Verification | v1.1.0 | 0/? | Not started | - |

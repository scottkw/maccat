# Roadmap: Mac Software List Generator

## Milestones

- ✅ **v0.46.0 Extension Cataloging** — Phases 1-5 (shipped 2026-06-13) — [archive](milestones/v0.46.0-ROADMAP.md)
- ✅ **v0.47.0 Catalog Retention & Sync** — Phase 6 (shipped 2026-06-14) — [archive](milestones/v0.47.0-ROADMAP.md)
- ✅ **v0.48.0 Machine Identity & Retention Control** — Phases 7-9 (shipped 2026-06-14) — [archive](milestones/v0.48.0-ROADMAP.md)
- ✅ **v0.49.0 Computer-Folder Model** — Phases 10-12 (shipped 2026-06-14) — [archive](milestones/v0.49.0-ROADMAP.md)
- ✅ **v1.0.0 Python Port & Distribution** — Phases 13-17 (shipped 2026-06-14) — [archive](milestones/v1.0.0-ROADMAP.md)
- ✅ **v1.1.0 Repo Separation & CI Build** — Phases 18-20 (shipped 2026-06-16) — [archive](milestones/v1.1.0-ROADMAP.md)
- 🚧 **v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog** — Phases 21-23 (in progress)

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

<details>
<summary>✅ v1.1.0 Repo Separation & CI Build (Phases 18-20) — SHIPPED 2026-06-16</summary>

- [x] Phase 18: Public Repo Migration (Genericized, Fresh History) (2/2 plans) — completed 2026-06-16
- [x] Phase 19: CI Build & Release Pipeline (2/2 plans) — completed 2026-06-16
- [x] Phase 20: Cut-Over & External-Catalog Verification (2/2 plans) — completed 2026-06-16

Full details: [milestones/v1.1.0-ROADMAP.md](milestones/v1.1.0-ROADMAP.md)

</details>

### 🚧 v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog (In Progress)

**Milestone Goal:** Make maccat the standalone canonical tool — collapse folder selection to a
single `--computer` flag, enrich every software section with version numbers, and retire the
zsh reference and its byte-parity gate.

- [x] **Phase 21: CLI Cleanup** - Remove `--personal`, `--office`, and `--machine`; `--computer NAME` becomes the sole named-folder flag (completed 2026-06-16)
- [x] **Phase 22: Versioned Catalog** - Add versions to Homebrew formulae/casks, Setapp, and web-installed apps; preserve determinism and graceful degradation (completed 2026-06-16)
- [ ] **Phase 23: Retire the zsh Reference** - Delete `update-list.sh` and the parity test suite; backfill coverage; scrub docs

## Phase Details

### Phase 21: CLI Cleanup
**Goal**: `--computer NAME` is the sole named-folder flag; `--personal`, `--office`, and `--machine` are completely removed from the codebase and all dead code paths are gone.
**Depends on**: Phase 20 (v1.1.0 complete — brownfield Python codebase in place)
**Requirements**: CLI-03, CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. Running `maccat --personal`, `maccat --office`, or `maccat --machine Ken` each produces a standard argparse "unrecognized argument" error — the flags no longer exist.
  2. Running `maccat --computer MyMac` selects the `MyMac` folder non-interactively, identical behavior to what `--computer` provided before.
  3. `maccat --help` output mentions only `--computer` for folder selection — no stale `--personal`, `--office`, or `--machine` entries appear.
  4. The interactive `select_computer` menu, `--rename`, `--no-commit`, `--archive-days`, and `--catalog-dir` flags all behave exactly as before (non-regression verified by the existing test suite passing clean).
**Plans**: 2 plans

Plans:
- [x] 21-01-PLAN.md — Remove --personal/--office/--machine from identity.py and cli.py; scrub docstring examples
- [x] 21-02-PLAN.md — Update tests to new signature; add removed-flag regression coverage; full suite gate

### Phase 22: Versioned Catalog
**Goal**: Every software section in the catalog carries a version number where one is obtainable — Homebrew formulae, Homebrew casks, Setapp apps, and web-installed apps now emit `name (version)` lines; runs stay deterministic and degrade gracefully when a version is unavailable.
**Depends on**: Phase 21 (CLI cleanup complete; clean baseline before output format changes)
**Requirements**: VER-01, VER-02, VER-03, VER-04, VER-05, VER-06
**Success Criteria** (what must be TRUE):
  1. A generated catalog's "Homebrew Packages" section shows each formula and cask with its version — e.g. `git 2.44.0` instead of `git`.
  2. A generated catalog's "Setapp Applications" and "Web-installed Applications" sections show each app with its version from `Info.plist` — e.g. `Fantastical (3.8.4)` instead of `Fantastical`.
  3. When a version cannot be read (missing `Info.plist`, absent `CFBundleShortVersionString` key, or brew returning no version), the item still appears by name only and the run completes without error.
  4. Two consecutive runs on the same machine produce byte-identical catalog sections (deterministic, stably sorted — FMT-04 preserved).
**Plans**: 3 plans

Plans:
- [x] 22-01-PLAN.md — Plist version helper + Homebrew versioned output + unit tests
- [x] 22-02-PLAN.md — Setapp + WebApps versioned output using plist helper + tests
- [x] 22-03-PLAN.md — Skip 3 invalidated parity cases + full suite gate

### Phase 23: Retire the zsh Reference
**Goal**: `update-list.sh`, the `zsh_parity` test suite, and the CI `zsh -n` gate are gone; the test suite stands on its own with direct collector tests backfilling the lost coverage; README and docs describe maccat as the standalone tool.
**Depends on**: Phase 22 (version changes land first — they break the parity golden files, making parity retirement the natural next step; ZSH-03 backfill tests are written against the final versioned collector behavior)
**Requirements**: ZSH-01, ZSH-02, ZSH-03, ZSH-04
**Success Criteria** (what must be TRUE):
  1. `update-list.sh` does not exist in the repo; the CI workflow no longer contains a `zsh -n update-list.sh` step; the `zsh_parity` test directory/files are gone.
  2. `pytest` passes with no skipped or xfailed tests attributable to the parity removal; `ruff` and `mypy --strict` report zero errors.
  3. Direct collector tests (static-fixture or parametrized unit tests) cover the four collectors that changed in Phase 22 — at minimum one test per collector verifying version-present and version-absent (graceful degradation) paths.
  4. The README and any docs that previously referenced `update-list.sh` or byte-parity now describe maccat as the standalone cataloging tool, with no stale zsh references.
**Plans**: 3 plans

Plans:
- [x] 23-01-PLAN.md — Backfill chrome_name + vsc_name helper tests (ZSH-03 gap fill)
- [ ] 23-02-PLAN.md — Delete update-list.sh, parity suite, tests/golden/, CI zsh -n step, conftest golden fixtures (ZSH-01 + ZSH-02)
- [ ] 23-03-PLAN.md — Scrub README: remove zsh reference section, update CLI docs to --computer (ZSH-04)

## Progress

**Execution Order:**
Phases execute in numeric order: 21 → 22 → 23

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
| 13. Package Foundation + Output Format | v1.0.0 | 3/3 | Complete | 2026-06-14 |
| 14. Config, Identity & Retention | v1.0.0 | 4/4 | Complete | 2026-06-14 |
| 15. Collectors | v1.0.0 | 8/8 | Complete | 2026-06-15 |
| 16. Git, CLI & Distribution | v1.0.0 | 3/3 | Complete | 2026-06-15 |
| 17. Parity & Safety Tests | v1.0.0 | 3/3 | Complete | 2026-06-15 |
| 18. Public Repo Migration | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 19. CI Build & Release Pipeline | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 20. Cut-Over & External-Catalog Verification | v1.1.0 | 2/2 | Complete | 2026-06-16 |
| 21. CLI Cleanup | v2.0.0 | 2/2 | Complete   | 2026-06-16 |
| 22. Versioned Catalog | v2.0.0 | 3/3 | Complete   | 2026-06-16 |
| 23. Retire the zsh Reference | v2.0.0 | 1/3 | In Progress|  |

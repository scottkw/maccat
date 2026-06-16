# Requirements: Mac Software List Generator — v1.1.0 Repo Separation & CI Build

**Defined:** 2026-06-15
**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.

## v1.1.0 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Migration

- [ ] **MIG-01**: A new **public** GitHub repo is created via the `gh` CLI to host maccat
- [ ] **MIG-02**: The new repo contains the maccat code (`src/`), tests, `pyproject.toml`, build tooling (`scripts/build-pyz.sh`), docs, the zsh reference (`update-list.sh`), and the `.planning/` GSD history at their current state
- [ ] **MIG-03**: The new repo's git history starts **fresh** — no personal catalog `.txt` files, hostnames, or machine inventory appear anywhere in the working tree or anywhere in the git log
- [ ] **MIG-04**: This repo is reduced to **catalog-data-only** — code, tests, build tooling, docs, and `.planning/` are removed; catalog folders, `machine-labels.tsv`, and archives remain
- [ ] **MIG-05**: maccat run from the new repo correctly catalogs against an external catalog repo via the existing config resolution (`--catalog-dir` flag > `MACCAT_CATALOG_DIR` env > `~/.config/maccat/config.toml`)

### Genericization

- [ ] **GEN-01**: The README documents install (download the `.pyz` from Releases), catalog-dir configuration, and basic usage — written for a general user, with no personal paths or values
- [ ] **GEN-02**: An example/template config shows how to point maccat at the user's own catalog repo, with no setup-specific values presented as canonical defaults
- [ ] **GEN-03**: No setup-specific content remains — personal hostnames/machine names, committed build artifacts (`dist/maccat.pyz`), stray root throwaway test scripts, and `personal`/`office`-as-canonical references are removed or genericized
- [ ] **GEN-04**: The repo includes an open-source LICENSE file

### CI / CD

- [ ] **CI-01**: The test workflow (pytest + ruff + mypy `--strict` + `zsh -n update-list.sh`, macOS runner, `PYTHONHASHSEED` 0/42/random matrix) runs on every push and pull request to `main` in the new repo
- [ ] **CI-02**: CI builds the `.pyz` (via `scripts/build-pyz.sh`) on every push/PR to `main` and uploads it as a workflow artifact for build validation
- [ ] **CI-03**: On a version-tag push (e.g. `v1.1.0`), CI creates a GitHub Release with the freshly compiled `.pyz` attached as a downloadable asset

## v2 / Future Requirements

Acknowledged but deferred — not in this milestone's roadmap.

### Distribution

- **PKG-04**: Publish maccat to PyPI / enable `pipx install` as a second distribution channel

### Features (separate future milestones)

- **RESTORE-xx**: Generate a reviewable `reinstall.sh` from a chosen catalog (deterministic sources installed, the rest a manual checklist; never auto-executed)
- **DIFF-xx**: Catalog diffing / change reports across snapshots
- **SRC-xx**: Additional browsers/editors (Safari, Edge, Brave, Zed, …)
- **CHR-02 / FF-02**: Browser-extension enabled/disabled state
- **CDX-02**: Codex plugins (when that subsystem ships)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| PyPI / pipx publishing (PKG-04) | Distribution-adjacent but a separate concern; keep this milestone to repo split + `.pyz` build/release |
| Migrating this repo's git history into the public repo | History is saturated with personal catalog commits (real software lists + hostnames); a fresh init guarantees zero leakage |
| New cataloging features | This milestone is infrastructure only; feature work resumes in the new repo afterward |
| Cross-platform CI (Linux/Windows runners) | maccat is macOS-only by design (BSD `date`, `/Applications`, macOS browser paths); CI stays on macOS |
| Code refactor / architecture changes during the move | Move the code as-is; refactoring is out of scope for a migration milestone |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MIG-01 | Phase 18 | Pending |
| MIG-02 | Phase 18 | Pending |
| MIG-03 | Phase 18 | Pending |
| MIG-04 | Phase 20 | Pending |
| MIG-05 | Phase 20 | Pending |
| GEN-01 | Phase 18 | Pending |
| GEN-02 | Phase 18 | Pending |
| GEN-03 | Phase 18 | Pending |
| GEN-04 | Phase 18 | Pending |
| CI-01 | Phase 19 | Pending |
| CI-02 | Phase 19 | Pending |
| CI-03 | Phase 19 | Pending |

**Coverage:**
- v1.1.0 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0 ✓

**By phase:**
- Phase 18 (Public Repo Migration): MIG-01, MIG-02, MIG-03, GEN-01, GEN-02, GEN-03, GEN-04 (7)
- Phase 19 (CI Build & Release Pipeline): CI-01, CI-02, CI-03 (3)
- Phase 20 (Cut-Over & External-Catalog Verification): MIG-05, MIG-04 (2)

---
*Requirements defined: 2026-06-15*
*Last updated: 2026-06-15 — roadmap created (Phases 18-20), 12/12 requirements mapped*

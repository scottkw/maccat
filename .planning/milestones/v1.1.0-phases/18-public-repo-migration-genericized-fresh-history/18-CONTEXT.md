# Phase 18: Public Repo Migration (Genericized, Fresh History) - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up a new **public GitHub** repo named `maccat` (owner `scottkw`) that holds the migrated,
genericized maccat code, tests, build tooling, docs, the zsh reference, and the `.planning/` GSD
history — started from a **fresh git history** containing zero personal catalog data anywhere in the
working tree or git log. Includes README, an example/template config, and a LICENSE. Covers
requirements MIG-01, MIG-02, MIG-03, GEN-01, GEN-02, GEN-03, GEN-04.

This phase does NOT touch this (source) repo's working tree beyond reading it, does NOT set up CI
(Phase 19), and does NOT reduce this repo to catalog-data-only (Phase 20 / cut-over).

</domain>

<decisions>
## Implementation Decisions

### Repo Identity & Publishing
- New repo name: **`maccat`** (one name across package/import/CLI/`.pyz`/`~/.config/maccat/`)
- Owner: GitHub account **`scottkw`** (gh-authenticated; token has `repo` + `workflow` scopes)
- Visibility: **public** from creation, via `gh repo create scottkw/maccat --public`
- Default branch: **`main`** (matches the existing `.github/workflows/ci.yml` trigger)

### License & Genericization Scope
- License: **MIT**
- Keep the zsh reference `update-list.sh` in the public repo (the parity tests + `zsh -n` CI gate depend on it)
- **Exclude from the public tree** (do not copy / never commit): `dist/maccat.pyz` (build artifact — CI/Releases produce it), `venv/` (local dev env), the three root throwaway scripts `test-parse-arguments-11-02.sh` / `test-rename-back-12-02.sh` / `test-rename-front-12-01.sh`, and all personal catalog data (`personal/`, `office/`, `machine-labels.tsv`, any `*.txt` catalogs/archives)
- Genericize catalog-dir examples in README/config: use neutral placeholders (e.g. `<your-computer>`, `home`/`work`) rather than the personal `personal`/`office` folders; no personal hostnames or paths

### Fresh-history mechanics (Claude's discretion within these constraints)
- Use a clean `git init` of a prepared/genericized tree (a `.gitignore`d staging copy or `git archive`-style export), NOT `git filter-branch`/`filter-repo` of this repo's history — guarantees MIG-03 (zero personal data in the log)
- Add a `.gitignore` to the new repo covering `venv/`, `dist/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, and catalog data patterns, so artifacts/personal data can never be committed later

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/` — the package (3,513 LOC, stdlib-only, mypy --strict clean)
- `tests/` — full suite incl. live `zsh_parity` tests + safety-invariant tests (434 tests)
- `pyproject.toml` — hatchling, `>=3.11`, zero runtime deps, `[dev]` extras (pytest/ruff/mypy)
- `scripts/build-pyz.sh` — builds the `.pyz` zipapp (used by Phase 19 CI)
- `docs/` — existing design docs (incl. superpowers specs)
- `update-list.sh` — the zsh reference (kept; parity oracle)
- `.github/workflows/ci.yml` — existing macOS test workflow (Phase 19 extends it)

### Established Patterns
- maccat resolves the catalog repo via config precedence: `--catalog-dir` flag > `MACCAT_CATALOG_DIR` env > `~/.config/maccat/config.toml` > error. The app repo is already decoupled from the catalog repo — so the code is already location-independent and safe to relocate.

### Integration Points
- This (source) repo's `origin` is a **private remote** (`a private catalog remote`), NOT GitHub. The new public repo lives on **GitHub** (`github.com/scottkw/maccat`). The two remotes are independent — this repo stays on a private remote as the private catalog-data repo.

</code_context>

<specifics>
## Specific Ideas

- README must read as a general-purpose tool: install by downloading the `.pyz` from GitHub Releases,
  configure a catalog dir, run. No personal values.
- Example config = a template `config.toml` (or documented snippet) showing how a user points maccat
  at their own catalog repo.

</specifics>

<deferred>
## Deferred Ideas

- **`.planning/` final-sync ordering (Phase 20 / cut-over):** The `.planning/` copied into the public
  repo in THIS phase is an *initial snapshot*. GSD keeps writing to this repo's `.planning/` through
  Phases 19, 20, and the milestone lifecycle (audit/complete/cleanup). The authoritative final
  `.planning/` push to the public repo and the reduction of this repo to catalog-data-only (MIG-04)
  must happen as the LAST deliberate step, after the lifecycle completes — NOT in this phase. (Run
  plan: autonomous `--to 19`, then manual cut-over.)
- PKG-04 (PyPI/pipx) — out of scope, future milestone.
- CI build/release pipeline — Phase 19.

</deferred>

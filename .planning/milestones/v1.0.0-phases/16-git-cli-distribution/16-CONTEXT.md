# Phase 16: Git, CLI & Distribution - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Infrastructure/integration phase — discuss skipped. This phase wires together everything
built in phases 13–15 into an end-to-end CLI + `.pyz` distributable. The behavior is fully
determined by zsh byte/behavior parity (`update-list.sh` main flow + git functions) plus the
already-locked research/CONTEXT decisions (argparse, stdlib zipapp, fixed flag set, MACCAT_CATALOG_DIR
env, config init/show subcommands). No user-facing design choices remain.

<domain>
## Phase Boundary

Build the `maccat` CLI entry point, the end-to-end run orchestration, the git integration, and the
single-file `.pyz` zipapp — making the tool runnable against a user-configured EXTERNAL catalog repo.
Fills the Phase-16 stubs left in phases 13–15 (`maccat.cli`, the argparse parser that calls
`resolve_computer_selection`, the `rename_machine` git commit, the generate-then-sweep assembly).

Requirements: PKG-03 (`.pyz` zipapp, `#!/usr/bin/env python3`, runs from any dir, never resolves the
catalog repo from `__file__`), PKG-05 (`--version` / `--help`), OPS-06 (git pull → generate →
commit/push as a single commit syncing adds/moves/deletes; `--no-commit` skips git while disk ops run).

In scope:
- **`src/maccat/cli.py`** (the `run()` that `__main__.py` already imports): argparse parser with the
  fixed flag set + `config` subcommand; dispatch to the run flow or to `config init`/`config show`.
- **End-to-end run orchestration** in the EXACT zsh order (success criterion 2):
  `resolve_catalog_repo (config) → select_computer → resolve_archive_days → git_pull → generate
  catalog (iterate get_registry() in section order, header first, raw vs flush per Section.raw,
  via CatalogWriter) → retain_newest_per_host(target) → prune_old_archives(target) →
  git_commit_and_push (unless --no-commit)`. The just-written catalog must NEVER be archived on the
  same run (generate-then-sweep).
- **`--rename` mode**: pull → rename folder + map rewrite → single commit (old-folder deletes +
  new-folder adds + map update) → exit, BEFORE any catalog generation/retention/prune (mirrors zsh).
  Wire the `auto_commit` path stubbed in `identity.rename_machine`.
- **Git integration** (mirror zsh `git_pull` :2327, `git_commit_and_push` :2374): `git add -A --
  "<path>/"` and `git add -- machine-labels.tsv` (the `--` is mandatory so leading-dash folder names
  stage correctly — success criterion 4); warn-and-continue on pull/push failure; fail-fast / warn
  per CFG-06 when the catalog dir isn't a git repo / has no remote.
- **`.pyz` packaging**: build via stdlib `python -m zipapp` (no third-party bundler) with an
  `#!/usr/bin/env python3` shebang and `maccat.__main__:main` entry; bundles only the package's own
  pure-Python source (no `.so`/`.dylib`). Must run from any directory and never resolve the catalog
  repo from `__file__`/cwd. A small build script/Makefile target is fine.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All choices at Claude's discretion — integration phase, behavior dictated by zsh parity +
locked prior decisions. Guidance:
- CLI: stdlib `argparse` (locked in research/Phase-14 context). Bare `maccat` = the catalog-generate
  run; `maccat config init` / `maccat config show` = the config subcommands (CFG-04). Run-flow flags:
  `--computer NAME` / `--personal` / `--office` / `--machine NAME` (mutually exclusive — reuse
  `identity.resolve_computer_selection`), `--rename ...`, `--archive-days N`, `--no-commit`,
  `--catalog-dir PATH` (CFG-03 override, never written back), `--version`, `--help`.
- Reuse, don't reimplement: config.py (resolve_catalog_repo / validate / config_init / config_show /
  resolve_archive_days), identity.py (select_computer / resolve_computer_selection / rename_machine /
  upsert_machine_label), retention.py (retain_newest_per_host / prune_old_archives), naming.py,
  collectors get_registry(), catalog/writer.py (CatalogWriter) + format.py.
- Orchestration order is NON-NEGOTIABLE (success criterion 2): git_pull → generate → retain → prune →
  commit/push. generate-then-sweep: never archive the just-written catalog.
- `.pyz`: stdlib `python -m zipapp` only (zero third-party). Never resolve catalog repo from
  `__file__` (PKG-03) — the catalog dir comes solely from config/env/flag (CFG-01 precedence).
- `git add` MUST use `-- <pathspec>` (leading-dash safety — success criterion 4).
- `--no-commit` runs all disk ops (generate/retain/prune) but skips git (success criterion 3).

</decisions>

<code_context>
## Existing Code Insights

### Reference Implementation (zsh — untouched parity source, update-list.sh)
- Main flow / ordering: `parse_arguments` :189; rename-mode short-circuit; `select_computer` →
  `resolve_archive_retention` :511 → `git_pull` :2327 → `generate_catalog` :2220 →
  `retain_newest_per_host` :942 → `prune_old_archives` :1022 → `git_commit_and_push` :2374
  (exact end-of-file order confirmed at update-list.sh:2461-2502).
- `git add -A -- "${TARGET_LOCATION}/"` and `git add -- machine-labels.tsv` (:2397-2400) — the `--`
  is the leading-dash-safety guard (success criterion 4). Rename uses the same pattern (:886-888).

### Stubs to fill (left by phases 13–15)
- `src/maccat/__main__.py:20` — `from maccat.cli import run` (+ NotImplementedError) → implement `maccat.cli.run`.
- `src/maccat/identity.py:444` `rename_machine(..., auto_commit=False)` :625 — wire the git commit.

### Built in prior phases (reuse — do NOT reimplement)
- 13: catalog/writer.py (CatalogWriter), catalog/format.py.
- 14: config.py, identity.py, retention.py, naming.py.
- 15: collectors/ + get_registry() (section-ordered, raw flag per Section).

### Research (`.planning/research/`)
- STACK.md / SUMMARY.md / ARCHITECTURE.md: argparse over click, stdlib `.pyz` zipapp (no shiv/pex —
  zero deps), run-from-any-dir, never resolve from `__file__`. (Stale names → translate to maccat.)
- pipx/PyPI is v1.1 (PKG-04 deferred) — this phase ships `.pyz` only; a pyproject.toml already exists.

</code_context>

<specifics>
## Specific Ideas

- Test the end-to-end run + git against a DISPOSABLE fixture (a `git init` temp repo with no remote),
  never the real catalog repo or this app repo — a live run is destructive (prunes archives, commits).
  This is a hard project constraint.
- Verify the `.pyz` runs from an unrelated cwd (e.g. `cd /tmp && /path/maccat.pyz --version`) and that
  it resolves the catalog dir from config/env/flag only — add a test asserting no `__file__`-relative
  catalog resolution.
- Reproduce the zsh leading-dash `git add --` safety and the warn-and-continue git failure behavior.

</specifics>

<deferred>
## Deferred Ideas

- Golden-output byte-parity test suite + destructive-op safety-invariant isolated tests — Phase 17.
- pipx / PyPI distribution channel (PKG-04) — v1.1.
- New collectors / restore-from-catalog — future milestones.

</deferred>

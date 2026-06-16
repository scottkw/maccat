# Phase 14: Config, Identity & Retention - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — port phase; most behavior fixed by byte/behavior parity with the untouched zsh `update-list.sh`. Two genuinely-new, user-facing config decisions were put to the user; everything else is parity-determined or Claude's discretion.

<domain>
## Phase Boundary

Implement the config + identity + retention layer of `maccat`, all WITHOUT touching a live
catalog repo (operate on disposable/temp fixtures):

- **Config resolution (CFG-01..06):** resolve the catalog-repo path by precedence
  **CLI flag (`--catalog-dir`) > env var (`MACCAT_CATALOG_DIR`) > config file > clear error**
  (no silent default). Config at `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml`
  (constructed directly — never trust `platformdirs` macOS default). `config init` (interactive
  capture + validate + write) and `config show` (print resolved effective config + precedence
  winner) subcommands. App repo is separated from catalog repo — never infer the catalog from
  `__file__`/`cwd`. Fail fast when the catalog dir is missing or not a git repo; warn-and-continue
  when the git remote is absent.
- **Computer-folder identity (OPS-01, OPS-02):** the always-shown selection menu
  (existing folders + create-new + Quit, remembered folder as Enter default), TTY-guarded;
  `--computer "Name"` with `--personal`/`--office`/`--machine` aliases + mutual-exclusion.
- **Machine-labels map (OPS-05):** read/write `machine-labels.tsv` (hostname→folder) with
  atomic tmp+rename writes, preserving comments and blank lines.
- **Retention (OPS-03, OPS-04):** `retain_newest_per_host` (two-pass per-host max-timestamp;
  keep ALL tied-newest; skip unparseable-timestamp files — never move/delete); `prune_old_archives`
  at N days with `--archive-days N` (or prompt). Generate-then-sweep ordering belongs to Phase 16;
  this phase implements the retention/prune functions and the rename mode.
- **Rename (OPS-07):** `rename_machine` renames a computer folder (+ its archive) with a
  **hard refuse-clobber** guard, opt-out-gated `[old]→[new]` filename rewrite, and single-commit
  map update (the commit itself wires in Phase 16; the rename logic + guards land here).
- **Interactive safety (OPS-08):** non-TTY runs never hang (fail-fast guards), EOF/Ctrl-D exits
  cleanly (no traceback, no infinite loop), invalid input re-prompts.

Requirements: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-07, OPS-08.

</domain>

<decisions>
## Implementation Decisions

### Config (user-decided)
- **Environment variable name:** `MACCAT_CATALOG_DIR` (matches the locked `maccat` name used for
  the package, CLI, and `~/.config/maccat/` dir — consistency over the research draft `MAC_CATALOG_DIR`).
- **config.toml schema:** flat top-level key `catalog_dir = "/abs/path"` (not a `[catalog]` table) —
  simplest for a single-value config; easy to extend later. Read with stdlib `tomllib` (3.11+),
  read-only (no toml writer needed beyond `config init`'s own simple emit).
- **Precedence (CFG-01, locked by requirement):** `--catalog-dir` flag > `MACCAT_CATALOG_DIR` env >
  config file `catalog_dir` > clear actionable error. `--catalog-dir` overrides for the run only and
  is NEVER written back to the config file (CFG-03).
- **Config path (CFG-02, locked):** `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml`,
  constructed directly via `Path.home()/".config"/"maccat"/"config.toml"` with `XDG_CONFIG_HOME`
  override — do NOT rely on `platformdirs` (returns `~/Library/Application Support` on macOS).
- **Validation (CFG-06):** before any catalog operation, validate the resolved dir exists AND is a
  git repo (`git rev-parse --git-dir` or equivalent); fail fast with a remediation hint
  (e.g. "Run `maccat config init`"). Absent git remote → warn-and-continue, not fatal.

### Parity-Determined (Claude's Discretion to match the zsh reference exactly)
- The selection menu, `--computer`/aliases + mutual-exclusion, retention two-pass + tied-newest +
  unparseable-skip, prune cutoff, atomic TSV writes, rename refuse-clobber + opt-out rewrite, and
  all interactive-safety behaviors must reproduce the zsh `update-list.sh` behavior. The zsh
  functions (`select_computer`, `validate_computer_name`/`_quiet`, `upsert_machine_label`,
  `rename_machine`, the retention/prune logic) ARE the spec — replicate behavior, not implementation
  detail. Python-internal structure (module layout, a `Config`/`RunContext` dataclass, argparse
  mutually-exclusive groups per research STACK) is at Claude's discretion.

### Claude's Discretion
- CLI parser library: stdlib `argparse` (research-recommended; zero-dep constraint, simple fixed
  flag set, mutually-exclusive groups model the selecting flags cleanly).
- Exact wording of new error/guidance messages, as long as they are clear and actionable.

</decisions>

<code_context>
## Existing Code Insights

### Reference Implementation (zsh — untouched parity source)
- `select_computer`, `validate_computer_name` / `validate_computer_name_quiet`,
  `upsert_machine_label`, `rename_machine`, and the retention/prune logic in `update-list.sh`
  are the behavioral spec. Read them for exact menu text, default handling, refuse-clobber,
  unparseable-timestamp skip, and TTY/EOF behavior.
- `machine-labels.tsv` at repo root is TAB-delimited, hostname→folder, atomic (tmp+rename) writes,
  comments/blank lines preserved.

### From Phase 13 (built, reuse)
- `src/maccat/` package skeleton, `__main__.py` version guard, `src/maccat/helpers/json_io.py`,
  `CatalogWriter`/format layer. The Python 3.11+ floor and stdlib-only constraint carry forward.

### Research already done (`.planning/research/`)
- SUMMARY.md / ARCHITECTURE.md / FEATURES.md / PITFALLS.md / STACK.md document the config design
  (XDG path, `catalog_dir` key, precedence chain, git-repo validation, `config init`/`config show`,
  argparse over click). NOTE: research uses STALE names (`mac-catalog`, `maclist`,
  `MAC_CATALOG_DIR`, `mac_software_list`) — the LOCKED names are `maccat` / `MACCAT_CATALOG_DIR` /
  `~/.config/maccat/`. Translate stale names when consuming research.

### Integration Points
- Config resolution feeds the run context that Phase 16 (git/CLI/distribution) wires end-to-end.
- Retention/prune functions are invoked by Phase 16 in correct generate-then-sweep order.

</code_context>

<specifics>
## Specific Ideas

- Verify ALL identity/retention/rename behavior against disposable fixtures (`mktemp -d` or a
  no-remote git clone), never the repo's real `personal/`/`office/` folders — a live run is
  destructive (hard-deletes archives, moves folders). This is a hard project constraint.
- Reproduce the v0.49.0 zsh-pitfall fixes the zsh tool already hardened against (bare-`local`
  echo, `NULLCMD` stdin hang, `git add` leading-dash) where the Python equivalents could regress:
  non-TTY fail-fast, EOF clean-exit, leading-dash-safe path handling.

</specifics>

<deferred>
## Deferred Ideas

- Named config profiles (multi-catalog-repo) — explicitly out of scope (`--catalog-dir` covers the
  one-off override case).
- The actual git pull/commit/push wiring and generate-then-sweep ordering — Phase 16.
- pipx/PyPI distribution channel — v1.1 (PKG-04 deferred).

</deferred>

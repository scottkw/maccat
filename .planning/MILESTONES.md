# Milestones

## v1.0.0 Python Port & Distribution (Shipped: 2026-06-15)

**Phases completed:** 5 phases, 21 plans, 19 tasks

**Key accomplishments:**

- importable `src/maccat` package skeleton with pyproject.toml (hatchling, >=3.11, zero runtime deps), sys.version_info guard in __main__.py, and dev venv with pytest/ruff/mypy
- emit_item (FMT-01), flush_section (LC_ALL=C sort subprocess), version_sort_tail, and CatalogWriter (atomic mkstemp+rename) — byte-exact parity with update-list.sh write_section/emit_item/flush_section
- `src/maccat/helpers/json_io.py`
- RED:
- 1. [Rule 1 - Bug] ruff lint: unused pytest import + import ordering in test_retention.py
- One-liner:
- One-liner:
- `src/maccat/collectors/base.py`
- `src/maccat/collectors/homebrew.py`
- SetappCollector
- ClaudeCollector implementing 3 JSON/filesystem-parsed sections (Plugins, MCP Servers, Skills & Agents) with CAT-05 transport-only MCP safety and YAML frontmatter name extraction
- GeminiCollector with CAT-05 MCP secret guard and Pitfall B 0-byte file guard, closing all four MCP collectors in Phase 15
- VSCodeCollector and CursorCollector using CLI-preferred/extensions.json-fallback two-path pattern with rsplit('@',1) last-@ split and NLS display name resolution via resolve_vsc_ext_name.
- One-liner:
- stdlib subprocess git integration with shell=False list-form args, '--' pathspec safety, and warn-and-continue behavior mirroring zsh:2327/2374/867
- One-liner:
- 1. [Rule 1 - Bug] Removed `set -e` from zsh capture script
- 17-case parametrized pytest suite proving Python collector output byte-matches committed .golden.txt files after normalize_catalog_body() on both sides, under PYTHONHASHSEED=0 and PYTHONHASHSEED=42.
- One-liner:

---

## v0.49.0 Computer-Folder Model (Shipped: 2026-06-14)

**Phases completed:** 3 phases, 5 plans, 6 tasks

**Key accomplishments:**

- Collapsed the separate machine-label concept into the folder-as-identity model: the top-level folder name IS the computer, catalog filenames carry `[folder]`, a single shared `validate_computer_name`/`_quiet` validator backs both the flag (fail-fast) and interactive (re-prompt) paths, and `machine-labels.tsv` was repurposed to a hostname→computer-folder map (`CURRENT_MACHINE="$TARGET_LOCATION"`).
- Added the `--computer "Name"` flag with `--personal`/`--office`/`--machine` aliases and a mutual-exclusion guard, rewired the main block to call `select_computer` once (Quit exits before any catalog/commit), and removed the legacy `get_target_location` + `resolve_machine_label` functions.
- Reworked `rename_machine`'s front half from the Phase 9 label-only flow into a folder-centric picker (alphabetical discovery + Quit), a validated new-name prompt, empty-list / new==old / folder-not-found / HARD refuse-clobber guards, and a single plain folder `mv` — proven by an isolated mktemp+PTY harness (23/23 PASS) with zero real-tree or real-git access.
- Reworked `rename_machine`'s back half into the folder-centric flow: an opt-out-gated in-folder filename rewrite (scoped to the moved folder + its archive), an unconditional atomic `machine-labels.tsv` update that runs in BOTH rewrite and opt-out modes, and a single commit staging the old + new folder paths + the map (with a folder-centric `--no-commit` manual path) — the `renamed_count==0` abort gate and all legacy shims removed, proven by a mktemp+PTY harness with a stubbed git (26/26 PASS) and zero real-tree/real-git access.

**Notable:** Live pty-driven UAT (run in a disposable clone) found and fixed 4 real defects that source/grep review + function-tests missed — most importantly a bare-`local` zsh quirk echoing `f=<path>` into the interactive menus of both `select_computer` and `rename_machine`, plus a `NULLCMD` stdin-hang in the map write, a `git add` leading-dash option-injection, and an EOF infinite-loop at the rename prompt.

**Known deferred items at close:** 1 maintenance smell (IN-03: folder-discovery duplicated between `select_computer` and `rename_machine`) tracked for a future extraction pass; audit-open's 2 flagged items were a resolved UAT file (0 pending) and a pre-milestone quick task already completed (commit 2a740e7) — neither is open work.

---

## v0.48.0 Machine Identity & Retention Control (Shipped: 2026-06-14)

**Phases completed:** 3 phases, 3 plans, 2 tasks

**Key accomplishments:**

- `--archive-days N` CLI flag with interactive fallback prompt, fail-fast integer validation, and dynamic ARCHIVE_AGE_DAYS flowing into prune_old_archives
- One-liner:
- One-liner:

---

## v0.47.0 Catalog Retention & Sync (Shipped: 2026-06-14)

**Phases completed:** 1 phase, 1 plan

**Delivered:** Reworked `update-list.sh`'s archive/retention/git logic so every run keeps only the newest catalog **per machine** in the targeted location's main folder, moves older per-machine catalogs to `archive/`, hard-deletes archive catalogs older than 30 days, and stages every change (adds + moves + deletions) in a single git commit so all machines converge.

**Key accomplishments:**

- Replaced the old `archive_old_catalogs` (move-at-60-days) with two purpose-built functions: `retain_newest_per_host` (keeps the newest catalog per hostname in the main folder, archives the rest) and `prune_old_archives` (hard-deletes archive catalogs older than 30 days). `ARCHIVE_AGE_DAYS` 60→30.
- Per-host retention uses a dependency-free two-pass Zsh associative-array algorithm keyed on the hostname embedded in each filename; tied-newest files are kept, and unparseable timestamps are skipped (never deleted).
- `git_commit_and_push` now stages the targeted location with `git add -A "${TARGET_LOCATION}/"`, so additions, moves, and deletions sync in one commit; `--no-commit` still skips git while the disk operations run.
- Corrected a latent main-block ordering bug — the old archive call ran before the new catalog was generated; the new order generates first, then sweeps/prunes, so the just-written catalog is never archived.
- Code review verified the destructive operations are safe by construction (only catalog-named files in the target location are ever moved/deleted; the newest-per-host is never removed); three warnings fixed.

---

## v0.46.0 Extension Cataloging (Shipped: 2026-06-13)

**Phases completed:** 5 phases, 12 plans, 14 tasks
**Timeline:** 2026-06-13 (single-day milestone, ~67 commits)
**Code:** `update-list.sh` grew from ~513 to 1672 lines (pure Zsh, zero new dependencies)

**Delivered:** A single `./update-list.sh` run now catalogs — alongside the existing Homebrew/App Store/Setapp/web-installed software — the plugins, MCP servers, and skills/agents of four AI coding CLIs (Claude Code, Codex, OpenCode, Gemini), the extensions of two editors (VS Code, Cursor), and the extensions of two browsers (Chrome, Firefox) across all profiles — 13 new sections, secret-clean and deterministic.

**Key accomplishments:**

- Built a reusable, dependency-free Zsh helper layer (`json_get` jq→plutil→grep, `chrome_ext_name` `__MSG_` resolution, `emit_item` uniform `name (version) [id]`, `flush_section` `LC_ALL=C sort -f -u`) that every collector shares (FMT-01, FMT-04).
- Added VS Code + Cursor extension collectors with full `displayName` resolution including `%nls%` placeholder lookup from `package.json`/`package.nls.json` (VSC-01, CUR-01).
- Added 9 AI-CLI collectors (Claude plugins/MCP/skills-agents, Codex MCP, OpenCode plugins/MCP/agents, Gemini extensions/MCP) capturing **identity only, never secrets** — MCP entries emit `name [transport]` and never env/headers/args/command/url (CC/CDX/OC/GEM, FMT-03).
- Added Chrome + Firefox extension collectors across all profiles with `__MSG_` name resolution, a 10-ID Google-component denylist, `sort -V` version selection, and Firefox `app-profile` filtering (CHR-01, FF-01).
- Wired all 13 collectors into `generate_catalog` (AI CLIs → editors → browsers) leaving the existing sections, archive, and git flow byte-unchanged (FMT-02).
- Proved the two non-negotiable gates on the real integrated catalog: **zero secret leakage** (scoped grep, 0 hits) and **diff-empty determinism** (two consecutive runs byte-identical).

**Process notes:** Code review caught and fixed a real FMT-03 secret-disclosure blocker in Phase 1 (`json_get` with an empty key dumped the entire JSON root via jq's `getpath([])`) before any MCP collector could trigger it. The secret-leakage gate was scoped to the new sections after research found legitimate Homebrew formulae (`libnghttp2`, `httpie`) contain the substring `http` (the ROADMAP's original whole-file grep would have false-positived). The JSON fallback chain was reconciled from the ROADMAP's `python3` to `plutil` after research found `/usr/bin/python3` is an xcrun install-prompt stub on clean macOS.

---

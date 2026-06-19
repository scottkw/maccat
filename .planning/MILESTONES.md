# Milestones

## v3.0.0 Markdown Catalog Format (Shipped: 2026-06-19)

**Phases completed:** 3 phases (30-32), 7 plans

**Delivered:** Replaced the plain-text catalog format with rendered markdown (`.md`) — YAML
frontmatter provenance + per-section `Name | Version | ID` tables — re-locked the
catalog→reinstall round-trip against the new format, and added `maccat convert --from PATH`
to upgrade legacy `.txt` catalogs in place. Breaking format change (precedent: v2.0.0);
format-only — all 22 sections and the data they collect are unchanged. `__version__` bumped
2.1.0 → 3.0.0 at release.

**Key accomplishments:**

- **Phase 30 (MD-01..05, FILE-01/02):** shared markdown emitter in `catalog/markdown.py`
  (`render_markdown_catalog`) — double-quoted YAML frontmatter (computer/hostname/generated/
  maccat_version), `# Installed Mac Software List` title, one `##` section per source rendering a
  uniform 3-col table; `(none found)` for empty/degraded; byte-deterministic (FMT-04),
  identity-only (FMT-03). `.txt`→`.md` moved across filename/retention/archive/git + the reinstall
  picker glob. `maccat generate` now emits `.md` via `CatalogWriter.write_raw`.

- **Phase 31 (RIN-01/02):** `parse_markdown_catalog` in `reinstall/parser.py` inverts the emitter
  (frontmatter-skip + ` | `-split table rows + backslash-aware cell unescape); the parser↔emitter
  round-trip re-locked by a contract test (replacing the v2.1.0 plain-text lock). `maccat reinstall`
  consumes `.md` only and refuses legacy `.txt` AND frontmatter-less `.md` (extension + content-sniff)
  with a `maccat convert --from` directive and non-zero exit. Legacy `parse_catalog` retained for convert.

- **Phase 32 (CONV-01/02/03):** `maccat convert --from PATH` reads a legacy `.txt` via the retained
  `parse_catalog`, bridges to the emitter (skipping the leading H1 section), writes the `.md`, removes
  the `.txt` (only after a successful write — atomicity), and stages both in one commit via
  `git_commit_convert`; `--no-commit` does file ops only. Frontmatter synthesized from the current
  machine (computer from filename; generated=now(); hostname; version); output filename preserves the
  original timestamp. Graceful degradation: aborts only on missing/unreadable/unrecognizable input.

**Quality:** 702 tests passing, ruff + mypy --strict clean, stdlib-only (no new deps). Each phase ran
adversarial code review + fix — most notably a Phase 30 blocker (YAML frontmatter injection on
colon-containing computer/hostname names that would have broken the Phase 31 round-trip), caught and
fixed before it shipped.

---

## v2.2.0 Broader Coverage (Shipped: 2026-06-17)

**Phases completed:** 3 phases (27-29), 5 plans

**Delivered:** Extended the catalog from 17 to 22 sections — adding Codex plugins, Zed extensions,
Microsoft Edge / Brave / Safari browser extensions — so a single snapshot captures more of a
machine's real tooling. All additive; existing sections + the reinstall pipeline unchanged.

**Key accomplishments:**

- **Phase 27 (CDX-02, BRW-03):** `CodexCollector` gained a second "Codex Plugins" section
  (identity-only, FMT-03; CLI-then-config.toml-header detection; `(none found)` on the installed
  plugin-less Codex v0.46.0). New `ZedCollector` reads `~/Library/Application Support/Zed/extensions/index.json`
  (`name (version) [id]`, dev-filtered). Added a section-title uniqueness test (reused by 28/29).

- **Phase 28 (BRW-01, BRW-02):** extracted `ChromiumBaseCollector` (3 real Chromium browsers justify
  it) — Chrome became a thin subclass with **byte-identical** output; Edge + Brave are thin subclasses
  (Brave's 20-ID denylist; Edge baseline + documented gap). Profile-enumeration presence detection
  (no spurious section from a NativeMessagingHosts-only base dir).

- **Phase 29 (BRW-04):** new `SafariCollector` via `pluginkit -mAvv -p com.apple.Safari.web-extension`
  + per-`.appex` `Info.plist` (`CFBundleDisplayName` / `CFBundleShortVersionString` /
  `CFBundleIdentifier`), per-extension never-raising; live-gated smoke test validates real output.

- **Quality:** code-review + auto-fix loop on every phase (fixed never-raising gaps in codex/zed and
  the Safari name-fallback chain); 628 tests pass, ruff + mypy --strict clean; reinstall pipeline
  needed ZERO changes (all 5 new sections → manual checklist automatically); audit PASSED (5/5).

**Notable (process):** mid-run `gsd-sdk` npx-cache eviction recovered (reinstalled GSD 1.42.3); a
Phase 29 executor worktree forked from a pre-27/28 base and would have clobbered canonical files on
merge — caught during merge inspection and reconstructed surgically on main (628 tests green).

**Known deferred items at close:** 1 — stale quick task `260614-ckx-fix-interactive-machine-label-ux`
(status missing, predates v2.0.0, out of scope; re-acknowledged — see STATE.md Deferred Items).
Plus the documented Edge component-denylist gap (no authoritative Microsoft list).

---

## v2.1.0 Reinstall from Catalog (Shipped: 2026-06-16)

**Phases completed:** 3 phases (24-26), 4 plans

**Delivered:** A `maccat reinstall` subcommand that parses a chosen catalog and generates a reviewable, never-auto-executed `reinstall.sh` — deterministic sources (Homebrew, mas, VS Code/Cursor) become guarded idempotent install commands; everything else becomes a manual checklist.

**Key accomplishments:**

- **MAS-01 + PARSE-01 (Phase 24):** `MasCollector` now preserves the numeric App Store ID (`AppName (version) [id]`, multi-word names + de-paren'd version); new `reinstall/parser.py` (`parse_catalog` → typed `ParsedCatalog`) inverts all six `emit_item` line shapes, locked by a round-trip contract test against `catalog/format.py`.
- **GEN-01..04 + MAN-01 (Phase 25):** `reinstall/emitter.py` renders an injection-safe (`shlex.quote` via `quote_for_script`), `bash -n`-clean, idempotent script — universal Homebrew guard, brace-group-guarded `mas install <id>` / editor `--install-extension`, `set -Eeuo pipefail` abort-resistance (runtime-execution-tested), and a manual checklist for Setapp/web/browser/AI-CLI tooling.
- **RST-01 + RST-02 (Phase 26):** `maccat reinstall [--from PATH | --computer NAME]` wired into `cli.py` via a surgical two-point dispatch that leaves the 13-step catalog-gen path untouched; writes `reinstall.sh` to cwd at 0o644, prints its absolute path, never subprocess-runs it.
- **Quality:** code-review + auto-fix loop on every phase caught and fixed a real `set -Eeuo pipefail` BLOCKER (bare `mas install` aborting mid-run) and a broken `reinstall --computer NAME` flag; 553 tests pass, ruff + mypy --strict clean; audit PASSED (9/9 requirements wired + E2E-verified).

**Known deferred items at close:** 1 — stale quick task `260614-ckx-fix-interactive-machine-label-ux` (status: missing, predates v2.0.0, out of scope; re-acknowledged — see STATE.md Deferred Items).

---

## v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog (Shipped: 2026-06-16)

**Phases completed:** 3 phases (21-23), 8 plans

**Delivered:** Made maccat the standalone canonical tool — collapsed folder selection to a single
`--computer` flag, added version numbers to every software catalog section, and retired the zsh
reference implementation and its byte-parity gate. First milestone where maccat evolves freely
without an `update-list.sh` parity anchor. 14/14 requirements; milestone audit PASSED.

**Key accomplishments:**

- **CLI cleanup (Phase 21, CLI-03..06):** removed `--personal`, `--office`, and `--machine` (and all
  associated code) — `--computer NAME` is now the sole named-folder selector; collapsed
  `resolve_computer_selection` from four params to a single keyword-only `computer`, simplified the
  argparse parser + `--rename` guards, and migrated the test suite (removed flags now error with
  argparse "unrecognized arguments").

- **Versioned catalog (Phase 22, VER-01..06):** Homebrew formulae/casks now emit `name (version)`
  via `brew list --versions` (all installed versions preserved); Setapp and web-installed
  `/Applications` apps read their version from `Info.plist` (`CFBundleShortVersionString` →
  `CFBundleVersion`) through a new never-raising stdlib-`plistlib` helper; graceful name-only
  degradation; ordering/determinism preserved (no `flush_section` re-sort). App Store unchanged.

- **Retired the zsh reference (Phase 23, ZSH-01..04):** deleted `update-list.sh`, the entire
  `tests/golden/` parity scaffold, `test_golden_parity.py`, `test_update_list_integrity.py`, and the
  CI `zsh -n` gate (kept the PYTHONHASHSEED matrix + pytest/ruff/mypy); backfilled the only two
  genuinely-missing helper branch tests (non-dict `messages.json`/`package.nls.json` degradation);
  scrubbed README of operational zsh references (kept one history note); maccat described as
  standalone.

**Notable:** Process resilience under failure — an executor died mid-plan (API socket close) during
22-01; the orchestrator recovered from the partial commit state without losing or duplicating work.
Adversarial gates caught real issues: the plan-checker rejected a 23-01 plan built on a false premise
(it would have duplicated existing helper tests), and code review caught a Critical never-raises
violation in the plist helper (array-root `Info.plist` → `AttributeError`) plus a TOCTOU on `stat()`
— both fixed before phase close. Final state: 421 passed / 5 skipped (unrelated `test_pyz` dist
artifact), ruff + mypy --strict clean.

**Known deferred items at close:** 1 stale quick task from a prior milestone
(`260614-ckx-fix-interactive-machine-label-ux`, status missing — predates v2.0.0, not in scope);
~88 stale `update-list.sh:NNNN` code-comment cross-references (consciously out of ZSH-04 scope).
See STATE.md Deferred Items.

---

## v1.1.0 Repo Separation & CI Build (Shipped: 2026-06-16)

**Phases completed:** 3 phases, 6 plans, 8 tasks

**Delivered:** Separated the `maccat` code from the private catalog data — extracted the code into a new **public** GitHub repo (`github.com/scottkw/maccat`) with an automated build/release pipeline, leaving this repo as catalog-data-only on its private remote.

**Key accomplishments:**

- **Public repo from a fresh history (Phase 18):** created `github.com/scottkw/maccat` (public, `main`) via `gh`, migrated genericized code/tests/build-tooling/docs/zsh-reference/`.planning` from a clean `git init` (not a history filter) so **zero personal catalog data** appears in the tree or git log; added MIT LICENSE, an install-from-Releases README, and `config.example.toml`. A two-surface privacy gate + manual scrub removed personal hostnames AND the private a private Git host host string from the migrated `.planning/` docs before the first push.
- **CI build + release pipeline (Phase 19):** the migrated macOS test workflow runs green on push/PR; added a `.pyz` build + `actions/upload-artifact` step (CI-02) and a separate tag-triggered `release.yml` that publishes a GitHub Release with `maccat.pyz` via `gh release create` — no third-party action, `contents: write` only (CI-03). Proven end-to-end with a throwaway `v0.0.1-ci-test` tag, then cleaned up.
- **Cut-over (Phase 20):** verified `maccat` catalogs correctly against an external disposable catalog repo (MIG-05), then reduced this repo to catalog-data-only — removed `src/tests/scripts/docs/.github/pyproject.toml/update-list.sh/CLAUDE.md` etc., kept the catalog folders + `machine-labels.tsv` + archives, and pointed the README at the public tool repo (MIG-04).

**Notable:** the adversarial plan-checker caught two real blockers in Phase 18 before execution (`.planning/` migrated but not genericized; a privacy-gate regex that would false-positive on legitimate code), and a human checkpoint before the irreversible public push surfaced a third leak (the private a private Git host host) the plan had missed. 12/12 requirements satisfied; milestone audit PASSED.

**GSD home moved:** future feature work happens in the maccat repo; this repo no longer carries `.planning/`.

---

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

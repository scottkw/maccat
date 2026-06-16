# Mac Software List Generator

## What This Is

**`maccat`** — a single-file Python (`.pyz`) CLI that catalogs everything installed on a macOS
machine — applications plus the extensions, plugins, MCP servers, and skills/agents of the
user's AI coding CLIs, editors, and browsers — into a timestamped, per-machine plain-text
snapshot, auto-archives old catalogs, and auto-commits/pushes to git. Runs against a
user-configured external catalog repo. It's a personal tool for keeping a restorable, diffable
history of a machine's full software + tooling state. (Originally a Zsh script, ported to Python
in v1.0.0; the zsh reference was retired in v2.0.0.)

## Shipped Milestones

- **v0.46.0 Extension Cataloging** (2026-06-13) — added 13 catalog sections for AI-CLI / editor /
  browser extensions, plugins, MCP servers, and skills/agents; secret-clean and deterministic.
- **v0.47.0 Catalog Retention & Sync** (2026-06-14) — main folders keep only the newest catalog
  per machine; archives hard-prune at 30 days; all changes (adds/moves/deletes) sync in one commit.
- **v0.48.0 Machine Identity & Retention Control** (2026-06-14) — `--archive-days N` flag (or prompt)
  makes archive retention configurable; catalogs are named with a user-chosen friendly label backed
  by a committed `machine-labels.tsv` hostname→label map (auto-resolved per machine); a `--rename`
  mode rewrites a label across all of a machine's files in both locations and commits the moves.
- **v0.49.0 Computer-Folder Model** (2026-06-14) — the top-level folder name IS the computer identity:
  catalog filenames carry `[folder]`, an always-shown `select_computer` menu (existing folders +
  create-new + Quit, remembered folder as the Enter default) replaces silent auto-resolution, a
  `--computer "Name"` flag with `--personal`/`--office`/`--machine` aliases selects/creates
  non-interactively, and `--rename` renames a computer folder (+ its archive) with an opt-out-gated
  rewrite of contained catalogs and a single-commit map update. The separate machine-label concept
  collapsed into the folder identity. Live pty-driven UAT caught and fixed a bare-`local` zsh quirk
  leaking `f=<path>` into the menus, a `NULLCMD` stdin-hang, a `git add` leading-dash injection, and
  an EOF prompt loop. Design: `docs/superpowers/specs/2026-06-14-computer-folder-model-design.md`.
- **v1.0.0 Python Port & Distribution** (2026-06-14) — re-implemented the ~2,470-line zsh
  `update-list.sh` as a modular, stdlib-only Python package **`maccat`** (`src/maccat/`, 3,513 LOC)
  at **byte-for-byte output parity** with the untouched zsh reference, distributed as a single-file
  `.pyz` zipapp that runs from any directory against a user-configured external catalog repo
  (config precedence: `--catalog-dir` flag > `MACCAT_CATALOG_DIR` env > `~/.config/maccat/config.toml`
  > error). All 12 collectors, the `name (version) [id]` format via `LC_ALL=C sort`, the computer-folder
  menu + all operational flags, two-pass retention, archive prune, atomic `machine-labels.tsv`, and
  git pull→generate→commit are ported. Parity is proven by a **live `zsh_parity` test suite** (13
  sections captured from zsh at test time and asserted byte-identical, IDs included) plus the three
  destructive-op safety invariants; CI runs on macOS across `PYTHONHASHSEED` 0/42/random with a
  `zsh -n update-list.sh` integrity gate. 434 tests; ruff + mypy --strict clean; the zsh script stays
  byte-unmodified. Adversarial code review caught a tautological parity gate (goldens written from
  Python) and an ID-erasing normalization bug — both fixed before completion.

- **v1.1.0 Repo Separation & CI Build** (2026-06-16) — extracted `maccat` into a new **public**
  GitHub repo (`github.com/scottkw/maccat`) from a **fresh git history** (code + tests + build
  tooling + docs + zsh reference + `.planning/`), with zero personal catalog data in the tree or log;
  added a CI `.pyz` build + artifact upload on push/PR and a tag-triggered `release.yml` that
  publishes a GitHub Release with `maccat.pyz` (no third-party action). Reduced **this** repo to
  catalog-data-only (catalog folders + `machine-labels.tsv` + archives kept; code/tooling/`.planning/`
  removed; README now points to the public tool repo). A human checkpoint before the public push
  caught a private-a private Git host-host leak the plan missed. 12/12 requirements; audit PASSED. **GSD home
  moved to the maccat repo** — future feature work happens there; this repo is now data-only.
- **v2.0.0 Standalone maccat — CLI Cleanup & Versioned Catalog** (2026-06-16) — made maccat the
  standalone canonical tool: removed `--personal`/`--office`/`--machine` so `--computer NAME` is the
  sole named-folder flag (CLI-03..06); added version numbers to every software section — Homebrew
  formulae/casks via `brew list --versions`, Setapp + web-installed `/Applications` via a new
  never-raising `plistlib` helper (VER-01..06); and retired `update-list.sh`, the `zsh_parity` suite,
  and the CI `zsh -n` gate, leaving direct collector tests as standalone coverage (ZSH-01..04). Code
  review caught a Critical never-raises bug in the plist helper; recovered from a mid-plan executor
  crash. 14/14 requirements; audit PASSED. Released v2.0.0 `.pyz`.

## Current Milestone: v2.1.0 Reinstall from Catalog

**Goal:** Generate a reviewable `reinstall.sh` from a chosen catalog — deterministically
installable sources become install commands, everything else becomes a manual checklist.
The script is never auto-executed.

**Target features:**
- **`maccat reinstall` subcommand** — `--from PATH` selects an explicit catalog; if omitted,
  the existing computer-picker chooses a computer and uses its newest catalog.
- **Catalog parsing** — read a catalog's plain-text sections back into structured items
  (name / version / id per source). The catalog is the source of truth.
- **Auto-install section** — self-contained `reinstall.sh` with `brew install` (formulae +
  casks), `mas install <id>`, and `code`/`cursor --install-extension <id>` lines; each line
  carries the cataloged version as a comment (`# cataloged: 2.44.0`); installs latest.
- **Manual checklist section** — non-deterministic sources listed for the user: Setapp apps,
  web-installed `/Applications`, Chrome/Firefox extensions, and AI-CLI MCP servers / plugins /
  skills / agents (identity-only reconfigure reminders).
- **Never auto-execute** — output a script the user reviews and runs; safe to re-run where practical.

**Key constraint:** AI-CLI MCP/plugins/skills can't be auto-installed — the catalog stores them
as identity-only (`name [transport]`, no command/url/args/env) by the FMT-03 secret-safety design,
so they can only be a manual reconfigure reminder.

## Next Candidate Milestones

After v2.1.0 (Reinstall from Catalog, now active): catalog diffing / change reports (diff two
catalogs over time), additional browsers/editors (Safari, Edge, Brave, Zed), PKG-04 (pipx/PyPI as
a second distribution channel), and the deferred v2 items (CHR-02/FF-02 extension enabled-state,
CDX-02 Codex plugins).

## Core Value

A single run produces one complete, restorable snapshot of a machine's software *and*
tooling extensions — accurate enough to rebuild the environment from, degrading gracefully
when any source isn't installed.

## Requirements

### Validated

<!-- Inferred from existing working code (commit f805a29 codebase map). -->

- ✓ Catalog Homebrew formulae and casks — existing
- ✓ Catalog Mac App Store apps via `mas` (name + version) — existing
- ✓ Catalog Setapp applications — existing
- ✓ Catalog web-installed `/Applications` apps — existing
- ✓ Per-machine timestamped output file `mac-software-list-[host]-TS.txt` — existing
- ✓ `--personal` / `--office` target selection (flag or interactive prompt) — existing
- ✓ Auto-archive catalogs older than 60 days into `[location]/archive/` — existing
- ✓ Git pull → generate → auto-commit/push, `--no-commit` to skip — existing
- ✓ Graceful degradation when an optional source/tool is absent — existing
- ✓ Catalog Claude Code plugins, MCP servers, skills/agents — v0.46.0
- ✓ Catalog Codex MCP servers (name + transport only; no plugin system in installed Codex) — v0.46.0
- ✓ Catalog OpenCode plugins, MCP servers, agents — v0.46.0
- ✓ Catalog Gemini CLI extensions + MCP servers — v0.46.0
- ✓ Catalog VS Code + Cursor extensions (name + version + ID, displayName/nls resolved) — v0.46.0
- ✓ Catalog Google Chrome extensions across all profiles (`__MSG_` resolved, components excluded) — v0.46.0
- ✓ Catalog Firefox extensions across all profiles (`app-profile` only) — v0.46.0
- ✓ Uniform `name (version) [id]` line format with graceful degradation (FMT-01/FMT-02) — v0.46.0
- ✓ No secrets ever written to the catalog — MCP entries are name + transport only (FMT-03) — v0.46.0
- ✓ Deterministic, stably-sorted output — repeated runs diff-empty (FMT-04) — v0.46.0
- ✓ Keep only the newest catalog per machine (hostname) in the target main folder — v0.47.0
- ✓ Move older per-machine catalogs to the target's `archive/` — v0.47.0
- ✓ Hard-delete archive catalogs older than 30 days — v0.47.0
- ✓ Retention + prune run on every invocation, scoped to the targeted location — v0.47.0
- ✓ Sync additions, moves, and deletions via the git commit/push cycle (machines converge) — v0.47.0
- ✓ Configurable archive-retention period — `--archive-days N` flag, else prompt (default 30), invalid values rejected before pruning — v0.48.0
- ✓ Catalog under a friendly machine label instead of the raw hostname — v0.48.0
- ✓ Select an existing label or create a new one (`--machine` flag, else numbered menu) — v0.48.0
- ✓ Remember each Mac's hostname→label mapping (committed `machine-labels.tsv`) so runs auto-resolve — v0.48.0
- ✓ Rename a machine label across all of its files (both locations, main + archive) in one commit — v0.48.0
- ✓ Top-level folders represent user-named computers; folder name is the machine identity (CID-01..03) — v0.49.0
- ✓ Catalog filenames correspond to their folder (`[folder]` label) — v0.49.0
- ✓ Always-shown computer menu (existing folders + create-new + Quit), remembered folder as Enter default (SEL-01..04) — v0.49.0
- ✓ `--computer "Name"` flag with `--personal`/`--office`/`--machine` back-compat aliases (CLI-01/02) — v0.49.0
- ✓ `--rename` renames a computer/folder (+ archive), opt-out-gated rewrite of contained filenames, single-commit map update (RNM-01..03) — v0.49.0
- ✓ Quit option on every interactive menu (clean exit, nothing written/committed) (QUIT-01) — v0.49.0
- ✓ Extracted to a public repo with CI `.pyz` build + tag-triggered Release; this repo reduced to catalog-data-only (MIG/CI/GEN) — v1.1.0
- ✓ `--computer NAME` is the sole named-folder flag; `--personal`/`--office`/`--machine` removed entirely (CLI-03..06) — v2.0.0
- ✓ Homebrew formulae + casks cataloged with versions via `brew list --versions`, all installed versions preserved (VER-01/02) — v2.0.0
- ✓ Setapp + web-installed `/Applications` apps cataloged with versions from `Info.plist` (Short→CFBundleVersion), shared never-raising `plistlib` helper (VER-03/04) — v2.0.0
- ✓ Graceful name-only degradation when a version is unobtainable; output stays deterministic/stably-sorted (VER-05/06) — v2.0.0
- ✓ Retired `update-list.sh`, the `zsh_parity` suite, and the CI `zsh -n` gate; suite stands on direct collector tests; README describes maccat as standalone (ZSH-01..04) — v2.0.0

### Active

_None — v2.0.0 shipped. No milestone is active. The next milestone's requirements will be
defined fresh via `/gsd-new-milestone` (REQUIREMENTS.md is archived per-milestone)._

Candidate future milestones: restore/reinstall from a catalog (generate a reviewable
`reinstall.sh`), catalog diffing/change reports, additional browsers/editors, PKG-04 pipx/PyPI
distribution, and v2 items CHR-02/FF-02 enabled-state + CDX-02 Codex plugins when that subsystem ships.

### Out of Scope

- Cross-platform support (Linux/Windows) — tool is macOS/Zsh-only by design; BSD `date -v`,
  `/Applications`, browser paths are macOS-specific
- Automated restore/reinstall from a catalog — this milestone catalogs only; restoration is
  a possible future milestone
- Diffing catalogs over time / change reports — valuable but separate; not in this milestone
- Rewriting the script's architecture (e.g. fixing globals-as-parameters) — bolt new sources
  onto existing conventions rather than refactor
- JSON/HTML output formats — output stays plain-text sectioned to keep one restorable snapshot
- Browsers/editors beyond those listed (Safari, Edge, Brave, Zed, etc.) — not requested

## Context

- **Existing implementation:** `update-list.sh` (~2,470 lines, Zsh) plus a committed
  `machine-labels.tsv` hostname→**computer-folder** map at the repo root. Data collection lives in
  `generate_catalog`, section formatting in `write_section`. As of v0.49.0 the folder name IS the
  computer identity: `select_computer` (always-shown menu + dynamic folder discovery + create-new +
  Quit + remembered default) sets `TARGET_LOCATION`, which feeds `CURRENT_MACHINE`/`OUTPUT_FILENAME`
  so catalogs are named `[folder]`; `validate_computer_name`/`_quiet` are the shared validators;
  `upsert_machine_label` records hostname→folder; `rename_machine` was reworked to rename a folder
  (+ archive) with an opt-out-gated `[old]→[new]` rewrite and single-commit map update. The legacy
  `get_target_location` and `resolve_machine_label` were removed. A source-guard at end-of-file
  (`[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`) makes functions sourceable for isolated tests.
  New sources still plug into `generate_catalog` via the append-to-`OUTPUT_FILE` side-effect pattern.
- **⚠️ Testing hazard:** running `update-list.sh` mutates real files — a normal run hard-deletes
  archive catalogs older than the retention cutoff; `--rename` moves real folders and commits.
  Verify by reading + `zsh -n`, source/grep assertions, or a throwaway `mktemp -d` fixture (or a
  disposable `git clone` driven through a pty for interactive flows) — never a live run against the
  repo's real folders. v0.49.0 UAT confirmed several zsh-specific pitfalls only surface on a real
  run: bare `local f` (no assignment) re-run in a loop echoes `f=<value>`; a bare `> file` redirect
  runs `NULLCMD` (cat) and hangs on a TTY; `git add` without `--` mis-parses leading-dash names.
- **Existing pattern to mirror:** each optional source checks availability (`command -v`),
  writes a fallback message when absent, and never aborts the run.
- **Discovery methods vary per tool and need research** before planning — prefer a tool's own
  CLI where one exists (`code --list-extensions`, `gemini extensions list`, `claude` plugin
  listing, etc.) over parsing config files, and fall back to parsing on-disk config/manifests
  (e.g. `~/.claude/`, `~/.codex/`, `~/.config/opencode/`, `~/.gemini/`, Chrome
  `Extensions/*/manifest.json`, Firefox profile `extensions.json`) where no CLI exists.
- Browser extensions store the human-readable name in localized manifest fields (Chrome
  `_locales`) — extracting a clean name + version + ID will require care, surfaced in research.
- Existing codebase map lives in `.planning/codebase/` (refreshed 2026-06-12).

## Constraints

- **Tech stack**: Pure Zsh shell script, no new runtime/deps — keep the tool single-file and
  dependency-free beyond optional CLIs it probes
- **Compatibility**: macOS-only (Zsh, BSD `date`, macOS filesystem layout)
- **Output format**: Plain-text sections appended to the existing per-machine catalog file —
  must not break existing sections or the archive/git flow
- **Detail level**: name + version + ID per extension/plugin where each is obtainable
- **Behavior**: graceful degradation is mandatory — a missing tool or browser must warn-and-continue

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extend `update-list.sh` in place rather than build a new tool | Keep one restorable snapshot per machine; matches existing workflow | — Pending |
| New sources go in the same catalog file as new sections | One file = one complete machine snapshot for restoration | — Pending |
| Catalog name + version + ID per item | Maximize fidelity for exact restoration | — Pending |
| Cover all browser profiles, not just default | Multi-profile setups are common; completeness over simplicity | — Pending |
| Comprehensive AI-CLI coverage (plugins + MCP + skills/agents) | User wants maximal tooling fidelity in the snapshot | — Pending |
| Include VS Code + Cursor alongside the four AI CLIs | Same extension/MCP concepts; natural siblings | — Pending |
| Decouple catalog identity from live hostname via friendly labels | Cryptic auto-hostnames (`computer-two.local`) are unreadable; stable labels survive hostname changes | ✓ Good — v0.48.0 (label feeds `OUTPUT_FILENAME`) |
| Persist a committed hostname→label map (first persistent state in the tool) | Each Mac must auto-resolve its own label; the shared roster also powers the select menu and rename | ✓ Good — v0.48.0 (`machine-labels.tsv`, TAB-delimited, atomic writes; shared by resolve + rename) |
| Rename as a separate mode that rewrites all of a machine's files | History must stay consistent; cleans up the two existing cryptic-named machines | ✓ Good — v0.48.0 (`--rename` short-circuits before catalog gen; single commit) |
| Configurable archive retention via `--archive-days N`, else prompt | Mirrors existing flag-or-prompt pattern (`--personal`/`--office`); no persisted config file | ✓ Good — v0.48.0 (TTY-guarded prompt, fail-fast validation) |
| Label/value validation is fail-fast before any file op; non-TTY runs never hang | Bulk file moves and prunes are destructive — reject bad input and missing-TTY prompts up front | ✓ Good — v0.48.0 (a broken label-validation regex was caught and fixed in code review) |
| Collapse machine-label + save-location into one concept: the folder IS the computer | The user's mental model is "each folder is a computer"; two parallel identity systems were redundant | ✓ Good — v0.49.0 (filename `[folder]`, map repurposed to hostname→folder, label menu folded into `select_computer`) |
| Always show the computer menu (remembered folder = Enter default) instead of silent auto-resolve | A Mac with no remembered folder must choose explicitly; explicit selection beats surprising auto-pick | ✓ Good — v0.49.0 (`select_computer`; no Enter-default when unmapped, fail-loud guard against empty selection) |
| `--rename` operates on the folder; rewrite contained catalogs by default with an opt-out | Folder = identity, so rename must move the folder; rewriting filenames keeps `[label]` consistent, but users may want to preserve history | ✓ Good — v0.49.0 (single `mv` + opt-out-gated rewrite + map update + single commit; hard refuse-clobber) |
| Verify destructive CLI tools with live pty-driven UAT in a disposable clone, not just static review | Real runs surface zsh quirks (bare-`local` echo, `NULLCMD` hang, `git add` dash-injection) that source/grep + function-tests miss | ✓ Good — v0.49.0 (4 real defects found & fixed during UAT that all gates had passed) |
| Port the tool to a modular Python package; leave `update-list.sh` untouched | At ~2,500 LoC with more planned, zsh is creaking; modular Python is maintainable and contributor-friendly, but the working zsh tool stays as the proven reference until parity is verified | — Pending v1.0.0 |
| Accept a new Python 3 runtime dependency (reverses the prior "pure zsh, no deps" constraint) | Distribution to other developers motivates the move; the audience already has python3 via Xcode CLT, and git (already required) co-installs it | — Pending v1.0.0 |
| Distribute as a `.pyz` zipapp + pipx channel; run against an external catalog repo via config-file-with-flag-override | Recipients won't have the source tree, so a single artifact matters; separating app repo from catalog repo lets others use the tool with their own catalogs | — Pending v1.0.0 |
| Port behind golden-output parity tests (byte-identical catalog section bodies vs the zsh script) | A rewrite of destructive, scar-tissue-rich code is only safe with parity fixtures; this also delivers the test suite the zsh tool never had | — Pending v1.0.0 |
| Name the Python tool `maccat` (short for "Mac Catalog") | Short, memorable, distinct from the zsh `update-list.sh`; one name across package/import, CLI command, `.pyz` artifact, and `~/.config/maccat/` config dir | — Pending v1.0.0 |
| Separate the code into a new public repo; this repo becomes catalog-data-only | Code and personal catalog data have opposite audiences (public vs private); separating them lets the tool be shared without exposing the user's machine inventory | — Pending v1.1.0 |
| Start the public repo from a fresh git history (no `git filter-branch` of the existing one) | This repo's history is saturated with personal catalog `.txt` commits (real software lists + hostnames); a clean init guarantees zero leakage and is simpler than scrubbing history | — Pending v1.1.0 |
| Move `.planning/` GSD history with the code, not the catalog repo | Future feature development (the thing GSD tracks) happens on the code; planning belongs beside what it plans | — Pending v1.1.0 |
| Genericize all setup-specific content before publishing (README, example config, default-path examples, `personal`/`office`) | A public tool must read as general-purpose, not as one user's install | — Pending v1.1.0 |
| CI builds + tests on every push/PR to main; publishes a Release `.pyz` only on a version tag | Continuous validation on main catches breakage early; tag-gated releases give clean, versioned download URLs without release noise | — Pending v1.1.0 |
| Collapse the four selecting-flags (`--personal`/`--office`/`--machine`/`--computer`) to a single `--computer NAME` | `--personal`/`--office` were one user's catalog names; `--machine` was a pure back-compat alias of `--computer`. Supplying the folder name is sufficient; folder = computer is the established model | ✓ Good — v2.0.0 (resolve_computer_selection collapsed to one param; removed flags argparse-error) |
| Add version numbers to the four version-less software sources (Homebrew formulae/casks, Setapp, web-installed `/Applications`) | Maximize restore fidelity — a snapshot should pin versions; `mas` already emits them, so close the gap | ✓ Good — v2.0.0 (`brew --versions`; shared never-raising `plistlib` helper; `name (version)`) |
| Remove `update-list.sh` + the `zsh_parity` byte-parity gate; maccat becomes the standalone source of truth | The zsh reference proved the port (v1.0.0) and has served its purpose; keeping it frozen blocks every output/CLI change. Backfill coverage with direct collector tests so the suite still stands | ✓ Good — v2.0.0 (every collector already had direct tests; only 2 helper branch-gaps needed backfill) |
| Show ALL installed Homebrew versions inside the parens, not just the highest | A restore snapshot should reflect exactly what's installed; multi-version installs (e.g. `python@3.11`) are real | ✓ Good — v2.0.0 |
| `.app` version: prefer CFBundleShortVersionString, fall back to CFBundleVersion, else name-only | Maximizes coverage while keeping the human-readable marketing version when present | ✓ Good — v2.0.0 |
| Reinstall produces a reviewable `reinstall.sh`, never auto-executed | Installing software is high-impact and machine-specific; the user must review before running. A script is inspectable, editable, and re-runnable | — Pending v2.1.0 |
| Auto-install only the deterministic sources (Homebrew, mas, VS Code/Cursor exts); everything else is a manual checklist | These have reliable CLI installers keyed on data the catalog holds (name / App Store id / extension id). Setapp, web apps, browser exts have no CLI install | — Pending v2.1.0 |
| AI-CLI MCP/plugins/skills are manual-checklist only, never auto-installed | The catalog stores them identity-only (`name [transport]`) by FMT-03 secret-safety — the command/url/args/env needed to reinstall are deliberately absent | — Pending v2.1.0 |
| Install latest, record the cataloged version as a comment (not version-pinned) | Pinning is unreliable across brew/mas/extensions (no versioned formulae variants, no mas version pin); the cataloged version stays as a reviewable reference | — Pending v2.1.0 |
| The catalog `.txt` is the reinstall source of truth (parse it back), not a live system scan | Reinstall is about restoring a captured snapshot to a new/wiped machine; parsing the emitted plain-text sections closes the catalog→restore loop | — Pending v2.1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-06-16 — started milestone v2.1.0 Reinstall from Catalog: add a `maccat reinstall` subcommand that parses a chosen catalog and generates a reviewable, never-auto-executed `reinstall.sh` (auto-install Homebrew/mas/VS Code+Cursor; manual checklist for Setapp/web apps/browser exts/AI-CLI tooling; install-latest with cataloged version as a comment). Starts at Phase 24.*

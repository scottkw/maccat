# Project Research Summary

**Project:** Mac Software List Generator — v1.0.0 Python Port & Distribution
**Domain:** Distributable macOS CLI tool — Python rewrite of a battle-tested Zsh cataloger
**Researched:** 2026-06-14
**Confidence:** HIGH

## Executive Summary

The v1.0.0 milestone rewrites a ~2,500-line Zsh cataloger as a modular Python package while keeping the Zsh reference untouched. The central challenge is not building something new — it is replicating byte-identical output from an existing, well-exercised reference implementation, then packaging the result so it runs against an arbitrary user-configured catalog repo. Every architectural and technology decision flows from three hard constraints: zero third-party runtime dependencies (enabling a stdlib `zipapp` artifact), Python 3.11 as the version floor (unlocking `tomllib` and `syrupy`), and byte-parity with the Zsh output as the safety gate that validates the port.

The recommended approach is a clean `src/`-layout Python package (`mac_software_list/`) with a `RunContext` frozen dataclass replacing Zsh globals, a `Collector` ABC with one file per source, and a shared `flush_section` that shells out to `LC_ALL=C sort -f -u` for byte-identical sort order. Config lives at `${XDG_CONFIG_HOME:-$HOME/.config}/mac-catalog/config.toml` (XDG convention, not `~/Library/Application Support`); the catalog repo path is always explicit — never inferred from `__file__` or `cwd()`. Distribution ships two artifacts: a stdlib `python -m zipapp` `.pyz` (single-file, no install step) and a PyPI wheel for `pipx install`. Golden-output parity tests (file-based fixtures, normalized volatile fields) are the acceptance gate for the entire port.

The top risks are all parity-related: sort-order divergence from incorrect Python sort semantics, trailing-newline/section-boundary byte drift, and the destructive-run hazard that makes generating golden fixtures a planning-first problem. Three categories of destructive-op regressions from prior milestones (catalog archiving order, unparseable-filename pruning, refuse-clobber rename) must be explicitly re-tested in the Python port. None of these risks are exotic — they are all directly visible in the Zsh source code and the v0.47.0–v0.49.0 defect record, making high-confidence mitigation strategies available for every one.

---

## Resolved Cross-Report Tensions

The following questions appeared as open items across individual research files and are **decided here**. Downstream planning must treat these as closed.

### 1. CLI library: argparse (stdlib) vs Click

**Decision: `argparse` (stdlib).**

The distribution model is a stdlib `.pyz` zipapp that bundles only the package's own source. A `.pyz` cannot vendor third-party deps without `shiv` or `pex`, both of which add extraction overhead and are designed for apps that actually have dependencies. Click is a third-party runtime dep; `argparse` is stdlib. The flag set is fixed and simple (`--computer`, `--rename`, `--no-commit`, `--archive-days`, `--catalog-dir`, `--version`); argparse's mutually-exclusive groups model these cleanly. Click's benefits (decorators, type inference, shell completion scaffolding) are irrelevant at this flag complexity and add zero value in a zero-dep tool.

### 2. Python version floor: 3.11

**Decision: `python_requires = ">=3.11"`. The 3.9 question is closed.**

Three independent justifications lock this:
- `tomllib` is stdlib in 3.11+. The config file is TOML. Without 3.11, a `tomli` backport dep is required, which breaks the zero-dep `.pyz` goal.
- Python 3.9 reached EOL on October 31, 2025. It receives no security patches. The Xcode CLT stub is frozen at 3.9.6 and Apple has not updated it in ~4 years — it is not a distribution target.
- `syrupy` (the golden snapshot test library) requires Python >= 3.10. Our dev toolchain requires 3.11 at minimum.

The realistic user base (macOS developers who install via pipx) already has Homebrew Python 3.11+. The README states `python3.11+` as a prerequisite.

### 3. Config location: ~/.config/<app>/config.toml (XDG)

**Decision: `${XDG_CONFIG_HOME:-$HOME/.config}/mac-catalog/config.toml`.**

`~/Library/Application Support/` is the macOS convention for GUI apps that manage config on behalf of the user. Developer CLIs (`gh`, `kubectl`, `docker`, `terraform`, `ruff`, `stripe`, `op`) all use `~/.config` on macOS. The `platformdirs` library returns `~/Library/Application Support` on macOS by default — do not rely on its defaults. Construct the path directly (`Path.home() / ".config" / "mac-catalog" / "config.toml"` with `XDG_CONFIG_HOME` override) or use `platformdirs.PlatformDirs(appname, unix=True)`. Constructing directly is simpler and has no external dependency.

### 4. Parity sort: shell out to LC_ALL=C sort -f -u

**Decision: shell out. Do not reimplement in Python. This is a hard design rule.**

`subprocess.run(["sort", "-f", "-u"], env={**os.environ, "LC_ALL": "C"})` is the `flush_section` implementation. Python's `sorted()` with `key=str.casefold` diverges from C-locale byte-order collation for any mixed-case name, non-ASCII character, or punctuation — which covers every real section. `locale.setlocale` is process-global and thread-unsafe. The shell-out is the same binary the Zsh script calls and guarantees byte-identical output with zero maintenance risk. Similarly, Chrome version-directory selection uses `sort -V` (via subprocess or a numeric-segment key) — not Python's default lexicographic sort.

---

## Key Findings

### Recommended Stack

The runtime package is purely stdlib — zero third-party dependencies. Every Zsh capability maps cleanly to a stdlib module: `json` + `plistlib` replace the `jq` / `plutil` chain; `datetime.timedelta` replaces BSD `date -v-Nd`; `subprocess.run(["git", ...])` replaces GitPython; `shutil.which` replaces `command -v`; `tomllib` (3.11 stdlib) reads the TOML config; `re` extracts YAML frontmatter from skills/agents. The one deliberate subprocess dependency that stays is the `sort` call — shelling out to `LC_ALL=C sort -f -u` for `flush_section` is the correct parity strategy.

The dev/test stack is separate from the runtime and never appears in the `.pyz`: `pytest >= 8.0` (test runner), `syrupy >= 5.0` (golden snapshot tests, `.ambr` files), `ruff >= 0.15` (lint + format), `mypy >= 1.10` (type checking), `uv >= 0.5` (venv and package management). Distribution uses `hatchling` as the build backend (build-time only; zero runtime presence) and `python -m zipapp` for the `.pyz` artifact.

**Core technologies:**
- Python 3.11+: runtime floor — EOL-safe, unlocks `tomllib`, matches Homebrew default, covers `syrupy`
- `argparse` (stdlib): CLI argument parsing — handles all flags; zero dep; mutually-exclusive groups model `--personal`/`--office`/`--computer` cleanly
- `tomllib` (stdlib 3.11+): config file parsing — reads `~/.config/mac-catalog/config.toml`; read-only; no backport needed
- `json` + `plistlib` (stdlib): JSON/plist manifest parsing — replaces `jq` + `plutil` entirely; no subprocess
- `subprocess.run(["sort", ...])`: sort with `LC_ALL=C` env — parity-critical; must not be replaced with Python sort
- `subprocess.run(["git", ...])`: git operations — `pull`, `add`, `commit`, `push`, `rev-parse`; `cwd=` kwarg replaces `cd "$SCRIPT_DIR"`
- `pathlib` + `tempfile` + `os.replace`: all path ops and atomic writes — replaces string path concatenation and `> tmp && mv tmp real`
- `python -m zipapp` (stdlib): `.pyz` build — no shiv, no pex; zero-dep tools use zipapp
- `hatchling` (build-time only): wheel build backend for pipx/PyPI distribution
- `syrupy` (dev only): golden snapshot tests — `assert result == snapshot`, `--snapshot-update`, human-readable `.ambr` diffs in git
- `uv` (dev only): venv and package management per CLAUDE.md preference

### Expected Features

**Must have (table stakes) — all required for v1.0.0:**
- All existing Zsh collectors ported at byte-parity: Homebrew, App Store, Setapp, web apps, Claude Code, Codex, OpenCode, Gemini, VS Code, Cursor, Chrome, Firefox
- Config file at `~/.config/mac-catalog/config.toml` with `catalog_dir` key; `config init` subcommand for first-run setup
- Config precedence chain: `--catalog-dir` flag > `MAC_CATALOG_DIR` env var > config file > error
- Validate `catalog_dir` exists and is a git repo before any operation; clear error message with remediation hint
- All existing flags ported: `--computer`, `--personal`, `--office`, `--machine`, `--rename`, `--archive-days`, `--no-commit`
- `--version` and `--help` on every command; sensible exit codes (0 = success, 1 = config/usage, 2 = runtime)
- Computer-folder menu with remembered default (interactive + `--computer` non-interactive)
- Newest-per-machine retention, archive prune, git pull/commit/push
- Graceful degradation: absent tool/browser writes `(none found)`, never aborts
- `.pyz` zipapp artifact and `pipx install` distribution path
- Golden-output parity test suite (section-level, normalized, file-based fixtures)
- `config show` subcommand: print resolved effective config

**Should have (differentiators — v1.x after core is stable):**
- Shell completion (bash/zsh) — medium complexity; defer until core is validated
- `--dry-run` flag — high value for new users; medium complexity to thread through collectors

**Defer to v2+:**
- Named config profiles (multi-catalog-repo support) — speculative; `--catalog-dir` covers the one-off case
- Reinstall/restore from a catalog — already tracked as the next milestone
- Catalog diffing/change reports — tracked

**Anti-features (do not build):**
- Cross-platform support (Linux/Windows) — macOS-only by design; OS branching dilutes identity
- Plugin system/extension API — personal cataloger; add collectors directly in the Python package
- TUI (rich/textual) — numbered menu already tested; a TUI rewrite is pure risk
- JSON/YAML output mode — plain-text sections are the product value; `git diff` is the dashboard
- Telemetry — personal tool distributed to developers who read source; any phoning home destroys trust

### Architecture Approach

The architecture inverts the Zsh anti-patterns: a `RunContext` frozen dataclass replaces module-level globals, a `Collector` ABC returning `CollectorResult` replaces the direct-append-to-OUTPUT_FILE pattern, and a `CatalogWriter` context manager with atomic tmp+rename replaces bare file appends. All dependencies flow downward toward leaf modules — no circular imports. The catalog-repo path is resolved once in `config.py`/`cli.py` and threaded as an explicit `Path` argument through `identity.py`, `retention.py`, `gitops.py`, and `CatalogWriter`; nothing uses `Path(__file__).parent` or `os.getcwd()` as a catalog root.

**Major components:**
1. `__main__.py` + `cli.py` — entry point, `argparse` argument parsing, `RunContext` construction, interactive menus with TTY guards
2. `config.py` — `Config` dataclass, `load_config()`, `resolve_catalog_repo()`; pure data, no side effects
3. `identity.py` — `select_computer()`, `validate_computer_name()`, `upsert_machine_label()`, `rename_machine()`; all take `catalog_repo` Path
4. `catalog/writer.py` + `catalog/format.py` — `CatalogWriter` context manager (atomic output), `emit_item()`, `flush_section()` (shells to `LC_ALL=C sort -f -u`), `write_section()`
5. `collectors/` sub-package — `Collector` ABC, `CollectorResult`/`Section` dataclasses, REGISTRY (ordered list), one file per source (12 collectors)
6. `helpers/` — `json_io.py` (`json_get`), `chrome_name.py` (`chrome_ext_name`), `vsc_name.py` (`resolve_vsc_ext_name`)
7. `gitops.py` — `git_pull()`, `git_commit_and_push()`, `rename_commit()`; all take `catalog_repo` Path via `cwd=`
8. `retention.py` — `retain_newest_per_host()`, `prune_old_archives()`; two-pass algorithm; skip-on-unparseable
9. `naming.py` — `parse_catalog_filename()`, `make_catalog_filename()`; pure functions, regex-based

**Package layout:** `src/mac_software_list/` with `catalog/`, `collectors/`, and `helpers/` sub-packages. Use `mac_software_list` as the Python import name (matches pyproject.toml convention). `src/` layout (PEP 517) prevents accidental imports of the uninstalled package during test runs.

### Critical Pitfalls

1. **Sort-order divergence (LC_ALL=C)** — Python `sorted(lines, key=str.casefold)` diverges from C-locale byte-order for mixed-case and non-ASCII names. Fix: always shell out to `subprocess.run(["sort", "-f", "-u"], env={**os.environ, "LC_ALL": "C"})` in `flush_section`. Establish this before writing any collector — parity failures accumulate.

2. **Section boundary byte drift** — Trailing newlines from `print()`, `str.join()`, and `subprocess.stdout` are subtly different. A single extra `\n` at a section boundary shifts all downstream sections. Fix: establish `CatalogWriter.write_section()` and run a binary byte-comparison parity test on an empty catalog before writing any collector.

3. **Archiving the just-written catalog (main-block ordering regression)** — Calling `retain_newest_per_host` before `generate_catalog` archives the new file before it exists. The v0.47.0 milestone documented this fix; the Python `main()` must replicate the order: generate → retain → prune → commit.

4. **Wrong catalog repo path (`__file__` / `cwd` drift)** — `Path(__file__).parent` points into the pipx venv, not the catalog repo. `os.getcwd()` is wherever the user launched from. Fix: `catalog_repo` is always resolved from config/flag in `config.py` and threaded as an explicit argument everywhere.

5. **Destructive-op regressions from prior milestones** — Three behaviors must be explicitly re-tested in Python: (a) `prune_old_archives` must skip (not delete) files with unparseable timestamps; (b) `retain_newest_per_host` must keep ALL files tied for newest (two-pass, not `max()`); (c) `rename_machine` must hard refuse-clobber before any `shutil.move()`.

6. **Parity fixture generation hazard** — The Zsh script is destructive. Golden fixtures cannot be generated by running it against the real repo. Fixtures must come from a controlled machine state in a disposable clone or a synthetic fixture environment. This is a planning-first problem.

7. **Non-TTY hang and EOF loop** — `input()` without a TTY guard blocks in cron/pipe. `except EOFError: continue` recreates the v0.49.0 infinite-loop defect. Fix: wrap all `input()` in `prompt()` with `sys.stdin.isatty()` guard; `except EOFError: return QuitSelection()`.

---

## Implications for Roadmap

The ARCHITECTURE.md build-order analysis is the authoritative phase sequencer. The following phase structure is the direct output of that dependency analysis, with pitfall mappings added.

### Phase 1: Foundation — Output Format + Pure Helpers

**Rationale:** `naming.py`, `catalog/format.py`, `catalog/writer.py`, and `helpers/json_io.py` have zero dependencies on the rest of the package. They produce all the load-bearing output contracts. Every collector and every parity test depends on these being correct. Start here; parity failures found early are cheap.

**Delivers:** `emit_item()`, `flush_section()` (with `LC_ALL=C sort` shell-out), `CatalogWriter` (atomic tmp+rename), `write_section()`, `parse_catalog_filename()`, `make_catalog_filename()`, `json_get()`

**Avoids:** Sort-order divergence (Pitfall 1), section boundary byte drift (Pitfall 3), `dict`/`set` non-determinism (Pitfall 4), atomic write omission (Pitfall 10)

**Research flag:** Standard patterns — all decisions are resolved in this summary.

### Phase 2: Helpers — Chrome and VS Code Name Resolution

**Rationale:** `helpers/chrome_name.py` and `helpers/vsc_name.py` wrap `json_io` and are shared across multiple collectors. Building them before collectors avoids duplication and keeps collectors thin.

**Delivers:** `chrome_ext_name()` (`__MSG_` resolution via `_locales/messages.json` with lowercase-key lookup), `resolve_vsc_ext_name()` (NLS placeholder resolution)

**Research flag:** Standard patterns — fully documented in STACK.md and ARCHITECTURE.md.

### Phase 3: Config + Identity + Retention

**Rationale:** The `catalog_repo` path threading is the architectural backbone. `identity.py` and `retention.py` both depend on `naming.py` (Phase 1). These three modules must be built and unit-tested before any pipeline modules can be wired together. This is also where two of the most dangerous regressions live (prune-on-parse-failure, tied-newest retention).

**Delivers:** `Config` dataclass + `load_config()` + `resolve_catalog_repo()` (XDG path, flag > env > file > error), `select_computer()`, `validate_computer_name()`, `upsert_machine_label()` (atomic TSV write), `rename_machine()` (refuse-clobber guard), `retain_newest_per_host()` (two-pass), `prune_old_archives()` (skip-on-unparseable), `config init` + `config show` subcommands

**Avoids:** Wrong catalog repo path (Pitfall 9), prune-on-parse-failure regression (Pitfall 7), tied-newest retention bug (Pitfall 8), refuse-clobber regression (Pitfall 11), atomic write omission for TSV (Pitfall 10)

**Research flag:** Standard patterns — all behaviors directly documented in PITFALLS.md. Write tests before implementation for retention and prune (safety-critical).

### Phase 4: Collectors

**Rationale:** All 12 collectors are independent of each other after Phase 2. They share the `Collector` ABC, `emit_item()`/`flush_section()`, and helpers. Within this phase, collectors can be built in any order; each is a self-contained unit. The REGISTRY is assembled last, encoding the fixed section order.

**Delivers:** `collectors/base.py` (ABC, `CollectorResult`, `Section`), then: `homebrew.py`, `mas.py`, `setapp.py`, `webapps.py`, `claude.py`, `codex.py`, `opencode.py`, `gemini.py`, `vscode.py`, `cursor.py`, `chrome.py`, `firefox.py`, `collectors/__init__.py` (REGISTRY)

**Avoids:** `sort -V` for Chrome version dirs (Pitfall 2), MCP secret re-introduction (FMT-03 guards), `dict`/`set` non-determinism

**Research flag:** The `claude mcp list` vs `~/.claude.json` question must be resolved before the Claude collector is implemented (see Open Questions). Chrome/Firefox filesystem paths should be verified against current macOS + browser versions.

### Phase 5: Git + CLI + Main Orchestration

**Rationale:** This phase wires all prior phases together. `gitops.py` depends on the catalog-repo path threading from Phase 3. `cli.py` / `__main__.py` depends on everything above. The main-block ordering regression is the primary risk.

**Delivers:** `gitops.py` (`git_pull`, `git_commit_and_push` with `-- <pathspec>` guard), `cli.py` (argparse, TTY-guarded interactive menus, `RunContext` construction), `__main__.py` (entry point with Python version guard, correct `main()` call ordering), `--version` via `importlib.metadata`

**Avoids:** Main-block ordering regression (Pitfall 6), non-TTY hang (Pitfall 14), EOF infinite loop (Pitfall 15), `git add` leading-dash injection (Pitfall 12), `--version` drift (Pitfall 16), `/usr/bin/python3` CLT stub hang (Pitfall 5)

**Research flag:** Standard patterns — all behaviors specified in PITFALLS.md. Implement `prompt()` TTY wrapper before any interactive prompt.

### Phase 6: Distribution

**Rationale:** After the package is functionally complete, package it for distribution. The `.pyz` zipapp must be validated as an artifact (not just the dev install) since `__file__`-relative path access and C extension inclusion are zipapp-specific failure modes.

**Delivers:** `pyproject.toml` (hatchling backend, `requires-python = ">=3.11"`, zero runtime deps, `[project.scripts]` entry point), `build-pyz.sh` (stdlib `python -m zipapp`, `#!/usr/bin/env python3` shebang), `.gitignore` entry for `*.pyz`, README install instructions, `pipx install` validation

**Avoids:** Committing `.pyz` to git (Pitfall 17), zipapp `__file__`-relative data access (Pitfall 13), CLT stub hang in shebang (Pitfall 5), `--version` drift (Pitfall 16)

**Research flag:** Standard patterns — fully documented in STACK.md.

### Phase 7: Parity Tests

**Rationale:** Golden-output parity tests are the safety gate for the entire port. They require all collectors (Phase 4) and the full pipeline (Phase 5), plus golden fixtures generated from the Zsh script under a controlled machine state. Parity test infrastructure (normalization utilities, fixture directory layout) should be scaffolded in Phase 1 to allow incremental format verification throughout development.

**Delivers:** `tests/golden/` fixture directory, `normalize_catalog_body()` (strip timestamps + machine labels), section-level parity tests parametrized over golden fixtures, full-catalog integration smoke test, `PYTHONHASHSEED=random` CI config

**Avoids:** False-confidence sort parity on ASCII-only fixtures (test with non-ASCII extension names), hash-randomization non-determinism

**Research flag:** The parity-fixture generation strategy (how to produce controlled Zsh golden fixtures given the destructive-run hazard) is an **open planning question** — must be resolved in Phase 7 planning before implementation begins.

### Phase Ordering Rationale

- foundation → helpers → config+identity+retention → collectors → git+cli+main → distribution → parity tests is the exact dependency order from ARCHITECTURE.md
- Each phase produces independently testable units before the phases that depend on them
- The two safety-critical phases (retention logic, main orchestration ordering) have test-before-implementation requirements
- Parity tests are last because they validate the complete system, but parity-test infrastructure is scaffolded in Phase 1 to allow incremental format verification throughout development

### Research Flags

Phases needing additional research or planning consideration:
- **Phase 4 (Collectors):** Chrome and Firefox filesystem paths should be verified against current macOS + browser versions. The `claude mcp list` vs `~/.claude.json` question must be resolved before the Claude collector is written.
- **Phase 7 (Parity Tests):** Golden fixture generation strategy is an open planning question — disposable-clone fixture vs. synthetic Python fixture environment; must be planned explicitly.

Phases with standard, fully-documented patterns (no additional research needed):
- **Phase 1 (Foundation):** All output format decisions are resolved in this summary.
- **Phase 2 (Helpers):** Chrome name resolution and NLS lookup fully specified in STACK.md/ARCHITECTURE.md.
- **Phase 3 (Config + Identity + Retention):** All behaviors derived from the Zsh source and documented in PITFALLS.md.
- **Phase 5 (Git + CLI):** TTY/EOF handling, argparse setup, `git add --` guard all specified.
- **Phase 6 (Distribution):** zipapp and pyproject.toml conventions fully documented.

---

## Watch Out For

These are the highest-probability "looks done but isn't" traps from PITFALLS.md:

| Check | How to Verify |
|-------|---------------|
| Sort parity with mixed-case + non-ASCII names | Binary compare Python vs Zsh output with `1Password`, `Bitwarden`, an extension with an accented name |
| Section boundary bytes | `xxd` or `bytes` comparison at section boundaries; one extra `\n` is invisible in text diffs |
| `retain_newest_per_host` two-pass | Test with two same-host same-timestamp files; both must survive |
| `prune_old_archives` skip-not-delete | Put a `.gitkeep` in the archive dir; verify it is not deleted |
| Main-block ordering | Two sequential runs: main folder has exactly 1 (newer) catalog, archive has the older |
| TTY guard | `echo "" | mac-catalog` (no `--computer` flag) must exit fast with a clear error, not hang |
| EOF handling | Ctrl-D at computer-select menu must produce clean quit, not traceback, not loop |
| `git add --` guard | Computer folder named `-test` stages correctly |
| Refuse-clobber rename | Rename to an existing folder name exits 1, both folders intact |
| MCP secrets | Grep the generated catalog for `token`, `Bearer`, `sk-`, `ghp_`, `key=`, `Authorization` — zero hits |
| `.pyz` zipapp | Run from `/tmp`; no `__file__`-relative path errors; `zipfile -l` shows no `.so`/`.dylib` |

---

## Open Questions

These items could not be fully resolved in research and must be addressed during phase planning:

1. **Parity-fixture generation strategy** — The Zsh script is destructive (deletes archive catalogs older than the retention cutoff, moves files on `--rename`, commits to git). Golden fixtures must be generated from a controlled machine state without touching the real repo. Leading options: (a) a disposable `git clone` with a no-remote fixture catalog repo driven through a pty; (b) a synthetic Python fixture environment that mocks filesystem inputs to each collector. Option (b) is more controllable but requires careful fixture design. Must be planned explicitly before Phase 7 is detailed.

2. **`claude mcp list` vs `~/.claude.json` parsing** — The Claude collector can either shell out to `claude mcp list --json` (CLI-first, matching the Zsh pattern) or parse `~/.claude.json` directly. The ARCHITECTURE.md integration table lists the CLI path. The question is whether `claude mcp list` produces stable, parseable JSON suitable for parity tests. Verify against the installed Claude Code version before the Claude collector is written.

3. **Package name canonicalization** — ARCHITECTURE.md uses `maclist` as the Python package name in some examples; STACK.md uses `mac_software_list`. Recommendation: `mac-software-list` as the PyPI/pipx install name, `mac_software_list` as the Python import package name. Decide once in Phase 1 when `pyproject.toml` is first created.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All claims verified against live machine (Python 3.9.6 stub, Homebrew 3.14, `tomllib` presence). Zero-dep stdlib feasibility verified capability-by-capability. |
| Features | HIGH | Distribution conventions well-documented; config precedence and XDG location confirmed by multiple independent sources. |
| Architecture | HIGH | Architecture derived directly from reading `update-list.sh` line-by-line and the v0.46.0–v0.49.0 defect record. |
| Pitfalls | HIGH | All 17 pitfalls derived from the actual Zsh source code and live pty-driven UAT defect records from prior milestones. No speculation. |

**Overall confidence: HIGH**

### Gaps to Address

- **Parity fixture generation strategy** (Open Question 1): Must be resolved in Phase 7 planning before any parity test implementation begins.
- **`claude mcp list` CLI stability** (Open Question 2): A one-time spot-check of `claude mcp list --json` output format before Phase 4 Claude collector planning will close this quickly.
- **Package name canonicalization** (Open Question 3): Trivial to close — decide `mac_software_list` as the import name in Phase 1 when `pyproject.toml` is first created.

---

## Sources

### Primary (HIGH confidence)
- `/Users/ken/dev/mac-software-list/update-list.sh` — authoritative Zsh reference; behavioral source of truth for format, degradation rules, sort, retention math, filename convention
- Python 3.11 stdlib docs (`tomllib`, `json`, `plistlib`, `zipapp`, `dataclasses`, `pathlib`, `argparse`) — live machine verified
- `syrupy` PyPI v5.3.2 (June 2026) — requires Python >=3.10; confirmed
- PyPA — Writing pyproject.toml, Creating CLI tools (`[project.scripts]` format, hatchling syntax)
- `.planning/MILESTONES.md` — v0.47.0 main-block ordering fix; v0.49.0 UAT defects (four confirmed live bugs)

### Secondary (MEDIUM confidence)
- mac.install.guide — Xcode CLT ships Python 3.9.6 (Oct 2024; verified unchanged June 2026 on this machine)
- atmos.tools changelog, ruff GitHub issue #10739, platformdirs issue #98 — XDG convention for macOS developer CLIs
- Python 3.9 EOL announcement (Red Hat, Dec 2025) — EOL date October 31, 2025
- shiv docs — comparison with zipapp; justification for "use zipapp for zero-dep tools"

### Tertiary (LOW confidence, no action required)
- ConfigArgParse precedence pattern — config precedence chain is a well-established convention; the specific library is not used
- pytest-approvaltests — referenced in FEATURES.md as optional; not recommended (plain file-based fixtures preferred)

---
*Research completed: 2026-06-14*
*Ready for roadmap: yes*

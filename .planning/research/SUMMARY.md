# Project Research Summary

**Project:** maccat v2.1.0 — Reinstall from Catalog
**Domain:** macOS software cataloger CLI — `maccat reinstall` subcommand
**Researched:** 2026-06-16
**Confidence:** HIGH

## Executive Summary

The `maccat reinstall` feature closes the catalog loop by generating a `reinstall.sh` bash
script from an existing plain-text catalog snapshot. The implementation is fully stdlib-only
(Python `re`, `pathlib`, `dataclasses`, `shlex`) with zero new dependencies. The feature
decomposes cleanly into three new modules — a section-boundary parser, a script emitter, and
a thin CLI orchestrator — wired into the existing `cli.py` subcommand dispatch as a one-liner
short-circuit after catalog repo resolution. All four deterministic sources (Homebrew, mas,
VS Code extensions, Cursor extensions) are auto-installable; all other sources land in a
runtime-echoed manual checklist.

Two scoped decisions shape the implementation and must not be re-litigated. First, the mas
App Store ID is NOT currently in the catalog (the collector discards column 1 of `mas list`
output), so v2.1.0 will add a catalog format change: `MasCollector` will emit `AppName
(version) [id]` using `emit_item`'s full three-field path, enabling `mas install <id>` in
the generated script. Older catalogs that predate this change will degrade those entries to
the manual checklist. Second, the formula/cask distinction is NOT a scope blocker: `brew
install <name>` installs a formula or a cask in modern Homebrew (verified Homebrew 6.0.2),
so the emitter uses plain `brew install` for all Homebrew items with a `brew list --cask
<name> &>/dev/null || brew install --cask <name>` guard for cask idempotency. Explicit cask
detection is deferred as a future enhancement.

The central implementation risks are idempotency and safety. `brew install --cask` exits
non-zero on an already-installed cask (Homebrew #15295), so each cask line requires the
`brew list --cask` guard. VS Code and Cursor extension installs need `--list-extensions |
grep` pre-checks rather than `--force`. The emitter must use `shlex.quote()` on every
catalog-derived value in shell position and write the output file at `0o644` (never
executable). The parser to `catalog/format.py` coupling is the primary anti-drift risk: a
mandatory round-trip contract test in `tests/reinstall/test_parser_contract.py` is the
mechanical guard.

---

## Key Findings

### Recommended Stack

No new dependencies. The entire feature is implemented with Python stdlib: `re` for the
section-boundary parser, `pathlib` for file I/O and newest-catalog scanning, `dataclasses`
for `ParsedItem`/`ParsedSection`/`ParsedCatalog`, and `shlex.quote()` for shell-safe
argument quoting in the emitter. The generated script is plain bash with no Brewfile, no
Jinja2, no template engine. A flat sequence of guarded install commands with inline version
comments is all that is required, and string formatting handles it cleanly.

**Core technologies:**
- `re` (stdlib): Right-anchored regex parsing of `emit_item` line shapes — purpose-built to
  avoid the embedded-parens ambiguity pitfall
- `shlex.quote` (stdlib): Shell-safe quoting for every catalog-derived value inserted into
  generated shell commands — mandatory, not optional
- `pathlib.Path` (stdlib): Newest-catalog scan + file write at `0o644`; already used in the
  existing codebase
- `dataclasses` (stdlib): `ParsedItem`, `ParsedSection`, `ParsedCatalog` — typed, testable,
  no third-party ORM overhead

**Install command syntax (verified live):**
- Homebrew formula: `brew list <name> &>/dev/null || brew install <name>`
- Homebrew cask: `brew list --cask <name> &>/dev/null || brew install --cask <name>`
- mas: `mas list | grep -q "^<id> " || mas install <id>` (requires ID in catalog — see MAS format change)
- VS Code: `code --list-extensions 2>/dev/null | grep -qi "^<id>$" || code --install-extension <id>`
- Cursor: `cursor --list-extensions 2>/dev/null | grep -qi "^<id>$" || cursor --install-extension <id>`

**Script conventions (non-negotiable):**
- Shebang: `#!/usr/bin/env bash` (portable; `/bin/bash` on macOS may be 3.x)
- Strict mode: `set -Eeuo pipefail`
- Provenance header with catalog filename, timestamp, computer name, review warning
- Section ordering: taps → formulae → casks → mas → VS Code → Cursor → manual checklist
- File permissions: `0o644` — requires `bash reinstall.sh`, not `./reinstall.sh`
- Never auto-execute: emitter is a pure string builder, zero subprocess calls

### Expected Features

**Must have (P1 — v2.1.0 launch):**
- `maccat reinstall` subcommand with `--from PATH` flag and interactive computer-picker
  fallback reusing existing `select_computer()`
- Catalog parser reading all section types back into structured `ParsedItem` objects
- `reinstall.sh` header: shebang, strict mode, provenance, item count summary, review warning
- Auto-install section: taps → formulae → casks → mas → VS Code → Cursor, each with
  skip-if-installed guard and `# cataloged: version` inline comment
- Tool-availability check (`command -v`) gating each section block; `brew` hard-exits on
  miss, others warn-and-continue
- Manual checklist section emitted via runtime `echo` statements (not static comments)
  covering Setapp, web apps, Chrome/Firefox extensions, all AI-CLI tooling
- Output path + `bash reinstall.sh` run instructions printed to stdout
- MAS catalog format change: `MasCollector` emits `AppName (version) [id]` — prerequisite
  for `mas install <id>` auto-install; older catalogs degrade mas entries to manual checklist

**Should have (P2 — v2.1.x after validation):**
- Item count summary in header comment (`# 42 formulae, 18 casks, 7 MAS apps, ...`)
- Prerequisites comment block in header (`# Requires: brew, mas, code, cursor`)
- Warn-and-continue for absent optional tools (vs. hard-exit on missing `mas`/`code`/`cursor`)

**Defer (v2.2+):**
- Diff-from-current-state before generating (requires catalog-diffing milestone)
- Multi-catalog merge (install union of two catalogs)
- Explicit cask detection with `[cask]` id marker in catalog

**Anti-features (never implement):**
- Version-pinned `brew install formula@x.y.z` — no stable version-pin for most formulae;
  cataloged version is comment-only
- `brew bundle` / Brewfile output — cannot cover VS Code/Cursor extensions in one file
- Auto-execution of the generated script — locked design decision
- `--force` on extension installs — redownloads even when current; use `--list-extensions`
  guard instead

### Architecture Approach

The reinstall subpackage (`src/maccat/reinstall/`) follows the existing short-circuit
dispatch pattern in `cli.py`: after `validate_catalog_repo()` and before the `--rename`
guard, a one-liner dispatches to `run_reinstall(args, catalog_repo)` and returns. Four new
modules are introduced — `parser.py`, `emitter.py`, `picker.py`, `cli.py` — and three
existing modules are reused unchanged (`identity.py:select_computer()`,
`naming.py:parse_catalog_filename()`, `config.py:resolve_catalog_repo()`). The critical
coupling is the parser to `catalog/format.py:emit_item()` contract: the parser inverts
exactly the four line shapes that `emit_item` produces, and a round-trip contract test
(`tests/reinstall/test_parser_contract.py`) is the sole mechanical anti-drift guard.

**Major components:**
1. `reinstall/parser.py` — Section-boundary state machine + right-anchored regex item
   parser; produces `ParsedCatalog` with typed `ParsedItem` objects carrying `name`,
   `version`, `id_`, and a degradation flag
2. `reinstall/emitter.py` — Per-source renderers (`_brew_block`, `_editor_ext_block`,
   `_manual_checklist_block`); static `SECTION_SOURCE_MAP` of 17 known section titles;
   `shlex.quote()` on all catalog-derived shell arguments; pure string builder
3. `reinstall/picker.py` — `resolve_catalog_path()`: `--from PATH` short-circuit or
   `select_computer()` + newest-file scan; independently testable
4. `reinstall/cli.py` — Thin orchestrator: resolve path → parse → emit → write at `0o644`
   → print output path

**Key architectural constraint:** `catalog/format.py:emit_item()` must NOT be changed in
this milestone except for the one deliberate change: `MasCollector` now calls it with the
numeric ID as the third argument. All other `emit_item()` call sites remain unchanged.

**MAS format change scope:** `MasCollector` in `collectors/mas.py` changes from
`awk '{print $2, $3}'` (which discards column 1, the numeric ID) to a Python parse that
extracts all three fields. The implementation subtlety: `mas list` column 3 already includes
parentheses around the version number (e.g., `(14.0)`), so the Python parse must strip those
parens before passing the version to `emit_item()` to avoid `AppName ((14.0)) [id]`.

### Critical Pitfalls

1. **MAS ID absent from current catalog** — `MasCollector` discards column 1 of `mas list`
   output. Auto-install via `mas install <id>` requires the numeric ID. Resolution decided:
   catalog format change in Phase 1. Catalogs generated before this change must degrade mas
   entries to the manual checklist in the parser. Verify the fix avoids double-parenthesizing
   the version (mas output already wraps version in parens).

2. **Formula/cask distinction is NOT a blocker** — `brew install <name>` works for both
   formulae and casks in Homebrew 6.0.2+ (confirmed via `brew install --help`). The only
   real issue is cask idempotency: `brew install --cask <name>` exits non-zero if already
   installed. Use the guard pattern for all Homebrew items. Explicit cask type detection
   is deferred. The PITFALLS agent over-flagged this as a scope blocker.

3. **Parser ambiguity: embedded parentheses in app names** — A name like
   `Smart Photo Widget (Dark).app (3.1.0)` must parse as name=`Smart Photo Widget (Dark).app`,
   version=`3.1.0`. Use right-anchored parsing: strip `[id]` suffix first, then `(version)`
   suffix, remainder is name. Never split on the first `(`.

4. **Shell injection via unquoted catalog values** — App names and version strings can
   contain `&`, `'`, `"`, `$`, backticks. Use `shlex.quote()` on every catalog-derived value
   in shell command position. Strip `\n`/`\r` from values used in comments. Establish
   `quote_for_script()` as the sole interpolation path — never bare f-string interpolation.

5. **Brew cask idempotency failure** — `brew install --cask <name>` exits non-zero when
   already installed (Homebrew #15295, confirmed current). With `set -Eeuo pipefail` this
   aborts the generated script mid-run. Every Homebrew item must use the guard:
   `brew list --cask <name> &>/dev/null || brew install --cask <name>`.

6. **Parser to emitter drift on `emit_item` shapes** — Any future change to `emit_item()`
   silently breaks the parser. Mitigation: module docstring cites the contract; round-trip
   test in `tests/reinstall/test_parser_contract.py` covers all six degradation variants.

---

## Implications for Roadmap

Three phases are suggested. The dependency chain is strict: catalog format fix → parser →
emitter → CLI wiring. Each phase is independently testable before the next begins.

### Phase 1: Catalog Format Fix + Parser Foundation

**Rationale:** The MAS ID absence is a hard prerequisite. Building the parser before
`MasCollector` emits the ID means mas auto-install must be retrofitted or ripped out later.
Fixing the format first means the parser is built against the final line shapes. The
round-trip contract test also cannot be written until `emit_item()` call shapes are final.

**Delivers:**
- `MasCollector` changed to extract all three `mas list` columns and call
  `emit_item(name, version, id_)` — new catalog line shape: `AppName (version) [id]`
- Mas collector tests updated to verify the new format, including version de-parens fix
- `reinstall/__init__.py` package marker
- `reinstall/parser.py`: `ParsedItem` (with `degraded` flag), `ParsedSection`,
  `ParsedCatalog` data structures; section-boundary state machine; right-anchored item
  regex (`_ITEM_RE_FULL`, `_ITEM_RE_VERSION`, `_ITEM_RE_ID`); degradation handling;
  sentinel-line skipping
- `tests/reinstall/test_parser_contract.py`: round-trip test for all six `emit_item`
  degradation variants; adversarial name fixtures (`Smart Photo Widget (Dark).app (3.1.0)`,
  extension with `(beta)` in display name, multi-version brew entry)

**Addresses:** mas auto-install (previously blocked), parser ambiguity pitfall, degraded
entry handling, multi-version brew version-as-metadata

**Research flag:** None needed — all line shapes read directly from `format.py` source.

---

### Phase 2: Script Emitter

**Rationale:** The emitter depends entirely on `ParsedCatalog` from Phase 1. Building it
after the parser is validated means the emitter can be tested with known-good `ParsedCatalog`
fixtures rather than parsing strings inline.

**Delivers:**
- `reinstall/emitter.py`: `emit_reinstall_script(catalog, generated_date) -> str`
- `_header_block()`: `#!/usr/bin/env bash`, `set -Eeuo pipefail`, provenance, item count
  summary, review warning
- `_brew_block()`: cask guard for every Homebrew item; `# cataloged: version` comments;
  `shlex.quote()` on name; multi-version version string in comment only (no version arg)
- `_mas_block()`: `mas list | grep -q "^<id> " || mas install <id>` guard; degrades to
  manual checklist for entries lacking an ID (pre-format-change catalogs)
- `_editor_ext_block("code", ...)` and `_editor_ext_block("cursor", ...)`: `--list-extensions
  | grep -qi` guard; extension IDs normalized to lowercase; `shlex.quote()` on ID
- `_manual_checklist_block()`: runtime `echo` statements for all non-auto-install sources;
  `# [ ] name (version)` format with AI-CLI transport included
- `command -v` guards at section start; `brew` hard-exits, others warn-and-continue
- `SECTION_SOURCE_MAP`: static dict of 17 known section titles; unknown titles fall through
  to manual checklist
- `quote_for_script()` wrapper as sole shell-interpolation path
- File written at `0o644`; zero subprocess calls in emitter

**Avoids:** Cask idempotency abort (brew list guard), shell injection (shlex.quote),
auto-execution (pure string builder), PATH guard omission, version-arg breakage

**Research flag:** None needed — all syntax verified live.

---

### Phase 3: Picker + CLI Wiring + Integration

**Rationale:** The picker and orchestrator are thin wrappers over Phase 1 and 2 work.
Touching `cli.py` last minimizes risk to the existing 13-step catalog-gen path.

**Delivers:**
- `reinstall/picker.py`: `resolve_catalog_path(catalog_repo, from_path, computer_name)` —
  `--from PATH` short-circuit or `select_computer()` + newest-file scan
- `reinstall/cli.py`: `run_reinstall(args, catalog_repo)` — thin orchestrator
- `cli.py` modifications: `reinstall` subparser with `--from` / `dest="from_path"` (handles
  `from` keyword conflict); dispatch block after `validate_catalog_repo()`, before `--rename`
- Integration smoke test: `maccat reinstall --from <fixture>` — verify file written, path
  printed, `--rename` guard does not fire on reinstall args

**Avoids:** Inlining logic into `run()` (violates 13-step invariant); `from` keyword
conflict in argparse; `--rename` guard accidentally triggering on reinstall

**Research flag:** None needed — dispatch pattern confirmed from `cli.py` source.

---

### Phase Ordering Rationale

- **Format fix gates mas auto-install.** Without the MAS ID in the catalog, the emitter
  cannot generate `mas install <id>`. Building emitter first forces a mid-phase rewrite.
- **Parser gates emitter.** The emitter's renderers take `ParsedCatalog` as input. The
  emitter API cannot be written without finalized parser output types.
- **Each phase is independently testable.** Phase 1: text-only parse tests. Phase 2:
  `ParsedCatalog` fixture → assert script string content. Phase 3: real files on disk.
- **`cli.py` changes are last.** The 13-step order in `run()` is NON-NEGOTIABLE. Touching
  it last minimizes disruption risk to the existing catalog-gen path.

### Research Flags

All three phases have standard, well-documented patterns. No `--research-phase` flag is
needed during planning.

- **Phase 1:** All line shapes read from `format.py` source; test fixtures in
  `test_homebrew.py` confirm mas ID is discarded. Build order and parser algorithm fully
  specified in ARCHITECTURE.md.
- **Phase 2:** All install command syntax verified live. Idempotency behaviors confirmed
  against official sources and Homebrew issue tracker. Shell-safety patterns are stdlib.
- **Phase 3:** Dispatch insertion point confirmed from `cli.py` source; `select_computer()`
  signature confirmed from `identity.py`.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Install syntax verified live (Homebrew 6.0.2, mas 7.0.0); VS Code CLI from official docs; Cursor base syntax HIGH (`--force` flag MEDIUM — community-confirmed, not in official docs) |
| Features | HIGH | Scope locked in PROJECT.md; all behaviors confirmed against official docs and Homebrew issue tracker |
| Architecture | HIGH | All module signatures read from source; dispatch pattern and `emit_item()` shapes confirmed from `cli.py` and `format.py` source |
| Pitfalls | HIGH | All pitfalls derived from reading actual collector source; test fixtures in `test_homebrew.py` confirm mas ID is absent |

**Overall confidence:** HIGH

### Gaps to Address

- **Cursor `--force` flag:** Confirmed working via community gists but not in official Cursor
  docs. No impact on implementation — the generated script uses the `--list-extensions` guard
  instead of `--force`, so this gap is moot.

- **MAS version de-parenthesization:** `mas list` column 3 includes parentheses around the
  version number (e.g., `(14.0)`). The `MasCollector` fix must strip those parens before
  passing to `emit_item()`. Verify against actual `mas list` output at the start of Phase 1.

- **Formula/cask name collision edge case:** A name existing as both a Homebrew formula and
  a cask (rare) will get plain `brew install <name>` which resolves to the formula. For the
  rare collision, a comment in the generated script noting `# if this is a cask: brew install
  --cask <name>` is sufficient. No scope change needed.

- **Taps:** If the catalog contains formulae from third-party taps, the generated script
  cannot emit `brew tap <tap>` prerequisites because tap information is not currently
  cataloged. In v2.1.0 the taps section will be empty or omitted. Document this limitation
  in the script header.

---

## Sources

### Primary (HIGH confidence)
- `src/maccat/collectors/mas.py` — `_parse_mas_output`: awk column-skip confirms ID absent
- `src/maccat/collectors/homebrew.py` — `collect()`: formula+cask concatenation without type marker
- `src/maccat/catalog/format.py` — `emit_item()`: all four line shapes and degradation rules
- `src/maccat/cli.py` — existing subcommand dispatch pattern, 13-step orchestration order
- `src/maccat/identity.py` — `select_computer()` signature
- `tests/collectors/test_homebrew.py` (lines 120–129) — fixture confirms mas ID is discarded
- Homebrew 6.0.2 live verification — `brew help install`, cask idempotency behavior
- mas 7.0.0 live verification — `mas help install`, idempotency warning behavior
- [VS Code CLI docs](https://code.visualstudio.com/docs/configure/command-line) — `--install-extension`, `--force`, `--profile` flags
- [Homebrew Manpage](https://docs.brew.sh/Manpage) — `--cask`, `-y`/`--no-ask`, upgrade behavior
- [Homebrew issue #15295](https://github.com/Homebrew/brew/issues/15295) — cask already-installed hard error
- [Homebrew issue #21416](https://github.com/Homebrew/brew/issues/21416) — taps-before-formulae ordering required
- [Homebrew discourse: skip-if-installed](https://discourse.brew.sh/t/skip-ignore-brew-install-if-package-is-already-installed/633) — canonical `brew list || brew install` guard pattern
- [betterdev.blog minimal safe bash template](https://betterdev.blog/minimal-safe-bash-script-template/) — `#!/usr/bin/env bash` + `set -Eeuo pipefail`

### Secondary (MEDIUM confidence)
- [Cursor forum: --list-extensions](https://forum.cursor.com/t/command-line-list-extensions/103565) — `cursor --install-extension` and `cursor --list-extensions` confirmed working on macOS
- [Community gist: VS Code extensions to Cursor](https://gist.github.com/kigster/fcf644441be8f5d9e1c5434ca9f1723a) — `cursor --force --install-extension` pattern in practice
- [Brewfile tips gist (ChristopherA)](https://gist.github.com/ChristopherA/a579274536aab36ea9966f301ff14f3f) — taps → formulae → casks → mas ordering convention
- [mas-cli README](https://github.com/mas-cli/mas) — `mas install` behavior and scripting commands

### Tertiary (LOW confidence)
- Cursor official docs for `--force` flag on `cursor --install-extension` — not yet documented;
  behavior inferred from VS Code codebase inheritance and community gist confirmation

---

## Cross-Researcher Conflict Resolution

**Conflict 1 — Formula/cask distinction (PITFALLS flagged as blocker; STACK and ARCHITECTURE did not):**
RESOLVED: Not a blocker. `brew install <name>` installs a formula or cask (confirmed via
`brew install --help`). The only genuine issue is cask idempotency (non-zero exit if already
installed, Homebrew #15295), which is resolved by the `brew list --cask` guard pattern. No
catalog format change is needed. ARCHITECTURE.md's `SECTION_SOURCE_MAP` correctly uses plain
`brew install` for all Homebrew items.

**Conflict 2 — MAS App Store ID (ARCHITECTURE showed mas as manual-only; PITFALLS showed it as a hard blocker):**
RESOLVED: The catalog format WILL change in Phase 1 (Option 2 from PITFALLS.md).
`MasCollector` will emit `AppName (version) [id]` preserving the numeric ID. The
`SECTION_SOURCE_MAP` entry for `"App Store Applications"` should be `("auto", "id_")` for
catalogs generated after the change. The parser's degradation flag determines which path is
taken at emitter runtime for older catalogs.

---
*Research completed: 2026-06-16*
*Ready for roadmap: yes*

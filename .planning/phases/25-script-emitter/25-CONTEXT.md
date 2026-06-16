# Phase 25: Script Emitter - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Render a `ParsedCatalog` (from Phase 24's `reinstall/parser.py`) into a complete,
injection-safe, idempotent `reinstall.sh` **script string**. New module
`src/maccat/reinstall/emitter.py` with `emit_reinstall_script()` and per-source renderers.
Covers GEN-01, GEN-02, GEN-03, GEN-04, MAN-01.

Out of boundary: resolving/selecting the catalog, file I/O, and the `maccat reinstall`
CLI subcommand + picker (all Phase 26). This phase produces the script string and (per
RST-01, finalized in Phase 26) the 0o644 write contract; the emitter itself performs ZERO
subprocess calls — it only builds text.

Key upstream fact: the catalog merges Homebrew **formulae and casks into a single
"Homebrew Packages" section** with NO formula/cask marker — the emitter cannot distinguish
them from catalog data alone. This drives the universal-guard decision below.
</domain>

<decisions>
## Implementation Decisions

### Homebrew Guard & Versions (GEN-01)
- **Universal idempotency guard** (formula/cask indistinguishable in catalog):
  `brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n>`
  — `brew install` auto-detects formula vs cask, so one install command covers both; the
  two `brew list` probes cover the installed-state of either kind. (`<n>` is the
  `quote_for_script()`-quoted name.)
- **Version comment:** append `# cataloged: <version-string-verbatim>` to each line. For
  multi-version Homebrew entries (`python@3.11 (3.11.1 3.11.2)`) emit the full string:
  `# cataloged: 3.11.1 3.11.2`. Items with no version → omit the comment.
- **Formula/cask ambiguity (GEN-01):** do NOT attempt per-name detection. Emit one
  section-top comment warning that a name which is BOTH a formula and a cask may need a
  manual `brew install --cask <n>` / `--formula <n>` disambiguation.
- **Degraded / `(none found)` Homebrew section:** skip entirely — emit no install lines and
  no checklist entry for it (a degraded section means the source was absent).

### SECTION_SOURCE_MAP & Manual Checklist (GEN-02/03, MAN-01)
- **Static `SECTION_SOURCE_MAP`** keyed on the verbatim section title (from `ParsedSection.title`).
  Exactly four auto-install mappings:
  - `"Homebrew Packages"` → brew block (`_brew_block`)
  - `"App Store Applications"` → mas block (`mas install <id>`, id-bearing items only)
  - `"VS Code Extensions"` → `code --install-extension` block (`_editor_ext_block`)
  - `"Cursor Extensions"` → `cursor --install-extension` block (`_editor_ext_block`)
- **mas entries WITHOUT an id** (pre-MAS-01 catalogs / id-less ParsedItems): route to the
  manual checklist under a heading like "App Store Applications (no ID — install manually)" —
  never emit a broken `mas install` line.
- **Unknown / future section title** not in `SECTION_SOURCE_MAP`: default to the **manual
  checklist** — never fabricate an install command. (Forward-compatible: a new catalog
  section still gets listed for the user.)
- **All other known sources → manual checklist, grouped by source title:** Setapp
  Applications, Web-installed Applications, Google Chrome Extensions, Firefox Extensions,
  Claude Code Plugins / MCP Servers / Skills & Agents, Codex MCP Servers, Gemini CLI
  Extensions / MCP Servers, and all OpenCode sections. No fabricated install commands
  (AI-CLI tooling is identity-only by FMT-03 — nothing to install from).

### Script Structure & Injection Safety (GEN-04, criterion 5)
- **Shebang + safety:** `#!/usr/bin/env bash` then `set -Eeuo pipefail`.
- **Provenance header:** comment block naming the source catalog (filename) and the
  generation date, plus a "review before running — never auto-executed" notice.
- **Section ordering:** header → Homebrew (one block: formulae+casks merged) → mas → code →
  cursor → manual checklist.
- **Injection safety:** a single `quote_for_script()` wrapper around `shlex.quote()` is the
  SOLE path any catalog-derived value reaches shell command position — no bare f-string
  interpolation in shell context. Additionally strip newlines from values placed in
  `# cataloged:` comments (comment-injection / line-break safety), since a newline in a
  comment would break the following command line.
- **VS Code / Cursor extension lines (GEN-03):** lowercase the marketplace id; guard with
  `command -v <editor> >/dev/null && ! <editor> --list-extensions | grep -qi "^<id>$" && <editor> --install-extension <id>`
  (PATH guard + idempotency check; id is the lowercased install key, quoted).
- **Manual checklist format:** per-source heading `echo` followed by one
  `echo "  - <name> (<version>)"` per item (version shown only when present). Echo strings
  are quoted/escaped so item text cannot break the script.

### Claude's Discretion
- Exact bash phrasing within the above guards, the `quote_for_script()` internals, the
  emitter function decomposition (`_brew_block` / `_editor_ext_block` /
  `_manual_checklist_block`), header wording, and test-fixture layout are at Claude's
  discretion within these decisions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/reinstall/parser.py` (Phase 24) — `parse_catalog()` → `ParsedCatalog`
  (`.sections: list[ParsedSection]`); each `ParsedSection` has `title` (verbatim), `items`
  (`list[ParsedItem]` with `name`, `version: str|None`, `id: str|None`, `raw_line`), and a
  `degraded` flag. The emitter consumes these — the parser is the sole input contract.
- `stdlib shlex` — `shlex.quote()` is the injection-safety primitive (stdlib, no new dep).
- Catalog section titles are fixed constants in `src/maccat/collectors/*.py` (e.g.
  `"Homebrew Packages"`, `"App Store Applications"`, `"VS Code Extensions"`,
  `"Cursor Extensions"`, `"Setapp Applications"`, `"Web-installed Applications"`,
  `"Google Chrome Extensions"`, `"Firefox Extensions"`, `"Claude Code Plugins"`,
  `"Claude Code MCP Servers"`, `"Claude Code Skills & Agents"`, `"Codex MCP Servers"`,
  `"Gemini CLI Extensions"`, `"Gemini CLI MCP Servers"`, plus OpenCode titles) — these are
  the keys for `SECTION_SOURCE_MAP`.

### Established Patterns
- `from __future__ import annotations` line 1; module-level ALL_CAPS constants
  (`SECTION_SOURCE_MAP`); type hints everywhere; stdlib-only; ruff + mypy --strict clean.
- `catalog/format.py::emit_item` is the read-only inverse partner (Phase 24) — DO NOT modify.

### Integration Points
- Public API the emitter must expose for Phase 26: `emit_reinstall_script(catalog: ParsedCatalog, *, source_name: str, generated: str) -> str` (exact signature at planner discretion, but must take a `ParsedCatalog` and produce the full script string). Phase 26 writes the string at mode 0o644 and never subprocess-runs it.
</code_context>

<specifics>
## Specific Ideas

- Generated script MUST pass `bash -n` (syntax check) — include a test that runs
  `bash -n` on the emitted string (skip gracefully if `bash` is unavailable, but it is
  present on macOS).
- Adversarial test: a catalog item whose name/version contains shell metacharacters
  (`$(...)`, backticks, `;`, spaces, quotes, embedded newline) must round-trip through
  `quote_for_script()` into a safe, `bash -n`-clean line — proving criterion 5.
- mas `mas install <id>` uses the numeric id (Phase 24 preserved it); id-less entries go to
  the checklist (GEN-02).
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Catalog resolution, the `reinstall`
subcommand, the computer-picker, and the 0o644 file write are Phase 26. RST-03 brew taps and
RST-04 AI-CLI auto-restore are v2 per REQUIREMENTS.md.)
</deferred>

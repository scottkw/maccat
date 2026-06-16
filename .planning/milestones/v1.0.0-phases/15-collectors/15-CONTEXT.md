# Phase 15: Collectors - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Infrastructure/port phase — discuss skipped. This is a pure byte-parity port of the
12 source collectors from the untouched zsh `update-list.sh`; the zsh script is the complete spec
and there are no user-facing design decisions to make. The only open choice (collector module
organization / a `Collector` pattern) is Claude's discretion and is already covered by research.

<domain>
## Phase Boundary

Implement all source collectors of `maccat` at byte-parity with the zsh `generate_catalog`, each
degrading gracefully when its source is absent, and never emitting secrets. Built on the Phase 13
output-format layer (`emit_item`/`flush_section`/`CatalogWriter`) and the Phase 13 name helpers
(`json_io`, `chrome_name`, `vsc_name`). This phase produces the catalog SECTION BODIES; the
end-to-end run wiring (config resolution → generate → retention sweep → git) is Phase 16.

The 12 logical collectors (zsh function → section title), in the EXACT `generate_catalog` order:
1. Installed Mac Software List (header section)
2. Homebrew Packages — `brew list --formula` / `--cask`
3. App Store Applications — `mas list`
4. Setapp Applications — `/Applications/Setapp/`
5. Web-installed Applications — `/Applications` scan
6. Claude Code Plugins — `collect_claude_plugins` (update-list.sh:1594)
7. Claude Code MCP Servers — `collect_claude_mcp` (:1638) — name + transport only
8. Claude Code Skills & Agents — `collect_claude_skills_agents` (:1692)
9. Codex MCP Servers — `collect_codex_mcp` (:1748) — name + transport only
10. OpenCode Plugins / MCP Servers / Agents — `collect_opencode_*` (:1802/:1861/:1930)
11. Gemini CLI Extensions / MCP Servers — `collect_gemini_*` (:1970/:2016)
12. VS Code Extensions / Cursor Extensions — `collect_vscode_extensions` (:1387) / `collect_cursor_extensions` (:1494)
    Google Chrome Extensions (all profiles) — `collect_chrome_extensions` (:2074)
    Firefox Extensions (all profiles) — `collect_firefox_extensions` (:2154)

**Canonical section order** (from `generate_catalog`, update-list.sh:2220-2480):
Installed Mac Software List → Homebrew Packages → App Store Applications → Setapp Applications →
Web-installed Applications → Claude Code Plugins → Claude Code MCP Servers →
Claude Code Skills & Agents → Codex MCP Servers → OpenCode Plugins → OpenCode MCP Servers →
OpenCode Agents → Gemini CLI Extensions → Gemini CLI MCP Servers → VS Code Extensions →
Cursor Extensions → Google Chrome Extensions → Firefox Extensions.

Requirements: CAT-01 (all collectors re-implemented), CAT-05 (no secrets — MCP entries emit name +
transport only, never env/headers/args/command/url), CAT-06 (graceful degradation — absent source
writes `(none found)`/fallback and never aborts).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — this is a byte-parity port with no
user-facing design freedom. The zsh collector functions ARE the spec (cited line numbers above);
replicate their discovery method, parsing, fallback messages, and output format exactly. Use the
Phase 13 output-format + name-resolution layer. Collector module organization (one module per
source, or a `Collector` ABC + registry as the prior research recommends) is at Claude's discretion
— prefer the research-recommended structure if it eases the byte-parity tests and the Phase-16
section-order registry.

Hard non-negotiables (from requirements + the existing zsh behavior):
- **CAT-05 (secrets):** MCP-server collectors emit name + transport ONLY — NEVER env, headers,
  args, command, or url. This is the single most important safety invariant of the phase.
- **CAT-06 (degradation):** every optional source checks availability (`command -v` / path exists)
  and writes the zsh-exact fallback (`(none found)` or the specific message) — never aborts the run.
- **CAT-03 (sort, from Phase 13):** ordering goes through `LC_ALL=C sort -f -u` (and `sort -V` for
  Chrome version-directory selection) — never Python `sorted()`.
- **Section order** must match `generate_catalog` exactly (success criterion 4).
- Prefer a tool's own CLI for discovery where one exists (`code --list-extensions`,
  `gemini extensions list`, etc.) and fall back to parsing on-disk config/manifests where no CLI
  exists — mirror whatever the zsh function actually does for each source.

</decisions>

<code_context>
## Existing Code Insights

### Reference Implementation (zsh — untouched parity source, update-list.sh)
- Mac apps / Homebrew / App Store / Setapp / Web: in `generate_catalog` (:2220-2480).
- AI CLIs: `collect_claude_plugins`/`_mcp`/`_skills_agents` (:1594/:1638/:1692),
  `collect_codex_mcp` (:1748), `collect_opencode_plugins`/`_mcp`/`_agents` (:1802/:1861/:1930),
  `collect_gemini_extensions`/`_mcp` (:1970/:2016).
- Editors: `collect_vscode_extensions` (:1387), `collect_cursor_extensions` (:1494).
- Browsers: `collect_chrome_extensions` (:2074), `collect_firefox_extensions` (:2154).
- Name resolution helpers: `chrome_ext_name` (:1148) and the VS Code `%nls%` logic — already
  ported to `src/maccat/helpers/chrome_name.py` + `vsc_name.py` in Phase 13.

### Built in prior phases (reuse — do NOT re-implement)
- Phase 13: `src/maccat/catalog/format.py` (`emit_item`, `flush_section`, `version_sort_tail`),
  `catalog/writer.py` (`CatalogWriter`), `helpers/json_io.py`, `helpers/chrome_name.py`,
  `helpers/vsc_name.py`.
- Phase 14: `src/maccat/{naming,retention,identity,config}.py`.

### Research (`.planning/research/`)
- ARCHITECTURE.md / FEATURES.md / PITFALLS.md detail per-tool discovery methods, the `Collector`
  ABC + registry pattern, and browser-extension name extraction pitfalls. NOTE stale names
  (mac-catalog/maclist) → translate to `maccat`.

### Integration Points
- Phase 16 wires a section-order REGISTRY (success criterion 4) and the end-to-end generate run.
- Phase 17 golden-parity tests assert each collector's section body byte-for-byte vs the zsh output.

</code_context>

<specifics>
## Specific Ideas

- The single biggest risk is CAT-05 (secret leakage). Every MCP collector must be tested to prove
  it emits name + transport only — success criterion 3 greps the full output for `token`, `Bearer`,
  `sk-`, `ghp_`, `key=`, `Authorization` and must return zero hits.
- Collectors that shell out (`brew`, `mas`, `code --list-extensions`) must use `shell=False`
  subprocess calls and degrade on non-zero exit / missing binary exactly like the zsh `command -v`
  guards. Tests should monkeypatch/mock these so they run on any machine (including CI without the
  tools installed).
- Chrome/Firefox collectors must cover ALL profiles, exclude component extensions, and resolve
  localized names — mirror the zsh logic exactly (Phase 13 helpers already handle name resolution).

</specifics>

<deferred>
## Deferred Ideas

- The end-to-end run orchestration + section-order registry wiring + git — Phase 16.
- Golden-output byte-parity fixtures/tests — Phase 17 (this phase adds per-collector unit tests
  with mocked sources; the full golden parity suite is Phase 17).
- New collectors beyond current parity (Safari/Edge/Brave/Zed; CHR-02/FF-02 enabled-state;
  CDX-02 Codex plugins) — out of scope (future milestone).

</deferred>

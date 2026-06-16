# Phase 3: AI-CLI Collectors - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds plain-text catalog sections to `update-list.sh` for the **plugins, MCP servers,
and skills/agents** of four AI coding CLIs — Claude Code, Codex, OpenCode, Gemini — using the
Phase 1 helpers (`json_get`, `emit_item`, `flush_section`). It covers CC-01, CC-02, CC-03,
CDX-01, OC-01, OC-02, OC-03, GEM-01, GEM-02, and the cross-cutting FMT-03 (secret exclusion).

The defining constraint is **FMT-03**: the catalog is git-committed and pushed, so MCP server
entries capture **name + transport-type only** — never env values, headers, tokens, args,
commands, or auth-bearing URL components. This is the single milestone-failing defect risk.

Collectors are DEFINED and self-testable but NOT wired into `generate_catalog` (Phase 5 wires
them). No editor or browser work here. Codex plugins/skills are explicitly out of scope (the
installed Codex has no plugin system — MCP-only; tracked as v2 CDX-02).
</domain>

<decisions>
## Implementation Decisions

### FMT-03 Secret Boundary (milestone-critical — USER LOCKED: strictest)
- An MCP entry emits **`name [transport]` only**, where transport is the type (`stdio` / `http` /
  `sse`) read from the config's `type` field (or inferred: presence of `command` ⇒ stdio,
  presence of `url` ⇒ http/sse).
- **NEVER emitted, for any MCP server, any tool:** `env`, `headers`, `args`, `command`,
  `url` (including host, query string, and userinfo), tokens, or any auth-bearing value.
- For http/sse servers, emit the transport label only — never the URL itself (URLs can carry
  auth in query/userinfo).
- MCP lines have no version → `emit_item "$name" "" "$transport"` → renders `name [transport]`.
- This boundary makes the Phase 5 secret-leakage gate pass by construction (grepping the output
  for `http`, `token`, `Bearer`, `key=`, `Authorization`, `sk-`, `ghp_` must return zero hits).

### Capture Scope (USER LOCKED: user/global only)
- Capture **user/global-level configs only**:
  - Claude Code MCP: `~/.claude.json` top-level `mcpServers`.
  - OpenCode MCP: `~/.config/opencode/opencode.json` `.mcp`.
  - Gemini MCP: `~/.gemini/settings.json` (location TBD — see research flag; top-level
    `mcpServers` is absent on this machine).
  - Codex MCP: prefer `codex mcp list --json` (CLI, per success criterion); fall back to
    parsing `~/.codex/config.toml` `[mcp_servers.*]` sections (TOML, not JSON).
- **Do NOT** scan per-project `mcpServers` (e.g. `~/.claude.json` `projects.<path>.mcpServers`)
  or project-local `.mcp.json` files — those are project state, not machine tooling state, and
  multiply the secret-exposure surface.
- A tool that is installed but has zero MCP servers / plugins / skills → its section is still
  written with `(none found)` (via `flush_section`'s empty path) and the run continues.

### Plugins / Skills / Agents Enumeration & Versioning (USER LOCKED: accept all)
- **Claude Code plugins (CC-01):** read `~/.claude/plugins/installed_plugins.json`
  (name + version + marketplace/id where available).
- **Claude Code skills & agents (CC-03):** enumerate the `~/.claude/skills/` directory (one
  dir per skill; name from the skill dir name and/or its `SKILL.md`) and `~/.claude/agents/`
  (`.md` files; name from filename/frontmatter).
- **OpenCode plugins (OC-01):** `~/.config/opencode/opencode.json` `.plugin`.
- **OpenCode agents (OC-03):** enumerate the `~/.config/opencode/agents/` directory (NOT the
  JSON `.agent` key, which is absent on this machine).
- **Gemini extensions (GEM-01):** enumerate `~/.gemini/extensions/` (one dir per extension;
  name + version from each extension's manifest — see research flag).
- **Versioning:** many skills/agents/plugins have no version → emit `name` (FMT-01 degrades
  cleanly: `name [id]` when an id exists, bare `name` otherwise). Never synthesize a version.

### Section Organization & Degradation (USER LOCKED: accept all)
- One section per (tool × concern), names matching the ROADMAP success criteria:
  - "Claude Code Plugins", "Claude Code MCP Servers", "Claude Code Skills & Agents"
  - "Codex MCP Servers"
  - "OpenCode Plugins", "OpenCode MCP Servers", "OpenCode Agents"
  - "Gemini CLI Extensions", "Gemini CLI MCP Servers"
- A tool not installed (no config dir / no CLI) → its section(s) still written with
  `(none found)`, run continues (FMT-02 graceful degradation).
- Identity for skills/agents: name, plus an id (slug/dir name) when meaningfully distinct.
- Everything routed through `emit_item` → `flush_section` (`LC_ALL=C sort -f -u`) for
  deterministic, stably-sorted output (FMT-04).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Phases 1–2)
- `json_get <file> <key>` (jq→plutil→grep, nested dotted keys, empty-key guarded, empty on miss).
- `emit_item <name> <version> <id>` (FMT-01 builder with dedup-suppression + full degradation).
- `flush_section` (buffers `_section_lines`, `LC_ALL=C sort -f -u`, `(none found)` when empty, resets).
- `write_section "$title"` (update-list.sh:254).
- Phase 2 collectors show the established pattern: `write_section` → `_section_lines=()` →
  loop over a JSON array (`while IFS= read -r`) → `emit_item` per item → `flush_section`.

### Established Patterns
- `local`-scoped vars; `[[ ]]`; `command -v` probing; double-quoted expansions; `return` (not
  `exit`) on non-fatal; null-glob guard (`[[ -e "$f" ]] || continue`) in glob/dir loops;
  `2>/dev/null` for noisy stderr; append catalog data to `OUTPUT_FILE`.

### Integration Points
- New collector functions defined alongside the existing helpers/collectors; NOT called from
  `generate_catalog` yet (Phase 5).
</code_context>

<specifics>
## Specific Ideas (verification grounding — THIS machine)

All four CLIs are installed (`claude`, `codex`, `opencode`, `gemini` on PATH), so the collectors
can be verified live. Observed config reality (drives research):
- **Claude:** `~/.claude.json` `mcpServers` has 1 server (`execbro`) with fields
  `args/command/env/type` — `env` is the secret-bearing field; `type` is the transport.
  Plugins in `~/.claude/plugins/installed_plugins.json` (`{plugins, version}` shape). Skills in
  `~/.claude/skills/`, agents in `~/.claude/agents/`.
- **Codex:** `~/.codex/config.toml` has NO `[mcp_servers]` section currently, and
  `codex mcp list --json` returned empty/failed → expect `(none found)`. Verify the exact CLI
  invocation and TOML fallback shape.
- **OpenCode:** `opencode.json` keys are `$schema, model, permission, plugin` — `.mcp` and
  `.agent` are ABSENT. Agents live in `~/.config/opencode/agents/` dir → expect MCP `(none found)`.
- **Gemini:** `settings.json` keys are `experimental, general, hooks, ide, security, statusLine,
  ui` — NO top-level `mcpServers`. Extensions in `~/.gemini/extensions/` (e.g. `conductor` dir +
  `extension-enablement.json`) → expect MCP location TBD / `(none found)`.
- FMT-03 must be proven with a real secret-bearing entry: the `execbro` server's `env` must NOT
  appear in output, only `execbro [stdio]`.
</specifics>

<deferred>
## Deferred Ideas
- Wiring collectors into `generate_catalog` — Phase 5.
- Codex plugins/skills — out of scope (no plugin system in installed Codex; v2 CDX-02).
- MCP enabled/disabled state — out of scope.
- Per-project MCP configs and project `.mcp.json` — deliberately excluded (scope + secrets).
</deferred>

<research_flags>
## Open Questions for Research (heavy on-disk discovery required — ROADMAP paths are partly wrong)
1. **Claude MCP transport derivation:** `mcpServers.<name>` has `type` (stdio/http/sse?) +
   `command`/`args`/`env` (stdio) or `url`/`headers` (http/sse). Confirm the exact field set per
   transport and the safe extraction (name + transport ONLY). Confirm `installed_plugins.json`
   shape for plugin name/version/id. Confirm skill identity source (`SKILL.md` frontmatter `name`
   vs dir name) and agent identity (`~/.claude/agents/*.md` frontmatter `name`/`description`).
2. **Codex MCP:** does `codex mcp list --json` work in the installed version? If not, what does
   `codex mcp list` output, and what is the `~/.codex/config.toml` `[mcp_servers.<name>]` TOML
   shape? Provide a dependency-free way to extract MCP server NAMES from TOML (grep for
   `[mcp_servers.<name>]` headers) without leaking values — json_get/plutil do NOT parse TOML.
3. **OpenCode:** confirm `.mcp` and `.plugin` shapes in `opencode.json` (both may be absent →
   (none found)). Confirm agents are enumerated from `~/.config/opencode/agents/` (files vs dirs;
   name source — frontmatter or filename).
4. **Gemini:** WHERE are MCP servers configured (not top-level `settings.json.mcpServers` here)?
   Check `~/.gemini/extensions/<ext>/gemini-extension.json` (extensions can declare mcpServers),
   and any other settings location. Confirm extension name+version source
   (`~/.gemini/extensions/<ext>/gemini-extension.json` manifest) and how `extension-enablement.json`
   relates. GEM-02 may resolve to per-extension MCP servers or `(none found)`.
5. **FMT-03 cross-source field map:** produce a definitive table — for each of the 4 tools' MCP
   sources, list which fields are SAFE (name, transport/type) and which are SECRET-BEARING
   (env, headers, args, command, url) so the collector never reads/emits a secret field.
6. **Determinism + Zsh dir iteration:** safe null-glob-guarded iteration of skills/agents/
   extensions directories; stable sort; spaces in names.
</research_flags>

---
phase: 03-ai-cli-collectors
plan: "01"
subsystem: update-list.sh
tags: [claude-code, plugins, mcp, skills, agents, fmt-03, security]
dependency_graph:
  requires: [02-01-SUMMARY.md]
  provides: [collect_claude_plugins, collect_claude_mcp, collect_claude_skills_agents]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [emit_item→flush_section collector, null_glob guard, FMT-03 safe extraction]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - FMT-03 jq expression reads only .key and .value.type from .mcpServers — never .env/.command/.args/.url/.headers
  - Transport label clamped to stdio|http|sse via case statement (ASVS V5)
  - Skills and agents share one combined section, sorted together by flush_section
  - Collectors defined but NOT called from generate_catalog (Phase 5 wires them)
metrics:
  duration_seconds: 143
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_modified: 1
---

# Phase 03 Plan 01: Claude Code Collectors (CC-01, CC-02, CC-03) Summary

## One-liner

Three Claude Code collector functions for plugins (name+version+ID via installed_plugins.json), MCP servers (name+transport only, FMT-03 safe), and skills/agents (bare names via SKILL.md/frontmatter enumeration).

## What Was Built

Three new Zsh collector functions inserted in `update-list.sh` after `collect_cursor_extensions` (line 762) and before `generate_catalog`:

| Function | Requirement | Source | Output Format |
|----------|-------------|--------|---------------|
| `collect_claude_plugins` | CC-01 | `~/.claude/plugins/installed_plugins.json` | `name (version) [name@marketplace]` |
| `collect_claude_mcp` | CC-02 + FMT-03 | `~/.claude.json` `.mcpServers` | `name [transport]` |
| `collect_claude_skills_agents` | CC-03 | `~/.claude/skills/*/` + `~/.claude/agents/*.md` | `name` (bare) |

All three follow the established Phase 2 pattern: `write_section` → `_section_lines=()` → enumerate → `emit_item` → `flush_section`.

## Task Results

### Task 1: collect_claude_plugins (CC-01)

- **Commit:** c7de07c
- **Files:** update-list.sh (+43 lines)
- **Implementation:**
  - jq path: `.plugins | to_entries[] | .key + "\t" + (.value[0].version // "")`
  - Name: `${key%%@*}` (strips `@marketplace` suffix per Pitfall 2)
  - ID: full key (`name@marketplace`)
  - plutil fallback: xml1 key enumeration + `plutil -extract "plugins.${key}.0.version" raw`
  - Graceful degradation: absent/malformed file → `flush_section` writes `(none found)`
- **Live result:** 9 plugins emitted

### Task 2: collect_claude_mcp (CC-02 + FMT-03)

- **Commit:** 8a9de4c
- **Files:** update-list.sh (+55 lines)
- **Implementation:**
  - jq path: `.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")`
  - NEVER reads `.value.env`, `.value.command`, `.value.args`, `.value.url`, `.value.headers`
  - Transport clamped: `case "$transport" in stdio|http|sse) : ;; *) transport="stdio" ;; esac`
  - plutil fallback: `plutil -extract "mcpServers" raw` for names, then `plutil -extract "mcpServers.${name}.type" raw` per server
- **FMT-03 proof:** `execbro [stdio]` — zero hits on `http|token|Bearer|key=|Authorization|sk-|ghp_`

### Task 3: collect_claude_skills_agents (CC-03)

- **Commit:** 7d1d505
- **Files:** update-list.sh (+49 lines)
- **Implementation:**
  - Skills: `setopt local_options null_glob` + `for skill_dir in "$skills_dir"/*/;` — `[[ -e "$skill_dir" ]] || continue`
  - Name: `grep '^name:' SKILL.md | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'`
  - Agents: `for f in "$agents_dir"/*.md;` — same frontmatter extraction
  - Both feeds same `_section_lines` buffer, sorted together by `flush_section`
  - `tr -d '"'` handles quoted `name: "value"` form (Pitfall 6)
- **Live result:** 70 skills + 33 agents = 103 combined entries

## Verification Results

| Check | Result |
|-------|--------|
| `zsh -n update-list.sh` | PASS |
| All three functions defined | PASS |
| `collect_claude_plugins` grep count = 1 | PASS |
| `collect_claude_mcp` grep count = 1 | PASS |
| `collect_claude_skills_agents` grep count = 1 | PASS |
| jq expression reads only `.key` + `.value.type` | PASS |
| No `.value.env/.command/.args/.url/.headers` in code | PASS |
| FMT-03: `execbro [stdio]` in live MCP output | PASS |
| FMT-03: zero secret pattern hits on MCP output | PASS (0 hits) |
| Plugin count = 9 | PASS |
| Skills count = 70 | PASS |
| Agents count = 33 | PASS |
| `generate_catalog` does NOT call new collectors | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **FMT-03 jq expression form:** `.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")` — tab-separated pair with tab read via `IFS=$'\t'` to keep name and transport distinct. This matches the exact pattern from 03-RESEARCH.md verified extraction.

2. **Transport clamping in both paths:** Applied `case` statement in both jq and plutil paths for consistent behavior — not just the primary path.

3. **`_section_lines=()` defensive reset:** Present at top of every collector as per the established contract, regardless of whether a prior collector may have left buffer state.

## Known Stubs

None. All three collectors are fully implemented. No hardcoded values or placeholders. The collectors produce real data on this machine from live files.

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns beyond those documented in the plan's threat model. The collectors read only local config files and emit only safe fields.

## Self-Check: PASSED

Files exist:
- update-list.sh: FOUND (modified with 3 new functions)

Commits exist:
- c7de07c: FOUND (collect_claude_plugins)
- 8a9de4c: FOUND (collect_claude_mcp)
- 7d1d505: FOUND (collect_claude_skills_agents)

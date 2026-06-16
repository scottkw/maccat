---
phase: 03-ai-cli-collectors
plan: "02"
subsystem: update-list.sh
tags: [codex, opencode, mcp, plugins, agents, fmt-03, security]
dependency_graph:
  requires: [03-01-SUMMARY.md]
  provides: [collect_codex_mcp, collect_opencode_plugins, collect_opencode_mcp, collect_opencode_agents]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [emit_item→flush_section collector, CLI-first with TOML fallback, null_glob guard, FMT-03 safe extraction]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - collect_codex_mcp prefers CLI (codex mcp list --json); TOML fallback reads section headers only
  - TOML fallback defaults transport to stdio (CLI is canonical; no value lines read)
  - collect_opencode_plugins uses ${entry%%@*} to strip git URL suffix (Pitfall 3 guard)
  - collect_opencode_mcp checks .mcp // empty null-check before iterating
  - collect_opencode_agents uses setopt local_options null_glob + [[ -e ]] guard
  - Collectors defined but NOT called from generate_catalog (Phase 5 wires them)
metrics:
  duration_seconds: 350
  completed_date: "2026-06-13"
  tasks_completed: 2
  files_modified: 1
---

# Phase 03 Plan 02: Codex MCP + OpenCode Collectors (CDX-01, OC-01, OC-02, OC-03) Summary

## One-liner

Four new Zsh collector functions for Codex MCP (CLI-first with TOML fallback) and OpenCode plugins/MCP/agents, all FMT-03 compliant and producing correct live output on this machine.

## What Was Built

Four new Zsh collector functions inserted in `update-list.sh` after `collect_claude_skills_agents` and before `generate_catalog`:

| Function | Requirement | Source | Output Format |
|----------|-------------|--------|---------------|
| `collect_codex_mcp` | CDX-01 | `codex mcp list --json` or `~/.codex/config.toml` | `name [transport]` |
| `collect_opencode_plugins` | OC-01 | `~/.config/opencode/opencode.json` `.plugin[]?` | `name` (bare) |
| `collect_opencode_mcp` | OC-02 + FMT-03 | `~/.config/opencode/opencode.json` `.mcp` | `name [transport]` |
| `collect_opencode_agents` | OC-03 | `~/.config/opencode/agents/*.md` | `name` (bare) |

All four follow the established Phase 2/03-01 pattern: `write_section` → `_section_lines=()` → enumerate → `emit_item` → `flush_section`.

## Task Results

### Task 1: collect_codex_mcp (CDX-01)

- **Commit:** 72e44fb
- **Files:** update-list.sh (+57 lines)
- **Implementation:**
  - Primary path: `codex mcp list --json` → jq `.[] | .name + "\t" + (.type // "stdio")`
  - Falls through to TOML on empty `[]` output (no servers configured on this machine)
  - TOML fallback: `grep '^\[mcp_servers\.' | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' | tr -d '"'`
    reads ONLY section header names; value lines never touched (FMT-03)
  - Transport clamped to `stdio|http|sse` whitelist via `case` statement
  - Default transport `stdio` in TOML fallback (CLI is canonical source)
- **Live result:** `(none found)` — `codex mcp list --json` returns `[]` on this machine

### Task 2: collect_opencode_plugins, collect_opencode_mcp, collect_opencode_agents (OC-01/02/03)

- **Commit:** 9468bbf
- **Files:** update-list.sh (+151 lines)
- **collect_opencode_plugins implementation:**
  - jq path: `jq -r '.plugin[]?'` — `?` handles null field silently
  - Name extraction: `name="${entry%%@*}"` strips `@git+https://...` suffix (Pitfall 3 guard)
  - plutil fallback: index loop `plutil -extract "plugin.${idx}" raw`
  - Live result: `superpowers` (1 plugin)
- **collect_opencode_mcp implementation:**
  - Null check: `jq -r '.mcp // empty'` — if empty output → `flush_section` + return
  - FMT-03 path (future): `jq -r '.mcp | to_entries[] | .key + "\t" + (.value.type // "stdio")'`
    reads ONLY `.key` (server name) + `.value.type` (transport); never `.command/.env/.args/.url/.headers`
  - plutil fallback: `plutil -extract "mcp" raw` null check + server enumeration
  - Transport clamped to `stdio|http|sse` whitelist
  - Live result: `(none found)` — `.mcp` is null in opencode.json on this machine
- **collect_opencode_agents implementation:**
  - `setopt local_options null_glob` + `[[ -e "$f" ]] || continue` null-glob guard
  - Name: `grep '^name:' "$f" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'`
  - Fallback: `basename "$f" .md`
  - Live result: 33 agent names from `~/.config/opencode/agents/*.md`

## Verification Results

| Check | Result |
|-------|--------|
| `zsh -n update-list.sh` | PASS |
| `collect_codex_mcp` defined (count=1) | PASS |
| `collect_opencode_plugins` defined (count=1) | PASS |
| `collect_opencode_mcp` defined (count=1) | PASS |
| `collect_opencode_agents` defined (count=1) | PASS |
| FMT-03: no `.env/.command/.args/.url/.headers` reads | PASS (0 hits) |
| `generate_catalog` does NOT call new collectors | PASS |
| Live Codex MCP: `(none found)` | PASS |
| Live OpenCode Plugins: `superpowers` | PASS |
| Live OpenCode MCP: `(none found)` | PASS |
| Live OpenCode Agents: 33 files with `name:` frontmatter | PASS |
| `${entry%%@*}` Pitfall 3 guard present | PASS |
| `null_glob` + `[[ -e ]]` guard in agents | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **TOML fallback transport default:** `stdio` is used for all TOML-fallback MCP servers. This is correct because (a) the CLI is the canonical source and it works, (b) the TOML fallback is only reached when CLI is unavailable, (c) reading `type` value lines from TOML adds risk of accidentally reading adjacent secret value lines — section headers only is simpler and safer.

2. **`_section_lines=()` defensive reset:** Present at top of every collector as per the established contract.

3. **`jq -r '.mcp // empty'` null-check pattern:** Used in `collect_opencode_mcp` to detect null `.mcp` field cleanly — `// empty` produces no output on null, which `[[ -z "..." ]]` catches reliably.

## Known Stubs

None. All four collectors are fully implemented. No hardcoded values or placeholders. The collectors produce real data on this machine from live files.

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns beyond those documented in the plan's threat model.

- T-03-04 (Codex TOML secret disclosure): MITIGATED — `grep` reads only `[mcp_servers.*]` section headers; `sed` extracts only the name portion; no value lines read.
- T-03-05 (Codex CLI JSON secret disclosure): MITIGATED — `jq` reads only `.name` and `.type`; transport clamped to whitelist; never reads `.command/.env/.args/.url/.headers`.
- T-03-06 (OpenCode MCP populated): MITIGATED — `to_entries[] | .key + "\t" + (.value.type // "stdio")` reads only key and type; currently null so `(none found)` is the output.
- T-03-07 (OpenCode plugin git URL): ACCEPTED — `${entry%%@*}` strips everything from first `@` onward; URL never emitted.

## Self-Check: PASSED

Files exist:
- update-list.sh: FOUND (modified with 4 new functions)

Commits exist:
- 72e44fb: FOUND (collect_codex_mcp)
- 9468bbf: FOUND (collect_opencode_plugins + collect_opencode_mcp + collect_opencode_agents)

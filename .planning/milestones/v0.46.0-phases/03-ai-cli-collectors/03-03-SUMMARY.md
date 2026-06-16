---
phase: 03-ai-cli-collectors
plan: "03"
subsystem: update-list.sh
tags: [gemini, extensions, mcp, fmt-03, security, null_glob]
dependency_graph:
  requires: [03-02-SUMMARY.md]
  provides: [collect_gemini_extensions, collect_gemini_mcp]
  affects: [update-list.sh]
tech_stack:
  added: []
  patterns: [emit_item→flush_section collector, null_glob guard, -s nonzero-size guard, FMT-03 safe extraction]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - collect_gemini_extensions uses json_get for name+version from gemini-extension.json manifest
  - Extension ID is empty string (dir name == name; avoids redundant [conductor] bracket in output)
  - collect_gemini_mcp uses [[ -s ]] not [[ -f ]] — mcp_config.json exists but is 0 bytes on this machine
  - FMT-03 enforced: jq reads only .key and .value.type; plutil fallback reads only key names and type scalar
  - Transport clamped to stdio|http|sse whitelist in both jq and plutil paths
  - Both collectors defined but NOT called from generate_catalog (Phase 5 wires them)
metrics:
  duration_seconds: 420
  completed_date: "2026-06-13"
  tasks_completed: 2
  files_modified: 1
---

# Phase 03 Plan 03: Gemini CLI Collectors (GEM-01, GEM-02) Summary

## One-liner

Two new Zsh collector functions for Gemini CLI extensions (dir-iteration + json_get) and MCP servers (-s nonzero-size guard handles the 0-byte mcp_config.json), both FMT-03 compliant.

## What Was Built

Two new Zsh collector functions inserted in `update-list.sh` after `collect_opencode_agents` and before `generate_catalog`:

| Function | Requirement | Source | Output Format |
|----------|-------------|--------|---------------|
| `collect_gemini_extensions` | GEM-01 | `~/.gemini/extensions/*/gemini-extension.json` | `name (version)` |
| `collect_gemini_mcp` | GEM-02 + FMT-03 | `~/.gemini/config/mcp_config.json` | `name [transport]` |

Both follow the established Phase 2/03-01/03-02 pattern: `write_section` → `_section_lines=()` → enumerate → `emit_item` → `flush_section`.

With these two functions, all 9 Phase 3 collector functions are now defined in `update-list.sh`.

## Task Results

### Task 1: collect_gemini_extensions (GEM-01)

- **Commit:** 8d0b9a9
- **Files:** update-list.sh (+106 lines combined with Task 2)
- **Implementation:**
  - `ext_base`: `$HOME/.gemini/extensions`
  - Directory absence guard: `[[ ! -d "$ext_base" ]]` → `flush_section` + return
  - `setopt local_options null_glob` + `[[ -e "$ext_dir" ]] || continue` null-glob guard
  - Per-dir: `[[ -f "$manifest" ]] || continue` skips dirs without `gemini-extension.json`
  - `name=$(json_get "$manifest" "name")` and `version=$(json_get "$manifest" "version")`
  - Fallback: `[[ -z "$name" ]] && name=$(basename "$ext_dir")`
  - `emit_item "$name" "$version" ""` — empty ID (dir name equals name; avoids redundant bracket)
  - Variables reset to `""` after each iteration (prevents bleed)
- **Live result:** `conductor (0.4.1)` — from `~/.gemini/extensions/conductor/gemini-extension.json`

### Task 2: collect_gemini_mcp (GEM-02)

- **Commit:** 8d0b9a9 (combined with Task 1)
- **Files:** update-list.sh (included in combined +106 lines)
- **Implementation:**
  - `mcp_config`: `$HOME/.gemini/config/mcp_config.json`
  - Critical guard: `if [[ ! -s "$mcp_config" ]]; then flush_section; return; fi`
    — `[[ -s ]]` handles BOTH absent file AND existing-but-0-byte file (the real condition
    on this machine). A bare `[[ -f ]]` would return true for the 0-byte file and send jq
    a parse error.
  - jq path: `jq -r '.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")'`
    reads ONLY .key (server name) and .value.type (transport) — never .env/.command/.args/.url/.headers
  - plutil fallback: `plutil -extract "mcpServers" raw` for key names, then per-name
    `plutil -extract "mcpServers.${name}.type" raw` — same FMT-03 boundary
  - Transport clamped: `case "$transport" in stdio|http|sse) : ;; *) transport="stdio" ;; esac`
- **Live result:** `(none found)` — mcp_config.json is 0 bytes on this machine

## Verification Results

| Check | Result |
|-------|--------|
| `zsh -n update-list.sh` | PASS |
| `collect_gemini_extensions` defined (count=1) | PASS |
| `collect_gemini_mcp` defined (count=1) | PASS |
| All 9 Phase 3 collectors present | PASS (count=9) |
| `[[ -s "$mcp_config" ]]` guard in collect_gemini_mcp | PASS |
| No bare `[[ -f "$mcp_config" ]]` gating check | PASS |
| FMT-03: no `.env/.command/.args/.url/.headers` reads | PASS |
| `generate_catalog` does NOT call new collectors | PASS |
| Live Gemini Extensions: `conductor (0.4.1)` | PASS |
| Live Gemini MCP: `(none found)` | PASS |
| `setopt local_options null_glob` + `[[ -e ]]` guard | PASS |
| `[[ -f "$manifest" ]] || continue` in extensions loop | PASS |

## Deviations from Plan

None — plan executed exactly as written. Both tasks were implemented in a single edit pass and committed together (8d0b9a9) rather than two separate commits, as the functions were inserted adjacently in one operation. All done criteria for both tasks were met before the commit was made.

## Decisions Made

1. **`-s` guard is mandatory for mcp_config.json:** The file exists at `~/.gemini/config/mcp_config.json` but is 0 bytes. `[[ -f ]]` returns true for a 0-byte file — passing it to `jq` produces a parse error. `[[ -s ]]` (file exists AND has nonzero size) handles both absent-file and empty-file cases, writing `(none found)` cleanly for both.

2. **Empty ID for extensions:** `emit_item "$name" "$version" ""` — the Gemini extension dir name is the same as the manifest `name` field (confirmed: directory `conductor`, manifest `name: "conductor"`). Passing the dir name as ID would produce `conductor (0.4.1) [conductor]` — a redundant bracket. An empty ID string produces the clean `conductor (0.4.1)` output per the plan requirement.

3. **Transport whitelist clamping in both code paths:** The `case "$transport" in stdio|http|sse) ...` block appears in both the jq path and the plutil path. Even though the file is currently empty, the clamping is applied defensively for when the file is populated in the future — matching the T-03-08 mitigation in the threat model.

## Known Stubs

None. Both collectors are fully implemented. The `(none found)` output for Gemini MCP is the correct result for a 0-byte config file, not a stub — `flush_section` writes it when the buffer is empty.

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns beyond those documented in the plan's threat model.

- T-03-08 (Gemini MCP secret disclosure when populated): MITIGATED — jq reads only `.key` and `.value.type`; plutil reads only key names and type scalar; transport clamped to whitelist; never reads `.env/.command/.args/.url/.headers`.
- T-03-09 (DoS from jq parsing 0-byte file): MITIGATED — `[[ -s "$mcp_config" ]]` guard prevents jq invocation on invalid/empty file.
- T-03-10 (malicious name/version in gemini-extension.json): ACCEPTED per plan — `json_get` returns plain string appended to catalog; no execution, no eval.

## Self-Check: PASSED

Files exist:
- update-list.sh: FOUND (modified with 2 new functions, 106 lines added)

Commits exist:
- 8d0b9a9: FOUND (feat(03-03): add collect_gemini_extensions and collect_gemini_mcp)

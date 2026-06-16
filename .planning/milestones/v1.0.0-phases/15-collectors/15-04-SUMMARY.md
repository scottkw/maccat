---
phase: 15-collectors
plan: 04
subsystem: collectors
tags: [python, claude, mcp, plugins, skills, agents, cat-05, security]

# Dependency graph
requires:
  - phase: 15-01
    provides: base.py Collector/CollectorResult/Section ABC
  - phase: 13
    provides: emit_item/flush_section format layer

provides:
  - ClaudeCollector with 3 sections (Claude Code Plugins, Claude Code MCP Servers, Claude Code Skills & Agents)
  - _read_yaml_name() module-level helper for YAML frontmatter name extraction
  - CAT-05 MCP transport-only safety pattern with _TRANSPORT_WHITELIST
  - 31 unit tests covering all three sub-collectors including CAT-05 secret-grep regression

affects: [15-05, 15-06, 15-07, 15-08, 17-parity-safety-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CAT-05: MCP collectors read ONLY .type field; _TRANSPORT_WHITELIST = frozenset({stdio,http,sse})"
    - "Module-level path constants (not class attrs) enable patch.object(module, name) monkeypatching"
    - "_read_yaml_name() helper: first 'name:' line, strip prefix + whitespace + double-quotes, OSError->empty"
    - "3-section collector: collect() returns CollectorResult(sections=[...]) with all raw=False"

key-files:
  created:
    - src/maccat/collectors/claude.py
    - tests/collectors/test_claude.py
  modified: []

key-decisions:
  - "Module-level constants (_PLUGINS_PATH, _CLAUDE_JSON, _SKILLS_DIR, _AGENTS_DIR) not class attributes — easier to monkeypatch in tests"
  - "_read_yaml_name() is a module-level function, not a method — available for reuse by later collectors (OpenCode, Gemini)"
  - "CAT-05: exactly one cfg.get() call in _collect_mcp() — only reads 'type' field; all other fields ignored by design"

patterns-established:
  - "Pattern: CAT-05 MCP safety — transport = cfg.get('type', 'stdio') clamped via _TRANSPORT_WHITELIST"
  - "Pattern: filesystem-fixture tests — redirect module-level paths via patch.object(claude_mod, '_PATH', tmp_path/...)"
  - "Pattern: SECRET_PATTERN regex grep over section output as regression guard for CAT-05"

requirements-completed: [CAT-01, CAT-05, CAT-06]

# Metrics
duration: 3min
completed: 2026-06-15
---

# Phase 15 Plan 04: ClaudeCollector Summary

**ClaudeCollector implementing 3 JSON/filesystem-parsed sections (Plugins, MCP Servers, Skills & Agents) with CAT-05 transport-only MCP safety and YAML frontmatter name extraction**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-15T00:46:22Z
- **Completed:** 2026-06-15T00:49:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ClaudeCollector returns 3 sections in fixed order; all raw=False (go through flush_section)
- CAT-05 enforced: _collect_mcp() contains exactly one cfg.get() call (for "type"); _TRANSPORT_WHITELIST clamps unknown values to "stdio"
- _read_yaml_name() module-level helper extracts YAML frontmatter name from SKILL.md / agent .md files; handles OSError, empty file, missing name: line, quoted values
- 31 tests pass; test_mcp_never_emits_secrets fixture contains command/args/env secrets and asserts SECRET_PATTERN regex finds 0 hits in section output

## Task Commits

Each task was committed atomically:

1. **Task 1: ClaudeCollector (plugins + MCP + skills/agents, CAT-05)** - `93e8547` (feat)
2. **Task 2: Unit tests for ClaudeCollector including CAT-05 MCP secret-grep** - `deaced4` (test)

## Files Created/Modified
- `src/maccat/collectors/claude.py` - ClaudeCollector with _collect_plugins(), _collect_mcp(), _collect_skills_agents(); module-level path constants and _TRANSPORT_WHITELIST
- `tests/collectors/test_claude.py` - 31 tests across TestClaudePlugins, TestClaudeMCP, TestClaudeSkillsAgents, TestReadYamlName, TestClaudeCollectorIntegration

## Decisions Made
- Module-level constants (not class attributes) for all paths so tests can use `patch.object(claude_mod, "_PLUGINS_PATH", tmp_path / "...")` without class-attribute lookup complexity
- `_read_yaml_name()` defined at module level (not a method) so it can be reused by future collectors without inheriting from ClaudeCollector
- CAT-05 pattern: the only `cfg.get()` call in `_collect_mcp()` is `cfg.get("type", "stdio")` — all other fields (command, env, args, url, headers) are structurally unreachable

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns beyond what the plan's threat model already covers. All file reads are via Path.read_text() on user-owned config files.

## Known Stubs

None - all three sub-collectors fully implemented.

## Self-Check: PASSED

Files exist:
- FOUND: src/maccat/collectors/claude.py
- FOUND: tests/collectors/test_claude.py

Commits exist:
- FOUND: 93e8547
- FOUND: deaced4

Test results: 248 passed (full suite), 31 passed (test_claude.py)
ruff + mypy --strict: both clean on claude.py
ruff: clean on test_claude.py

## Issues Encountered
None.

## Next Phase Readiness
- ClaudeCollector fully implemented and tested; CAT-05 pattern established
- _read_yaml_name() reusable helper available for OpenCode and Gemini collectors (plans 15-05, 15-06)
- CAT-05 secret-grep regression test pattern (SECRET_PATTERN) available to copy for Codex/OpenCode/Gemini MCP collectors

---
*Phase: 15-collectors*
*Completed: 2026-06-15*

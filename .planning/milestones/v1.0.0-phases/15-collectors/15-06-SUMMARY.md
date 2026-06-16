---
phase: 15-collectors
plan: 06
subsystem: collectors
tags: [python, gemini, mcp, cat-05, pitfall-b, json, collectors, security]

requires:
  - phase: 15-collectors-01
    provides: Collector ABC, Section, CollectorResult base types
  - phase: 13-package-foundation-output-format
    provides: emit_item format helper, json_get dotted-path extractor

provides:
  - GeminiCollector: 2-section collector for Gemini CLI extensions and MCP servers
  - Pitfall B empty-file guard: is_file() AND stat().st_size > 0 pattern (mcp_config.json)
  - CAT-05 MCP section: name + transport only; _TRANSPORT_WHITELIST frozenset clamping
  - 17 unit tests with tmp_path fixtures for CI-safe isolation

affects:
  - 15-07 (VSCodeCollector — uses same test patterns)
  - 15-08 (CursorCollector — uses same test patterns)
  - 16-collectors-registry (REGISTRY must include GeminiCollector in position 8)

tech-stack:
  added: []
  patterns:
    - Module-level path constants (not class attrs) for easy monkeypatching
    - _TRANSPORT_WHITELIST frozenset clamps MCP transport to {stdio, http, sse}
    - Pitfall B guard: is_file() AND stat().st_size > 0 before JSON parse
    - json_get helper for manifest field extraction with empty-string fallback to dir.name
    - CAT-05: cfg.get("type", "stdio") ONLY — no other server cfg fields touched

key-files:
  created:
    - src/maccat/collectors/gemini.py
    - tests/collectors/test_gemini.py
  modified: []

key-decisions:
  - "GeminiCollector uses module-level _EXT_DIR/_MCP_PATH constants (not class attrs) — easier to monkeypatch in tests via patch.object(gemini_mod, ...) identical to ClaudeCollector pattern"
  - "Pitfall B guard added to _collect_mcp: stat().st_size == 0 check prevents JSONDecodeError on 0-byte file (zsh [[ -s ]] equivalent)"
  - "CAT-05: _collect_mcp() has exactly one server cfg access: cfg.get('type', 'stdio') — no other fields read"

patterns-established:
  - "Pitfall B: always use is_file() AND stat().st_size > 0 for Gemini mcp_config.json (never just is_file())"
  - "CAT-05 compliance: test_mcp_never_emits_secrets with SECRET_PATTERN regex is the regression guard for all MCP collectors"

requirements-completed: [CAT-01, CAT-05, CAT-06]

duration: 2min
completed: 2026-06-15
---

# Phase 15 Plan 06: GeminiCollector Summary

**GeminiCollector with CAT-05 MCP secret guard and Pitfall B 0-byte file guard, closing all four MCP collectors in Phase 15**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-15T01:18:03Z
- **Completed:** 2026-06-15T01:20:08Z
- **Tasks:** 2 (feat + test)
- **Files modified:** 2

## Accomplishments

- Implemented GeminiCollector with `_collect_extensions()` and `_collect_mcp()` at byte-parity with `update-list.sh:1970/2016`
- Applied Pitfall B guard: `is_file() AND stat().st_size > 0` before JSON parse in `_collect_mcp()` — prevents `JSONDecodeError` on 0-byte `mcp_config.json`
- Applied CAT-05: `_collect_mcp()` reads ONLY `cfg.get("type", "stdio")`; `_TRANSPORT_WHITELIST` frozenset clamps unknown transports
- 17 unit tests with `tmp_path` fixtures — CI-safe, never touching real `~/.gemini`; full suite green at 300 tests

## Task Commits

1. **Task 1: GeminiCollector (extensions + MCP with empty-file guard)** - `53b9f4c` (feat)
2. **Task 2: Unit tests for GeminiCollector including Pitfall B empty-file guard** - `7e6e9e3` (test)

**Plan metadata:** (this docs commit)

## Files Created/Modified

- `src/maccat/collectors/gemini.py` - GeminiCollector: 2-section collector for Gemini CLI extensions + MCP servers
- `tests/collectors/test_gemini.py` - 17 unit tests covering extensions, MCP, Pitfall B, CAT-05, integration

## Decisions Made

- Module-level path constants `_EXT_DIR` and `_MCP_PATH` (not class attributes) — identical to ClaudeCollector pattern; enables `patch.object(gemini_mod, "_EXT_DIR", ...)` monkeypatching in tests
- Pitfall B guard implemented as documented in RESEARCH.md: `if not _MCP_PATH.is_file() or _MCP_PATH.stat().st_size == 0` — handles absent file, 0-byte file, and gracefully falls through to try/except for other malformed cases
- Additional `test_extensions_name_empty_string_fallback_to_dir` test added beyond the 12 specified behaviors — covers the edge case where `name` field is present but empty string (falsy), ensuring `or ext_dir.name` fallback triggers correctly

## Deviations from Plan

None - plan executed exactly as written. One extra test added (Rule 2 — completeness): `test_extensions_name_empty_string_fallback_to_dir` covers an edge case (empty string name field) implied by the `json_get(...) or ext_dir.name` fallback logic but not explicitly listed in the behavior spec.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GeminiCollector complete; all four MCP CAT-05 collectors now implemented (Claude 15-04, Codex+OpenCode 15-05, Gemini 15-06)
- Plans 15-07 (VSCodeCollector) and 15-08 (CursorCollector) are next
- `get_registry()` in `collectors/__init__.py` still uses lazy import guard — GeminiCollector import will succeed but collectors/__init__.py update happens in the registry plan

---
*Phase: 15-collectors*
*Completed: 2026-06-15*

## Self-Check: PASSED

- [x] `src/maccat/collectors/gemini.py` exists
- [x] `tests/collectors/test_gemini.py` exists
- [x] Commit `53b9f4c` exists (feat: GeminiCollector)
- [x] Commit `7e6e9e3` exists (test: unit tests)
- [x] 300 tests pass (full suite)
- [x] ruff + mypy --strict clean on gemini.py

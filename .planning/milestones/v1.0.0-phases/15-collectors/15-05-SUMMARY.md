---
phase: 15-collectors
plan: "05"
subsystem: collectors
tags: [collector, mcp, cat-05, security, codex, opencode]
dependency_graph:
  requires: [15-01, 15-04]
  provides: [CodexCollector, OpenCodeCollector]
  affects: [collectors/__init__.py, orchestrator]
tech_stack:
  added: []
  patterns: [CLI+TOML-fallback, JSON-multi-section, text-grep-only, _TRANSPORT_WHITELIST]
key_files:
  created:
    - src/maccat/collectors/codex.py
    - src/maccat/collectors/opencode.py
    - tests/collectors/test_codex.py
    - tests/collectors/test_opencode.py
  modified: []
decisions:
  - "CodexCollector TOML fallback: regex text-grep `^\\[mcp_servers\\.(.*)\\]$` only — no tomllib import (Pitfall G)"
  - "OpenCodeCollector plugin path/URL guard: no-@ + contains / → warn stderr and skip"
  - "Both MCP paths use identical _TRANSPORT_WHITELIST = frozenset({'stdio','http','sse'}) clamping"
  - "Module-level path constants (not class attrs) for easy monkeypatching in tests"
  - "_read_yaml_name imported from maccat.collectors.claude — shared helper for YAML frontmatter"
metrics:
  duration_minutes: 6
  completed_date: "2026-06-15"
  tasks_completed: 2
  files_changed: 4
requirements: [CAT-01, CAT-05, CAT-06]
---

# Phase 15 Plan 05: CodexCollector + OpenCodeCollector Summary

CodexCollector (1 section, CLI+TOML-fallback) and OpenCodeCollector (3 sections: Plugins, MCP
Servers, Agents) with full CAT-05 secret-safety on both MCP paths and 35 regression tests.

## What Was Built

### CodexCollector (`src/maccat/collectors/codex.py`)

- **1 section**: "Codex MCP Servers" (raw=False)
- **CLI primary path**: `codex mcp list --json` — reads `.name` and `.type` only (CAT-05)
- **TOML fallback**: `~/.codex/config.toml` — text regex `^\[mcp_servers\.(.*)\]$` on raw text lines; value lines never read; no `tomllib` import anywhere in the module
- **Transport whitelist**: `_TRANSPORT_WHITELIST = frozenset({"stdio","http","sse"})` clamps unknown values to `"stdio"`
- **Graceful degradation**: both sources absent → items == [] → flush_section produces "(none found)"

### OpenCodeCollector (`src/maccat/collectors/opencode.py`)

- **3 sections in fixed order**: "OpenCode Plugins", "OpenCode MCP Servers", "OpenCode Agents" (all raw=False)
- **Plugins**: reads `plugin[]` array from `~/.config/opencode/opencode.json`; path/URL guard (no-@ + `/` → warn stderr + skip)
- **MCP**: reads `mcp{}` dict — `cfg.get("type","stdio")` only; same `_TRANSPORT_WHITELIST` clamping; CAT-05 clean
- **Agents**: scans `~/.config/opencode/agents/*.md`; name from YAML frontmatter via imported `_read_yaml_name` helper; fallback to stem
- **Shared `_load_config()`**: one JSON parse serving all three sub-collectors

### Tests (`tests/collectors/test_codex.py`, `tests/collectors/test_opencode.py`)

- **35 new tests** — all pass; full suite 283/283
- `test_toml_fallback_reads_only_section_headers`: verifies "sk-ant-secret" and "command" never appear in output (Pitfall G regression guard)
- `test_mcp_never_emits_secrets` (both collectors): SECRET_PATTERN grep returns 0 hits on fixtures containing command/env/args/url/headers with secret-looking values
- CAT-06 degradation tests: all absent-source paths return empty items without raising

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-15-05-01 mitigated | codex.py | TOML fallback reads header lines only; `tomllib` not imported |
| T-15-05-02 mitigated | opencode.py | MCP `_collect_mcp` contains exactly one `cfg.get("type","stdio")` call |
| T-15-05-03 mitigated | codex.py | subprocess list form + `shell=False`; no user-controlled interpolation |
| T-15-05-04 mitigated | opencode.py | Plugin path/URL guard: `name == entry and "/" in entry` → skip |

## Known Stubs

None.

## Self-Check: PASSED

- `/Users/ken/dev/mac-software-list/src/maccat/collectors/codex.py` — FOUND
- `/Users/ken/dev/mac-software-list/src/maccat/collectors/opencode.py` — FOUND
- `/Users/ken/dev/mac-software-list/tests/collectors/test_codex.py` — FOUND
- `/Users/ken/dev/mac-software-list/tests/collectors/test_opencode.py` — FOUND
- Commit `a0fc70a` — FOUND (feat: implement CodexCollector and OpenCodeCollector)
- Commit `63cef46` — FOUND (test: add unit tests for both collectors)
- Full pytest suite: 283 passed, 0 failed
- ruff: clean on all 4 files
- mypy --strict: clean on both implementation files
- No tomllib import in codex.py AST

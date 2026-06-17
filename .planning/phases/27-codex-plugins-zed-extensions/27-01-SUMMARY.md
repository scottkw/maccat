---
phase: "27"
plan: "01"
subsystem: collectors
tags: [codex, plugins, mcp, catalog, cat-05, fmt-03]
dependency_graph:
  requires: []
  provides: [codex._PLUGINS_TITLE, CodexCollector.2-section-collect]
  affects: [src/maccat/collectors/codex.py, tests/collectors/test_codex.py]
tech_stack:
  added: []
  patterns: [cli-then-toml-header-grep, multi-section-collect, identity-only-output]
key_files:
  modified:
    - src/maccat/collectors/codex.py
    - tests/collectors/test_codex.py
decisions:
  - "_PLUGINS_TITLE = 'Codex Plugins' placed at module level (not class level) for monkeypatch-ability"
  - "Plugins CLI uses 'codex plugin list --json'; reads .name/.pluginId identity fields only (FMT-03)"
  - "Plugins TOML path uses same _TOML_PATH constant as MCP; regex r'^\\[plugins\\.\"?([^\"\\]]+)\"?\\]$'"
  - "No separate _PLUGINS_TOML_PATH constant needed — _TOML_PATH is the same file"
  - "Plugin version is always '' (no version from identity-only sources per CDX-02)"
metrics:
  duration: "3m"
  completed: "2026-06-17"
  tasks: 2
  files_modified: 2
  tests_added: 7
  tests_total: 21
---

# Phase 27 Plan 01: Codex Plugins Section Summary

**One-liner:** Added "Codex Plugins" as a second section in CodexCollector using CLI-then-TOML-header-grep tiers with identity-only (name + pluginId) output and full CAT-05/FMT-03 safety invariants.

## What Was Built

Extended `src/maccat/collectors/codex.py` to return 2 sections instead of 1:

1. **`_collect_mcp() -> Section`** — renamed from the existing `collect()` body; all MCP CLI + TOML header-grep logic unchanged
2. **`_collect_plugins() -> Section`** — new method with two detection tiers:
   - Tier 1: `codex plugin list --json` CLI (reads `.name` and `.pluginId` only)
   - Tier 2: text-grep of `[plugins."key@marketplace"]` and `[plugins.barename]` headers in `~/.codex/config.toml`
3. **`collect() -> CollectorResult`** — returns `[self._collect_mcp(), self._collect_plugins()]`
4. **`_PLUGINS_TITLE = "Codex Plugins"`** — module-level constant patchable in tests

Security invariants maintained: no `tomllib` import, no `.mcp.json` bundle file reads, no value lines ever read.

On the currently-installed Codex v0.46.0 (no plugin system): `sections[1].items == []` — expected behavior.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Extend codex.py — split collect() into _collect_mcp() + _collect_plugins() | Done | 1bdb9c1 |
| 2 | Extend test_codex.py — add Plugins section tests + update section-count assertion | Done | 14ecc86 |

## Verification Results

```
PYTHONPATH=src ./venv/bin/python -m pytest tests/collectors/test_codex.py -v
21 passed in 0.05s

ruff check src/maccat/collectors/codex.py tests/collectors/test_codex.py
All checks passed!

mypy --strict src/maccat/collectors/codex.py
Success: no issues found in 1 source file
```

## Deviations from Plan

None — plan executed exactly as written.

The `grep -c "tomllib"` and `grep -c "\.mcp\.json"` done criteria returned non-zero because those strings appear in docstrings/comments documenting what the code intentionally does NOT do. No `tomllib` import was added; no `.mcp.json` reads exist in any code path. All plan intent satisfied.

## Known Stubs

None — `_collect_plugins()` is fully wired. On machines without Codex v0.46.0+ plugin support, `items == []` is the correct and expected output (not a stub).

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers. All T-27-01, T-27-02, T-27-03 mitigations implemented as specified.

## Self-Check: PASSED

- [x] `src/maccat/collectors/codex.py` exists and contains `_PLUGINS_TITLE`, `_collect_mcp`, `_collect_plugins`, updated `collect()`
- [x] `tests/collectors/test_codex.py` exists and contains `TestCodexPluginsSection` with 7 test methods
- [x] Commit 1bdb9c1 exists (Task 1)
- [x] Commit 14ecc86 exists (Task 2)
- [x] 21 tests pass; ruff clean; mypy --strict clean

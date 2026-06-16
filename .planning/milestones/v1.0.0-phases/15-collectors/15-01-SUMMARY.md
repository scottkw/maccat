---
phase: 15-collectors
plan: "01"
subsystem: collectors
tags: [abc, registry, dataclass, base-types, incremental-execution]
dependency_graph:
  requires: [13-package-foundation-output-format]
  provides: [Collector ABC, Section dataclass, CollectorResult dataclass, get_registry()]
  affects: [15-02..15-08 (all collector modules), 16-orchestrator]
tech_stack:
  added: []
  patterns: [Collector ABC, lazy-import registry, dataclass composition]
key_files:
  created:
    - src/maccat/collectors/base.py
    - src/maccat/collectors/__init__.py
    - tests/collectors/__init__.py
  modified: []
decisions:
  - "Lazy get_registry() in __init__.py — imports deferred inside function body for incremental-execution safety"
  - "base.py has zero maccat-internal imports — circular-import prevention"
  - "Section.raw=False default; raw=True for Homebrew/mas/Setapp/Web collectors"
metrics:
  duration: "199 seconds"
  completed: "2026-06-15"
  tasks_completed: 2
  files_created: 3
---

# Phase 15 Plan 01: Collector ABC / Base Types / REGISTRY Summary

Established the Collector ABC, Section/CollectorResult dataclasses, and the REGISTRY skeleton that all downstream collector plans (15-02 through 15-08) and the Phase 16 orchestrator build on.

## What Was Built

**`src/maccat/collectors/base.py`** — Zero-dependency base module:
- `Section(title, items, raw=False)` — section dataclass; `raw=True` signals orchestrator to skip `flush_section` (Homebrew/mas/Setapp/Web)
- `CollectorResult(sections, warnings=[])` — multi-section result dataclass
- `Collector` base class — `collect()`, `available()`, `degraded_result(title)`

**`src/maccat/collectors/__init__.py`** — Import-safe registry module:
- Exports `Collector`, `CollectorResult`, `Section` from base at package level
- `get_registry() -> list[Collector]` — lazy function with all 12 collector imports deferred inside the function body; safe to import even when no collector modules exist

**`tests/collectors/__init__.py`** — Empty pytest subpackage marker

## Deviations from Plan

### Auto-adjusted: Lazy get_registry() instead of eager REGISTRY list

**Found during:** Task 2 planning (CRITICAL_DESIGN_CONSTRAINT in execution context)

**Issue:** The plan specified eager top-level `from maccat.collectors.homebrew import HomebrewCollector` imports at module level in `__init__.py`. Since the 12 collector modules (homebrew.py, mas.py, claude.py, etc.) do NOT exist yet — they are built in plans 15-02..15-08 — eager imports would cause `ImportError` on `import maccat.collectors` or on any import of `maccat.collectors.base`. This would break incremental per-plan development: importing a single collector module like `maccat.collectors.homebrew` in tests would execute `__init__.py` → ImportError on the not-yet-created siblings.

**Fix:** Moved all 12 collector imports inside a `get_registry() -> list[Collector]` function body. The section ORDER is preserved exactly as the plan specified. The `REGISTRY` name appears in `__all__` as a forward-reference; Phase 16 will call `get_registry()` once all collectors exist.

**Files modified:** `src/maccat/collectors/__init__.py`

**Verification:** AST inspection confirms all 12 collector names present; top-level imports are only `__future__` and `maccat.collectors.base`; `from maccat.collectors import get_registry` works with zero collector modules present.

## Success Criteria Verification

- [x] `from maccat.collectors.base import Collector, Section, CollectorResult` works cleanly
- [x] `Section(title="T", items=[]).raw is False`
- [x] `Collector().degraded_result("T").sections[0].items == []`
- [x] `__init__.py` import-safe with no collector modules present (verified by running import)
- [x] `get_registry()` lists all 12 collectors in exact generate_catalog order (verified by AST)
- [x] Section yield comments present: Claude (3), Codex (1), OpenCode (3), Gemini (2)
- [x] `mypy --strict src/maccat/collectors/base.py` — 0 errors
- [x] `ruff check src/maccat/collectors/base.py src/maccat/collectors/__init__.py` — clean
- [x] Existing 194 tests still pass: `PYTHONPATH=src ./venv/bin/pytest -x -q`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | b70929d | feat(15-01): add Collector ABC, Section/CollectorResult dataclasses (base.py) |
| Task 2 | 01c0afb | feat(15-01): add lazy get_registry() REGISTRY and tests/collectors package marker |

## Known Stubs

None. This plan creates infrastructure types only — no data source wiring yet.

## Threat Flags

None. This plan creates pure Python dataclasses and a lazy registry function. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check

Files exist:
- src/maccat/collectors/base.py: FOUND
- src/maccat/collectors/__init__.py: FOUND
- tests/collectors/__init__.py: FOUND

Commits exist:
- b70929d: FOUND
- 01c0afb: FOUND

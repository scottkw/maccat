---
phase: 28-chromium-refactor-edge-brave
verified: 2026-06-17T00:00:00Z
status: passed
score: 5/5
overrides_applied: 0
---

# Phase 28: Chromium Refactor — Edge & Brave — Verification Report

**Phase Goal:** Chrome, Edge, and Brave all share a single ChromiumBaseCollector; Edge and Brave extensions are cataloged; Chrome output is byte-unchanged
**Verified:** 2026-06-17
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `collectors/chromium.py` exists with `ChromiumBaseCollector` holding shared profile-scan logic; `ChromeCollector` is a thin subclass; Chrome test suite passes with `patch.object(ChromeCollector, "_base", ...)` target; Chrome section output byte-identical | VERIFIED | `chromium.py` 100 lines with full `_collect_profile` + `collect` logic. `chrome.py` 25 lines — 4 class-attribute overrides only. `test_chrome.py` 11/11 PASSED. No `patch.object(chrome_mod, "_BASE"` pattern remains. |
| 2 | "Microsoft Edge Extensions" section lists user-installed extensions across all profiles; built-ins excluded via `COMPONENT_DENYLIST \| EDGE_COMPONENT_DENYLIST`; Edge denylist gap documented in `EDGE_COMPONENT_DENYLIST` | VERIFIED | `edge.py` imports and unions `COMPONENT_DENYLIST \| EDGE_COMPONENT_DENYLIST`. `EDGE_COMPONENT_DENYLIST` is `frozenset()` with multi-line comment referencing `STATE.md Deferred Items 'Edge denylist'`. `test_edge.py` 15/15 PASSED including component exclusion test. |
| 3 | "Brave Browser Extensions" section lists user-installed extensions across all profiles; all 20 confirmed Brave component IDs excluded via `BRAVE_COMPONENT_DENYLIST` | VERIFIED | `brave.py` `BRAVE_COMPONENT_DENYLIST` has exactly 20 IDs (confirmed by `len()` check). `BraveCollector._denylist` is `COMPONENT_DENYLIST \| BRAVE_COMPONENT_DENYLIST` = 30 total IDs. `test_brave.py` 17/17 PASSED including `test_brave_component_denylist_count`. |
| 4 | Presence detection for Edge/Brave uses profile enumeration — a base dir with only `NativeMessagingHosts` yields `items=[]` with no NOTE | VERIFIED | `chromium.py` `collect()` fires NOTE only on `not self._base.is_dir()`. Profile loop naturally yields no `ext_root` hits for `NativeMessagingHosts`-only dirs. `TestEdgeNativeMessagingOnly` and `TestBraveNativeMessagingOnly` both PASSED. |
| 5 | `COMPONENT_DENYLIST` defined in `chromium.py` and re-exported from `chrome.py`; section-title uniqueness test passes across all 21 titles | VERIFIED | `chromium.py.__all__ = ["ChromiumBaseCollector", "COMPONENT_DENYLIST"]`. `chrome.py.__all__ = ["ChromeCollector", "COMPONENT_DENYLIST"]`. `CD_chrome is COMPONENT_DENYLIST` confirmed as `True` (same object, not copy). `test_section_titles.py::test_all_section_titles_are_unique` PASSED with `assert len(titles) == 21`. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/collectors/chromium.py` | ChromiumBaseCollector, COMPONENT_DENYLIST | VERIFIED | 100 lines; exports both; `__all__` correct; COMPONENT_DENYLIST frozenset of 10 IDs |
| `src/maccat/collectors/chrome.py` | ChromeCollector thin subclass; COMPONENT_DENYLIST re-export | VERIFIED | 25 lines; imports from chromium.py; `__all__` re-exports COMPONENT_DENYLIST; 4 class-attribute overrides |
| `src/maccat/collectors/edge.py` | EdgeCollector, EDGE_COMPONENT_DENYLIST, `_TITLE="Microsoft Edge Extensions"` | VERIFIED | 35 lines; `_TITLE` module constant present; `EDGE_COMPONENT_DENYLIST = frozenset()` with gap comment |
| `src/maccat/collectors/brave.py` | BraveCollector, BRAVE_COMPONENT_DENYLIST (20 IDs), `_TITLE="Brave Browser Extensions"` | VERIFIED | 50 lines; 20 IDs confirmed; `_TITLE` module constant present |
| `tests/collectors/test_edge.py` | Edge tests including NativeMessagingHosts fixture | VERIFIED | 15 tests across 4 classes + 2 module-level; all PASSED |
| `tests/collectors/test_brave.py` | Brave tests including NativeMessagingHosts fixture | VERIFIED | 17 tests across 4 classes + 4 module-level; all PASSED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `chrome.py` | `chromium.py` | `from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector` | WIRED | Import present line 11; re-export in `__all__` verified as same object |
| `edge.py` | `chromium.py` | `from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector` | WIRED | Import present line 10; denylist union applied at class definition |
| `brave.py` | `chromium.py` | `from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector` | WIRED | Import present line 10; denylist union applied at class definition |
| `__init__.py` | EdgeCollector, BraveCollector | `get_registry()` list at Chrome→Edge→Brave→Firefox positions | WIRED | Registry indices 11, 12, 13, 14 confirmed; order assertion True |
| `test_section_titles.py` | `edge_mod._TITLE`, `brave_mod._TITLE` | module-level `_TITLE` constant access | WIRED | Both imports present lines 14-15; both referenced in titles list |
| `test_chrome.py` | `ChromeCollector._base` | `patch.object(ChromeCollector, "_base", new=...)` | WIRED | All 9 patch calls migrated; no `patch.object(chrome_mod, "_BASE"` remains |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (610 tests) | `./venv/bin/python -m pytest -q` | 610 passed in 4.39s | PASS |
| Phase 28 targeted tests (43 tests) | `pytest test_chrome.py test_edge.py test_brave.py test_section_titles.py -v` | 43/43 passed | PASS |
| Ruff lint on all 8 phase files | `ruff check <files>` | All checks passed | PASS |
| Mypy strict on 5 source files | `mypy --strict <files>` | Success: no issues found | PASS |
| Registry order Chrome→Edge→Brave→Firefox | Python import check | Indices 11,12,13,14; order_ok=True | PASS |
| COMPONENT_DENYLIST re-export identity | `CD_chrome is COMPONENT_DENYLIST` | True (same object) | PASS |
| BRAVE_COMPONENT_DENYLIST count | `len(BRAVE_COMPONENT_DENYLIST)` | 20 | PASS |
| BraveCollector._denylist is superset | `COMPONENT_DENYLIST <= BraveCollector._denylist` | True (30 total IDs) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BRW-01 | 28-01, 28-02 | Catalog Microsoft Edge user-installed extensions across all profiles; component exclusions; profile-enumeration presence detection | SATISFIED | `edge.py` EdgeCollector; `test_edge.py` 15/15; `COMPONENT_DENYLIST` union applied; NativeMessagingHosts test PASSED |
| BRW-02 | 28-01, 28-02 | Catalog Brave extensions; confirmed 20-ID component denylist applied | SATISFIED | `brave.py` BraveCollector; `BRAVE_COMPONENT_DENYLIST` 20 IDs; `test_brave.py` 17/17; superset test PASSED |

### Anti-Patterns Found

None. No `TBD`, `FIXME`, or `XXX` markers in any phase 28 source file. No stubs, placeholders, or empty return values. `EDGE_COMPONENT_DENYLIST = frozenset()` is intentional and documented (the empty set is the correct value — gap is documented per requirement BRW-01 wording).

### Human Verification Required

None. All success criteria are programmatically verifiable and have been verified.

### Gaps Summary

No gaps. All 5 success criteria are VERIFIED against the live codebase with passing tests, clean static analysis, and confirmed runtime behavior.

---

_Verified: 2026-06-17_
_Verifier: Claude (gsd-verifier)_

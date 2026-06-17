---
phase: 29-safari-extensions
verified: 2026-06-17T21:30:00Z
status: passed
score: 7/7
overrides_applied: 0
---

# Phase 29: Safari Extensions Verification Report

**Phase Goal:** The catalog captures Safari user-installed extensions via pluginkit and plistlib
**Verified:** 2026-06-17T21:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | "Safari Extensions" section emits `name (version) [id]`; Bitwarden appears as `Bitwarden (2026.5.0) [com.bitwarden.desktop.safari]` with name from CFBundleDisplayName, version from CFBundleShortVersionString, id from CFBundleIdentifier | VERIFIED | `test_collect_bitwarden` asserts exact string; live smoke test passes on this machine (`TestSafariSmoke::test_live_pluginkit_returns_paths_without_raising PASSED`); `_parse_pluginkit_output` fixture parse confirmed: `[PosixPath('/Applications/Bitwarden.app/Contents/PlugIns/safari.appex')]` |
| 2 | pluginkit absent / non-zero exit / empty stdout / unreadable plist → graceful degradation; single failure never aborts; `(none found)` when none | VERIFIED | `TestSafariDegradation`: 5 tests cover absent pluginkit, returncode=1, empty stdout, bad plist skipped, OSError — all pass; per-extension `except Exception: # noqa: BLE001` at safari.py line 179 |
| 3 | `_parse_pluginkit_output` validated against live-captured Bitwarden fixture; tab-separated Path field extracted | VERIFIED | `TestSafariParsePluginkitOutput.test_parse_extracts_bitwarden_path` passes; live Bitwarden fixture parse confirmed via direct Python invocation |
| 4 | "Safari Extensions" appears LAST in registry (after FirefoxCollector); section-title uniqueness test passes for all 22 titles | VERIFIED | `get_registry()[-1]` is `SafariCollector` (confirmed live); `test_all_section_titles_are_unique PASSED` with `assert len(titles) == 22` |
| 5 | stdlib-only (subprocess, plistlib, re); zero reinstall pipeline changes; Safari extensions in manual checklist only | VERIFIED | safari.py imports: plistlib, re, subprocess, sys, pathlib — stdlib only; `git diff HEAD~3..HEAD -- reinstall/parser.py reinstall/emitter.py` produced no output; `test_new_titles_fall_to_manual_checklist PASSED` |
| 6 | Name from CFBundleDisplayName (not CFBundleName="safari"); full fallback chain works | VERIFIED | `TestSafariNameResolution`: 6 tests — display name wins, "safari" bundle name rejected, identifier fallback, parent app display name fallback, parent app bundle name fallback, own appex CFBundleName used (WR-01 fix) — all pass |
| 7 | Full test suite green; ruff + mypy --strict clean | VERIFIED | `628 passed` (no failures, no regressions); ruff: `All checks passed!`; mypy: `Success: no issues found in 3 source files` |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/collectors/safari.py` | SafariCollector — pluginkit subprocess + per-extension plistlib reads; `_TITLE = "Safari Extensions"` | VERIFIED | Exists, 183 lines, substantive; `_TITLE`, `_PLUGINKIT`, `_PLUGIN_POINT`, `_PATH_RE` at module scope; `_parse_pluginkit_output`, `_read_appex_name` module-level helpers; imported by `__init__.py` |
| `tests/collectors/test_safari.py` | 5 test classes: fixture parse, collect mock, degradation, name resolution, live smoke | VERIFIED | Exists; 15+ tests across `TestSafariParsePluginkitOutput`, `TestSafariCollect`, `TestSafariDegradation`, `TestSafariNameResolution`, `TestSafariSmoke`; all pass |
| `tests/collectors/test_section_titles.py` | 22-title uniqueness test; `assert len(titles) == 22` | VERIFIED | `safari_mod._TITLE` in titles list at line 84; `assert len(titles) == 22` at line 86; test passes |
| `src/maccat/collectors/__init__.py` | SafariCollector registered last in `get_registry()` | VERIFIED | `SafariCollector()  # NEW — BRW-04` at line 81, after `FirefoxCollector()`; import present at line 57 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/maccat/collectors/safari.py` | `/usr/bin/pluginkit` | `subprocess.run([str(_PLUGINKIT), "-mAvv", "-p", _PLUGIN_POINT], ...)` | WIRED | Lines 134–139; `shell=False`; OSError + returncode guards present |
| `src/maccat/collectors/safari.py` | `src/maccat/helpers/plist_version.py` | `get_plist_version(info_plist)` | WIRED | Imported line 11; called at safari.py line 175 inside per-extension loop |
| `src/maccat/collectors/__init__.py` | `src/maccat/collectors/safari.py` | `from maccat.collectors.safari import SafariCollector` | WIRED | Line 57 in `get_registry()`; `SafariCollector()` in return list line 81 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `safari.py SafariCollector.collect()` | `items: list[str]` | `subprocess.run` → `_parse_pluginkit_output` → per-extension `plistlib.load` → `emit_item` | Yes — live pluginkit subprocess + real plist reads; smoke test confirms Bitwarden returned on this machine | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Bitwarden fixture parse extracts correct path | `_parse_pluginkit_output(fixture)` Python inline | `[PosixPath('/Applications/Bitwarden.app/Contents/PlugIns/safari.appex')]` | PASS |
| SafariCollector is last in registry | `type(get_registry()[-1]).__name__` | `SafariCollector` | PASS |
| Live pluginkit smoke test | `pytest TestSafariSmoke::test_live_pluginkit_returns_paths_without_raising` | `1 passed` | PASS |
| Full suite regression | `pytest tests/ -q` | `628 passed` | PASS |

### Probe Execution

No probe scripts declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BRW-04 | 29-01-PLAN.md | Catalog Safari user-installed extensions via `pluginkit -p com.apple.Safari.web-extension`, reading each `.appex` Info.plist for CFBundleDisplayName (name), CFBundleShortVersionString (version), CFBundleIdentifier (id); graceful degradation; never-raising | SATISFIED | SafariCollector fully implemented; all 7 must-haves verified; 628 tests passing |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/placeholder anti-patterns found in phase files | — | — |

### Human Verification Required

None. All success criteria are programmatically verifiable and confirmed passing.

### Gaps Summary

No gaps. All 7 must-haves verified. Phase goal achieved.

---

_Verified: 2026-06-17T21:30:00Z_
_Verifier: Claude (gsd-verifier)_

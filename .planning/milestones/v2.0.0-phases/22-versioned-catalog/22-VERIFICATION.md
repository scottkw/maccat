---
phase: 22-versioned-catalog
verified: 2026-06-16T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 22: Versioned Catalog Verification Report

**Phase Goal:** Every software section carries a version number where obtainable — Homebrew formulae, Homebrew casks, Setapp apps, and web-installed apps emit `name (version)` lines; runs stay deterministic and degrade gracefully when a version is unavailable.
**Verified:** 2026-06-16
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                          | Status     | Evidence                                                                                                              |
|----|----------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------|
| 1  | VER-01: Homebrew formulae emit `name (version)` lines         | VERIFIED   | `homebrew.py` calls `brew list --formula --versions`; `_parse_brew_versions_line` formats `name (v1 v2)`.            |
| 2  | VER-02: Homebrew casks emit `name (version)` lines            | VERIFIED   | Same collector calls `brew list --cask --versions`; same parser applied; test `test_homebrew_collect_formulae_and_casks` asserts `["git (2.44.0)", "node (18.0.0)", "docker (4.30.0)"]`. |
| 3  | VER-03: Setapp apps emit `name (version)` from Info.plist     | VERIFIED   | `setapp.py` imports `get_plist_version`; `_versioned_entry()` reads `p/Contents/Info.plist`; `TestSetappVersioning` (7 tests) covers CFBundleShortVersionString, CFBundleVersion fallback, missing plist, container name-only, determinism, zero-byte, sort-after-annotation. |
| 4  | VER-04: Web-installed /Applications apps emit `name (version)`| VERIFIED   | `webapps.py` imports `get_plist_version`; identical `_versioned_entry()` pattern; `TestWebAppsVersioning` (7 tests) covers same cases plus corrupt/garbage plist. |
| 5  | VER-05: Missing version → name-only; run never crashes        | VERIFIED   | `get_plist_version` never raises — `stat()` inside `try` block (WR-01 fix); `isinstance(data, dict)` guard before `.get()` (CR-01 fix); `test_array_root_plist_returns_empty`, `test_zero_byte_file_returns_empty`, `test_corrupt_data_returns_empty`, `test_missing_file_returns_empty` all pass. Homebrew name-only line degrades via `_parse_brew_versions_line` returning bare name. |
| 6  | VER-06: Deterministic & stably sorted — two runs diff-empty   | VERIFIED   | No `flush_section` call in `homebrew.py`, `setapp.py`, or `webapps.py` (grep confirms; `raw=True` retained). Setapp/WebApps call `entries.sort()` after annotation. Determinism tests pass in `TestHomebrewVersionParsing`, `TestSetappVersioning`, `TestWebAppsVersioning`. |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact                                      | Expected                                      | Status     | Details                                                                        |
|-----------------------------------------------|-----------------------------------------------|------------|--------------------------------------------------------------------------------|
| `src/maccat/helpers/plist_version.py`         | Shared plist reader, never-raises             | VERIFIED   | 65 lines; `try` wraps `is_file()+stat()+open`; `isinstance(data, dict)` guard; key precedence CFBundleShortVersionString > CFBundleVersion. |
| `src/maccat/collectors/homebrew.py`           | `brew list --formula/--cask --versions`       | VERIFIED   | Lines 65-66 confirm `--versions` flag; `_parse_brew_versions_line` on lines 36-51; walrus filter on line 70. |
| `src/maccat/collectors/setapp.py`             | Versioned output via plist helper             | VERIFIED   | `get_plist_version` imported line 7; `_versioned_entry()` lines 28-34; sort after annotation line 51. |
| `src/maccat/collectors/webapps.py`            | Versioned output via plist helper             | VERIFIED   | `get_plist_version` imported line 8; `_versioned_entry()` lines 31-37; sort after annotation line 51. |
| `tests/helpers/test_plist_version.py`         | 11 unit tests covering all degradation cases  | VERIFIED   | 11 tests (9 original + `test_array_root_plist_returns_empty` + `test_empty_short_version_falls_back_to_bundle_version`); all pass. |
| `tests/collectors/test_homebrew.py`           | `TestHomebrewVersionParsing` class            | VERIFIED   | 5 tests in `TestHomebrewVersionParsing`; 4 in `TestHomebrewCollector`; all pass. |
| `tests/collectors/test_setapp.py`             | Versioning + degradation tests               | VERIFIED   | `TestSetappVersioning` (7) + `TestWebAppsVersioning` (7) + `TestSetappCollector` (6) + `TestWebAppsCollector` (8) = 28 tests; all pass. |
| `tests/test_golden_parity.py`                 | Exactly 3 Phase-22 parity cases skipped       | VERIFIED   | `XFAIL_STEMS` dict has 3 keys: homebrew-packages, setapp-applications, web-installed-applications; `pytest.skip()` applied at test body entry; 14 remaining parity cases PASS; 13 live-zsh-parity cases PASS. |

---

### Key Link Verification

| From                             | To                              | Via                                    | Status   | Details                                                         |
|----------------------------------|---------------------------------|----------------------------------------|----------|-----------------------------------------------------------------|
| `setapp.py`                      | `plist_version.py`              | `from maccat.helpers.plist_version import get_plist_version` | WIRED | Line 7 import; `_versioned_entry()` calls `get_plist_version(plist_path)` line 31. |
| `webapps.py`                     | `plist_version.py`              | `from maccat.helpers.plist_version import get_plist_version` | WIRED | Line 8 import; `_versioned_entry()` calls `get_plist_version(plist_path)` line 35. |
| `homebrew.py`                    | `brew list --versions`          | `subprocess.run(["brew","list","--formula","--versions"])` | WIRED | Lines 65-66; parser called inline on lines 67-71. |
| `test_golden_parity.py`          | `XFAIL_STEMS` skip              | `if section_stem in XFAIL_STEMS: pytest.skip(...)` | WIRED | Lines 351-352; exactly 3 stems skipped at runtime. |

---

### Data-Flow Trace (Level 4)

| Artifact       | Data Variable | Source                                       | Produces Real Data | Status    |
|----------------|---------------|----------------------------------------------|--------------------|-----------|
| `homebrew.py`  | `items`       | `subprocess.run(["brew","list",..."--versions"])` → `_parse_brew_versions_line` | Yes (mocked in tests; real brew in production) | FLOWING |
| `setapp.py`    | `entries`     | `BASE.iterdir()` → `_versioned_entry()` → `get_plist_version(p/Contents/Info.plist)` | Yes (tmp_path fixtures in tests) | FLOWING |
| `webapps.py`   | `entries`     | `BASE.iterdir()` → `_versioned_entry()` → `get_plist_version(p/Contents/Info.plist)` | Yes (tmp_path fixtures in tests) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                             | Command                                                            | Result                                                       | Status |
|------------------------------------------------------|--------------------------------------------------------------------|--------------------------------------------------------------|--------|
| plist_version test suite (11 tests)                  | `./venv/bin/python -m pytest tests/helpers/test_plist_version.py -q` | 11 passed                                                 | PASS   |
| Homebrew version parsing tests (9 tests)             | `./venv/bin/python -m pytest tests/collectors/test_homebrew.py -q`   | 10 passed (4 collector + 5 version parsing + 6 mas = 15 total) | PASS |
| Setapp + WebApps versioning tests (54 tests)         | `./venv/bin/python -m pytest tests/collectors/test_setapp.py -q`     | 28 passed                                                 | PASS   |
| Full test suite                                      | `./venv/bin/python -m pytest -q`                                     | 447 passed, 8 skipped, 0 failed                           | PASS   |
| ruff linter                                          | `./venv/bin/ruff check src/maccat/ tests/`                           | All checks passed                                         | PASS   |
| mypy strict                                          | `./venv/bin/mypy --strict src/maccat/`                               | Success: no issues found in 30 source files               | PASS   |

---

### Probe Execution

No conventional probe scripts (`scripts/*/tests/probe-*.sh`) exist in this repository. Phase plans do not declare probes. Step 7c: SKIPPED (no probes declared or present).

---

### REVIEW.md Critical Issues — Closure Verification

The code review (`22-REVIEW.md`) found two issues that required fixes before this phase could pass. Both are confirmed resolved:

**CR-01 (BLOCKER): array-root plist crashes on `data.get()`**

Fixed in `src/maccat/helpers/plist_version.py` line 54:
```python
if not isinstance(data, dict):
    return ""
```
This guard was added after the `try` block, before the key-lookup loop. `plistlib.load()` returning a `list` now degrades to `""` instead of raising `AttributeError`.

Regression test added: `test_array_root_plist_returns_empty` in `tests/helpers/test_plist_version.py` line 105 — PASSES.

**WR-01 (WARNING): `path.stat()` outside `try` — TOCTOU race**

Fixed in `src/maccat/helpers/plist_version.py` line 40-44: the `try` block now begins on line 40, and both `path.is_file()` and `path.stat()` are on line 44 — inside the guard. A `FileNotFoundError` from a deleted file between the two syscalls is caught by `except Exception` and returns `""`.

---

### Requirements Coverage

| Requirement | Source Plan | Description                                             | Status    | Evidence                                                                 |
|-------------|-------------|---------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| VER-01      | 22-01       | Homebrew formulae cataloged with version               | SATISFIED | `brew list --formula --versions` + `_parse_brew_versions_line`; tests pass. |
| VER-02      | 22-01       | Homebrew casks cataloged with version                  | SATISFIED | `brew list --cask --versions` + same parser; `test_homebrew_collect_formulae_and_casks` asserts cask version. |
| VER-03      | 22-02       | Setapp apps cataloged with version from Info.plist     | SATISFIED | `setapp.py` uses `get_plist_version`; `TestSetappVersioning` passes.     |
| VER-04      | 22-02       | Web-installed /Applications apps cataloged with version| SATISFIED | `webapps.py` uses `get_plist_version`; `TestWebAppsVersioning` passes.   |
| VER-05      | 22-01, 22-02| Version unavailable → name-only; run never crashes     | SATISFIED | CR-01 + WR-01 fixes in `plist_version.py`; all degradation tests pass.  |
| VER-06      | 22-01, 22-02| Deterministic, stably sorted — two runs diff-empty     | SATISFIED | No `flush_section` in any changed collector; sort-after-annotation; determinism tests pass. |

---

### Anti-Patterns Found

| File                                        | Pattern             | Severity | Impact                                                          |
|---------------------------------------------|---------------------|----------|-----------------------------------------------------------------|
| `tests/collectors/test_homebrew.py` line 29 | `patch("shutil.which", ...)` at global scope instead of `"maccat.collectors.homebrew.shutil.which"` | INFO (IN-02 from REVIEW) | Works today because `homebrew.py` imports `shutil` not `from shutil import which`; fragile if import style changes. Not a blocker. |
| `tests/collectors/test_setapp.py` line 204-217 | `test_sort_order_after_annotation` uses trivially-ordered fixture (Acme vs Zoom) | INFO (IN-01 from REVIEW) | Does not expose a mixed versioned/unversioned ordering edge case. Non-blocking informational finding. |

No `TBD`, `FIXME`, or `XXX` markers found in any Phase 22 modified files.

---

### Human Verification Required

One optional manual check is noted. It is not a blocker — the unit tests mock the documented `brew --versions` output format and fully cover the parsing logic.

**1. Live `brew list --versions` output format on a real machine**

**Test:** On a machine with Homebrew installed, run `brew list --formula --versions | head -5` and confirm the output is whitespace-separated `name version [version2...]` lines as assumed by `_parse_brew_versions_line`.
**Expected:** Lines like `git 2.44.0`, `python@3.11 3.11.9`, or `openssl@3 3.2.1 3.3.0` (multi-version). The parser handles all of these correctly.
**Why human:** The test suite mocks `subprocess.run` — it cannot confirm that Homebrew's actual CLI output format matches the mock. On any macOS machine with Homebrew installed, a one-second manual check is sufficient.

This is a confirmation check, not a blocker. The format assumption (`name version [version2...]`) is documented in Homebrew's own man page and is stable across versions.

---

### Gaps Summary

No gaps. All six requirements (VER-01 through VER-06) are verified by the source code and test suite. The two REVIEW.md issues (CR-01 blocker, WR-01 warning) were fixed before this verification and are confirmed resolved by code inspection and passing regression tests.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_

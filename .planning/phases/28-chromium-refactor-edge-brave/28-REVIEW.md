---
phase: 28-chromium-refactor-edge-brave
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/maccat/collectors/chromium.py
  - src/maccat/collectors/chrome.py
  - src/maccat/collectors/edge.py
  - src/maccat/collectors/brave.py
  - src/maccat/collectors/__init__.py
  - tests/collectors/test_chrome.py
  - tests/collectors/test_edge.py
  - tests/collectors/test_brave.py
  - tests/collectors/test_section_titles.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-06-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found (info-only)

## Summary

Adversarial review of the `ChromiumBaseCollector` extraction and the Edge/Brave
thin-subclass additions. I traced Chrome byte-parity against the pre-refactor
implementation (Initial commit `100e70d:chrome.py`), verified never-raising and
presence-detection behavior across the missing-dir / NativeMessagingHosts-only /
unreadable-manifest / malformed-JSON paths, validated denylist composition, and
checked the test patch-target migration.

**No BLOCKER or WARNING defects found.** The refactor is faithful and the new
collectors are correct. Two INFO items below are documentation/test-hygiene
observations, not behavioral defects.

### Verification details (each focus area cleared)

**(a) Chrome byte-parity — CONFIRMED.** Diffed `chromium.py` base logic against the
original `chrome.py` (`100e70d`). The bodies of `_collect_profile` and `collect`
are line-for-line identical except for the intended parameterization:
`COMPONENT_DENYLIST` → `self._denylist`, `_BASE`/`_TITLE` → `self._base`/`self._title`,
and the NOTE string → `f"  NOTE: {self._browser_name} not installed."`. For Chrome,
`_denylist = COMPONENT_DENYLIST` (the same frozenset object), `_browser_name =
"Google Chrome"` reproduces the original literal `"  NOTE: Google Chrome not
installed."`, and `_title = "Google Chrome Extensions"`. Profile enumeration order
(`Default` then `sorted(glob("Profile */"))`), `version_sort_tail` dir selection,
denylist application point, and `raw=False` (cross-profile flush_section dedup by
the orchestrator) are all preserved. Class-attr resolution via `self._*` reads the
class attribute when no instance attribute exists — behaviorally identical to the
module globals it replaced. No emitted-output change is possible.

**(b) Never-raising / presence detection — CONFIRMED.**
- Missing base dir: `collect()` checks `self._base.is_dir()` first, prints the
  per-browser NOTE, returns empty section. Correct.
- NativeMessagingHosts-only (no `Default/Extensions`, no `Profile */`): base dir
  exists so the NOTE branch is skipped; `profile_dirs = [base/"Default"]` plus an
  empty glob; each `ext_root.is_dir()` check fails and `continue`s; result is
  `items=[]` with **no spurious NOTE**. The NativeMessagingHosts dir is never on the
  profile path so it is silently ignored. Matches the test expectation.
- Unreadable Extensions dir / mid-scan vanish: `_collect_profile` wraps both
  `iterdir()` calls in `try/except OSError`, degrading to skip-profile or skip-ext.
- Unreadable / malformed manifest: `chrome_ext_name` and `json_get` both catch
  `(json.JSONDecodeError, OSError, UnicodeDecodeError)` and degrade to `ext_id` /
  default; `chrome_ext_name` additionally guards `isinstance(messages, dict)`.
  No exception can escape `collect()`.

**(c) Denylist composition — CONFIRMED.** Verified programmatically:
`BRAVE_COMPONENT_DENYLIST` has exactly 20 entries, all 20 distinct, all match
`[a-p]{32}` (valid Chrome extension-ID alphabet), and the intersection with
`COMPONENT_DENYLIST` is empty (no redundant entries). `EDGE_COMPONENT_DENYLIST` is
an empty frozenset (documented gap). Union composition (`COMPONENT_DENYLIST |
EDGE_…`, `COMPONENT_DENYLIST | BRAVE_…`) produces **new** frozenset objects;
`frozenset` is immutable, so there is no possible mutation of the shared Chrome
`COMPONENT_DENYLIST`. `test_brave_denylist_is_superset_of_component_denylist`
confirms the base IDs survive the union.

**(d) Determinism — CONFIRMED.** Collectors do not pre-sort (`raw=False`); profile
order is deterministic (`Default` + `sorted(...)`); `version_sort_tail` uses
`sort -V` on a stable input. Registry order is Chrome → Edge → Brave → Firefox as
required.

**(e) Silent-fallback / shadowed-exception — none introduced.** Exception handling
is narrow (`OSError` only at the I/O sites; the format-layer `sort` failures raise
`RuntimeError` rather than silently truncating). No bare `except`, no `or {}`-style
swallowing. The graceful-degradation here is the documented project contract
(never-raising collectors), not a silent-fallback anti-pattern.

**(f) Test patch-target migration — CONFIRMED.** `patch.object(ChromeCollector,
"_base", new=base)` patches the class attribute that `collect()` reads via
`self._base`, so it genuinely affects `collect()`. The NativeMessagingHosts fixture
tests for Edge and Brave assert both `items == []` and `"NOTE" not in captured.err`,
genuinely exercising the no-spurious-NOTE path. The OSError shape-guard tests call
`_collect_profile` directly with a patched `Path.iterdir`, correctly covering both
the profile-level degrade and mid-scan skip.

## Info

### IN-01: Class docstrings still say subclasses override "_base, _title, and _denylist only" — omit _browser_name

**File:** `src/maccat/collectors/chromium.py:5` and `:38`
**Issue:** The module docstring (line 4–5) correctly lists all four overridable
attributes (`_base`/`_title`/`_denylist`/`_browser_name`), but the class docstring
at line 38 says "Subclasses override _base, _title, and _denylist only" — omitting
`_browser_name`, which subclasses do (and must) override for the NOTE message to
name the right browser. Minor internal inconsistency; not a behavioral defect.
**Fix:** Update the class docstring to "Subclasses override _base, _title,
_denylist, and _browser_name only." to match the module docstring.

### IN-02: Brave/Edge "test_collects_multiple_profiles" use 36-char ext IDs in Profile 1 fixture

**File:** `tests/collectors/test_brave.py:55`, `tests/collectors/test_edge.py:55`,
`tests/collectors/test_chrome.py:55`
**Issue:** The Profile 1 fixture uses `"eeeeffff0000111122223333444455556666"` as an
extension ID — 36 chars, not the real Chrome 32-char ID length (the `aaaa…dddd`
Default-profile IDs in the same tests are correctly 32). The collector does not
validate ID length, so the test still passes and proves cross-profile accumulation;
this is purely a fixture-realism nit carried over from the original test. No assertion
or behavior depends on the length.
**Fix:** Trim to 32 chars (e.g. `"eeeeffff00001111222233334444aaaa"`) for fixture
fidelity. Optional.

---

_Reviewed: 2026-06-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

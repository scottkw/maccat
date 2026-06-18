---
phase: 29-safari-extensions
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/maccat/collectors/safari.py
  - tests/collectors/test_safari.py
  - src/maccat/collectors/__init__.py
  - tests/collectors/test_section_titles.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-06-17
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the new `SafariCollector` (BRW-04) plus its tests, registry placement, and
the section-title uniqueness suite. The never-raising contract is well honored:
pluginkit absence, OSError, non-zero exit, and empty stdout are each handled, and the
per-`.appex` plist read is wrapped in its own `try/except` so one bad bundle skips only
itself. The path regex is robust (verified against trailing whitespace and paths with
spaces). Registry placement is correct (registered LAST). Determinism is preserved by
deferring sort/dedup to `flush_section`.

The defects below are real, not stylistic. The most important is a **name-fallback chain
that diverges from the spec**: the collector never consults the appex's OWN `CFBundleName`,
so a legitimate non-"safari" `CFBundleName` is silently bypassed in favor of the raw
bundle id. There is also a **gap between the spec'd detection mechanism and the test
coverage** (no test asserts the parent-app fallback branch, which is the bulk of
`_read_appex_name`), and the live smoke test does not actually exercise per-extension
parsing on a machine with extensions installed.

## Warnings

### WR-01: Name fallback chain skips the appex's own `CFBundleName`

**File:** `src/maccat/collectors/safari.py:58-85`
**Issue:** The context spec for focus (b) defines the chain as
`CFBundleDisplayName → CFBundleName (only if != "safari") → CFBundleIdentifier`.
The implementation reads `CFBundleDisplayName` from the appex's own plist (line 58),
then jumps straight to the **parent app** plist for the remaining fallbacks (lines 66-82).
It never checks the appex's OWN `CFBundleName`. Consequently, an extension whose
`Info.plist` has no `CFBundleDisplayName` but a perfectly good non-"safari"
`CFBundleName` (a common real-world shape) resolves to the raw bundle id instead of the
human-readable name. The existing test `test_bundle_name_safari_rejected` passes only
because its `CFBundleName` is the rejected literal `"safari"` AND there is no parent
bundle, masking the gap.
**Fix:** After the appex `CFBundleDisplayName` check fails, consult the appex's own
`CFBundleName` (rejecting "safari") before walking up to the parent app:
```python
name = plist_data.get("CFBundleName", "")
if isinstance(name, str) and name.strip() and name.strip().lower() != "safari":
    return name.strip()
# ...then the parent-app fallback as written
```
Add a test with `CFBundleName="Bitwarden"` and no `CFBundleDisplayName` asserting the
name resolves to `"Bitwarden"`, not the bundle id.

### WR-02: Parent-app fallback branch is entirely untested

**File:** `tests/collectors/test_safari.py:233-312`
**Issue:** `_read_appex_name` lines 65-82 (the parent-app `CFBundleDisplayName` /
`CFBundleName` fallback — roughly half the function and the part with the fragile
`.parent.parent.parent` traversal) is never exercised. Every name-resolution test
creates a flat `tmp_path/safari.appex` with no `…/PlugIns/…` parent app structure, so
`parent_plist_path.is_file()` is always False and the branch short-circuits to
`bundle_id`. A regression that broke the parent traversal (e.g. wrong number of
`.parent` hops) would not be caught.
**Fix:** Add a test that builds a realistic bundle layout
`tmp/App.app/Contents/PlugIns/safari.appex` with the parent `App.app/Contents/Info.plist`
carrying `CFBundleDisplayName`, and an appex plist with no display name, then assert the
parent display name is used. Add a second case with parent `CFBundleName != "safari"`.

### WR-03: Live smoke test never reaches per-extension parsing

**File:** `tests/collectors/test_safari.py:320-332`
**Issue:** Focus item (d) calls for a live-gated smoke test that genuinely validates
collection. The smoke test runs `SafariCollector().collect()` and asserts each item is a
`str`, but on a typical CI/build agent `pluginkit` exists yet zero Safari web extensions
are installed, so `collect()` returns early at the empty-stdout guard
(`safari.py:142-144`) and the `for item in ...` loop body never executes. The test is
therefore green even if `_parse_pluginkit_output` or the plist-read loop is broken on
real output. It only proves "does not raise," not "parses real output."
**Fix:** Keep the no-raise smoke test, but also assert against the captured real-output
fixture at the unit level by feeding `_BITWARDEN_FIXTURE` through a mocked `collect()`
that points at a fabricated appex (or, minimally, document that the captured fixture in
`test_parse_extracts_bitwarden_path` is the parsing-correctness guarantee and the live
test is no-raise only). Consider asserting `result.sections[0].items` count > 0 only when
extensions are detected, guarded separately.

## Info

### IN-01: Missing `__all__` export list (inconsistent with siblings)

**File:** `src/maccat/collectors/safari.py:1-21`
**Issue:** `firefox.py` (`__all__ = ["FirefoxCollector"]`) and `__init__.py`
(`__all__ = [...]`) declare explicit export lists, but `safari.py` does not. Minor
consistency drift; `_parse_pluginkit_output` and `_read_appex_name` are imported by name
in tests so an `__all__` should still expose `SafariCollector` at minimum.
**Fix:** Add `__all__ = ["SafariCollector"]` after the constants block.

### IN-02: `available()` is dead for orchestration

**File:** `src/maccat/collectors/safari.py:103-105`
**Issue:** The orchestrator (`cli.py:318-319`) calls `collect()` directly and never calls
`available()`; `collect()` independently re-checks `_PLUGINKIT.is_file()` at line 117.
The `available()` override is thus unreachable in the production path. This mirrors the
sibling convention (firefox.py has no `available()` either), so it is not a bug — but the
duplicated existence check is worth a note for maintainers who might assume `available()`
gates collection.
**Fix:** Either remove `available()` or add a comment that it exists only for symmetry /
potential future gating; keep the in-`collect()` check as the source of truth.

### IN-03: Detection diverges from spec'd `shutil.which` mechanism (acceptable)

**File:** `src/maccat/collectors/safari.py:19,105,117`
**Issue:** Focus item (a) references `shutil.which`/OSError for absence detection. The
implementation hardcodes `Path("/usr/bin/pluginkit").is_file()` instead. On macOS
`pluginkit` is always at `/usr/bin/pluginkit`, and the hardcoded constant is what the
tests monkeypatch, so this is functionally correct and never-raising. Flagged only so the
deviation from the stated mechanism is on record.
**Fix:** No change required. If alignment with the spec wording is desired, switch to
`shutil.which("pluginkit")` and adjust the test monkeypatch target accordingly.

---

_Reviewed: 2026-06-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 29-safari-extensions
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/maccat/collectors/safari.py
  - tests/collectors/test_safari.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 29: Code Review Report (Iteration 2)

**Reviewed:** 2026-06-17
**Depth:** standard
**Files Reviewed:** 2
**Status:** clean

## Summary

Re-review of the Safari extensions collector after iteration-1 fixes for WR-01
(name fallback chain), WR-02 (parent-app fallback tests), and WR-03 (smoke test
strengthening / `__all__`). All three prior findings are confirmed resolved. No
new BLOCKER or WARNING defects were found. Never-raising guarantees remain
intact. One minor INFO observation is noted below (non-blocking, no fix
required).

### WR-01 verification — name fallback chain (RESOLVED)

`_read_appex_name` (safari.py:40-97) implements the full 5-step chain exactly as
documented, in order:

1. `CFBundleDisplayName` (appex) — line 61-67
2. `CFBundleName` (appex), rejected if `== "safari"` (case-insensitive) — line 70-76
3. parent app `CFBundleDisplayName` — line 85-87
4. parent app `CFBundleName`, rejected if `== "safari"` — line 88-94
5. `bundle_id` final fallback — line 97

- **Never empty:** `bundle_id` is validated non-empty in `collect()` (lines
  168-173) before `_read_appex_name` is ever called, so step 5 always yields a
  usable string.
- **Never "safari":** both `CFBundleName` steps reject the literal "safari"
  case-insensitively. `CFBundleDisplayName` is intentionally *not* rejected (an
  author-supplied display name is authoritative; only the generic binary
  `CFBundleName` is the known false positive). Matches `test_display_name_wins`.
- **Order correct:** each branch returns immediately on success, so precedence
  is exactly DisplayName(appex) > Name(appex) > DisplayName(parent) >
  Name(parent) > id.
- Type-guarded throughout (`isinstance(..., str)` before `.strip()`); whole
  function wrapped in `try/except Exception` → never raises.

### WR-02 verification — parent-app fallback tests (RESOLVED)

`test_parent_app_display_name_fallback` and `test_parent_app_bundle_name_fallback`
both construct a realistic `SomeApp.app/Contents/PlugIns/safari.appex` layout.
The appex's own plist supplies the rejected `CFBundleName="safari"` and no
`CFBundleDisplayName`, forcing resolution into the parent branch. The path math
holds: `appex.parent` (PlugIns) → `.parent` (Contents) → `.parent` (SomeApp.app)
→ `/Contents/Info.plist`. Both tests genuinely exercise lines 78-94 (step 3 and
step 4 respectively), not an earlier short-circuit.

### WR-03 verification — smoke test reaches per-extension parsing (RESOLVED)

`test_live_pluginkit_returns_paths_without_raising` now probes raw `pluginkit`
first, skips when absent or zero extensions, then runs the real collector and
asserts each emitted item is a non-empty string ending in `]` with a `[`
present — proving the per-extension plist-read path produced a
`CFBundleIdentifier`. This reaches per-extension parsing rather than
short-circuiting on the empty-stdout branch. `__all__ = ["SafariCollector"]`
present (IN-01 resolved).

### Never-raising / no new defects

- `collect()`: every external interaction guarded — pluginkit absence (line
  129), `OSError` on subprocess (line 140), non-zero exit (line 147), empty
  stdout (line 154), and a per-extension `try/except Exception` (lines 162-180)
  that `continue`s so one bad plist never aborts the run.
- `_parse_pluginkit_output`: pure string/regex, no I/O, cannot raise.
- `available()`: `Path.is_file()` does not raise.
- Shallow/short appex paths: `appex.parent.parent.parent` clamps at filesystem
  root in pathlib; the subsequent `.is_file()` returns False and resolution
  degrades to `bundle_id`. No crash.
- `shell=False` on the subprocess call with a list argv — no command-injection
  surface.

## Info

### IN-01: Smoke-test `[id]` shape assertion can theoretically misfire on an id-promoted item

**File:** `tests/collectors/test_safari.py:467`
**Issue:** The live smoke test asserts `item.rstrip().endswith("]")` as proof the
`[id]` bracket group was emitted. `emit_item` only appends `[id]` when both a
name and an id are present; if a real extension had an empty/whitespace name the
id is promoted and the brackets are *suppressed* (`emit_item` format.py:31-32,
"id only" branch returns the bare id with no brackets). In that case the
assertion would fail even though the collector behaved correctly. This is
extremely unlikely in practice (a real Safari extension nearly always has a name,
and the name fallback chain resolves to `bundle_id` rather than empty, so the
name segment is never empty here) and it only affects a live-gated dev-machine
test, so it is non-blocking.
**Fix (optional):** Assert the parsed shape more tolerantly — e.g. require
`"[" in item and item.rstrip().endswith("]")` only, which already holds given the
never-empty name guarantee; the current assertion is in fact safe today because
`_read_appex_name` never returns an empty name. No change required for ship.

---

_Reviewed: 2026-06-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

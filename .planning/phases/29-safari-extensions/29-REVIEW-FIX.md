---
phase: 29-safari-extensions
fixed_at: 2026-06-17T00:00:00Z
review_path: .planning/phases/29-safari-extensions/29-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-06-17
**Source review:** .planning/phases/29-safari-extensions/29-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03)
- Fixed: 3
- Skipped: 0
- Bonus: IN-01 (`__all__`) applied as a trivial one-liner per the prompt's allowance.

## Fixed Issues

### WR-01: Name fallback chain skips the appex's own `CFBundleName`

**Files modified:** `src/maccat/collectors/safari.py`, `tests/collectors/test_safari.py`
**Commits:** `d4526a2` (source + IN-01), `ed92e8a` (test)
**Applied fix:** Inserted the locked chain step between the appex `CFBundleDisplayName`
check and the parent-app fallback: after the appex DisplayName fails, the collector now
consults the appex's OWN `CFBundleName`, accepting it only when non-empty and not the
generic binary name `"safari"` (case-insensitive). Updated the docstring resolution chain
to the 5-step order (appex DisplayName → appex Name≠safari → parent DisplayName → parent
Name≠safari → bundle_id). Added `test_appex_own_bundle_name_used`: an appex with no
`CFBundleDisplayName` but `CFBundleName="Bitwarden"` now resolves to `"Bitwarden"`, not
the bundle id. Verified: ruff clean, mypy --strict clean, test passes.

### WR-02: Parent-app fallback branch is entirely untested

**Files modified:** `tests/collectors/test_safari.py`
**Commit:** `d994cc7`
**Applied fix:** Added two tests that build a realistic
`tmp/SomeApp.app/Contents/PlugIns/safari.appex` layout with the parent app's
`Contents/Info.plist` and an appex plist lacking a usable name (no DisplayName,
`CFBundleName="safari"` which is rejected). `test_parent_app_display_name_fallback`
asserts the parent's `CFBundleDisplayName` ("SomeApp") is used; `test_parent_app_bundle_name_fallback`
asserts the parent's `CFBundleName` ("SomeApp") is used when the parent has no DisplayName.
These exercise the `.parent.parent.parent` traversal that was previously never hit.
Verified: ruff clean, mypy --strict clean, both tests pass.

### WR-03: Live smoke test never reaches per-extension parsing

**Files modified:** `tests/collectors/test_safari.py`
**Commit:** `0bd23b3`
**Applied fix:** Strengthened `test_live_pluginkit_returns_paths_without_raising`. It now
probes raw `pluginkit` first and `pytest.skip`s when pluginkit is absent OR returns zero
extensions (keeping CI without Safari extensions green), and a second skip guards the case
where pluginkit reports extensions but none parse into items. When items ARE produced, it
asserts each is a non-empty string ending in a `[id]` bracket group — proving the
parse + plist-read path ran end-to-end rather than short-circuiting at the empty-stdout
guard. Added `import subprocess`. On the dev machine (Bitwarden present) the test now PASSES
(not skips), validating real-output parsing. Verified: ruff clean, mypy --strict clean.

## Notes on Info findings (out of critical_warning scope)

- **IN-01 (missing `__all__`):** Applied as a trivial one-liner —
  `__all__ = ["SafariCollector"]` after the constants block, matching `firefox.py`
  (`__all__ = ["FirefoxCollector"]`). Folded into commit `d4526a2`.
- **IN-02 (`available()` reachability):** Not fixed. Out of scope and explicitly a
  non-bug (mirrors sibling convention). No change.
- **IN-03 (hardcoded `/usr/bin/pluginkit`):** Not fixed. Out of scope; reviewer marked
  "No change required" — functionally correct and never-raising on macOS.

---

_Fixed: 2026-06-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

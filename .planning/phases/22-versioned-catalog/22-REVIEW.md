---
phase: 22-versioned-catalog
reviewed: 2026-06-16T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - src/maccat/helpers/plist_version.py
  - src/maccat/collectors/homebrew.py
  - src/maccat/collectors/setapp.py
  - src/maccat/collectors/webapps.py
  - tests/collectors/test_homebrew.py
  - tests/collectors/test_setapp.py
  - tests/helpers/test_plist_version.py
  - tests/test_golden_parity.py
findings:
  critical: 1
  warning: 1
  info: 2
  total: 4
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 22 adds version strings to four collectors (Homebrew formulae/casks via
`brew --versions`, Setapp apps and web-installed apps via a new shared
`plist_version` helper). The implementation is structurally sound: the helper is
correctly shared by two collectors, the walrus-operator filter in
`HomebrewCollector.collect()` is correct, the `raw=True` / no-`flush_section`
invariant is preserved throughout, exactly three parity cases are skipped (not
xfailed, not regenerated), and `update-list.sh` is untouched.

One BLOCKER was found: `get_plist_version` unconditionally calls `.get()` on the
return value of `plistlib.load()` outside the `try` block. `plistlib.load()` can
legally return a non-dict root (e.g. a plist whose root is an XML `<array>`), in
which case `.get()` raises `AttributeError` and escapes the function entirely —
violating the stated "never raises" contract and crashing the catalog run for any
app that ships such a plist.

One WARNING was found: `path.stat()` on line 41 of `plist_version.py` is also
outside the `try` block, so a file deleted between the `is_file()` check and the
`stat()` call raises an uncaught `FileNotFoundError`.

The ordering/determinism concern (VER-06) is safe: appending ` (version)` to all
names preserves sort order because the comparison resolves at the differing byte
within the names themselves, before reaching any appended suffix. The
mixed-versioned/unversioned edge case (name-only degradation) was traced
exhaustively — `(` (ord 40) sorts before every uppercase letter and digit, so
`"Foo.app (1.0)"` always orders identically to bare `"Foo.app"` relative to any
other entry. No ordering inversion is possible.

No `flush_section` routing was introduced for any of the four changed sections.
The three golden files for the changed sections retain their stale name-only
content (correctly not regenerated). The live `test_live_zsh_parity` test was
never active for these three sections (they are in `NON_ZSH_CAPTURABLE`) — this
is pre-existing and not a Phase 22 regression.

---

## Critical Issues

### CR-01: `data.get()` is outside the `try` block — crashes on non-dict plist root

**File:** `src/maccat/helpers/plist_version.py:52-53`

**Issue:** `plistlib.load()` can return any Python object — its return type is
`Any`. A valid XML plist file whose root element is `<array>` (not `<dict>`)
parses successfully without raising, but the returned `list` object has no `.get()`
method. The `try / except Exception` block (lines 44-49) only wraps the
`plistlib.load()` call. The dict-access loop on lines 52-55 is **outside** the
try block, so `.get()` on a list root raises `AttributeError`, escapes the
function, and propagates up through `_versioned_entry()` into `collect()` —
aborting the entire section.

Confirmed with a live reproduction:

```
$ python3 -c "
import plistlib, io
data = plistlib.loads(plistlib.dumps([{'k': 'v'}]))
data.get('CFBundleShortVersionString')   # AttributeError: 'list' object has no attribute 'get'
"
```

Array-root plists are rare in macOS app bundles but are legal XML plist syntax and
do exist in the wild (e.g. some helper-app frameworks and embedded frameworks use
them). The module docstring and function docstring both promise "Never raises".

The annotation `data: dict[str, object]` (line 46) is incorrect — it is a
programmer assertion, not enforced by `plistlib`. `mypy --strict` accepts it
silently because `plistlib.load` returns `Any`, which is assignable to any type.

**Fix:** Either extend the `try` block to cover the dict access, or add an
`isinstance` guard after loading:

```python
    try:
        with path.open("rb") as fh:
            data = plistlib.load(fh)
    except Exception:  # noqa: BLE001
        return ""

    # Guard: plistlib.load can return a list (array-root plist) — not a dict.
    if not isinstance(data, dict):
        return ""

    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        value = data.get(key)
        if value is not None:
            return str(value)

    return ""
```

A matching test should be added to `tests/helpers/test_plist_version.py`:

```python
def test_array_root_plist_returns_empty(self, tmp_path: Path) -> None:
    """Plist with array root (not dict) returns empty string without raising."""
    plist_file = tmp_path / "Info.plist"
    plist_file.write_bytes(plistlib.dumps([1, 2, 3], fmt=plistlib.FMT_XML))
    assert get_plist_version(plist_file) == ""
```

---

## Warnings

### WR-01: `path.stat()` is outside the `try` block — can raise on TOCTOU race

**File:** `src/maccat/helpers/plist_version.py:41`

**Issue:** The fast-path check on line 41 is:

```python
if not path.is_file() or path.stat().st_size == 0:
    return ""
```

`path.is_file()` is safe (returns `False` on any OS error). But `path.stat()` is
a separate syscall outside the `try` block. If a file is deleted between the
`is_file()` call and the `stat()` call — possible when scanning a live
`/Applications` directory during an app update or uninstall — `stat()` raises
`FileNotFoundError` (a subclass of `OSError`), which escapes the function and
violates "never raises".

The probability during a normal catalog run is very low, but `/Applications` is
written by system processes concurrently with the scan, making this a realistic
race.

**Fix:** Wrap the stat guard inside the `try` block, or simply let `open()` +
`plistlib.load()` handle the size check implicitly (zero-byte files cause
`plistlib` to raise `InvalidFileException`, which the `except Exception` already
catches):

```python
    # Fast-path: non-existent path (is_file is safe — returns False on error)
    if not path.is_file():
        return ""

    try:
        with path.open("rb") as fh:
            raw = fh.read()
        if not raw:          # zero-byte: plistlib would raise anyway, short-circuit
            return ""
        data = plistlib.loads(raw)
    except Exception:  # noqa: BLE001
        return ""
```

Alternatively, simply move the `stat()` inside the `try` block:

```python
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return ""
        with path.open("rb") as fh:
            data = plistlib.load(fh)
    except Exception:  # noqa: BLE001
        return ""
```

---

## Info

### IN-01: `test_sort_order_after_annotation` assertion is partially tautological

**File:** `tests/collectors/test_setapp.py:204-217`

**Issue:** The test verifies `items == sorted(items)`. Since `items` is produced by
`SetappCollector.collect()` which explicitly calls `entries.sort()`, this assertion
can only fail if the sort call is accidentally removed — it proves nothing about
correctness of the sort key. The additional assertion `items.index("Acme.app (1.0)") < items.index("Zoom.app (2.0)")` is meaningful, but the test never checks a
case where a name's versioned form would sort differently than its bare form (i.e.
a name that is a strict prefix of another name, where one degrades to name-only).
The test name implies it is testing a non-obvious ordering property, but the chosen
fixture (`Acme` vs `Zoom`) makes the assertion trivially true regardless of whether
sort happens before or after annotation.

**Fix:** Add a fixture pair where sort order under the annotated strings *could*
differ from sort order under bare names — e.g. `"App.app"` (versioned) and
`"App.app Helper"` (no plist, degraded to name-only). This exercises the mixed
versioned/unversioned path that the test's docstring implies.

### IN-02: `test_homebrew_collect_formulae_and_casks` patches `shutil.which` at wrong scope

**File:** `tests/collectors/test_homebrew.py:29`

**Issue:** The patch target is `"shutil.which"` (the original module), not
`"maccat.collectors.homebrew.shutil.which"` (the name as bound in the collector's
module). This works today because `homebrew.py` imports `shutil` and calls
`shutil.which(...)` — patching `shutil.which` globally does redirect the call. But
this is fragile: if the import is changed to `from shutil import which`, the global
patch would stop working. The other test in the same file (`test_homebrew_absent_returns_fallback`) has the same issue. Compare with
`test_golden_parity.py` line 170, which correctly patches
`"maccat.collectors.homebrew.shutil.which"`.

**Fix:** Use the module-scoped patch target consistently:

```python
patch("maccat.collectors.homebrew.shutil.which", return_value="/usr/local/bin/brew")
```

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

---
phase: 24-catalog-format-fix-parser-foundation
reviewed: 2026-06-16T19:16:51Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/maccat/collectors/mas.py
  - src/maccat/reinstall/parser.py
  - src/maccat/reinstall/__init__.py
  - tests/collectors/test_homebrew.py
  - tests/reinstall/test_parser_contract.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-06-16T19:16:51Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 24 changes: `mas.py` (now preserving the App Store numeric ID
via `emit_item`), the new `reinstall/parser.py` (right-anchored regex + section
state machine that inverts `catalog/format.py::emit_item`), the empty
`reinstall/__init__.py` package marker, and the two test files.

The core design is sound and the existing test suite passes (36 passed). The
regex is well-constructed (no catastrophic backtracking observed even on
50k-char / many-open-paren inputs) and the documented "right-anchored / last
parens wins" lossy cases are correctly tested. The state machine correctly
handles the byte protocol of `CatalogWriter.write_section`/`write_lines` for the
happy path and the EOF-flush fallback.

No Critical issues found (no injection, no secrets, no crashes on the documented
paths; `subprocess.run` is invoked with `shell=False` and a list argv). However
there are real robustness and convention gaps — most notably **unhandled
subprocess exceptions in `mas.py` that can crash the whole CLI**, a **silent
non-zero-exit path that violates the project's warn-and-continue convention**,
and **two undocumented/untested silent-degradation paths in the parser** (nested
parens, trailing whitespace). The Phase-23 verbatim `_run` helper in
`homebrew.py` was also not reused by `mas.py`, leaving divergent error handling
between the two raw collectors.

## Warnings

### WR-01: `mas list` subprocess can raise an unhandled exception and crash the CLI

**File:** `src/maccat/collectors/mas.py:75-77`
**Issue:** `subprocess.run(["mas", "list"], ...)` has no `try/except`. `available()`
checks `shutil.which("mas")` earlier, but there is a TOCTOU window (tool removed
between check and run) and other failure modes (`PermissionError`, `OSError`
from exec, the binary being a broken symlink). Any of these raises out of
`collect()`, propagates through the orchestrator loop in `cli.py:248-257`, and
aborts the entire catalog run — directly violating the project's mandatory
"graceful degradation: a missing tool must warn-and-continue" constraint
(CLAUDE.md / project constraints). `homebrew.py` has the same gap but at least
funnels through `_run`; `mas.py` calls `subprocess.run` inline.
**Fix:** Wrap the call and degrade to the existing error Section:
```python
try:
    result = subprocess.run(
        ["mas", "list"], capture_output=True, text=True, shell=False
    )
except OSError as exc:
    print(f"  WARNING: could not run mas: {exc}", file=sys.stderr)
    return CollectorResult(
        sections=[Section(title=TITLE,
                          items=["Could not retrieve App Store list."],
                          raw=True)]
    )
```

### WR-02: mas non-zero exit returns an error section silently (no stderr warning)

**File:** `src/maccat/collectors/mas.py:78-87`
**Issue:** When `mas list` exits non-zero, the collector returns the
"Could not retrieve App Store list." section but prints **nothing** to stderr.
Every other degradation path in this file (mas absent, line 59-62) and the sibling
homebrew collector (`homebrew.py:55`) emit a `WARNING:`/`NOTE:` to stderr per the
project's "Output Conventions" (warn-and-continue). The user running the CLI gets
no signal that the App Store section silently failed — they only discover the gap
by diffing the catalog later. This is the "silent fallback converts hard failure
into silent corruption" anti-pattern called out in the root CLAUDE.md.
**Fix:** Emit a stderr warning before returning the error section:
```python
if result.returncode != 0:
    print(
        f"  WARNING: mas list failed (exit {result.returncode}).",
        file=sys.stderr,
    )
    return CollectorResult(...)
```

### WR-03: Parser silently drops version on names containing nested parentheses

**File:** `src/maccat/reinstall/parser.py:38-49`
**Issue:** Branch 1/2 of `ITEM_RE` use `\((?P<version>[^)]+)\)`, where `[^)]+`
cannot span an inner `)`. For a real-world line like `Foo (Bar (Baz)) [9]`,
branch 1 fails (the version group can't reach the trailing `]`), branch 2 fails,
and the regex falls through to **branch 3 (id-only)**, yielding
`name="Foo (Bar (Baz))", version=None, id="9"` — the version is silently lost
without any round-trip-lossy flag. The `ADVERSARIAL_CASES` table in
`test_parser_contract.py:36-45` covers single-level embedded parens but **not**
nested parens, so this lossy path is both undocumented and untested. Given the
module's purpose (rebuild an environment from the catalog), silently dropping a
version is a data-fidelity defect.
**Fix:** Either (a) add a nested-paren `ADVERSARIAL_CASES` row and document it as
KNOWN LOSSY in the module docstring so the behavior is an explicit contract, or
(b) make the version group balance one level of nesting, e.g.
`\((?P<version>(?:[^()]|\([^()]*\))+)\)`. Option (a) is lower-risk and matches the
existing "documented lossy" pattern; pick one and lock it with a test.

### WR-04: Trailing whitespace on an item line silently degrades it to name-only

**File:** `src/maccat/reinstall/parser.py:48` (the `$` anchor) and `_parse_item_line`
**Issue:** `ITEM_RE` anchors the optional version/id group directly against `$`
with no tolerance for trailing whitespace. A line such as `"name (1.0) "`
(one trailing space) fails branches 1-3 and falls back to name-only:
`name="name (1.0) ", version=None, id=None`. `emit_item` never produces trailing
whitespace, so this is harmless for self-produced catalogs, but the parser's
docstring promises it "Never raises ... Unparseable lines are returned as
name-only" — implying robustness for external/edited catalogs, which it does not
actually deliver for the common trailing-whitespace case. This is a silent
data-loss path with no test coverage.
**Fix:** Strip the line before matching (`raw_line.rstrip()` for the regex while
preserving the original in `raw_line`), or add optional trailing whitespace to the
pattern: insert `\s*` before the final `$`. Add a test row for a trailing-space
line.

### WR-05: Header section is parsed as a spurious empty `ParsedSection` (no test coverage)

**File:** `src/maccat/reinstall/parser.py:136-187`
**Issue:** Real catalogs (see `cli.py:246-257`) begin with
`w.write_section("Installed Mac Software List")` followed immediately by the next
collector's `write_section` — i.e. the header has a title + separator but **zero
content lines**. Tracing the state machine: the leading `\n` of the *next*
section is seen as a blank line in COLLECTING and flushes
`ParsedSection(title="Installed Mac Software List", items=[], degraded=False)`.
So every parsed catalog will contain a leading empty section that downstream
Phase-25 reinstall logic must know to skip. None of the integration tests in
`TestParseCatalog` exercise the actual multi-section-with-header layout that
`cli.py` produces (`_CATALOG_TWO_SECTIONS` omits the header), so this behavior is
unverified and a likely surprise for the consumer.
**Fix:** Add an integration test that feeds the real header+sections layout and
asserts the resulting section list (documenting whether the empty header section
is expected output, or filtering it in `parse_catalog`). Decide and lock the
contract rather than leaving it implicit.

## Info

### IN-01: `mas.py` does not reuse the `_run` helper pattern from `homebrew.py`

**File:** `src/maccat/collectors/mas.py:75-88`
**Issue:** `homebrew.py:26-34` centralizes subprocess invocation + non-zero
handling in `_run`. `mas.py` re-implements an inline `subprocess.run` with
different (and weaker — see WR-01/WR-02) error handling. Two raw collectors with
divergent subprocess error semantics is a maintainability hazard.
**Fix:** Consider a shared helper on `Collector` (base) or mirror the `_run`
shape so both collectors degrade identically.

### IN-02: Parser docstrings say "four shapes" but `emit_item` produces six

**File:** `src/maccat/reinstall/parser.py:113` (and `:36-37`)
**Issue:** `parse_catalog`'s docstring states "Inverts all four emit_item() line
shapes", but `emit_item` (format.py:19-25) and the test table
(`ROUND_TRIP_CASES`, 6 rows) enumerate six shapes (including the two id-promoted
forms). The comment at lines 31-37 correctly says "all six emit_item output
shapes", so the docstrings are internally inconsistent.
**Fix:** Update the line-113 docstring to "all six emit_item line shapes".

### IN-03: 2-field mas line where field 2 is itself parenthesized produces an odd name

**File:** `src/maccat/collectors/mas.py:42-51`
**Issue:** For input `"123  (1.0)"` (id + a single parenthesized token, no real
name), `len(parts) == 2`, so the `>= 3` version-stripping branch is skipped and
the result is `name="(1.0)", version="", id="123"` → emitted as `(1.0) [123]`.
This is a degenerate mas-output case (unlikely in practice) but the name now
literally contains parens, which the parser will then re-interpret as a version on
the way back. Round-trip stability for this input is not guaranteed and not
tested.
**Fix:** Low priority. If desired, treat a lone parenthesized token after the id
as a version with an empty name, or add a test pinning the current behavior.

### IN-04: `id` field uses `# noqa: A003` to shadow the builtin

**File:** `src/maccat/reinstall/parser.py:62`
**Issue:** `ParsedItem.id` shadows the `id` builtin (suppressed with `noqa: A003`).
This is an accepted, documented tradeoff for domain clarity and is fine — noting
only that it forces `id=...` keyword usage and could confuse readers expecting the
builtin. No action required; flagged for completeness.

---

_Reviewed: 2026-06-16T19:16:51Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 31-markdown-only-reinstall-parser
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/maccat/reinstall/parser.py
  - src/maccat/reinstall/cli.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `parse_markdown_catalog`, `_unescape_cell`, `_parse_markdown_row`, and the updated
`run_reinstall` orchestrator in `cli.py`. The implementation is substantially correct. The
round-trip losslessness invariant holds for all reachable emit_item-derived inputs, the
frontmatter guards reliably reject legacy `.txt` catalogs and malformed `.md` files, and no
parsed value is ever executed. Two warnings and two informational items were found; no
blockers.

**Round-trip correctness (confirmed):** The column-split-on-` | ` approach is correct by
construction: `_escape_cell` converts every literal `|` to `\|`, so the only ` | ` substrings
remaining in an emitted row are the genuine column delimiters. `_unescape_cell`'s pipe-first
order is mathematically equivalent to backslash-first for this escape scheme — both produce
the correct original value for all adversarial inputs (lone backslash, lone pipe,
backslash-pipe, double-backslash). `str.strip()` applied before unescape correctly handles
the space-padded cell format.

**Security posture (confirmed):** No `eval`, no subprocess calls in parser or cli. Emitter
guards command context with `shlex.quote()` and comment context with `safe_comment_value()`.
The generated `reinstall.sh` is written at mode `0o644` (not executable) and is never
auto-run. ITEM_RE and the body-scan logic show no ReDoS risk (negated character classes,
no catastrophic alternation).

---

## Warnings

### WR-01: `degraded` field silently lost in markdown round-trip — downstream assumption gap

**File:** `src/maccat/reinstall/parser.py:347-348`

**Issue:** `parse_markdown_catalog` never sets `ParsedSection.degraded = True`. This is
structurally correct: the markdown emitter (`catalog/markdown.py`) erases the distinction
between truly empty sections and degraded sections — both render as `(none found)` with no
table rows. After a markdown round-trip, a section that was degraded (e.g., `brew` not
installed) returns with `degraded=False, items=[]`.

The emitter's `_should_skip` in `emitter.py:62` is:
```python
return section.degraded or len(section.items) == 0
```

This means `_should_skip` still returns `True` for degraded sections that came through the
markdown parser (because `items == []`). The current downstream behavior is therefore
accidentally correct. However, any future consumer that gates logic specifically on
`section.degraded` (rather than `items == []`) will silently mis-classify markdown-parsed
degraded sections as clean-but-empty sections.

**Fix:** Document this known lossiness explicitly on `parse_markdown_catalog`. Add a comment
at the `MD_NONE_FOUND` handling block (line 347-349) that states why `degraded` is never
set to True for markdown-parsed catalogs:

```python
elif line == MD_NONE_FOUND:
    # Markdown format does not distinguish "degraded" from "empty" —
    # both are rendered as "(none found)" by the emitter. After a
    # markdown round-trip, degraded sections always return with
    # degraded=False and items=[]. Downstream consumers must use
    # `len(section.items) == 0` rather than `section.degraded` to
    # skip empty sections parsed from .md files.
    pass
```

---

### WR-02: `if not lines` guard is dead code — masks a real edge case

**File:** `src/maccat/reinstall/parser.py:319`

**Issue:** The frontmatter validation guard reads:

```python
if not lines or lines[0] != "---":
```

`text.split("\n")` on any string — including `""` (empty file) — always returns a list with
at least one element (`[""]`). Therefore `not lines` is permanently `False` and the branch
is dead code. This is harmless today because `lines[0] != "---"` catches the empty-file
case (`""` != `"---"`). However, the dead branch creates a misleading contract comment: the
docstring says the function raises `ValueError` when the file "lacks a valid opening `---`
frontmatter fence", and a reader relying on the dead branch as a guard against empty-`lines`
is reasoning incorrectly.

The deeper concern: the dead code signals that the author may have been thinking of a
`readlines()` model (which returns `[]` for empty files) rather than `split("\n")` (which
never returns `[]`). If `read_text` is ever changed to `readlines()` the guard becomes
necessary and the dead branch would save it — but in the current code it is actively
misleading.

**Fix:** Remove the dead branch and tighten the comment:

```python
# text.split("\n") always yields at least [""], so lines is never empty.
# Check only for missing opening fence.
if lines[0] != "---":
    raise ValueError(
        f"{path} is missing valid YAML frontmatter (no opening '---' fence). "
        f"It may be a legacy .txt catalog renamed to .md. "
        f"Convert it first with: maccat convert --from {path}"
    )
```

---

## Info

### IN-01: `_unescape_cell` order-independence comment is accurate but under-specified

**File:** `src/maccat/reinstall/parser.py:258-260`

**Issue:** The docstring states "Both orders are mathematically correct for this escape
scheme" without proof. This is true — the two escape tokens (`\\` and `\|`) share no
prefix/suffix relationship that could cause interference — but the claim is non-obvious and
will require a future maintainer to reason through it when considering modifications to the
escape scheme. If the escape scheme is ever extended (e.g., escaping backticks), the
order-independence claim would need re-verification.

**Fix:** Extend the comment to state the invariant that makes order-independence hold:

```python
# Order independence holds because the two escape tokens ('\\\\' and '\\|')
# are disjoint: replacing one cannot create or destroy the other. This
# invariant must be verified if the escape scheme is ever extended.
```

---

### IN-02: Structural mismatch fallback in `_parse_markdown_row` conflates all column content into name

**File:** `src/maccat/reinstall/parser.py:276-278`

**Issue:** When `len(cols) != 3` (structural mismatch — row has the wrong number of
pipe-delimited columns), the fallback is:

```python
name = _unescape_cell(inner)
return ParsedItem(name=name or row, version=None, id=None, raw_line=row)
```

`inner` is the full interior of the row (everything between leading `| ` and trailing ` |`),
which for a malformed row may include all three columns' worth of text joined by whatever
delimiters were present. The recovered `name` therefore mixes column content. The `raw_line`
field preserves the original row, so no data is lost, but the `name` field is semantically
garbled for any consumer that uses it.

This only fires for rows that are not well-formed emit_item outputs (hand-edited files,
corrupted catalogs). For the current downstream (emitter), a garbled name is shell-quoted
and echoed in the manual checklist — ugly but not dangerous.

**Fix:** No code change required for the current use case. Document the fallback intent
explicitly:

```python
# Structural mismatch: fewer or more than 3 pipe-delimited columns.
# This only arises from hand-edited or externally generated .md files.
# raw_line preserves the original row; name is a best-effort concatenation
# of all cell content (garbled but shell-safe via shlex.quote in emitter).
name = _unescape_cell(inner)
return ParsedItem(name=name or row, version=None, id=None, raw_line=row)
```

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

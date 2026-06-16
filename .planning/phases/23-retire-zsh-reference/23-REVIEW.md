---
phase: 23-retire-zsh-reference
reviewed: 2026-06-16T15:56:04Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/test_helpers.py
  - tests/conftest.py
  - .github/workflows/ci.yml
  - README.md
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-06-16T15:56:04Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found (2 Info items only)

## Summary

Phase 23 is a deletion-and-docs phase: `update-list.sh`, the entire `tests/golden/` scaffold,
`tests/test_golden_parity.py`, `tests/test_update_list_integrity.py`, the `update_golden`
fixture, and the CI `zsh -n` syntax check are all gone. The only new logic is two test methods
in `tests/test_helpers.py` that cover the `isinstance(..., dict)` degradation branches added
in a prior phase.

All deletions are confirmed. The two new test methods correctly exercise the target branches.
`conftest.py` is clean (no dangling `update_golden`/golden references). CI YAML is valid and
all material gates (pytest/ruff/mypy, PYTHONHASHSEED matrix) are intact. README carries no
operational zsh references beyond the single permitted lineage note on the last line of the
Prerequisites section.

Two info-level items are flagged: stale inline cross-reference comments in two source helpers
that point to an unresolvable `REVIEW.md` label (the file does not exist at the referenced
implicit path), and the pre-existing `update-list.sh:NNNN` annotations throughout source and
test files that now point to a deleted file. Neither blocks the build or test suite.

## Narrative Findings (AI reviewer)

## Info

### IN-01: `# (See REVIEW.md CR-01)` / `# (See REVIEW.md WR-02)` in `chrome_name.py` and `vsc_name.py` are unresolvable

**Files:**
- `src/maccat/helpers/chrome_name.py:51`
- `src/maccat/helpers/chrome_name.py:67`
- `src/maccat/helpers/vsc_name.py:52`
- `src/maccat/helpers/vsc_name.py:65`

**Issue:** Four inline comments cite `REVIEW.md` with bare finding IDs (`CR-01`,
`WR-02`, `CR-02`, `WR-01`) but there is no `REVIEW.md` at the repo root, in
`src/maccat/helpers/`, or at any unambiguous relative path. A reader following the
reference cannot locate the document. Cross-checking the milestone archives shows no
single REVIEW that uses all four IDs with the descriptions implied by these comments
(graceful-degradation constraint, byte-parity constraint). The comments were authored
during initial development as forward-references to review findings that were never
surfaced in a corresponding file, or were written against a planning REVIEW.md that
was never co-located with the source.

This is purely a navigability issue; the code logic guarded by these comments is
correct and is now covered by the two new tests (Phase 23 ZSH-03).

**Fix:** Replace the unresolvable citations with self-contained prose that states the
constraint directly. Example for `chrome_name.py:51`:

```python
# A messages.json that is valid JSON but not an object (e.g. a top-level array)
# has no .items(). Degrade to ext_id rather than raising AttributeError and
# aborting the catalog run (graceful-degradation constraint).
if not isinstance(messages, dict):
    return ext_id
```

And for `chrome_name.py:67`:

```python
# A non-string .value.message (e.g. NLS v2 object) cannot be reproduced via
# str(); degrade to ext_id to avoid emitting a Python repr (byte-parity
# constraint — first match wins even if unusable).
```

Apply the same pattern in `vsc_name.py:52` and `vsc_name.py:65`.

---

### IN-02: Pervasive `update-list.sh:NNNN` cross-references throughout `src/` and `tests/` now point to a deleted file

**Representative locations (not exhaustive):**
- `src/maccat/helpers/chrome_name.py:17`
- `src/maccat/helpers/vsc_name.py:15`
- `src/maccat/catalog/writer.py:4`
- `src/maccat/catalog/format.py:3`
- `src/maccat/collectors/chrome.py:1`
- `src/maccat/collectors/vscode.py:3`
- `src/maccat/gitops.py:3`
- `src/maccat/retention.py:9`
- `tests/test_writer.py:5`
- `tests/test_format.py:3`
- `tests/collectors/test_chrome.py:3`
- `tests/test_identity.py:494`

**Issue:** Approximately 88 comments across `src/` (71) and `tests/` (17) cite
`update-list.sh` by line number as a behavioral spec anchor. The file was deleted in
this phase. The comments accurately described the original porting intent and remain
correct as documentation of implemented behavior; however, a reader with no access to
git history cannot verify the reference. No build, lint, or test gate fails because of
these comments.

The 23-CONTEXT.md explicitly permits this: the phase decision was to delete
`update-list.sh` outright, relying on git history if needed, and the scope for ZSH-04
was limited to operational references in README and docs — not internal code comments.

**Fix (optional, future cleanup):** Convert the most load-bearing spec comments
(e.g. `writer.py`, `format.py`, `chrome_name.py`) into self-contained behavioral
descriptions that do not require the deleted file. Lower-priority collector
comments can simply drop the line-number citation and retain the functional
description. No action required in this phase.

---

_Reviewed: 2026-06-16T15:56:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

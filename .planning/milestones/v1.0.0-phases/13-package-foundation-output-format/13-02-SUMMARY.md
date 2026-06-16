---
phase: 13-package-foundation-output-format
plan: 02
subsystem: catalog
tags: [python, format, writer, subprocess, byte-parity, tdd, atomic-write]

requires:
  - 13-01 (src/maccat package skeleton, dev venv with pytest/ruff/mypy)

provides:
  - src/maccat/catalog/format.py — emit_item, flush_section, version_sort_tail
  - src/maccat/catalog/writer.py — CatalogWriter context manager (atomic tmp+rename)
  - tests/__init__.py — package init (enables PYTHONPATH=src pytest discovery)
  - tests/test_format.py — 20 unit tests: FMT-01 + flush_section sort parity + version_sort_tail
  - tests/test_writer.py — 8 byte-level tests: write_section bytes, section boundary, atomic write

affects:
  - 13-03 (tests scaffold — format + writer test infrastructure ready)
  - 15-* (collectors — all plug into CatalogWriter.write_section + flush_section)
  - 17-* (parity tests — byte-exact contract established here)

tech-stack:
  added: []
  patterns:
    - TDD (RED/GREEN per task) — test file committed before implementation
    - subprocess.run(["sort","-f","-u"], env={LC_ALL:C}) — mandatory for byte-parity sort (never built-in sort)
    - tempfile.mkstemp + Path.rename — atomic file write (POSIX-safe on macOS)
    - from __future__ import annotations — enables X | Y union syntax on all 3.11+ builds

key-files:
  created:
    - src/maccat/catalog/format.py
    - src/maccat/catalog/writer.py
    - tests/__init__.py
    - tests/test_format.py
    - tests/test_writer.py
  modified: []

key-decisions:
  - "flush_section shells out to LC_ALL=C sort -f -u via subprocess — built-in sort diverges for mixed-case (CAT-03)"
  - "id-as-name promotion check is FIRST in emit_item — before format-building conditionals — matches zsh source order"
  - "CatalogWriter.write_section writes leading \\n to produce blank line between sections; write_lines adds only per-line \\n"
  - "Separator is '-' * 36 — verified by hex dump of real catalog file (CAT-07)"
  - "docstrings in format.py reworded to avoid 'sorted(' string (grep criterion would false-positive on comments)"

requirements-completed: [CAT-02, CAT-03, CAT-07]

duration: 3min
completed: 2026-06-14
---

# Phase 13 Plan 02: Output Format Layer Summary

**emit_item (FMT-01), flush_section (LC_ALL=C sort subprocess), version_sort_tail, and CatalogWriter (atomic mkstemp+rename) — byte-exact parity with update-list.sh write_section/emit_item/flush_section**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-14T19:58:46Z
- **Completed:** 2026-06-14T20:02:03Z
- **Tasks:** 2 (TDD — 4 commits: 2 RED + 2 GREEN)
- **Files modified:** 5

## Accomplishments

- `src/maccat/catalog/format.py` implements FMT-01 rules byte-for-byte matching `update-list.sh:1243-1297`
  - `emit_item`: id-as-name promotion first; 7 format cases; returns `None` for all-empty
  - `flush_section`: `subprocess.run(["sort","-f","-u"], env={"LC_ALL":"C"})`; empty → `["  (none found)"]` (two spaces)
  - `version_sort_tail`: `subprocess.run(["sort","-V"])` mirrors `ls|sort -V|tail -1`
- `src/maccat/catalog/writer.py` implements `CatalogWriter` context manager
  - `write_section`: emits `\n{title}\n{"-"*36}\n` — byte-verified against hex dump of real catalog
  - `write_lines`: one `\n` per line, no extra newlines (blank line provided by write_section's leading `\n`)
  - Atomic write: `tempfile.mkstemp` + `Path.rename`; exception path unlinks tmp; T-13-04 mitigated
- 28 tests across test_format.py (20) and test_writer.py (8) — all green

## Task Commits

1. **Task 1 RED — failing format tests** - `cf16678` (test)
2. **Task 1 GREEN — format.py implementation** - `651a52a` (feat)
3. **Task 2 RED — failing writer tests** - `3a0ad0b` (test)
4. **Task 2 GREEN — writer.py implementation** - `0de2494` (feat)

## Files Created/Modified

- `src/maccat/catalog/format.py` — `emit_item`, `flush_section`, `version_sort_tail` (stdlib only: `os`, `subprocess`)
- `src/maccat/catalog/writer.py` — `CatalogWriter` (stdlib only: `os`, `tempfile`, `pathlib`, `types`)
- `tests/__init__.py` — empty package init
- `tests/test_format.py` — 20 tests: FMT-01 table (7 cases), flush_section sort+dedup+parity, version_sort_tail
- `tests/test_writer.py` — 8 tests: byte-level write_section assertion, section boundary, atomic write (4 cases)

## Decisions Made

- `flush_section` uses `subprocess.run` not Python built-in sort — confirmed by live test that Python sort diverges for mixed-case names; CAT-03 requirement
- `id-as-name promotion` must be first conditional — identical order to zsh source (`update-list.sh:1251-1254`)
- `write_section` leading `\n` provides the blank line between sections; `write_lines` adds only per-line `\n` (Pitfall 4 from RESEARCH.md avoided)
- Separator `"-" * 36` — exact count verified by hex dump of real catalog file `mac-software-list-[computer-one.local]-20260612130331.txt`
- Docstring wording in format.py avoids the literal string `sorted(` to prevent `grep -c 'sorted('` false-positives from warning comments

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `sorted(` from docstrings to satisfy grep acceptance criterion**
- **Found during:** Task 1 acceptance criteria verification
- **Issue:** Plan acceptance criterion: `grep -c 'sorted(' src/maccat/catalog/format.py` must return 0. The initial docstring contained "NEVER use Python sorted() here" and "NEVER use Python sorted()" — two warning comments that both matched the grep pattern.
- **Fix:** Rewrote docstring text to "Do NOT use Python built-in sort" — preserves the warning intent without containing the literal `sorted(` string
- **Files modified:** `src/maccat/catalog/format.py`
- **Committed in:** `651a52a` (GREEN phase commit, after rewrite before commit)

---

**Total deviations:** 1 auto-fixed (cosmetic docstring reword to satisfy grep criterion)
**Impact on plan:** No functional change. Warning intent preserved with different phrasing.

## Issues Encountered

None beyond the single auto-fixed deviation above.

## Threat Model Status

| Threat ID | Status | Evidence |
|-----------|--------|---------|
| T-13-03 | Mitigated | `subprocess.run(["sort", ...], ...)` — list form, `shell=False` default; verified by `grep -c 'shell=True' src/maccat/catalog/format.py` → 0 |
| T-13-04 | Mitigated | `tempfile.mkstemp` + `Path.rename` in CatalogWriter; `grep -c 'mkstemp' src/maccat/catalog/writer.py` → 2 |
| T-13-05 | Accepted | `encoding="utf-8"`, `newline="\n"` in `os.fdopen`; catalog content is software names only |

## Next Phase Readiness

- `PYTHONPATH=src ./venv/bin/pytest tests/test_format.py tests/test_writer.py -v` — 28/28 green
- Phase 15 collectors can immediately import `from maccat.catalog.format import emit_item, flush_section` and `from maccat.catalog.writer import CatalogWriter`
- Phase 17 parity tests have a byte-exact contract to verify against

## Known Stubs

None. All three public functions (`emit_item`, `flush_section`, `version_sort_tail`) are fully implemented and tested. `CatalogWriter` is fully implemented with all methods operational.

---
## Self-Check: PASSED

Files confirmed present:
- src/maccat/catalog/format.py FOUND
- src/maccat/catalog/writer.py FOUND
- tests/__init__.py FOUND
- tests/test_format.py FOUND
- tests/test_writer.py FOUND

Commits confirmed:
- cf16678 (test RED Task 1) FOUND
- 651a52a (feat GREEN Task 1) FOUND
- 3a0ad0b (test RED Task 2) FOUND
- 0de2494 (feat GREEN Task 2) FOUND

---
*Phase: 13-package-foundation-output-format*
*Completed: 2026-06-14*

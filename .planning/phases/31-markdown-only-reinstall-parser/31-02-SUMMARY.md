---
phase: 31-markdown-only-reinstall-parser
plan: "02"
subsystem: reinstall/cli
status: completed-via-31-01-deviation
tags: [cli, reinstall, markdown, fixtures, subsumed]
dependency_graph:
  requires:
    - "31-01: parse_markdown_catalog + ValueError refusal contract"
  provides:
    - "run_reinstall consumes .md only (parse_markdown_catalog); legacy .txt + malformed .md refused with convert directive"
  affects:
    - "reinstall pipeline end-to-end; reinstall test fixtures now .md"
tech_stack:
  added: []
  patterns:
    - "ValueError → sys.exit('ERROR: ...') in CLI (same pattern as OSError; keeps parser pure/testable)"
key_files:
  created: []
  modified:
    - src/maccat/reinstall/cli.py
    - tests/reinstall/test_reinstall_cli.py
    - tests/reinstall/test_picker_and_reinstall_cli.py
decisions:
  - "31-02 scope was completed inside 31-01's worktree as auto-applied Rule-2 deviations, not as a separate executor run. Re-dispatching 31-02 would have found the work already committed and risked a conflicting no-op merge, so the orchestrator verified the acceptance criteria directly and recorded this SUMMARY instead."
requirements: [RIN-02]
---

# Plan 31-02 Summary — Reinstall CLI Markdown Wiring (subsumed by 31-01)

## Outcome

**31-02's full scope was delivered as part of plan 31-01's execution** (auto-applied
deviations under execute-plan Rule 2), because the `.txt` refusal contract (RIN-02) and
its tests could not be exercised without simultaneously wiring `cli.py` and updating the
reinstall CLI test fixtures. The 31-01 executor correctly recognized this coupling and
completed both plans' file sets in one atomic worktree.

Rather than re-dispatch a 31-02 executor over already-committed work (which would no-op
or conflict), the orchestrator verified 31-02's acceptance criteria directly against the
merged `main`.

## Commits (from the 31-01 worktree merge, HEAD 56f9ddc)

- `0e88146` feat(31-01): add parse_markdown_catalog and helpers to reinstall/parser.py
- `2cf0e46` feat(31-01): add TestMarkdownRoundTrip + TestMarkdownParserRefusal; wire cli.py to parse_markdown_catalog
- (fixture updates to `test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py` included in the same wave)

## 31-02 acceptance criteria — verified on merged main

- **cli.py wired to markdown parser:** `run_reinstall` does deferred-import of
  `parse_markdown_catalog` and calls it (cli.py:56,69); legacy `parse_catalog` no longer
  called by the reinstall pipeline. ✓
- **Error wiring:** `except OSError` expanded to `except (OSError, ValueError) as exc:
  sys.exit(f"ERROR: {exc}")` (cli.py:70). ✓
- **`.txt` refused (extension check):** `maccat reinstall --from old.txt` exits **1** with
  `ERROR: ... is not a markdown catalog (.md extension required). Convert it first with:
  maccat convert --from ...`. ✓
- **Malformed `.md` refused (content-sniff):** `maccat reinstall --from bad.md` (no
  frontmatter) exits **1** with `ERROR: ... is missing valid YAML frontmatter ... Convert
  it first with: maccat convert --from ...`. ✓ (Satisfies the CONTEXT.md "extension AND
  content-sniff" decision.)
- **No silent partial parse:** refusal happens in `parse_markdown_catalog` before any
  `ParsedCatalog` is returned; nothing is written or executed. ✓
- **Legacy `parse_catalog` importable + unchanged:** `from maccat.reinstall.parser import
  parse_catalog` succeeds; Phase 32 convert dependency preserved. ✓
- **Fixtures migrated:** `test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py`
  now use `.md` fixtures with valid frontmatter + tables. ✓

## Verification

- `./venv/bin/pytest tests/reinstall/` → 140 passed
- `./venv/bin/pytest tests/` → 690 passed (full suite)
- `./venv/bin/ruff check src/ tests/` → clean
- `./venv/bin/mypy --strict src/maccat` → clean (41 files)

## Self-Check: PASSED

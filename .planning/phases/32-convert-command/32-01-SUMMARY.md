---
phase: 32-convert-command
plan: "01"
subsystem: convert
tags: [convert, gitops, atomicity, bridge, legacy-txt]
dependency_graph:
  requires:
    - src/maccat/reinstall/parser.py::parse_catalog
    - src/maccat/catalog/markdown.py::render_markdown_catalog
    - src/maccat/collectors/base.py::Section
    - src/maccat/gitops.py (pre-existing guards)
  provides:
    - src/maccat/convert.py::run_convert
    - src/maccat/gitops.py::git_commit_convert
  affects:
    - src/maccat/cli.py (Plan 02 will wire subcommand)
tech_stack:
  added: []
  patterns:
    - Deferred imports per PKG-03 (all maccat.* imports inside function body)
    - Atomic replace: write_text before unlink (CONV-03 invariant)
    - No-clobber guard: sys.exit on target .md exists (USER OVERRIDE)
    - Bridge: ParsedCatalog -> list[Section(raw=True)] skipping header section
    - warn-and-continue pattern for git ops (mirrors git_commit_rename)
key_files:
  created:
    - src/maccat/convert.py
  modified:
    - src/maccat/gitops.py
decisions:
  - "Output filename uses txt_path.with_suffix('.md') — preserves original 14-digit timestamp, intentionally differs from frontmatter generated field"
  - "catalog_repo heuristic: txt_path.parent.parent — gracefully degrades via relative_to guard if wrong"
  - "Bridge skips ParsedSection with title == _HEADER_TITLE ('Installed Mac Software List') to prevent spurious ## heading"
  - "degraded flag from ParsedSection is intentionally not surfaced to emitter — both empty and degraded render as (none found)"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-18T23:30:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 32 Plan 01: Convert Core Pipeline Summary

**One-liner:** `run_convert` + `git_commit_convert` — `.txt`→`.md` atomic in-place replacement with bridge, frontmatter synthesis from current machine, and single-commit git staging.

## What Was Built

### Task 1: `src/maccat/convert.py` (created)

14-step orchestration pipeline in `run_convert(args)`:

1. Deferred imports per PKG-03 (`maccat.*` inside function body, stdlib at module level)
2. `txt_path = Path(args.from_path).expanduser().resolve()`
3. File existence check: `sys.exit("ERROR: ...")` if not `is_file()`
4. Readability check: `sys.exit("ERROR: ...")` if not `os.access(txt_path, os.R_OK)`
5. Filename regex match via `_TXT_FILENAME_RE`; extracts `computer` label; `sys.exit` if no match
6. No-clobber guard (USER OVERRIDE): `sys.exit("ERROR: ...")` if `md_path.exists()`
7. `parsed = parse_catalog(txt_path)` — never raises
8. Bridge: `[Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True) for ps in parsed.sections if ps.title != _HEADER_TITLE]`
9. Synthesize frontmatter: `datetime.now()`, `socket.gethostname()`, `maccat.__version__`
10. `content = render_markdown_catalog(sections, computer=..., hostname=..., generated=..., maccat_version=...)`
11. `md_path.write_text(content, encoding="utf-8")` — atomicity gate
12. `txt_path.unlink()` — ONLY after step 11 succeeds
13. `print(f"Converted: ...")`
14. `gitops.git_commit_convert(catalog_repo, md_path, txt_path)` if `not args.no_commit`

Module-level constants: `_TXT_FILENAME_RE`, `_HEADER_TITLE`

### Task 2: `git_commit_convert` appended to `src/maccat/gitops.py` (modified)

New function after `git_commit_rename` (line 252+):
- `_git_available()` + `_is_git_repo(catalog_repo)` guards
- `relative_to(catalog_repo)` with `ValueError` guard for file-outside-repo scenario
- Two `git add -A -- <relpath>` calls (new `.md` + deleted `.txt`)
- No-changes guard via `git diff --cached --quiet`
- Single commit with message `f"Convert catalog: {txt_path.name!r} -> {md_path.name!r}"`
- warn-and-continue on push failure (mirrors `git_commit_rename`)
- `shell=False` throughout; all args list-form; no `check=True`

## Verification Results

| Check | Result |
|-------|--------|
| `from maccat.convert import run_convert` | PASS |
| `from maccat.gitops import git_commit_convert` | PASS |
| `mypy --strict src/maccat/convert.py src/maccat/gitops.py` | PASS (0 errors) |
| `ruff check src/maccat/convert.py src/maccat/gitops.py` | PASS (0 errors) |
| `pytest tests/test_gitops.py -x -q` | PASS (10/10) |
| parser.py and markdown.py unmodified | PASS |

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| `_TXT_FILENAME_RE` defined at module level | PASS |
| `_HEADER_TITLE` defined + used in bridge filter (count >= 2) | PASS (count=2) |
| `raw=True` in bridge (count >= 1) | PASS |
| `md_path.exists()` no-clobber guard present | PASS (count=1) |
| `txt_path.unlink()` after `write_text` in source order | PASS (line 118 vs 121) |
| `def git_commit_convert` in gitops.py | PASS (count=1) |
| `relative_to(catalog_repo)` appears twice | PASS (rel_md + rel_txt) |
| `ValueError` guard present | PASS (count=1) |
| `shell=True` count = 0 | PASS |
| parser.py and markdown.py unmodified | PASS |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: convert.py | `1a43da5` | feat(32-01): implement run_convert orchestrator in convert.py |
| Task 2: gitops.py | `c1d93d5` | feat(32-01): add git_commit_convert to gitops.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch at wrong base commit**

- **Found during:** Initial setup (before Task 1)
- **Issue:** Worktree branch was at commit `d58f381` (pre-Phase 30/31), missing `src/maccat/catalog/markdown.py` and other Phase 30/31 source files. The `<worktree_branch_check>` preamble's merge-base check detected the mismatch correctly.
- **Fix:** Ran `git reset --hard d44f22bc5d73f0df2b6f25cdd77e67ad92b8b397` to align the worktree branch with the expected base. The untracked `convert.py` (already written) was preserved since `git reset --hard` does not delete untracked files.
- **Impact:** No code changes required; all Phase 30/31 source files (`markdown.py`, updated `parser.py`, etc.) became available.

## Threat Surface Scan

No new threat surface beyond what the plan's threat model covers (T-32-01 through T-32-SC). All mitigations present: `is_file()` + `os.access(R_OK)` validation, `with_suffix(".md")` output path derivation, no-clobber guard, atomicity invariant, list-form subprocess args.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `src/maccat/convert.py` exists | FOUND |
| `src/maccat/gitops.py` exists (modified) | FOUND |
| `32-01-SUMMARY.md` exists | FOUND |
| Commit `1a43da5` (Task 1) exists | FOUND |
| Commit `c1d93d5` (Task 2) exists | FOUND |

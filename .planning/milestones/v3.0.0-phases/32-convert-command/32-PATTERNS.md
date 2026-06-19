# Phase 32: Convert Command - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 4 (3 new, 1 modified)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/maccat/convert.py` | orchestrator/utility | transform (file-I/O) | `src/maccat/reinstall/cli.py` | role-match (same shape: deferred imports, validate input, transform, write) |
| `src/maccat/cli.py` | CLI entry point | request-response | `src/maccat/cli.py` itself (reinstall block) | exact (same file — adding a sibling subparser + dispatch block) |
| `src/maccat/gitops.py` | utility | file-I/O + subprocess | `src/maccat/gitops.py::git_commit_rename` | exact (same file — adding a sibling function with identical guard/stage/commit/push structure) |
| `tests/test_convert.py` | test | transform + integration | `tests/reinstall/test_reinstall_cli.py` + `tests/reinstall/test_picker_and_reinstall_cli.py` | role-match |

---

## Pattern Assignments

### `src/maccat/convert.py` (orchestrator, transform)

**Analog:** `src/maccat/reinstall/cli.py`

**Module docstring pattern** (reinstall/cli.py lines 1-14):
```python
"""Convert subcommand orchestrator.

Provides :func:`run_convert`, which drives the complete pipeline:
  1. Validate the --from file exists and is readable.
  2. Parse the .txt filename for the computer label.
  3. Guard: target .md must not already exist.
  4. parse_catalog() → ParsedCatalog.
  5. Bridge: ParsedCatalog → list[Section] (raw=True, skip header section).
  6. Synthesize frontmatter (now(), gethostname(), __version__).
  7. render_markdown_catalog() → markdown string.
  8. Write .md (atomicity gate).
  9. Unlink .txt (ONLY after .md write succeeded).
  10. git_commit_convert() unless --no-commit.

All maccat.* imports are deferred inside :func:`run_convert`'s body per PKG-03.
"""
from __future__ import annotations

import argparse
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path
```

**Private filename regex** (modeled on naming.py lines 18-19 — `.txt` variant):
```python
# Matches: mac-software-list-[computer]-YYYYMMDDHHMMSS.txt
# Derived from naming.py::_FILENAME_RE which uses \.md$ — swap to \.txt$
_TXT_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)
_HEADER_TITLE = "Installed Mac Software List"
```

**Deferred-import + validate + orchestrate pattern** (reinstall/cli.py lines 54-81):
```python
def run_convert(args: argparse.Namespace) -> None:
    # Deferred imports per PKG-03
    from maccat import __version__
    from maccat.catalog.markdown import render_markdown_catalog
    from maccat.collectors.base import Section
    from maccat.reinstall.parser import parse_catalog

    txt_path = Path(args.from_path).expanduser().resolve()

    # 1. File existence + readability (mirrors reinstall/picker.py WR-01 pattern)
    if not txt_path.is_file():
        sys.exit(f"ERROR: Catalog file not found or not a regular file: {txt_path}")
    if not os.access(txt_path, os.R_OK):
        sys.exit(f"ERROR: Catalog file is not readable: {txt_path}")

    # 2. Filename must be a recognizable legacy .txt catalog
    m = _TXT_FILENAME_RE.match(txt_path.name)
    if not m:
        sys.exit(
            f"ERROR: {txt_path.name!r} is not a recognizable legacy catalog filename. "
            f"Expected: mac-software-list-[computer]-YYYYMMDDHHMMSS.txt"
        )
    computer = m.group("machine")

    # 3. No-clobber guard (USER OVERRIDE — do NOT remove this check)
    md_path = txt_path.with_suffix(".md")
    if md_path.exists():
        sys.exit(
            f"ERROR: Target already exists: {md_path}\n"
            f"Remove it first, then re-run: maccat convert --from {txt_path}"
        )

    # 4. Parse the legacy .txt (never raises)
    parsed = parse_catalog(txt_path)

    # 5. Bridge: ParsedCatalog → list[Section], skip header section
    sections: list[Section] = [
        Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)
        for ps in parsed.sections
        if ps.title != _HEADER_TITLE
    ]

    # 6. Synthesize frontmatter (USER OVERRIDE: current machine at conversion time)
    now = datetime.now()
    generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")

    # 7. Render markdown
    content = render_markdown_catalog(
        sections,
        computer=computer,
        hostname=socket.gethostname(),
        generated=generated_iso,
        maccat_version=__version__,
    )

    # 8. Write .md — atomicity gate: .txt not touched until this succeeds
    md_path.write_text(content, encoding="utf-8")

    # 9. Remove .txt (ONLY after .md write succeeded — CONV-03 invariant)
    txt_path.unlink()

    print(f"Converted: {txt_path.name} -> {md_path.name}")

    # 10. Git commit (unless --no-commit)
    if not args.no_commit:
        from maccat import gitops
        # Heuristic: .txt lives at <repo>/<computer>/filename → parent.parent = repo
        catalog_repo = txt_path.parent.parent
        gitops.git_commit_convert(catalog_repo, md_path, txt_path)
```

**Error handling pattern:** `sys.exit(f"ERROR: ...")` (non-zero exit, no traceback). Matches exact convention from `cli.py` line 235 and `reinstall/picker.py`. Never use `raise`; never catch internal `parse_catalog` exceptions (it never raises).

---

### `src/maccat/cli.py` — subparser registration (modified, adding convert block)

**Analog:** `src/maccat/cli.py` lines 106-143 (existing reinstall subparser block)

**Subparser registration pattern** (cli.py lines 106-143 — copy and adapt):
```python
# In _build_parser(), after the reinstall_parser block (lines 106-143):
convert_parser = subparsers.add_parser(
    "convert",
    help="Convert a legacy .txt catalog to .md format",
)
convert_parser.add_argument(
    "--from",
    metavar="PATH",
    dest="from_path",
    required=True,           # bare `maccat convert` has no valid behavior
    help="Legacy .txt catalog file to convert",
)
# WR-03 SUPPRESS pattern (same rationale as reinstall --computer, cli.py:132-143):
# default=argparse.SUPPRESS prevents the subparser's False from clobbering
# a top-level --no-commit True set before the subcommand token.
convert_parser.add_argument(
    "--no-commit",
    action="store_true",
    dest="no_commit",
    default=argparse.SUPPRESS,
    help="Perform file operations without git commit",
)
```

**Dispatch pattern — step 4b in `run()`** (cli.py lines 250-255 — the reinstall --from dispatch):
```python
# In run(), alongside the existing step 4b reinstall dispatch (cli.py:250-255):
# convert is ALSO repo-agnostic (--from mode; no resolve_catalog_repo needed).
# Place this block immediately after the reinstall --from dispatch.
if args.subcommand == "convert":
    from maccat.convert import run_convert
    run_convert(args)
    return
```

**Docstring update** (cli.py lines 39-40 — the subcommand list in `_build_parser` docstring):
```
Subcommands:
  config init      Interactive first-run setup.
  config show      Print effective configuration.
  reinstall        Generate reinstall.sh from a catalog.
  convert          Convert a legacy .txt catalog to .md format.
```

---

### `src/maccat/gitops.py` — new `git_commit_convert` function (modified)

**Analog:** `src/maccat/gitops.py::git_commit_rename` (lines 169-251)

**Full function pattern** (copy structure of git_commit_rename lines 169-251, adapt for two file paths):
```python
def git_commit_convert(
    catalog_repo: Path,
    md_path: Path,    # absolute path of the newly-written .md
    txt_path: Path,   # absolute path of the removed .txt
) -> None:
    """Stage the new .md and the deleted .txt, then commit and push.

    Mirrors git_commit_rename pattern:
    - _git_available() + _is_git_repo() guards (lines 189-193).
    - Two git add -A -- <relpath> calls for the individual file paths.
    - relative_to() guard: if either path is outside catalog_repo, warn and return.
    - No-changes guard: skip commit when nothing staged (lines 214-219).
    - warn-and-continue on commit failure and push failure (lines 229-251).
    """
    if not _git_available():
        return
    if not _is_git_repo(catalog_repo):
        return

    # Compute relative paths — guard against file-outside-repo scenario (Pitfall 3)
    try:
        rel_md = md_path.relative_to(catalog_repo)
        rel_txt = txt_path.relative_to(catalog_repo)
    except ValueError:
        print(
            "  WARNING: Catalog file is outside the repo root. Skipping git operations."
        )
        return

    # Stage the new .md (git add -A records the new file; '-A' + '--' = zsh:2397 pattern)
    subprocess.run(
        ["git", "add", "-A", "--", str(rel_md)],
        cwd=catalog_repo,
        capture_output=True,
    )
    # Stage the deleted .txt (git add -A records the deletion from the index)
    subprocess.run(
        ["git", "add", "-A", "--", str(rel_txt)],
        cwd=catalog_repo,
        capture_output=True,
    )

    # No-changes guard (mirrors git_commit_rename lines 214-219)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=catalog_repo,
    )
    if diff.returncode == 0:
        print("  No changes staged.")
        return

    commit_msg = f"Convert catalog: {txt_path.name!r} -> {md_path.name!r}"
    commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=catalog_repo,
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0:
        print("  WARNING: Failed to create commit.")
        return
    print(f"  Committed: {commit_msg}")

    push = subprocess.run(
        ["git", "push"],
        cwd=catalog_repo,
        capture_output=True,
        text=True,
    )
    if push.returncode == 0:
        print("  Successfully pushed to remote.")
    else:
        print()
        print("  WARNING: Failed to push to remote repository.")
        print("  The commit has been saved locally. You can push manually later with:")
        print(f"    cd {catalog_repo} && git push")
        print()
```

**Key difference from git_commit_rename:** `git_commit_rename` stages directory paths (`f"{old_name}/"`, `f"{new_name}/"`) and also stages `machine-labels.tsv`. `git_commit_convert` stages exactly two individual file paths (the `.md` and the `.txt`) using relative paths computed via `relative_to(catalog_repo)`. No `machine-labels.tsv` staging needed.

---

### `tests/test_convert.py` (test, transform + integration)

**Analog:** `tests/reinstall/test_reinstall_cli.py` + `tests/reinstall/test_picker_and_reinstall_cli.py`

**Fixture `.txt` content pattern** (minimal valid legacy catalog for tests):
```python
_MINIMAL_TXT_CATALOG = (
    "Installed Mac Software List\n"
    "------------------------------------\n"
    "\n"
    "Homebrew Packages\n"
    "------------------------------------\n"
    "wget (1.21.3)\n"
    "git (2.44.0)\n"
    "\n"
    "App Store Applications\n"
    "------------------------------------\n"
    "Final Cut Pro (10.7.1) [424389933]\n"
    "\n"
    "Setapp Applications\n"
    "------------------------------------\n"
    "  (none found)\n"
)
```

**Fixture creation pattern** (test_reinstall_cli.py lines 47-58 + test_picker_and_reinstall_cli.py lines 173-193):
```python
@pytest.fixture()
def fixture_txt_catalog(self, tmp_path: Path) -> Path:
    """Minimal valid legacy .txt catalog in tmp_path.

    Filename follows mac-software-list-[machine]-timestamp.txt convention
    so _TXT_FILENAME_RE can parse it.
    """
    catalog = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
    catalog.write_text(_MINIMAL_TXT_CATALOG, encoding="utf-8")
    return catalog
```

**`sys.argv` integration test pattern** (test_reinstall_cli.py lines 64-85):
```python
def test_convert_writes_md_removes_txt(
    self,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fixture_txt_catalog: Path,
) -> None:
    monkeypatch.setattr(
        sys, "argv",
        ["maccat", "convert", "--from", str(fixture_txt_catalog)],
    )
    # Patch git commit so no real git ops run in unit tests
    monkeypatch.setattr("maccat.gitops.git_commit_convert", MagicMock())

    from maccat.cli import run
    run()  # must not raise SystemExit

    md = fixture_txt_catalog.with_suffix(".md")
    assert md.exists(), ".md must be written"
    assert not fixture_txt_catalog.exists(), ".txt must be removed"
```

**`argparse.Namespace` direct call pattern** (test_picker_and_reinstall_cli.py lines 21-30):
```python
def _make_convert_args(
    from_path: str | None = None,
    no_commit: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        from_path=from_path,
        no_commit=no_commit,
    )
```

**`SystemExit` guard pattern** (test_picker_and_reinstall_cli.py lines 97-103):
```python
with pytest.raises(SystemExit) as exc:
    run_convert(args)
assert exc.value.code != 0
```

**Unreadable file permission test pattern** (test_picker_and_reinstall_cli.py lines 113-133):
```python
@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root bypasses file permission checks; 0o000 is still readable",
)
def test_exits_cleanly_on_unreadable_file(self, tmp_path: Path) -> None:
    f = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
    f.write_text("x", encoding="utf-8")
    os.chmod(f, 0o000)
    try:
        args = _make_convert_args(from_path=str(f))
        with pytest.raises(SystemExit) as exc:
            run_convert(args)
        assert exc.value.code != 0
    finally:
        os.chmod(f, 0o644)
```

**`git_repo` fixture usage** (conftest.py lines 22-40 — for git commit tests):
```python
# conftest.py provides git_repo fixture — a git init'd tmp_path with test
# user config. Use it for any test that exercises git_commit_convert.
def test_git_commit_convert_stages_both_files(
    self,
    git_repo: Path,
    ...
) -> None:
    # place .txt inside git_repo/TestMac/ so relative_to works
    ...
```

**Round-trip test pattern** (from CONTEXT.md specifics — unique to this phase):
```python
def test_round_trip_convert_then_parse_markdown(
    self, tmp_path: Path, fixture_txt_catalog: Path
) -> None:
    """Convert a .txt fixture then parse the output .md — full chain test."""
    from maccat.convert import run_convert
    from maccat.reinstall.parser import parse_markdown_catalog

    args = _make_convert_args(from_path=str(fixture_txt_catalog), no_commit=True)
    run_convert(args)

    md_path = fixture_txt_catalog.with_suffix(".md")
    parsed = parse_markdown_catalog(md_path)   # must not raise
    assert len(parsed.sections) > 0
```

---

## Shared Patterns

### Clean ERROR Convention
**Source:** `src/maccat/cli.py` lines 214, 235; `src/maccat/reinstall/picker.py` (WR-01 pattern)
**Apply to:** `convert.py::run_convert` — all abort paths
```python
sys.exit(f"ERROR: <actionable message>")
```
No tracebacks. Non-zero exit code. Single string argument to `sys.exit`.

### Warn-and-Continue Convention
**Source:** `src/maccat/gitops.py` lines 27-28, 43-46, 79-83, 161-165, 243-250
**Apply to:** `gitops.py::git_commit_convert` — all non-fatal git failures
```python
print("  WARNING: <description>. Skipping git operations.")
return
```
No `raise`. Function returns silently after printing the warning.

### Deferred Imports (PKG-03)
**Source:** `src/maccat/reinstall/cli.py` lines 54-57; `src/maccat/cli.py` lines 253, 339
**Apply to:** `convert.py::run_convert` — all `maccat.*` imports; `cli.py` dispatch block
```python
# Inside the function body, not at module level:
from maccat import __version__
from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section
from maccat.reinstall.parser import parse_catalog
```

### argparse.SUPPRESS for Subparser Flag Defaults
**Source:** `src/maccat/cli.py` lines 132-136 (reinstall `--computer` default)
**Apply to:** `convert` subparser `--no-commit` registration in `_build_parser`
```python
convert_parser.add_argument(
    "--no-commit",
    action="store_true",
    dest="no_commit",
    default=argparse.SUPPRESS,   # prevents clobbering top-level --no-commit
    ...
)
```

### subprocess / git call style
**Source:** `src/maccat/gitops.py` lines 118-128, 196-212
**Apply to:** `gitops.py::git_commit_convert`
- `shell=False` always; args are list-form
- `cwd=catalog_repo` on every call
- `"--"` before every pathspec (`["git", "add", "-A", "--", str(rel_path)]`)
- `capture_output=True` for staging calls; `capture_output=True, text=True` for commit/push

### `from __future__ import annotations`
**Source:** All existing modules (`cli.py:1`, `gitops.py:1`, `naming.py:1`, `reinstall/cli.py:15`)
**Apply to:** `convert.py` — must be the first statement after the module docstring

---

## No Analog Found

All files for this phase have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `src/maccat/` (all modules), `tests/reinstall/`, `tests/conftest.py`
**Files read:** 7 source files, 2 test files, 1 conftest
**Pattern extraction date:** 2026-06-18

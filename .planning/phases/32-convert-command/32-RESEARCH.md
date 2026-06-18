# Phase 32: Convert Command - Research

**Researched:** 2026-06-18
**Domain:** Python CLI subcommand; legacy-to-markdown catalog conversion; single-commit git staging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Synthesized Frontmatter (USER OVERRIDE — "Fill from current machine")**
- `computer`: parsed from the `.txt` filename `mac-software-list-[computer]-TS.txt`
- `generated`: `now()` (current ISO-8601 local time) — NOT the original filename timestamp
- `hostname`: current machine's hostname (`socket.gethostname()`)
- `maccat_version`: current `maccat.__version__`
- Coherence note (locked): OUTPUT FILENAME keeps the ORIGINAL 14-digit timestamp from the source filename (`.txt` → `.md`, same basename). Filename timestamp (original) intentionally differs from frontmatter `generated` (now()). Do NOT reconcile them.

**In-Place Replacement & Git (CONV-02)**
- Output filename = source basename with `.txt` → `.md` (original timestamp preserved)
- If target `.md` already exists → ERROR and skip (USER OVERRIDE — do not clobber). Clean ERROR + non-zero exit; tell user to remove the existing `.md` first
- On success: write `.md`, remove old `.txt`, stage BOTH in a SINGLE commit
- `--no-commit`: perform file ops (write `.md`, remove `.txt`) WITHOUT any git calls

**Graceful Degradation (CONV-03)**
- Abort (clean ERROR + non-zero exit) ONLY when: `--from` file is missing/unreadable, OR filename is not a recognizable catalog (cannot derive `computer`)
- Warn-and-continue for parseable-but-weird content: `parse_catalog` never raises
- Never delete `.txt` unless `.md` was written successfully

### Claude's Discretion

- `ParsedCatalog` → `list[Section]` bridge: `Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)`. Degraded/empty `ParsedSection`s (items=[]) render as `(none found)`. Implementer's call on exact bridging.
- Parsing the LEGACY `.txt` filename for `computer`: `naming.parse_catalog_filename` matches `.md` only; convert needs its own `.txt`-aware extraction (a `.txt` variant of `_FILENAME_RE`, or generalize). Implementer's choice.
- `convert` subcommand wiring in `cli.py` (a new `subparsers.add_parser("convert", …)` alongside `reinstall`), with deferred imports per PKG-03.

### Deferred Ideas (OUT OF SCOPE)

- **CONV-bulk** — bulk / folder-wide convert (`--computer NAME` or all catalogs). Explicitly out of scope for this single-file phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONV-01 | `maccat convert --from PATH` reads a legacy plain-text `.txt` catalog (via the existing text parser) and rewrites its full contents — every section and every item's name/version/ID — as the new markdown `.md` catalog | Bridge: `Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)` → `render_markdown_catalog`; raw=True preserves order, `_render_table` re-parses each `raw_line` via `_ITEM_RE` to extract name/version/id columns |
| CONV-02 | convert replaces the original in-place — writes `.md`, removes old `.txt`, stages both in a single commit; `--no-commit` performs file ops without git | `git_commit_convert` (new function modeled on `git_commit_rename`): two `git add -A -- <path>` calls (new `.md` and deleted `.txt`), single commit, no-changes guard, warn-and-continue on push failure |
| CONV-03 | convert degrades gracefully on malformed or partial legacy input — warns and skips unparseable content rather than aborting or fabricating data, never executes anything | `parse_catalog` never raises; ONLY abort on missing/unreadable `--from` file or unparseable filename; warn-and-continue otherwise |
</phase_requirements>

---

## Summary

Phase 32 adds `maccat convert --from PATH`, a single-file legacy `.txt` → markdown `.md` upgrader. The phase wires together three already-built components: the legacy plain-text parser (`reinstall/parser.py::parse_catalog`), the markdown emitter (`catalog/markdown.py::render_markdown_catalog`), and the gitops module (`gitops.py`). No new external dependencies; stdlib-only; ruff + mypy --strict clean.

The central data flow is: `.txt` → `parse_catalog` → `ParsedCatalog` → bridge (`ParsedCatalog` → `list[Section]` with `raw=True`) → `render_markdown_catalog` → `.md`. The bridge is the only novel code; everything else is reuse of stable Phase 30/31 modules.

The most critical correctness constraint is the atomicity invariant: the `.txt` must never be deleted unless the `.md` write succeeded. The most critical design constraint is the USER OVERRIDE on no-clobber: if the target `.md` exists, exit with ERROR and do nothing.

**Primary recommendation:** Implement as `src/maccat/convert.py` (flat module, not a sub-package) with a single `run_convert(args)` function. Register the `convert` subcommand in `cli.py` via a new `subparsers.add_parser("convert", …)` block, dispatched at step 4b alongside the existing `reinstall` early-exit. The `.txt`-filename parser is a private constant `_TXT_FILENAME_RE` in `convert.py` — do not modify `naming.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI surface (`maccat convert --from PATH`) | CLI (`cli.py`) | `convert.py` | argparse registration in `_build_parser`; dispatch in `run()` mirrors reinstall pattern |
| `.txt`-filename parsing for `computer` | `convert.py` (private) | — | `naming.py::parse_catalog_filename` matches `.md` only; a private `_TXT_FILENAME_RE` in `convert.py` is the simplest approach that avoids modifying a stable module |
| Legacy `.txt` reading | `reinstall/parser.py::parse_catalog` | — | Retained unchanged for this purpose; do NOT modify |
| `ParsedCatalog` → `list[Section]` bridge | `convert.py` | — | Domain glue code; too small for its own module |
| Markdown emission | `catalog/markdown.py::render_markdown_catalog` | — | Stable emitter from Phase 30; not modified |
| File write + `.txt` removal | `convert.py` | — | Atomicity invariant must be co-located with the write |
| Single-commit git staging | `gitops.py` (new function) | `convert.py` | New `git_commit_convert` mirrors `git_commit_rename` pattern; `convert.py` calls it |

---

## Standard Stack

### Core (all already present — no new installs)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `reinstall/parser.py::parse_catalog` | in-repo | Read legacy `.txt` → `ParsedCatalog` | Retained by design for convert; never raises |
| `catalog/markdown.py::render_markdown_catalog` | in-repo | Emit markdown from `list[Section]` | Phase 30 canonical emitter; handles raw=True |
| `collectors/base.py::Section` | in-repo | Bridge dataclass | Already imported throughout the codebase |
| `gitops.py` | in-repo | Git staging + commit | All git ops go through this module |
| `naming.py::make_catalog_filename` | in-repo | Produce `.md` output filename from `[machine]-[ts]` components | Canonical filename constructor |
| `socket` (stdlib) | stdlib | `socket.gethostname()` for `hostname` frontmatter | Same source as `cli.py` step 10 |
| `datetime` (stdlib) | stdlib | `datetime.now()` for `generated` frontmatter | Same source as `cli.py` step 9 |
| `re` (stdlib) | stdlib | `.txt` filename regex | Same technique as `naming.py` |

### No New Packages

This phase is stdlib-only. No `pip install` step. No Package Legitimacy Audit required. [VERIFIED: CONTEXT.md constraint "stdlib-only, no PyYAML"]

---

## Architecture Patterns

### System Architecture Diagram

```
maccat convert --from PATH
        │
        ▼
   cli.py::run()
   step 4b dispatch ──► convert already matches from_path not None?
        │                        │
        │                        ▼
        │               run_convert(args)
        │                  │
        │    ┌─────────────┼─────────────────────────────────────┐
        │    │             │                                       │
        │    ▼             ▼                                       ▼
        │  validate      parse `.txt`                        synthesize
        │  --from file   filename for                        frontmatter
        │  exists +      computer label                      (now, gethostname,
        │  readable      (private regex)                     __version__)
        │    │             │                                       │
        │    └─────────────┘                                       │
        │                  │                                       │
        │                  ▼                                       │
        │            parse_catalog(path)                           │
        │            └─ ParsedCatalog                              │
        │                  │                                       │
        │                  ▼                                       │
        │         bridge: ParsedCatalog → list[Section]           │
        │         Section(title, items=[raw_line…], raw=True)     │
        │                  │                                       │
        │                  └──────────────┬────────────────────────┘
        │                                 ▼
        │                   render_markdown_catalog(sections, ...)
        │                          │
        │                          ▼
        │              check: target .md exists? → ERROR + exit
        │                          │
        │                          ▼
        │              write .md file (Path.write_text)
        │                          │
        │                          ▼  ← atomicity gate: only if write succeeded
        │              unlink .txt file (Path.unlink)
        │                          │
        │               --no-commit?
        │              /           \
        │           yes             no
        │            │               │
        │           done       git_commit_convert(repo, md_path, txt_path)
        │                      (new gitops function: add .md + add .txt, single commit)
        │                            │
        │                           done
```

### Recommended Project Structure

```
src/maccat/
├── convert.py          # NEW: run_convert(args) orchestrator + _TXT_FILENAME_RE
├── cli.py              # MODIFIED: add convert subparser + dispatch at step 4b
└── gitops.py           # MODIFIED: add git_commit_convert() function
tests/
└── test_convert.py     # NEW: unit + integration tests for convert
```

No sub-package needed — `convert.py` as a flat module mirrors how smaller features are structured in this codebase (compare: `retention.py`, `naming.py`, `identity.py`).

### Pattern 1: `.txt` Filename Extraction (Private Regex in `convert.py`)

**What:** A private `_TXT_FILENAME_RE` constant in `convert.py` that mirrors `naming.py::_FILENAME_RE` but matches `.txt` instead of `.md`. Returns `computer` (string) and `timestamp` (string), or `None` on no-match.

**When to use:** Called once at the start of `run_convert` to derive `computer` from the `--from` path's `stem + ".txt"` filename. Abort with clean ERROR if it returns `None`.

**Concrete regex:** [VERIFIED: derived directly from `naming.py::_FILENAME_RE` source]

```python
# Source: src/maccat/naming.py::_FILENAME_RE (lines 18-19), adapted for .txt
_TXT_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)
```

This handles the legacy filename shape `mac-software-list-[computer]-YYYYMMDDHHMMSS.txt` exactly. It captures `machine` (the computer label, between literal `[` and `]`) and `ts` (the 14-digit timestamp). The `machine` value becomes the `computer` frontmatter field and the subdirectory where the output `.md` is written.

**Note on output path:** The output `.md` goes into the SAME directory as the source `.txt` (i.e., `path.parent / path.stem + ".md"`). This is the in-place replacement contract from CONV-02 — not into the machine's subfolder. The source file already lives at the right location.

**Example:**
```python
# Source: derived from naming.py pattern [VERIFIED: src/maccat/naming.py]
import re
from pathlib import Path

_TXT_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

def _extract_computer(path: Path) -> str | None:
    """Return the computer label from a legacy .txt catalog filename, or None."""
    m = _TXT_FILENAME_RE.match(path.name)
    if not m:
        return None
    return m.group("machine")
```

### Pattern 2: `ParsedCatalog` → `list[Section]` Bridge

**What:** Convert each `ParsedSection` to a `Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)`.

**Why `raw=True`:** With `raw=True`, `render_markdown_catalog` skips `flush_section` (which would re-sort items). The raw lines are passed directly to `_render_table`, which calls `_parse_columns` (via `_ITEM_RE`) on each line to extract `name`, `version`, `id_` for the table cells. This preserves original collector-native order and faithfully reproduces every item's name/version/ID. [VERIFIED: `catalog/markdown.py` lines 193-198]

**Why `raw_line` (not `name`/`version`/`id` fields):** The `raw_line` is the original text-format string (e.g., `"Final Cut Pro (10.7.1) [424389933]"`). The markdown emitter's `_render_table` calls `_parse_columns` which applies `_ITEM_RE` to re-extract the fields. Using `raw_line` means the exact same regex inversion that the emitter already uses, rather than reconstructing `emit_item`-shaped strings from the parsed fields (which could lose edge cases). [VERIFIED: `catalog/markdown.py::_render_table` lines 101-119]

**Empty/degraded sections:** When `ps.items == []` (empty section — either truly empty or the `NONE_FOUND_SENTINEL` was hit, or all lines were `DEGRADATION_LINES`), the bridge produces `Section(title=ps.title, items=[], raw=True)`. `render_markdown_catalog` renders this as `(none found)` because the `not items` branch fires. [VERIFIED: `catalog/markdown.py` line 195]

**The header section:** `parse_catalog` produces a leading `ParsedSection(title="Installed Mac Software List", items=[], degraded=False)` from real catalogs (the WR-05 contract). The bridge should skip this section (it's not a data section; the emitter writes its own `# Installed Mac Software List` title unconditionally). Filter: `[s for s in parsed.sections if s.title != "Installed Mac Software List"]` OR skip any section whose title matches the emitter's own title constant.

**Concrete bridge code:**
```python
# Source: derived from catalog/markdown.py and collectors/base.py [VERIFIED]
from maccat.collectors.base import Section
from maccat.reinstall.parser import ParsedCatalog

_HEADER_TITLE = "Installed Mac Software List"

def _bridge(parsed: ParsedCatalog) -> list[Section]:
    sections: list[Section] = []
    for ps in parsed.sections:
        if ps.title == _HEADER_TITLE:
            continue  # emitter writes this title itself
        sections.append(Section(
            title=ps.title,
            items=[it.raw_line for it in ps.items],
            raw=True,
        ))
    return sections
```

### Pattern 3: `git_commit_convert` in `gitops.py`

**What:** New function that stages a newly-written `.md` file and the deleted `.txt` file in a single commit.

**Modeled on:** `git_commit_rename` [VERIFIED: `src/maccat/gitops.py` lines 169-251] which stages two paths with `git add -A -- <path>`, checks no-changes guard, and commits.

**Key difference from `git_commit_rename`:** `git_commit_rename` stages two directory paths (`{old_name}/` and `{new_name}/`). `git_commit_convert` stages two individual file paths (the new `.md` and the removed `.txt`). The `-A` flag on `git add` handles both the new file (add) and the deleted file (remove from index).

**Signature:**
```python
def git_commit_convert(
    catalog_repo: Path,
    md_path: Path,    # absolute path of the newly-written .md
    txt_path: Path,   # absolute path of the removed .txt
) -> None:
```

**Implementation sketch:**
```python
# Source: modeled on gitops.py::git_commit_rename [VERIFIED: src/maccat/gitops.py:169-251]
def git_commit_convert(catalog_repo: Path, md_path: Path, txt_path: Path) -> None:
    if not _git_available():
        return
    if not _is_git_repo(catalog_repo):
        return

    # Stage the new .md (git add -A records the new file)
    subprocess.run(
        ["git", "add", "-A", "--", str(md_path.relative_to(catalog_repo))],
        cwd=catalog_repo, capture_output=True,
    )
    # Stage the deleted .txt (git add -A records the deletion)
    subprocess.run(
        ["git", "add", "-A", "--", str(txt_path.relative_to(catalog_repo))],
        cwd=catalog_repo, capture_output=True,
    )
    # No-changes guard
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=catalog_repo,
    )
    if diff.returncode == 0:
        print("  No changes staged.")
        return
    commit_msg = f"Convert catalog: {txt_path.name!r} -> {md_path.name!r}"
    commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=catalog_repo, capture_output=True, text=True,
    )
    if commit.returncode != 0:
        print("  WARNING: Failed to create commit.")
        return
    print(f"  Committed: {commit_msg}")
    push = subprocess.run(
        ["git", "push"], cwd=catalog_repo, capture_output=True, text=True,
    )
    if push.returncode == 0:
        print("  Successfully pushed to remote.")
    else:
        print()
        print("  WARNING: Failed to push to remote repository.")
        print(f"  The commit is saved locally. Resolve with: cd {catalog_repo} && git push")
        print()
```

**Paths passed as relative strings:** `git add` requires paths relative to the repo root when `cwd=catalog_repo`. Use `path.relative_to(catalog_repo)` to compute relative paths. If the `.txt`/`.md` lives OUTSIDE the repo root (user passed an arbitrary `--from PATH`), `relative_to` will raise `ValueError`. Guard: if `catalog_repo` cannot be determined or the file is outside it, skip git ops with a WARNING (consistent with all other warn-and-continue patterns in `gitops.py`).

### Pattern 4: `cli.py` Subcommand Registration

**Placement in `run()`:** The convert dispatch belongs at step 4b alongside the existing `reinstall --from` dispatch — BEFORE `resolve_catalog_repo`. Like `reinstall --from`, `convert --from` is repo-agnostic (the `.txt` can be anywhere). [VERIFIED: `cli.py` lines 250-255]

**Subparser registration in `_build_parser`:**
```python
# Source: modeled on cli.py::_build_parser reinstall block [VERIFIED: cli.py lines 106-143]
convert_parser = subparsers.add_parser(
    "convert",
    help="Convert a legacy .txt catalog to .md format",
)
convert_parser.add_argument(
    "--from",
    metavar="PATH",
    dest="from_path",
    default=None,
    help="Legacy .txt catalog file to convert",
)
convert_parser.add_argument(
    "--no-commit",
    action="store_true",
    default=False,
    dest="no_commit",
    help="Perform file operations without git commit",
)
```

**Note on `--no-commit`:** The top-level `--no-commit` flag already exists on the main parser and ends up in `args.no_commit`. The convert subparser should also register `--no-commit` so that `maccat convert --from FILE --no-commit` is accepted (subparser placement after the subcommand token). Use `argparse.SUPPRESS` as default to avoid clobbering the top-level flag — same pattern as `reinstall --computer`. [VERIFIED: cli.py lines 132-143]

**Dispatch in `run()` step 4b:**
```python
# Deferred import per PKG-03
if args.subcommand == "convert":
    from maccat.convert import run_convert
    run_convert(args)
    return
```

### Pattern 5: Atomicity / Failure Ordering

The sequence inside `run_convert` after validation must be:

1. Parse `.txt` filename → `computer` (or abort)
2. Validate `--from` file exists + readable (or abort)
3. Check target `.md` does NOT exist (or abort with no-clobber ERROR)
4. `parse_catalog(txt_path)` → `ParsedCatalog`
5. Bridge → `list[Section]`
6. `render_markdown_catalog(...)` → `content: str`
7. `md_path.write_text(content, encoding="utf-8")` ← `.md` written
8. `txt_path.unlink()` ← `.txt` removed (ONLY after step 7 succeeded)
9. If `auto_commit`: `git_commit_convert(catalog_repo, md_path, txt_path)`

If step 7 raises `OSError`, step 8 never executes — `.txt` is safe. This is the simplest correct approach and requires no rollback logic.

### Anti-Patterns to Avoid

- **Deleting `.txt` before `.md` write completes:** Violates CONV-03 atomicity contract. The unlink must be strictly after `write_text` returns without exception.
- **Clobbering existing `.md`:** USER OVERRIDE — always check for target existence before writing and exit with ERROR if it exists.
- **Passing `raw=False` to Section:** Would trigger `flush_section` re-sort, breaking original order. Must be `raw=True`.
- **Including the "Installed Mac Software List" header section in the bridge output:** The emitter writes its own `# Installed Mac Software List` H1 unconditionally. Passing it as a Section produces a spurious `## Installed Mac Software List` heading.
- **Raising `ValueError` for parseable-but-weird `.txt` content:** `parse_catalog` handles all degraded input internally. `run_convert` must never inspect or re-raise parse internals.
- **Calling `git_commit_and_push` instead of a new function:** `git_commit_and_push` stages a computer directory (`{computer}/`) and `machine-labels.tsv`. That is wrong for convert — we need to stage exactly two specific file paths.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing legacy `.txt` content | Custom line parser | `reinstall/parser.py::parse_catalog` | Already handles all 6 emit_item shapes, degradation lines, sentinel, EOF flush |
| Markdown catalog rendering | String formatting loop | `catalog/markdown.py::render_markdown_catalog` | Phase 30 canonical emitter; handles frontmatter, empty sections, `_DEGRADATION_LINES` filter, `_escape_cell` |
| Git staging of two files | Custom subprocess sequence | New `gitops.py::git_commit_convert` (modeled on `git_commit_rename`) | `_git_available` + `_is_git_repo` guards + no-changes guard + warn-and-continue on push already codified |
| Hostname / version / timestamp | Re-derive from args or file | `socket.gethostname()`, `maccat.__version__`, `datetime.now()` | Same sources as `cli.py` step 10 — provenance is always current machine at conversion time |

---

## Common Pitfalls

### Pitfall 1: Header Section Leaking Into Bridge Output

**What goes wrong:** `parse_catalog` always produces a leading `ParsedSection(title="Installed Mac Software List", items=[])` for real catalogs (WR-05 contract, locked by test). If the bridge passes this to `render_markdown_catalog`, the output gets a spurious `## Installed Mac Software List` section heading (the emitter writes `# Installed Mac Software List` as an H1 AND a `## Installed Mac Software List` H2 data section).

**Why it happens:** The bridge naively iterates `parsed.sections` without filtering the header.

**How to avoid:** Skip any `ParsedSection` whose `title == "Installed Mac Software List"` in the bridge loop. [VERIFIED: `reinstall/parser.py` lines 155-162 — WR-05 contract is documented and locked]

**Warning signs:** Output `.md` has `## Installed Mac Software List` heading with `(none found)` beneath the H1.

### Pitfall 2: `--no-commit` Flag Shadowing Between Parser Levels

**What goes wrong:** The top-level parser registers `--no-commit` → `args.no_commit`. If the convert subparser also registers `--no-commit` with `default=False` (not `argparse.SUPPRESS`), argparse will overwrite a top-level `--no-commit True` with `False` during subparser parsing.

**Why it happens:** argparse processes subparser arguments after top-level arguments, and a plain `default=False` assignment unconditionally clobbers the namespace attribute.

**How to avoid:** Register the convert subparser's `--no-commit` with `default=argparse.SUPPRESS` — same pattern as `reinstall --computer`. [VERIFIED: `cli.py` lines 132-143 — WR-03 comment explains the SUPPRESS pattern]

### Pitfall 3: File Outside Repo Root Breaks `relative_to()`

**What goes wrong:** `Path.relative_to(catalog_repo)` raises `ValueError` if the `.txt` file's path is not under `catalog_repo`. This is a valid user scenario — `convert --from /some/other/path/catalog.txt`.

**Why it happens:** `git add <path>` in `git_commit_convert` requires paths relative to the repo root when `cwd=catalog_repo`. If the file is outside the repo, there is no valid relative path.

**How to avoid:** In `git_commit_convert`, wrap `path.relative_to(catalog_repo)` in a try/except and print a WARNING + return (skipping git ops) if the path is not under the repo. This is consistent with the warn-and-continue invariant across all `gitops.py` functions. [VERIFIED: `gitops.py` design invariants — "warn-and-continue: no function raises"]

**Alternative approach:** Determine `catalog_repo` from config in `run_convert` (same as `run()` does for the main flow), and if resolution fails or the file is not under the repo, skip git ops silently.

### Pitfall 4: `parse_catalog` Opens `.md` Files

**What goes wrong:** `parse_catalog` has no extension guard — it will happily read any file handed to it. If a user accidentally passes a `.md` file as `--from`, `parse_catalog` will return a mostly-empty `ParsedCatalog` (the state machine will find no `SEPARATOR` lines), and `run_convert` will silently produce a nearly-empty `.md`.

**Why it happens:** `parse_catalog` is a general-purpose reader; the extension check is the caller's responsibility.

**How to avoid:** In `run_convert`, check `txt_path.suffix == ".txt"` before calling `parse_catalog`. If the suffix is not `.txt`, exit with a clean ERROR: "Expected a legacy .txt catalog; got `.md`. Use `maccat reinstall` to use markdown catalogs." This check is AFTER the filename-regex check (which already requires `.txt`), so this is belt-and-suspenders — but explicit.

**Warning signs:** Output `.md` has `# Installed Mac Software List` title but all sections show `(none found)`.

### Pitfall 5: Degraded `ParsedSection` Is Not the Same as Empty

**What goes wrong:** `ps.degraded == True` means the section contained a known DEGRADATION_LINE (e.g., "Homebrew is not installed."). `ps.items` will be `[]` in this case. However, both a truly empty section AND a degraded section map to `items=[]` in the bridge, both rendering as `(none found)` — which is correct. The `degraded` flag is intentionally not passed to the emitter.

**Why it matters:** The `render_markdown_catalog` renders BOTH empty and degraded sections as `(none found)`. The `degraded` flag is not recoverable from the markdown round-trip (documented in `parse_markdown_catalog` at line 355). This is lossless for the reinstall emitter (`_should_skip()` drops sections with `items == []` regardless of `degraded`). [VERIFIED: `reinstall/parser.py` lines 350-357]

**How to avoid:** This is expected behavior, not a bug. Document in code comments that `degraded` is intentionally not surfaced. The bridge correctly ignores it.

---

## Code Examples

### Full `run_convert` Orchestration Sketch

```python
# Source: derived from cli.py::run() step 4b pattern [VERIFIED: src/maccat/cli.py:250-255]
#         and reinstall/cli.py::run_reinstall [VERIFIED: src/maccat/reinstall/cli.py]
from __future__ import annotations

import argparse
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

_TXT_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)
_HEADER_TITLE = "Installed Mac Software List"


def run_convert(args: argparse.Namespace) -> None:
    # Deferred imports per PKG-03
    from maccat import __version__
    from maccat.catalog.markdown import render_markdown_catalog
    from maccat.collectors.base import Section
    from maccat.reinstall.parser import parse_catalog

    txt_path = Path(args.from_path).expanduser().resolve()

    # 1. File existence + readability
    if not txt_path.is_file():
        sys.exit(f"ERROR: Catalog file not found or not a regular file: {txt_path}")
    # (os.access check for readability — mirror reinstall/picker.py WR-01)
    import os
    if not os.access(txt_path, os.R_OK):
        sys.exit(f"ERROR: Catalog file is not readable: {txt_path}")

    # 2. Filename must be a recognizable legacy catalog
    m = _TXT_FILENAME_RE.match(txt_path.name)
    if not m:
        sys.exit(
            f"ERROR: {txt_path.name!r} is not a recognizable legacy catalog filename. "
            f"Expected: mac-software-list-[computer]-YYYYMMDDHHMMSS.txt"
        )
    computer = m.group("machine")

    # 3. Target .md must not already exist (no-clobber USER OVERRIDE)
    md_path = txt_path.with_suffix(".md")
    if md_path.exists():
        sys.exit(
            f"ERROR: Target already exists: {md_path}\n"
            f"Remove it first, then re-run: maccat convert --from {txt_path}"
        )

    # 4. Parse the legacy .txt
    parsed = parse_catalog(txt_path)

    # 5. Bridge: ParsedCatalog → list[Section], skip header section
    sections: list[Section] = [
        Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)
        for ps in parsed.sections
        if ps.title != _HEADER_TITLE
    ]

    # 6. Synthesize frontmatter (USER OVERRIDE: "Fill from current machine")
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

    # 8. Write .md (atomicity gate — must succeed before .txt is deleted)
    md_path.write_text(content, encoding="utf-8")

    # 9. Remove .txt (ONLY after .md write succeeded)
    txt_path.unlink()

    print(f"Converted: {txt_path.name} -> {md_path.name}")

    # 10. Git commit (unless --no-commit)
    auto_commit = not args.no_commit
    if auto_commit:
        from maccat import gitops
        # catalog_repo resolution: the .txt lives in <repo>/<computer>/
        # parent of txt_path is the computer folder; parent of that is the repo
        catalog_repo = txt_path.parent.parent
        gitops.git_commit_convert(catalog_repo, md_path, txt_path)
```

**Note on `catalog_repo` derivation:** Since the `.txt` follows the naming convention `<repo>/<computer>/mac-software-list-[computer]-TS.txt`, `txt_path.parent.parent` is the repo root. If the user passes an arbitrary path outside this structure, `git_commit_convert` will catch the `relative_to` error and warn-and-continue. This is simpler than requiring config resolution in `run_convert` and is consistent with the "degrades gracefully" invariant.

### Fixture `.txt` Content for Tests

```
Installed Mac Software List
------------------------------------

Homebrew Packages
------------------------------------
wget (1.21.3)
git (2.44.0)

App Store Applications
------------------------------------
Final Cut Pro (10.7.1) [424389933]

Setapp Applications
------------------------------------
  (none found)
```

This fixture exercises: a plain section with items, a section with version+id items, and an empty section rendered via `NONE_FOUND_SENTINEL`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain-text `.txt` catalog | Markdown `.md` catalog | Phase 30 (v3.0.0) | `convert` bridges the gap; old catalogs remain usable |
| `parse_catalog` (text parser) | `parse_markdown_catalog` (MD parser) | Phase 31 (v3.0.0) | Both parsers coexist; `parse_catalog` is retained exclusively for `convert` input |

**Two parsers coexist after Phase 32 is complete:**
- `parse_catalog` — legacy `.txt` reader; used ONLY by `maccat convert`. Read-only; not modified.
- `parse_markdown_catalog` — new `.md` reader; used by `maccat reinstall`. Raises `ValueError` for `.txt` input.

---

## Open Questions

1. **`catalog_repo` derivation for git commit**
   - What we know: The `.txt` file passed via `--from` could be anywhere. In normal use it lives at `<repo>/<computer>/mac-software-list-[computer]-TS.txt`, so `txt_path.parent.parent` gives the repo root.
   - What's unclear: Should `run_convert` load config to resolve `catalog_repo` authoritatively, or derive it from the file path heuristically?
   - Recommendation: Use the heuristic `txt_path.parent.parent` and let `_is_git_repo` fail gracefully (warn-and-continue) if it's wrong. This avoids config dependency in the convert path, matching the `reinstall --from` pattern which is also repo-agnostic. If the heuristic is wrong, the user gets a WARNING about no git commit but the `.md` conversion still succeeds.

2. **`--from` is required, not optional**
   - What we know: CONV-01/02/03 specify single-file `--from PATH` only. Bulk is deferred (CONV-bulk). The `convert` subcommand with no `--from` has no valid behavior.
   - What's unclear: Should bare `maccat convert` (no `--from`) print help or exit with ERROR?
   - Recommendation: Make `--from` a required argument (`required=True`) on the subparser, so argparse itself prints usage + error. This is the simplest approach and consistent with "CONV-bulk deferred."

---

## Environment Availability

Step 2.6: No new external tools required beyond what the existing test suite already uses. `git` is already probed in `gitops.py` via `_git_available()`. Python stdlib (`re`, `socket`, `datetime`, `pathlib`, `os`) is always available on macOS. SKIPPED for further analysis — this phase is code/config changes only against the existing venv.
<br>

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | `git_commit_convert` | ✓ (assumed present per gitops guards) | any | `_git_available()` returns False + warn-and-continue |
| Python stdlib (`re`, `socket`, `datetime`, `pathlib`, `os`) | `convert.py` | ✓ | stdlib | — |
| `maccat.reinstall.parser.parse_catalog` | `run_convert` | ✓ (in-repo, Phase 25) | in-repo | — |
| `maccat.catalog.markdown.render_markdown_catalog` | `run_convert` | ✓ (in-repo, Phase 30) | in-repo | — |

---

## Validation Architecture

`nyquist_validation` is explicitly `false` in `.planning/config.json`. Validation Architecture section omitted per config.

---

## Security Domain

`security_enforcement` is not set in config (treated as enabled). However, this phase has no authentication, session management, cryptography, or user-controlled output paths beyond the `--from` flag. The primary concern is path traversal — `Path.expanduser().resolve()` normalizes the input, and the write path is derived deterministically from the source path (`with_suffix(".md")`), not from user-supplied data. No secrets are written to the `.md` (the emitter already enforces FMT-03 identity-only for MCP/AI-CLI entries).

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `Path.expanduser().resolve()` + `_TXT_FILENAME_RE` match + `is_file()` + `os.access(R_OK)` |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary file read via `--from` | Information Disclosure | `os.access(R_OK)` check; no content is echoed to stdout |
| Path traversal in output | Tampering | Output path derived as `txt_path.with_suffix(".md")` — cannot escape `txt_path.parent` |
| Clobbering existing `.md` | Tampering | No-clobber ERROR guard (USER OVERRIDE) before any write |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `txt_path.parent.parent` is the catalog repo root in normal usage | Code Examples, Open Questions | git commit would warn-and-continue (no data loss, just no commit) |
| A2 | The header section title is exactly "Installed Mac Software List" and is always the first section | Pattern 2, Pitfall 1 | If the title ever changes, the bridge would include a spurious H2 — but this title is a format constant locked by tests |

---

## Sources

### Primary (HIGH confidence)

- `src/maccat/reinstall/parser.py` — `parse_catalog` state machine, `ParsedCatalog`/`ParsedSection`/`ParsedItem` shapes, `SEPARATOR`/`NONE_FOUND_SENTINEL`/`DEGRADATION_LINES` constants, WR-05 header-section contract [VERIFIED: read directly]
- `src/maccat/catalog/markdown.py` — `render_markdown_catalog` signature + raw=True branch, `_render_table`, `_DEGRADATION_LINES`, `_escape_cell`, `_parse_columns`/`_ITEM_RE`, `render_frontmatter` [VERIFIED: read directly]
- `src/maccat/collectors/base.py` — `Section(title, items, raw)` dataclass [VERIFIED: read directly]
- `src/maccat/naming.py` — `_FILENAME_RE` pattern (basis for `_TXT_FILENAME_RE`), `make_catalog_filename`, `parse_catalog_filename` [VERIFIED: read directly]
- `src/maccat/gitops.py` — `git_commit_rename` pattern (basis for `git_commit_convert`), `_git_available`/`_is_git_repo` guards, warn-and-continue invariants [VERIFIED: read directly]
- `src/maccat/cli.py` — `_build_parser` subparser registration, reinstall dispatch pattern at step 4b, deferred imports (PKG-03), `--no-commit` SUPPRESS pattern [VERIFIED: read directly]
- `src/maccat/reinstall/cli.py` — `run_reinstall` orchestrator structure (the direct analog for `run_convert`) [VERIFIED: read directly]
- `.planning/phases/32-convert-command/32-CONTEXT.md` — locked decisions including both USER OVERRIDEs [VERIFIED: read directly]
- `.planning/config.json` — `nyquist_validation: false` confirmed [VERIFIED: read directly]

### Secondary (MEDIUM confidence)

- `tests/reinstall/test_reinstall_cli.py` and `tests/reinstall/test_picker_and_reinstall_cli.py` — test patterns for subcommand integration tests (fixture structure, `monkeypatch.setattr(sys, "argv", ...)`, `git_repo` fixture usage) [VERIFIED: read directly]
- `tests/conftest.py` — `git_repo` fixture (disposable `git init` in `tmp_path`) [VERIFIED: read directly]
- `tests/reinstall/test_parser_contract.py` — round-trip test pattern (fixture `.txt` → parse → assert) [VERIFIED: read directly]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules read directly; no new packages
- Architecture: HIGH — patterns traced directly from analogous existing code (`reinstall`, `gitops`, `naming`)
- Pitfalls: HIGH — derived from actual code constants (WR-05 contract documented in `parse_catalog` docstring; SUPPRESS pattern documented with comment in `cli.py`)

**Research date:** 2026-06-18
**Valid until:** Until `catalog/markdown.py`, `reinstall/parser.py`, or `naming.py` are modified (stable modules post-Phase 31)

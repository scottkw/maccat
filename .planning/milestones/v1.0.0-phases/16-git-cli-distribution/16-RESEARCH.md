# Phase 16: Git, CLI & Distribution - Research

**Researched:** 2026-06-14
**Domain:** Python CLI (argparse) + git subprocess integration + stdlib zipapp distribution
**Confidence:** HIGH — all claims verified against live source code, stdlib docs, and prior phase artifacts

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at Claude's discretion — behavior is fully determined by zsh
byte/behavior parity (`update-list.sh` main flow + git functions) plus already-locked decisions
from earlier phases. No user-facing design choices remain.

- CLI: stdlib `argparse`. Bare `maccat` = catalog-generate run. `maccat config init` / `maccat config show` = config subcommands (CFG-04).
- Run flags: `--computer NAME` / `--personal` / `--office` / `--machine NAME` (mutually exclusive), `--rename`, `--archive-days N`, `--no-commit`, `--catalog-dir PATH` (CFG-03 override, never written back), `--version`, `--help`.
- Orchestration order is NON-NEGOTIABLE: `git_pull → generate → retain → prune → commit/push`. Generate-then-sweep: never archive the just-written catalog.
- `.pyz`: stdlib `python -m zipapp` only (zero third-party). Never resolve catalog repo from `__file__`.
- `git add` MUST use `-- <pathspec>` (leading-dash safety — success criterion 4).
- `--no-commit` runs all disk ops (generate/retain/prune) but skips git (success criterion 3).

### Claude's Discretion
All implementation details (module structure, RunContext fields, test design, build script layout).

### Deferred Ideas (OUT OF SCOPE)
- Golden-output byte-parity test suite + destructive-op safety-invariant isolated tests — Phase 17.
- pipx / PyPI distribution channel (PKG-04) — v1.1.
- New collectors / restore-from-catalog — future milestones.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-03 | `.pyz` zipapp, `#!/usr/bin/env python3` shebang, runs from any dir, never resolves catalog from `__file__` | Zipapp section: src/-as-source solves import, PKG-03 cwd-independence section |
| PKG-05 | `--version` and `--help` | argparse standard behavior section |
| OPS-06 | git pull → generate → commit/push single commit; `--no-commit` skips git, disk ops still run | Verified git command sequence + orchestration order sections |
</phase_requirements>

---

## Summary

Phase 16 is a pure wiring/integration phase: `src/maccat/cli.py` + `src/maccat/gitops.py` + `__main__.py` stub completion + `.pyz` build script. Every piece of business logic is already implemented in phases 13–15. The work is: (1) build the argparse parser, (2) implement the end-to-end run orchestrator, (3) implement git pull/commit/push via subprocess mirroring the zsh functions exactly, (4) wire the rename-mode git commit stub in `identity.py`, and (5) write a build script that produces a correct, importable `.pyz`.

The zsh reference at `update-list.sh:2327` (git_pull) and `update-list.sh:2374` (git_commit_and_push) is the byte/behavior spec for git operations. The orchestration order at lines 2443–2505 is the non-negotiable run order. Both are read verbatim below.

**Primary recommendation:** `src/maccat/cli.py` for argparse + run orchestration. `src/maccat/gitops.py` for git operations. Build script uses `python -m zipapp src --output dist/maccat.pyz --python "/usr/bin/env python3" --main "maccat.__main__:main" --compress`. The `src/` directory (not `src/maccat/`) must be the zipapp source so `maccat/` appears as a top-level directory inside the zip archive, making `import maccat` resolve correctly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI argument parsing | `src/maccat/cli.py` | `src/maccat/__main__.py` (entry dispatch) | argparse lives in cli.py; __main__.py calls main() which calls run() |
| Run orchestration (ordered flow) | `src/maccat/cli.py` (run function) | — | Single function assembles the ordered pipeline; all called modules are already built |
| Git pull / commit / push | `src/maccat/gitops.py` | — | Isolated module for all subprocess git calls; cwd=catalog_repo replaces `cd "$SCRIPT_DIR"` |
| Rename-mode git commit | `src/maccat/identity.py:625` stub wired to `gitops.py` | — | The stub already exists; Phase 16 fills it in by calling `gitops.git_commit_rename` |
| `.pyz` build | `scripts/build-pyz.sh` (new) or `Makefile` (new) | — | One-liner wrapping `python -m zipapp src ...`; build artifact goes to `dist/maccat.pyz` |
| Version string | `src/maccat/__init__.py:__version__` | — | Already defined as "1.0.0"; argparse `version=` reads it |

---

## Standard Stack

### Core (all stdlib, already in use)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `argparse` | stdlib | CLI flag parsing, subcommands | Locked decision; handles all flags + `config` subparser |
| `subprocess` | stdlib | Git operations (shell=False, list form) | Locked decision; mirrors zsh `git pull/add/commit/push` |
| `pathlib.Path` | stdlib | All path arguments | Already used across all modules |
| `python -m zipapp` | stdlib | Build `.pyz` artifact | Locked decision; zero third-party |

### Existing modules to reuse (do NOT reimplement)

| Module | Entry Points Used in Phase 16 |
|--------|-------------------------------|
| `maccat.config` | `load_config()`, `resolve_catalog_repo()`, `validate_catalog_repo()`, `config_init()`, `config_show()`, `resolve_archive_days()` |
| `maccat.identity` | `resolve_computer_selection()`, `select_computer()`, `rename_machine()` |
| `maccat.retention` | `retain_newest_per_host()`, `prune_old_archives()` |
| `maccat.naming` | `make_catalog_filename()` |
| `maccat.collectors` | `get_registry()` |
| `maccat.catalog.writer` | `CatalogWriter` |
| `maccat.catalog.format` | `flush_section()` |
| `maccat.__init__` | `__version__` |

### No new packages

No packages are installed in this phase. Runtime remains zero-dependency stdlib-only.

---

## Package Legitimacy Audit

No new packages installed in Phase 16. The runtime package is zero-dependency. Dev dependencies (pytest, ruff, mypy) were installed in prior phases.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture: Run Flow

```
argv
  │
  ▼
__main__.main()
  │  version guard (PKG-02) already in place
  ▼
cli.run()
  │
  ├─ argparse parser
  │    ├─ bare invocation (no subcommand) → generate-run dispatch
  │    └─ config subcommand → config_init() or config_show()
  │
  ├─ [rename mode short-circuit, mirrors zsh:2447-2451]
  │    ├─ gitops.git_pull(catalog_repo)          ← warn-and-continue
  │    ├─ identity.rename_machine(catalog_repo, auto_commit=auto_commit)
  │    └─ sys.exit(0)
  │
  ├─ resolve_catalog_repo()                       ← CFG-01 precedence
  ├─ validate_catalog_repo()                      ← CFG-06 fail-fast / warn
  ├─ identity.resolve_computer_selection()        ← mutual-exclusion guard
  ├─ identity.select_computer(catalog_repo, ...)  ← menu or flag resolution
  ├─ config.resolve_archive_days()                ← flag or prompt
  │
  ├─ gitops.git_pull(catalog_repo)                ← warn-and-continue [zsh:2464]
  │
  ├─ [generate phase]
  │    ├─ timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  [zsh:2469]
  │    ├─ filename = make_catalog_filename(computer, timestamp) [zsh:2471]
  │    ├─ output_file = catalog_repo / computer / filename      [zsh:2474]
  │    ├─ (catalog_repo / computer).mkdir(parents=True, exist_ok=True) [zsh:2477]
  │    └─ with CatalogWriter(output_file) as w:
  │          w.write_section("Installed Mac Software List")     [zsh:2226]
  │          for collector in get_registry():
  │            result = collector.collect()
  │            for section in result.sections:
  │              w.write_section(section.title)
  │              if section.raw:
  │                w.write_lines(section.items)
  │              else:
  │                w.write_lines(flush_section(section.items))
  │
  ├─ retention.retain_newest_per_host(catalog_repo / computer)  [zsh:2492]
  ├─ retention.prune_old_archives(catalog_repo / computer / "archive", archive_days) [zsh:2495]
  │
  └─ if auto_commit:
       gitops.git_commit_and_push(catalog_repo, computer, timestamp) [zsh:2499]
     else:
       print no-commit message [zsh:2501-2504]
```

### Recommended Project Structure (new files only)

```
src/
├── maccat/
│   ├── __main__.py    # MODIFY: stub → call cli.run(); version guard stays
│   ├── cli.py         # NEW: argparse parser + run orchestration
│   └── gitops.py      # NEW: git_pull, git_commit_and_push, git_commit_rename
scripts/
└── build-pyz.sh       # NEW: one-liner zipapp build script
dist/                  # NEW: created by build-pyz.sh (gitignored output)
tests/
├── test_cli.py        # NEW: argparse tests, --no-commit, end-to-end fixture
└── test_gitops.py     # NEW: git pull/commit/push against temp git repos
```

### Pattern 1: git operations — subprocess list-form, cwd=catalog_repo [VERIFIED: zsh source]

**Exact zsh behavior** (lines 2327–2354 for git_pull, 2374–2431 for git_commit_and_push):

```python
# src/maccat/gitops.py
import subprocess
import shutil
from pathlib import Path


def git_pull(catalog_repo: Path) -> None:
    """Mirror zsh git_pull :2327.

    - warn-and-continue on rev-parse failure (not a git repo) [zsh:2340-2343]
    - bare 'git pull' (no --rebase, no strategy flag) [zsh:2346]
    - warn-and-continue on pull failure [zsh:2349-2353]
    - cwd=catalog_repo replaces 'cd "$SCRIPT_DIR"' [zsh:2334]
    """
    print()
    print("-" * 78)
    print("Git: Pulling latest changes from remote...")
    print("-" * 78)

    if not shutil.which("git"):
        print("  WARNING: git not found. Skipping git pull.")
        return

    rev = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=catalog_repo,
        capture_output=True,
    )
    if rev.returncode != 0:
        print("  WARNING: Not a git repository. Skipping git pull.")
        return

    result = subprocess.run(
        ["git", "pull"],
        cwd=catalog_repo,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  Successfully pulled latest changes.")
    else:
        print()
        print("  WARNING: Failed to pull from remote repository.")
        print("  Continuing with local state. You may need to resolve conflicts later.")
        print()


def git_commit_and_push(
    catalog_repo: Path,
    computer: str,
    timestamp: str,
) -> None:
    """Mirror zsh git_commit_and_push :2374.

    Stage sequence (zsh:2397-2400):
      git add -A -- "{computer}/"         → all adds/moves/deletes in computer folder
      git add -- machine-labels.tsv       → map file changes (2>/dev/null || true)

    Commit message (zsh:2410):
      "Added [{computer}] catalog at {timestamp}"

    No-changes-to-commit guard (zsh:2403-2406):
      git diff --cached --quiet → return early

    Push (zsh:2422-2430):
      warn-and-continue on failure; local commit preserved.
    """
    print()
    print("-" * 78)
    print("Git: Committing and pushing changes...")
    print("-" * 78)

    if not shutil.which("git"):
        print("  WARNING: git not found. Skipping git operations.")
        return

    rev = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=catalog_repo,
        capture_output=True,
    )
    if rev.returncode != 0:
        print("  WARNING: Not a git repository. Skipping git operations.")
        return

    # Stage all changes in the computer folder (new catalog, archived moves, pruned deletes)
    # The '--' end-of-options marker is mandatory for leading-dash folder safety.
    print(f"  Staging all changes in {computer}/...")
    subprocess.run(
        ["git", "add", "-A", "--", f"{computer}/"],
        cwd=catalog_repo,
    )

    # Stage map file if it changed; suppress errors (file may not exist)
    subprocess.run(
        ["git", "add", "--", "machine-labels.tsv"],
        cwd=catalog_repo,
        capture_output=True,
    )

    # Nothing to commit guard
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=catalog_repo,
    )
    if diff.returncode == 0:
        print("  No changes to commit.")
        return

    commit_msg = f"Added [{computer}] catalog at {timestamp}"
    print("  Creating commit...")
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

    print("  Pushing to remote...")
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


def git_commit_rename(
    catalog_repo: Path,
    old_name: str,
    new_name: str,
) -> None:
    """Mirror zsh rename_machine git block :867-910.

    Stage sequence (zsh:886-888):
      git add -A -- "{old_name}/"   → records the folder's deletions
      git add -A -- "{new_name}/"   → records the moved folder + rewritten filenames
      git add -- machine-labels.tsv → map update

    Commit message (zsh:893):
      "Rename computer: '{old_name}' -> '{new_name}'"

    No-changes guard: git diff --cached --quiet → return early (zsh:889-892).
    Push warn-and-continue (zsh:901-910).
    """
    rev = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=catalog_repo,
        capture_output=True,
    )
    if rev.returncode != 0:
        print("  WARNING: Not a git repository. Skipping git operations.")
        return

    # Stage old folder path (records deletions even though dir is gone) [zsh:886]
    subprocess.run(
        ["git", "add", "-A", "--", f"{old_name}/"],
        cwd=catalog_repo,
        capture_output=True,
    )
    # Stage new folder path (records new dir + any rewritten filenames) [zsh:887]
    subprocess.run(
        ["git", "add", "-A", "--", f"{new_name}/"],
        cwd=catalog_repo,
        capture_output=True,
    )
    # Stage map file [zsh:888]
    subprocess.run(
        ["git", "add", "--", "machine-labels.tsv"],
        cwd=catalog_repo,
        capture_output=True,
    )

    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=catalog_repo,
    )
    if diff.returncode == 0:
        print("  No changes staged.")
        return

    commit_msg = f"Rename computer: '{old_name}' -> '{new_name}'"
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
        print(f"  The commit is saved locally; the folder has ALREADY been renamed")
        print(f"  ('{old_name}/' -> '{new_name}/'). Do NOT re-run --rename. Resolve with:")
        print(f"    cd {catalog_repo} && git pull --rebase && git push")
        print()
```

[VERIFIED: update-list.sh lines 2327-2354, 2374-2431, 867-910]

### Pattern 2: argparse with mutually-exclusive computer flags + config subcommand [ASSUMED]

```python
# src/maccat/cli.py  (illustrative — exact implementation is Claude's discretion)
import argparse
from maccat import __version__

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maccat",
        description="Mac software catalog generator",
    )
    parser.add_argument("--version", action="version", version=f"maccat {__version__}")
    parser.add_argument("--catalog-dir", metavar="PATH",
                        help="Override catalog repo (CFG-03, never written back)")

    # Mutually exclusive computer-selecting group [mirrors zsh:189-277]
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--personal", action="store_true")
    group.add_argument("--office", action="store_true")
    group.add_argument("--computer", metavar="NAME")
    group.add_argument("--machine", metavar="NAME",  # silent back-compat alias
                       dest="computer")

    parser.add_argument("--rename", action="store_true",
                        help="Rename a computer folder interactively")
    parser.add_argument("--archive-days", type=int, metavar="N",
                        help="Archive retention in days (default: 30)")
    parser.add_argument("--no-commit", action="store_true",
                        help="Skip git commit/push; generate/retain/prune still run")

    # config subcommand (CFG-04)
    sub = parser.add_subparsers(dest="subcommand")
    config_p = sub.add_parser("config")
    config_sub = config_p.add_subparsers(dest="config_subcommand")
    config_sub.add_parser("init")
    config_sub.add_parser("show")

    return parser
```

**Note on `--machine` alias:** argparse `add_mutually_exclusive_group` allows multiple arguments
with the same `dest`. Setting `dest="computer"` on `--machine` makes both flags write to
`args.computer`. The mutual-exclusion group handles the "only one" rule. This mirrors the zsh
`parse_arguments` where both `--computer` and `--machine` set `TARGET_LOCATION`.

[ASSUMED — argparse docs pattern; verify against actual argparse behavior]

### Pattern 3: generate-then-sweep ordering — how the just-written catalog is never archived [VERIFIED: zsh source]

The zsh script at lines 2469–2495 makes the ordering explicit:

1. `CURRENT_DATE=$(date "+%Y%m%d%H%M%S")` — timestamp captured AFTER `git_pull` completes
2. `generate_catalog` — writes `mac-software-list-[computer]-YYYYMMDDHHMMSS.txt` (now exists on disk)
3. `retain_newest_per_host "$TARGET_LOCATION"` — the just-written file is the NEWEST for its
   machine, so `pass 1` records it as `newest[computer] = YYYYMMDDHHMMSS`. `pass 2` sees it
   equals the newest → keeps it. It is NEVER moved to archive in the same run.
4. `prune_old_archives "$TARGET_LOCATION"` — operates only on `archive/` (already-archived files),
   never touches the `computer/` main directory.

Python must preserve this ordering. The timestamp must be captured immediately before creating the
`CatalogWriter` (like the zsh `CURRENT_DATE=$(date...)` immediately before `generate_catalog`),
not before `git_pull`.

[VERIFIED: update-list.sh:2469-2495]

### Pattern 4: zipapp build — src/ as source directory [VERIFIED: live test]

The zipapp source must be `src/` (the directory containing `maccat/`), NOT `src/maccat/`
(the package itself). This is the critical src-layout concern:

```bash
# CORRECT: maccat/ appears as a top-level subdirectory in the archive
python3 -m zipapp src \
    --output dist/maccat.pyz \
    --python "/usr/bin/env python3" \
    --main "maccat.__main__:main" \
    --compress

# Archive structure (verified live):
#   __main__.py          ← generated by zipapp, calls maccat.__main__.main()
#   maccat/
#   maccat/__init__.py
#   maccat/__main__.py
#   maccat/cli.py
#   ...
```

```bash
# WRONG: package contents are at archive root; 'import maccat' fails
python3 -m zipapp src/maccat --output dist/maccat-wrong.pyz ...
# Archive structure (verified live):
#   __init__.py          ← at root; 'import maccat' → ModuleNotFoundError
#   __main__.py
#   config.py
#   ...
```

The `--main "maccat.__main__:main"` flag causes zipapp to generate a `__main__.py` wrapper:
```python
# -*- coding: utf-8 -*-
import maccat.__main__
maccat.__main__.main()
```
This correctly dispatches into the version guard and then `cli.run()`.

[VERIFIED: live `python -m zipapp` test in this session]

**`__pycache__` exclusion:** `python -m zipapp` includes `__pycache__/*.pyc` files from `src/`
if they exist. This increases archive size (~26 pyc files per test run) but does NOT break
execution. For a clean artifact, run `find src -name '__pycache__' -exec rm -rf {} + 2>/dev/null`
before the zipapp call in the build script.

### Anti-Patterns to Avoid

- **Using `src/maccat/` as zipapp source:** Archive has no `maccat/` package directory; `import maccat` fails at runtime. Always pass `src/` (or a copy of it). [VERIFIED: live test]
- **Resolving catalog_repo from `__file__` or `Path.cwd()`:** In a `.pyz`, `__file__` resolves to a path inside the zip archive (e.g., `/path/to/maccat.pyz/maccat/cli.py`) — it has no relation to any catalog repo. Always get catalog_repo from `config.resolve_catalog_repo()`. [VERIFIED: PKG-03 requirement]
- **Using `git pull --rebase` or any strategy flag:** The zsh script uses bare `git pull` (line 2346). No rebase flag. Copy exactly.
- **Staging with `git add -A .` instead of `git add -A -- "<folder>/":`** A folder named `-foo` would be parsed as a git option, causing silent staging failure. The `--` pathspec separator is mandatory. [VERIFIED: zsh:2397 comment + zsh:886 comment]
- **Capturing `git commit` output with `capture_output=True` when the user expects to see it:** The zsh script uses `git commit -m ... &>/dev/null` to suppress output. Python should suppress (capture_output=True) to avoid double-printing.
- **Calling `git add machine-labels.tsv` with check=True:** The zsh uses `2>/dev/null || true`. The file may not exist (fresh catalog repo). Use `capture_output=True` without `check=True`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git operations | Custom git library | `subprocess.run(["git", ...], cwd=catalog_repo)` | Already proven approach; zero deps; 5 commands only |
| Computer flag mutual exclusion | Custom counting logic | `argparse.add_mutually_exclusive_group()` | Already implemented in `identity.resolve_computer_selection`; argparse enforces at parse time |
| Catalog repo resolution | Custom path search | `config.resolve_catalog_repo()` already exists | Phase 14 artifact; tested with 42 tests |
| Git repo validation | Custom `os.path.exists(".git")` check | `config.validate_catalog_repo()` already exists | Handles missing dir, non-git dir, no remote (CFG-06) |
| Archive retention | Custom date math | `retention.retain_newest_per_host()` + `retention.prune_old_archives()` already exist | Phase 14 artifact; two-pass algorithm tested |
| Filename construction | Custom string formatting | `naming.make_catalog_filename()` already exists | Phase 13 artifact |
| Version string | Hardcoded in argparse | `from maccat import __version__` | `__init__.py:__version__ = "1.0.0"` already defined |

---

## Common Pitfalls

### Pitfall 1: Wrong zipapp source directory breaks `import maccat`
**What goes wrong:** Using `src/maccat/` as the zipapp source puts `__init__.py` at the archive
root. When Python runs the `.pyz`, it appends the `.pyz` path to `sys.path`. `import maccat` looks
for `maccat/__init__.py` inside the zip — but it's at `__init__.py` (the root), not `maccat/__init__.py`.
`ModuleNotFoundError: No module named 'maccat'`.
**Why it happens:** Mirroring the "build from the package directory" intuition from `wheel` builds.
**How to avoid:** Always pass `src/` (parent of `maccat/`) to `python -m zipapp`. [VERIFIED: live test]
**Warning signs:** Running `maccat.pyz --version` from any directory raises ModuleNotFoundError.

### Pitfall 2: Timestamp captured before git_pull breaks generate-then-sweep invariant
**What goes wrong:** If the timestamp is captured before `git_pull`, and a remote pull brings in
a catalog for the same computer with the SAME timestamp (extremely unlikely but possible), the
`retain_newest_per_host` pass 1 would see two files with the same timestamp and keep both — correct
behavior. However, if the timestamp is captured at program start (before the pull brings in newer
files), the new remote catalog could have a NEWER timestamp than the local run's timestamp, causing
the local file to be immediately archived in the same run.
**How to avoid:** Capture `timestamp = datetime.now().strftime("%Y%m%d%H%M%S")` immediately before
creating `CatalogWriter`, exactly as zsh does `CURRENT_DATE=$(date "+%Y%m%d%H%M%S")` at line 2469
(immediately before `generate_catalog` at 2480). [VERIFIED: zsh:2469-2480]

### Pitfall 3: `--machine` as a separate mutually-exclusive slot adds an off-by-one count
**What goes wrong:** If argparse's mutually-exclusive group has 4 separate arguments
(`--personal`, `--office`, `--computer NAME`, `--machine NAME`) with separate destinations,
and the planner checks `args.machine` independently, the mutual-exclusion rule may not cover
the `--machine` × `--computer` combination (both write different `dest` vars).
**How to avoid:** Give `--machine` the same `dest="computer"` as `--computer`, OR use the existing
`identity.resolve_computer_selection()` which already implements the mutual-exclusion counting.
argparse's `add_mutually_exclusive_group()` handles the XOR constraint at parse time. [ASSUMED]

### Pitfall 4: `git add -A -- "personal/"` vs `git add -A -- "personal"` (trailing slash matters)
**What goes wrong:** `git add -A -- "personal"` might match a file named `personal` at the repo
root in addition to the directory. The zsh script explicitly uses `"${TARGET_LOCATION}/"` (with
trailing slash — see line 2397). The trailing slash is explicit git pathspec syntax meaning "this
path is a directory".
**How to avoid:** Always append `/` when constructing the pathspec: `f"{computer}/"`. [VERIFIED: zsh:2397]

### Pitfall 5: `git commit --quiet` vs capturing stdout
**What goes wrong:** `git commit -m "..." &>/dev/null` in zsh suppresses both stdout and stderr.
In Python, `subprocess.run(..., capture_output=True)` also suppresses both. If instead
`stdout=None` (default) is used, git commit's output appears interleaved with maccat's output.
**How to avoid:** `capture_output=True` on commit; print a custom confirmation line from Python.
The zsh pattern of printing `"  Committed: $commit_message"` after a successful commit should be
reproduced. [VERIFIED: zsh:2413-2415]

### Pitfall 6: `__main__.py` changes needed — currently raises NotImplementedError
**What goes wrong:** The current `src/maccat/__main__.py:main()` raises `NotImplementedError("Phase 16")`.
After Phase 16 implements `cli.run()`, `__main__.py` must call it properly, not just import it.
**How to avoid:** The plan must include a task to replace the `NotImplementedError` stub with
`from maccat.cli import run; run()`. [VERIFIED: src/maccat/__main__.py:19-21]

### Pitfall 7: Rename-mode × selecting-flag combination guard belongs in argparse, not identity.py
**What goes wrong:** `identity.resolve_computer_selection()` does NOT implement the
`--rename` × selecting-flag combination guard (it has a NOTE comment explicitly saying so at
`identity.py:99-101`). The check "if --rename AND any selecting-flag → exit 1" must be done in
`cli.py` after parsing, mirroring zsh:274-277.
**How to avoid:** After `parser.parse_args()`, before any other logic: if `args.rename` and
any selecting flag is set, raise `SystemExit`. [VERIFIED: identity.py:99-101 comment]

---

## Code Examples

### Exact zsh git_pull text (verbatim, for output parity)

```
# zsh:2328-2353 produces this output:
#
# (blank line)
# ------------------------------------------------------------------------------
# Git: Pulling latest changes from remote...
# ------------------------------------------------------------------------------
#   Successfully pulled latest changes.
#   (OR)
#   WARNING: Not a git repository. Skipping git pull.
#   (OR)
#
#   WARNING: Failed to pull from remote repository.
#   Continuing with local state. You may need to resolve conflicts later.
#
```

Note: The zsh separator is `"------------------------------------------------------------------------------"` (78 dashes). This is a cosmetic detail; the Python version may use the same count for exact stdout parity, or a close approximation (not tested in any parity suite in this phase).

### Exact zsh commit message format [VERIFIED: zsh:2410]

```
Added [{computer}] catalog at {YYYYMMDDHHMMSS}
```
Example: `Added [personal] catalog at 20260614201500`

### Exact zsh rename commit message format [VERIFIED: zsh:893]

```
Rename computer: '{old_name}' -> '{new_name}'
```

### Exact --no-commit message format [VERIFIED: zsh:2501-2504]

```
(blank line)
Git auto-commit is disabled (--no-commit flag was used).
To commit manually, run:
  cd {catalog_repo} && git add -A -- "{computer}/" && git add -- machine-labels.tsv 2>/dev/null; git commit -m 'Added catalog' && git push
```

### build-pyz.sh build script

```bash
#!/usr/bin/env bash
# build-pyz.sh — builds dist/maccat.pyz from src/
# Source MUST be src/ (not src/maccat/) — see Phase 16 research Pitfall 1.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
DIST_DIR="$SCRIPT_DIR/dist"
OUTPUT="$DIST_DIR/maccat.pyz"

mkdir -p "$DIST_DIR"

# Remove __pycache__ for a clean archive
find "$SRC_DIR" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

python3 -m zipapp "$SRC_DIR" \
    --output "$OUTPUT" \
    --python "/usr/bin/env python3" \
    --main "maccat.__main__:main" \
    --compress

echo "Built: $OUTPUT"
```

### Testing the .pyz (smoke test pattern)

```python
# tests/test_cli.py — .pyz smoke test
import subprocess, sys
from pathlib import Path

def test_pyz_version_from_unrelated_cwd(tmp_path):
    """PKG-03: .pyz runs from any directory."""
    pyz = Path(__file__).parent.parent / "dist" / "maccat.pyz"
    if not pyz.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")
    result = subprocess.run(
        [sys.executable, str(pyz), "--version"],
        cwd=str(tmp_path),   # unrelated cwd
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "maccat" in result.stdout

def test_pyz_no_file_relative_catalog(tmp_path):
    """PKG-03: catalog_repo must never come from __file__."""
    pyz = Path(__file__).parent.parent / "dist" / "maccat.pyz"
    if not pyz.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")
    # Run from tmp_path with no config → must raise actionable SystemExit,
    # NOT silently use a __file__-relative path.
    result = subprocess.run(
        [sys.executable, str(pyz)],
        cwd=str(tmp_path),
        env={},  # no MACCAT_CATALOG_DIR
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "catalog" in result.stderr.lower() or "catalog" in result.stdout.lower()
```

### End-to-end test fixture pattern (disposable git repo)

```python
# tests/test_cli.py — end-to-end run against a disposable fixture
import subprocess, sys
from pathlib import Path

@pytest.fixture
def disposable_catalog_repo(tmp_path):
    """A real git repo with no remote — safe to run retention + commit against."""
    repo = tmp_path / "catalog"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo,
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo,
                   check=True, capture_output=True)
    return repo

def test_full_run_no_commit(disposable_catalog_repo, monkeypatch):
    """OPS-06: --no-commit runs generate/retain/prune but skips git commit."""
    from maccat.cli import run
    # Inject catalog_repo via env; --personal to skip interactive menu;
    # --no-commit to skip git push (no remote).
    monkeypatch.setenv("MACCAT_CATALOG_DIR", str(disposable_catalog_repo))
    # Run with mocked collectors (empty output) to avoid real filesystem probing
    # ... (see plan-level detail)
```

**Key constraint from MEMORY.md and CONTEXT.md specifics:**
The end-to-end test fixture MUST use a `git init` temp repo. Running against the real catalog
repo or the app repo is destructive (prunes archives, commits). Tests must never touch
`personal/`, `office/`, or the app repo's git history.

---

## Runtime State Inventory

Not applicable — this is a greenfield addition (new files: `cli.py`, `gitops.py`, `build-pyz.sh`).
No existing state is renamed or migrated. The rename-mode git commit stub at `identity.py:625`
is wired (not renamed). No stored data, live service config, OS-registered state, secrets, or
stale build artifacts are involved.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | gitops.py (git_pull, git_commit_and_push) | ✓ | system git | warn-and-continue (already in design) |
| Python 3.11+ | zipapp + venv | ✓ | Homebrew python3 | — (PKG-02 version guard) |
| `python -m zipapp` | build-pyz.sh | ✓ | stdlib, always available | — |
| `find` (BSD) | collectors (already used) | ✓ | macOS built-in | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `git` — code already plans warn-and-continue.

---

## Validation Architecture

> `nyquist_validation: false` in `.planning/config.json` — skip this section.

---

## Security Domain

Git operations via subprocess with `shell=False` and list-form arguments are safe against
injection. The `computer` folder name has already been validated by `validate_computer_name`
(phases 13–14) before reaching `git_commit_and_push`. The `--` pathspec separator handles the
only remaining injection vector (leading-dash folder names). No new network endpoints,
authentication, or secrets are introduced.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SCRIPT_DIR` global (zsh) | `catalog_repo: Path` argument (Python) | This milestone | Enables running from `.pyz` or any directory |
| `cd "$SCRIPT_DIR"` before every git call | `cwd=catalog_repo` kwarg in subprocess | This phase | No directory mutation; safe for concurrent calls |
| `git add -A` (no pathspec) | `git add -A -- "{computer}/"` | This phase (from zsh model) | Leading-dash folder safety |

---

## Open Questions

1. **`--machine` as argparse `dest` alias vs separate dest**
   - What we know: `--machine` is a "silent back-compat alias for --computer" (zsh:238-250). `identity.resolve_computer_selection()` has `machine: str | None` as a separate parameter.
   - What's unclear: Whether Phase 16 should (a) keep `--machine` as a separate argparse dest and pass it to `resolve_computer_selection(machine=args.machine)`, or (b) merge both into `dest="computer"` in the mutually-exclusive group.
   - Recommendation: Option (a) is safer — it preserves the existing `resolve_computer_selection` signature exactly. The mutual-exclusion group catches the XOR constraint. Planner's choice.

2. **`config show` needs the `flag_val` argument**
   - What we know: `config_show(flag_val, config, config_path)` exists in `config.py`. `flag_val` is the value of `--catalog-dir` at runtime.
   - What's unclear: Whether `maccat config show --catalog-dir /foo` should show the overridden path or always show the config-file value.
   - Recommendation: Pass `args.catalog_dir` as `flag_val` to `config_show`, consistent with how the rest of the CLI uses it.

3. **`dist/maccat.pyz` gitignore status**
   - What we know: There is currently no `dist/` directory and no `.gitignore` entry for it.
   - Recommendation: Add `dist/` to `.gitignore` (built artifact, not source). The build script creates it. Plan should include a task to update `.gitignore`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | argparse `add_mutually_exclusive_group` with `dest="computer"` on both `--computer` and `--machine` correctly enforces XOR | Pattern 2: argparse | Would require separate handling of `--machine`; low risk — easy to test |
| A2 | The no-commit message format from zsh is cosmetic and does not need to be byte-identical in this phase | Anti-patterns | Phase 17 parity tests may catch this; flag it in plan |

---

## Sources

### Primary (HIGH confidence)
- `update-list.sh:2327-2354` (git_pull), `update-list.sh:2374-2431` (git_commit_and_push), `update-list.sh:2443-2505` (main flow), `update-list.sh:867-910` (rename git block) — exact line-verified zsh source
- `src/maccat/__main__.py` — live Phase-16 stub
- `src/maccat/identity.py:625` — auto_commit stub location
- `src/maccat/config.py` — resolve_catalog_repo, validate_catalog_repo, resolve_archive_days signatures
- `src/maccat/identity.py:81` — resolve_computer_selection signature
- `src/maccat/collectors/__init__.py` — get_registry(), 12 collectors, 17 sections
- `src/maccat/catalog/writer.py` — CatalogWriter, write_section, write_lines
- `pyproject.toml` — package name is `maccat`, entry point `maccat.__main__:main`
- Live zipapp tests (this session) — confirmed `src/` vs `src/maccat/` behavior

### Secondary (MEDIUM confidence)
- Python stdlib zipapp docs [CITED: https://docs.python.org/3/library/zipapp.html] — `--main`, `--compress`, `--python` flags
- argparse docs [CITED: https://docs.python.org/3/library/argparse.html] — mutually exclusive groups, version action

### Tertiary (LOW confidence)
- None — all critical claims verified against live source

---

## Metadata

**Confidence breakdown:**
- Git command sequence: HIGH — read verbatim from zsh source + line numbers
- Orchestration order: HIGH — read verbatim from zsh main block
- Zipapp build approach: HIGH — verified live with actual `python -m zipapp` calls
- argparse design: MEDIUM — pattern is well-established; exact `dest` aliasing for `--machine` needs test verification
- Test design: MEDIUM — pattern is conventional pytest; specific mock strategy is Claude's discretion

**Research date:** 2026-06-14
**Valid until:** 2026-09-14 (stdlib-only; extremely stable)

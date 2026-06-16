# Phase 16: Git, CLI & Distribution - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 10 (new or modified)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog (Python) | Closest Analog (Zsh) | Match Quality |
|-------------------|------|-----------|-------------------------|----------------------|---------------|
| `src/maccat/cli.py` | entrypoint / orchestrator | request-response | `src/maccat/__main__.py` (version guard + deferred imports) | `update-list.sh:189` (parse_arguments) + `update-list.sh:2443–2505` (main flow) | role-match |
| `src/maccat/gitops.py` | service | request-response | `src/maccat/collectors/homebrew.py` (subprocess list-form, shutil.which, warn-and-continue) | `update-list.sh:2327` (git_pull), `update-list.sh:2374` (git_commit_and_push), `update-list.sh:867` (rename git block) | exact |
| `src/maccat/__main__.py` (edit stub) | entrypoint | request-response | itself (lines 19–21 replace NotImplementedError) | `update-list.sh:2443` (main block entry) | exact |
| `src/maccat/identity.py` (wire :625 stub) | service | request-response | `src/maccat/config.py` (subprocess + warn-and-continue, _is_git_repo pattern) | `update-list.sh:867–910` (rename_machine git block) | exact |
| `scripts/build-pyz.sh` | config / build | — | `update-list.sh` shebang conventions (bash, set -euo pipefail) | `update-list.sh:1–10` (shebang + safety) | role-match |
| `.gitignore` (edit) | config | — | existing `.gitignore` (if present) | — | config-match |
| `tests/test_cli.py` | test | — | `tests/test_config.py` (class-per-group, monkeypatch env, pytest.raises(SystemExit)) | — | role-match |
| `tests/test_gitops.py` | test | — | `tests/test_identity.py` (git_repo fixture, subprocess git operations under test) | `update-list.sh:2327–2431` (behavior spec) | role-match |
| `tests/test_e2e.py` (end-to-end run) | test | — | `tests/conftest.py` git_repo/catalog_repo fixtures + `tests/test_retention.py` (isolated tmp_path) | `update-list.sh:2443–2505` (behavior spec for full run) | role-match |
| `tests/test_pyz.py` (zipapp smoke) | test | — | `tests/test_config.py` (subprocess in tests, skip guards) | — | partial-match |

---

## Pattern Assignments

### `src/maccat/cli.py` (entrypoint / orchestrator, request-response)

**Zsh analog:** `update-list.sh:189` (parse_arguments) and `update-list.sh:2443–2505` (main flow)
**Python analog:** `src/maccat/__main__.py` (deferred import pattern, version guard position)

**Imports pattern** — deferred maccat.* imports inside run(), not at module top:
```python
# src/maccat/cli.py
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# All maccat.* imports go INSIDE run() or called functions — never at module top.
# Mirrors __main__.py deferral pattern to ensure version guard fires first.
```

**argparse parser pattern** (mirrors zsh parse_arguments :189–277):
```python
def _build_parser() -> argparse.ArgumentParser:
    from maccat import __version__

    parser = argparse.ArgumentParser(
        prog="maccat",
        description="Mac software catalog generator",
    )
    parser.add_argument("--version", action="version", version=f"maccat {__version__}")
    parser.add_argument(
        "--catalog-dir", metavar="PATH",
        help="Override catalog repo (CFG-03, never written back)",
    )

    # Mutually exclusive computer-selecting flags [zsh:189–268]
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--personal", action="store_true")
    group.add_argument("--office", action="store_true")
    group.add_argument("--computer", metavar="NAME")
    group.add_argument("--machine", metavar="NAME")   # back-compat alias; separate dest

    parser.add_argument("--rename", action="store_true",
                        help="Rename a computer folder interactively")
    parser.add_argument("--archive-days", type=int, metavar="N")
    parser.add_argument("--no-commit", action="store_true",
                        help="Skip git; disk ops (generate/retain/prune) still run")

    sub = parser.add_subparsers(dest="subcommand")
    config_p = sub.add_parser("config")
    config_sub = config_p.add_subparsers(dest="config_subcommand")
    config_sub.add_parser("init")
    config_sub.add_parser("show")

    return parser
```

**--rename × selecting-flag guard** (zsh:274–277; NOT in identity.resolve_computer_selection — see identity.py:99–101 NOTE):
```python
# After parser.parse_args(), BEFORE any other logic:
if args.rename and any([args.personal, args.office, args.computer, args.machine]):
    sys.exit(
        "ERROR: --rename cannot be combined with --personal, --office, --computer, or --machine."
    )
```

**Run orchestration order** (NON-NEGOTIABLE per CONTEXT, mirrors zsh:2443–2505):
```python
def run() -> None:
    from maccat import gitops
    from maccat.catalog.format import flush_section
    from maccat.catalog.writer import CatalogWriter
    from maccat.collectors import get_registry
    from maccat.config import (
        config_init, config_show, load_config,
        resolve_archive_days, resolve_catalog_repo, validate_catalog_repo,
    )
    from maccat.identity import rename_machine, resolve_computer_selection, select_computer
    from maccat.naming import make_catalog_filename
    from maccat.retention import prune_old_archives, retain_newest_per_host

    parser = _build_parser()
    args = parser.parse_args()

    # config subcommand dispatch (CFG-04)
    if args.subcommand == "config":
        cfg = load_config()
        if args.config_subcommand == "init":
            config_init()
        elif args.config_subcommand == "show":
            config_show(args.catalog_dir, cfg, None)
        return

    # --rename × selecting-flag guard [zsh:274–277]
    if args.rename and any([args.personal, args.office, args.computer, args.machine]):
        sys.exit("ERROR: --rename cannot be combined with computer-selecting flags.")

    cfg = load_config()
    catalog_repo = resolve_catalog_repo(args.catalog_dir, cfg)
    validate_catalog_repo(catalog_repo)     # fail-fast / warn (CFG-06)
    auto_commit = not args.no_commit

    # --rename short-circuit [zsh:2447–2451] — pull, rename, commit, exit BEFORE generate
    if args.rename:
        gitops.git_pull(catalog_repo)
        rename_machine(catalog_repo, auto_commit=auto_commit)
        return

    # Normal run flow (ordering is NON-NEGOTIABLE)
    computer = resolve_computer_selection(
        computer=args.computer, personal=args.personal,
        office=args.office, machine=args.machine,
    )
    computer = select_computer(catalog_repo, pre_selected=computer)
    archive_days = resolve_archive_days(args.archive_days)

    gitops.git_pull(catalog_repo)                              # [zsh:2465]

    # Timestamp captured AFTER git_pull — never before [zsh:2469, Pitfall 2]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")       # [zsh:2469]
    filename = make_catalog_filename(computer, timestamp)      # [zsh:2471]
    output_file = catalog_repo / computer / filename           # [zsh:2474]
    (catalog_repo / computer).mkdir(parents=True, exist_ok=True)  # [zsh:2477]

    # Catalog generation [zsh:2480 generate_catalog]
    with CatalogWriter(output_file) as w:
        w.write_section("Installed Mac Software List")         # [zsh:2226]
        for collector in get_registry():
            result = collector.collect()
            for section in result.sections:
                w.write_section(section.title)
                if section.raw:
                    w.write_lines(section.items)               # raw: no flush_section
                else:
                    w.write_lines(flush_section(section.items))

    retain_newest_per_host(catalog_repo / computer)            # [zsh:2492]
    prune_old_archives(catalog_repo / computer / "archive", archive_days)  # [zsh:2495]

    if auto_commit:
        gitops.git_commit_and_push(catalog_repo, computer, timestamp)  # [zsh:2499]
    else:
        print()
        print("Git auto-commit is disabled (--no-commit flag was used).")
        print("To commit manually, run:")
        print(f"  cd {catalog_repo} && git add -A -- \"{computer}/\" && "
              f"git add -- machine-labels.tsv 2>/dev/null; "
              f"git commit -m 'Added catalog' && git push")   # [zsh:2501–2504]
```

---

### `src/maccat/gitops.py` (service, request-response)

**Zsh analog:** `update-list.sh:2327` (git_pull), `update-list.sh:2374` (git_commit_and_push), `update-list.sh:867` (rename git block)
**Python analog:** `src/maccat/collectors/homebrew.py` and `src/maccat/collectors/mas.py` (subprocess list-form, `shutil.which`, warn-and-continue)

**Imports pattern** (lines 1–6):
```python
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
```

**shutil.which availability check pattern** — from `src/maccat/collectors/homebrew.py:22`:
```python
# homebrew.py:22
def available(self) -> bool:
    return shutil.which("brew") is not None

# gitops.py mirrors: check for git before every public function
if not shutil.which("git"):
    print("  WARNING: git not found. Skipping git pull.")
    return
```

**subprocess list-form, cwd=catalog_repo pattern** — from `src/maccat/collectors/mas.py:65–67` and `src/maccat/config.py:156–165`:
```python
# mas.py:65–67 — the canonical subprocess call form in this codebase
result = subprocess.run(
    ["mas", "list"], capture_output=True, text=True, shell=False
)
if result.returncode != 0:
    ...

# config.py:156–165 — git subprocess pattern already established
result = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    cwd=path,
    capture_output=True,
    text=True,
)
```

**git_pull function** (mirrors zsh:2327–2354):
```python
def git_pull(catalog_repo: Path) -> None:
    """Warn-and-continue on non-git-repo or pull failure. [zsh:2327]"""
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
        ["git", "pull"],          # bare 'git pull' — NO --rebase [zsh:2346]
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
```

**git_commit_and_push function** (mirrors zsh:2374–2431):
```python
def git_commit_and_push(catalog_repo: Path, computer: str, timestamp: str) -> None:
    """Stage folder + tsv map, guard no-changes, commit, push warn-and-continue. [zsh:2374]"""
    # ... (see RESEARCH.md Pattern 1 for full implementation)

    # Stage pattern — '--' end-of-options MANDATORY [zsh:2397; success criterion 4]
    subprocess.run(
        ["git", "add", "-A", "--", f"{computer}/"],   # trailing slash [zsh:2397 comment]
        cwd=catalog_repo,
    )
    # Map file — suppress errors (may not exist) [zsh: || true]
    subprocess.run(
        ["git", "add", "--", "machine-labels.tsv"],
        cwd=catalog_repo,
        capture_output=True,   # no check=True; file may not exist
    )

    # No-changes-to-commit guard [zsh:2403–2406]
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=catalog_repo,
    )
    if diff.returncode == 0:
        print("  No changes to commit.")
        return

    # Commit message format [zsh:2410]
    commit_msg = f"Added [{computer}] catalog at {timestamp}"
    commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=catalog_repo,
        capture_output=True,   # suppress git's own output; Python prints confirmation
        text=True,
    )
    if commit.returncode != 0:
        print("  WARNING: Failed to create commit.")
        return
    print(f"  Committed: {commit_msg}")

    # Push — warn-and-continue [zsh:2422–2430]
    push = subprocess.run(["git", "push"], cwd=catalog_repo, capture_output=True, text=True)
    if push.returncode == 0:
        print("  Successfully pushed to remote.")
    else:
        print()
        print("  WARNING: Failed to push to remote repository.")
        print(f"  cd {catalog_repo} && git push")
        print()
```

**git_commit_rename function** (mirrors zsh:867–910):
```python
def git_commit_rename(catalog_repo: Path, old_name: str, new_name: str) -> None:
    """Stage both folder paths + tsv, commit rename. [zsh:867–910]"""
    # Stage sequence [zsh:886–888]
    subprocess.run(["git", "add", "-A", "--", f"{old_name}/"], cwd=catalog_repo, capture_output=True)
    subprocess.run(["git", "add", "-A", "--", f"{new_name}/"], cwd=catalog_repo, capture_output=True)
    subprocess.run(["git", "add", "--", "machine-labels.tsv"], cwd=catalog_repo, capture_output=True)

    # Rename commit message [zsh:893]
    commit_msg = f"Rename computer: '{old_name}' -> '{new_name}'"
```

---

### `src/maccat/__main__.py` (edit — fill stub at lines 19–21)

**Analog:** itself (current content at lines 19–21)

**Current stub** (lines 19–21):
```python
def main() -> None:
    from maccat.cli import run  # noqa: F401  # Phase 16 will implement maccat.cli
    raise NotImplementedError("Phase 16")
```

**Replacement** — remove `NotImplementedError`, call `run()`:
```python
def main() -> None:
    from maccat.cli import run
    run()
```

The version guard at lines 3–15 and the `if __name__ == "__main__":` block at lines 24–25 are UNCHANGED. Only lines 19–21 change.

---

### `src/maccat/identity.py` (edit — wire stub at line 625)

**Analog:** `src/maccat/config.py` (subprocess git pattern, `_is_git_repo` function)

**Current stub** (line 625):
```python
    # Phase 16: if auto_commit: git_commit_rename(catalog_repo, old_name, new_name)
```

**Replacement** — wire the git commit, inside `rename_machine()` after the TSV map update:
```python
    # Wire rename git commit [zsh:867–910] — Phase 16
    if auto_commit:
        from maccat import gitops
        gitops.git_commit_rename(catalog_repo, old_name, new_name)
```

Note: `gitops` import is local/deferred (inside the function body) to avoid circular imports and to match the deferred-import pattern established in `__main__.py` and `get_registry()`.

---

### `scripts/build-pyz.sh` (new build script)

**Analog:** `update-list.sh` shebang + safety conventions

**Shebang and safety pattern** — from `update-list.sh:1`:
```bash
#!/usr/bin/env bash
# build-pyz.sh — builds dist/maccat.pyz from src/
# Source MUST be src/ (not src/maccat/) — see Phase 16 research Pitfall 1.
set -euo pipefail
```

**Critical zipapp invocation** (verified in RESEARCH.md Pattern 4):
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"      # adjust if script is in scripts/
DIST_DIR="$SCRIPT_DIR/../dist"
OUTPUT="$DIST_DIR/maccat.pyz"

mkdir -p "$DIST_DIR"

# Remove __pycache__ for a clean archive
find "$SRC_DIR" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# CORRECT: src/ as source so maccat/ appears as top-level dir in archive
python3 -m zipapp "$SRC_DIR" \
    --output "$OUTPUT" \
    --python "/usr/bin/env python3" \
    --main "maccat.__main__:main" \
    --compress

echo "Built: $OUTPUT"
```

**NEVER use `src/maccat/` as the zipapp source** — see RESEARCH.md Pitfall 1.

---

### `.gitignore` (edit — add dist/)

**Pattern:** Append `dist/` entry (build artifact, not source).

```
dist/
```

---

### `tests/test_gitops.py` (test)

**Analog:** `tests/test_identity.py` (git_repo fixture + subprocess-level operations under test) and `tests/test_config.py` (monkeypatch, pytest.raises)

**Imports pattern** (from `tests/test_config.py:1–24`):
```python
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from maccat.gitops import git_commit_and_push, git_commit_rename, git_pull
```

**git_repo fixture** — reuse from `tests/conftest.py:22–40` (already defined, covers all git tests):
```python
# Reuse the existing conftest.py git_repo fixture — do NOT redefine.
# git_repo: disposable git init in tmp_path, user.email + user.name set.
# Note: no remote → push will fail (warn-and-continue is the expected behavior).

def test_git_pull_no_remote_warns(git_repo: Path, capsys) -> None:
    """git_pull on a repo with no remote warns and continues."""
    git_pull(git_repo)
    captured = capsys.readouterr()
    # May warn "not a git repo" or fail-to-pull — either is warn-and-continue
    # (no remote configured → return code != 0 on git pull)
    assert "WARNING" in captured.out or "Successfully" in captured.out
```

**Stage + commit pattern under test** (key test: `--` pathspec safety and no-changes guard):
```python
def test_git_commit_leading_dash_safety(git_repo: Path) -> None:
    """git add -A -- 'computer/' must not error when called with a plain folder name."""
    # Create a file in the computer subfolder
    computer_dir = git_repo / "personal"
    computer_dir.mkdir()
    (computer_dir / "test.txt").write_text("hello", encoding="utf-8")

    # Must not raise; the '--' separator prevents leading-dash misparse
    git_commit_and_push(git_repo, "personal", "20260614120000")
    # With no remote, push will warn but commit should succeed
```

**No-changes guard test**:
```python
def test_git_commit_no_changes_exits_cleanly(git_repo: Path, capsys) -> None:
    """Nothing staged → no-changes guard returns without error."""
    git_commit_and_push(git_repo, "personal", "20260614120000")
    captured = capsys.readouterr()
    assert "No changes to commit" in captured.out
```

---

### `tests/test_cli.py` (test — argparse, --no-commit, end-to-end fixture)

**Analog:** `tests/test_config.py` (class-per-group, monkeypatch env, `pytest.raises(SystemExit)`)

**Imports pattern** (from `tests/test_config.py:1–24`):
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
```

**disposable_catalog_repo fixture** — extends the existing `git_repo` conftest fixture:
```python
@pytest.fixture()
def disposable_catalog_repo(git_repo: Path) -> Path:
    """Git repo ready for end-to-end run tests — isolated, no real catalog touched.

    Builds on conftest.git_repo (disposable tmp_path + git init).
    NEVER reference real personal/ or office/ directories.
    """
    return git_repo  # or pre-populate as needed for specific tests
```

**argparse tests**:
```python
class TestArgparse:
    def test_version_exits_cleanly(self) -> None:
        """--version exits 0 and prints 'maccat'."""
        from maccat.cli import _build_parser
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0

    def test_mutually_exclusive_flags_error(self) -> None:
        """--personal + --office together → argparse error (SystemExit 2)."""
        from maccat.cli import _build_parser
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--personal", "--office"])
        assert exc.value.code == 2

    def test_rename_with_selecting_flag_error(self) -> None:
        """--rename + --personal → SystemExit before run."""
        with pytest.raises(SystemExit):
            from maccat.cli import run
            import sys
            sys.argv = ["maccat", "--rename", "--personal"]
            run()
```

**--no-commit end-to-end test** (disposable git repo, monkeypatched env):
```python
class TestNoCommit:
    def test_no_commit_skips_git(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """--no-commit runs generate/retain/prune but skips git commit/push."""
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(disposable_catalog_repo))
        # monkeypatch get_registry() to return empty list to avoid real system probing
        with patch("maccat.collectors.get_registry", return_value=[]):
            from maccat.cli import run
            import sys
            monkeypatch.setattr(sys, "argv", ["maccat", "--personal", "--no-commit"])
            run()
        # No commit should have been made
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=disposable_catalog_repo,
            capture_output=True, text=True,
        )
        assert result.stdout.strip() == ""   # no commits
```

---

### `tests/test_pyz.py` (zipapp smoke test)

**Analog:** `tests/test_config.py` (subprocess in tests, skip guards for optional deps)

**Pattern** — skip if dist/maccat.pyz not built yet (from RESEARCH.md Code Examples):
```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PYZ = Path(__file__).parent.parent / "dist" / "maccat.pyz"


def _pyz_skip():
    if not PYZ.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")


def test_pyz_version_from_unrelated_cwd(tmp_path: Path) -> None:
    """PKG-03: .pyz --version works from an unrelated cwd."""
    _pyz_skip()
    result = subprocess.run(
        [sys.executable, str(PYZ), "--version"],
        cwd=str(tmp_path),
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "maccat" in result.stdout


def test_pyz_no_file_relative_catalog(tmp_path: Path) -> None:
    """PKG-03: without MACCAT_CATALOG_DIR set, must exit nonzero with actionable message."""
    _pyz_skip()
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in ("MACCAT_CATALOG_DIR", "XDG_CONFIG_HOME")}
    result = subprocess.run(
        [sys.executable, str(PYZ)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "catalog" in output   # actionable error message, not silent __file__ fallback
```

---

## Shared Patterns

### subprocess List-Form (shell=False, cwd=path)
**Source:** `src/maccat/collectors/mas.py:65–67`, `src/maccat/config.py:156–165`
**Apply to:** `gitops.py` (all git calls), `tests/test_cli.py` (subprocess in tests)

```python
# Canonical form — always list args, never string, shell=False (the default)
result = subprocess.run(
    ["git", "operation"],
    cwd=catalog_repo,
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print("  WARNING: ...")
    return  # warn-and-continue; never raise
```

### shutil.which Tool-Availability Check
**Source:** `src/maccat/collectors/homebrew.py:22`, `src/maccat/collectors/mas.py:25`
**Apply to:** `gitops.py` (check for `git` before every public function)

```python
import shutil
if not shutil.which("git"):
    print("  WARNING: git not found. Skipping git operations.")
    return
```

### Warn-and-Continue (non-fatal subprocess failures)
**Source:** `src/maccat/collectors/homebrew.py:36–45`, `src/maccat/collectors/mas.py:49–64`
**Apply to:** `gitops.git_pull` (pull failure), `gitops.git_commit_and_push` (push failure)

```python
# Collector pattern (homebrew.py:36–45):
if not self.available():
    print("  WARNING: brew not found.", file=sys.stderr)
    return CollectorResult(sections=[Section(..., items=["Homebrew is not installed."], raw=True)])

# Git pattern (mirrors exactly): non-zero exit → print WARNING, return (do not raise)
if result.returncode != 0:
    print("  WARNING: Failed to pull from remote repository.")
    print("  Continuing with local state. ...")
    return
```

### Deferred Imports Inside Function Body
**Source:** `src/maccat/__main__.py:19–21`, `src/maccat/collectors/__init__.py:41–53`
**Apply to:** `src/maccat/cli.py:run()` (all maccat.* imports), `src/maccat/identity.py:625` (gitops import)

```python
# __main__.py pattern:
def main() -> None:
    from maccat.cli import run   # deferred — after version guard
    run()

# get_registry() pattern:
def get_registry() -> list[Collector]:
    from maccat.collectors.homebrew import HomebrewCollector  # deferred — incremental safety
    ...
```

### Atomic Temp-File Write
**Source:** `src/maccat/config.py:227–242`, `src/maccat/catalog/writer.py` (CatalogWriter.__enter__/__exit__)
**Apply to:** Not directly needed in Phase 16 new files (gitops.py does no file writes), but used by CatalogWriter in the generate phase.

### pytest Disposable Git Repo Fixture
**Source:** `tests/conftest.py:22–40` (git_repo), `tests/conftest.py:43–55` (catalog_repo)
**Apply to:** `tests/test_gitops.py`, `tests/test_cli.py` (end-to-end tests)

```python
# REUSE existing fixtures — never redefine git_repo or catalog_repo
# conftest.py:22–40:
@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    return tmp_path
```

### pytest Class-Per-Group Test Structure
**Source:** `tests/test_config.py:31–63` (TestResolveConfigPath), `tests/test_identity.py:35–69` (TestValidateComputerName)
**Apply to:** `tests/test_cli.py`, `tests/test_gitops.py`

```python
class TestGitPull:
    def test_not_a_git_repo_warns(self, tmp_path: Path, capsys) -> None: ...
    def test_repo_with_no_remote_warns(self, git_repo: Path, capsys) -> None: ...

class TestGitCommitAndPush:
    def test_leading_dash_safety(self, git_repo: Path) -> None: ...
    def test_no_changes_returns_early(self, git_repo: Path, capsys) -> None: ...
    def test_commit_message_format(self, git_repo: Path, capsys) -> None: ...
```

### from __future__ import annotations + type hints
**Source:** All existing Phase 13–15 Python files (e.g., `src/maccat/config.py:1`, `src/maccat/collectors/homebrew.py:1`)
**Apply to:** All Phase 16 .py files

```python
from __future__ import annotations
# ... imports ...
def git_pull(catalog_repo: Path) -> None: ...
def git_commit_and_push(catalog_repo: Path, computer: str, timestamp: str) -> None: ...
```

---

## No Analog Found

All files map to zsh behavior-spec analogs plus Python structural analogs from phases 13–15. No file is without a pattern source.

---

## Anti-Patterns to Avoid (Critical)

| Anti-Pattern | Where It Fails | Correct Pattern |
|---|---|---|
| `python -m zipapp src/maccat` | `import maccat` fails (no `maccat/` dir in archive root) | `python -m zipapp src` (parent of `maccat/`) |
| Capturing timestamp before `git_pull` | Same-run archive of the new catalog (Pitfall 2) | `timestamp = datetime.now()...` immediately before `CatalogWriter(output_file)` |
| `git add -A .` without `--` | Leading-dash folder names parsed as git options | `git add -A -- "computer/"` (trailing slash + `--`) |
| `check=True` on `git add -- machine-labels.tsv` | Raises on missing file (fresh repo) | `capture_output=True` without `check=True` |
| `from maccat.cli import ...` at module top of `__main__.py` | Bypasses version guard | All `maccat.*` imports inside `main()` body |
| `git pull --rebase` | Diverges from zsh behavior (zsh:2346 bare pull) | `["git", "pull"]` (no flags) |
| `resolve_catalog_repo` using `Path(__file__)` | Breaks in .pyz (resolves inside zip) | `resolve_catalog_repo(flag_val, cfg)` via config/env/flag only |
| Implementing `--rename × selecting-flag` guard in `identity.py` | identity.py:99–101 explicitly excludes it | Implement in `cli.py` after `parse_args()` |

---

## Metadata

**Analog search scope:** `src/maccat/` (all Phase 13–15 modules), `tests/` (all test files), `update-list.sh` (lines 189–277, 867–910, 2220–2313, 2327–2431, 2443–2505), `.planning/phases/13–15/` (PATTERNS.md, SUMMARY.md files)
**Files scanned:** 14 source files + 8 test files + 1 zsh reference
**Pattern extraction date:** 2026-06-14

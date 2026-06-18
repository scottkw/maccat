"""Git operations for the maccat catalog tool.

Three public functions mirror the zsh git helper functions in update-list.sh:
  git_pull             — zsh:2327-2354
  git_commit_and_push  — zsh:2374-2431
  git_commit_rename    — zsh:867-910

Design invariants:
- shell=False throughout; all args are list-form (never string interpolation).
- cwd=catalog_repo replaces 'cd "$SCRIPT_DIR"' in zsh.
- All git add calls use '--' before the pathspec (leading-dash folder safety; zsh:2397).
- warn-and-continue: no function raises; all failures print WARNING and return.
- No check=True on any git call (all warn-and-continue per zsh || true / 2>/dev/null).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_SEP = "-" * 78


def _git_available() -> bool:
    """Return True when git is on PATH; print WARNING and return False otherwise."""
    if shutil.which("git") is None:
        print("  WARNING: git not found. Skipping git operations.")
        return False
    return True


def _is_git_repo(catalog_repo: Path) -> bool:
    """Return True when catalog_repo is inside a git repository.

    Runs 'git rev-parse --git-dir' to detect the repo; prints WARNING on failure.
    Mirrors zsh:2340-2343 and zsh:2395-2396 (rev-parse guard before every git op).
    """
    rev = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=catalog_repo,
        capture_output=True,
    )
    if rev.returncode != 0:
        print("  WARNING: Not a git repository. Skipping git operations.")
        return False
    return True


def git_pull(catalog_repo: Path) -> None:
    """Pull latest changes from remote.

    Mirrors zsh git_pull :2327-2354:
    - Bare 'git pull' only — no --rebase, no strategy flags (zsh:2346).
    - warn-and-continue on non-git-repo (zsh:2340-2343).
    - warn-and-continue on pull failure (zsh:2349-2353).

    Args:
        catalog_repo: Path to the catalog git repository.
    """
    print()
    print(_SEP)
    print("Git: Pulling latest changes from remote...")
    print(_SEP)

    if not _git_available():
        return

    if not _is_git_repo(catalog_repo):
        return

    result = subprocess.run(
        ["git", "pull"],  # bare pull — NO --rebase (zsh:2346)
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
    """Stage the computer folder and TSV map, then commit and push.

    Mirrors zsh git_commit_and_push :2374-2431:
    - Stages all changes in 'computer/' with '--' end-of-options (zsh:2397).
    - Stages machine-labels.tsv without check=True (file may not exist; zsh:|| true).
    - No-changes guard: skips commit when nothing is staged (zsh:2403-2406).
    - Commit message: 'Added [{computer}] catalog at {timestamp}' (zsh:2410).
    - warn-and-continue on commit failure and push failure (zsh:2422-2430).

    Args:
        catalog_repo: Path to the catalog git repository.
        computer:     Computer folder name (e.g. "MyMac", "WorkLaptop").
        timestamp:    14-digit timestamp string (YYYYMMDDHHMMSS).
    """
    print()
    print(_SEP)
    print("Git: Committing and pushing changes...")
    print(_SEP)

    if not _git_available():
        return

    if not _is_git_repo(catalog_repo):
        return

    # Stage all changes in computer folder — '--' is MANDATORY (zsh:2397 leading-dash safety)
    print(f"  Staging all changes in {computer}/...")
    subprocess.run(
        ["git", "add", "-A", "--", f"{computer}/"],
        cwd=catalog_repo,
    )

    # Stage map file; suppress errors — file may not exist in a fresh repo (zsh:|| true)
    subprocess.run(
        ["git", "add", "--", "machine-labels.tsv"],
        cwd=catalog_repo,
        capture_output=True,
    )

    # No-changes guard: if nothing is staged, skip the commit (zsh:2403-2406)
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
    """Stage both folder paths and TSV map, then commit the rename.

    Mirrors zsh rename_machine git block :867-910:
    - Stages old folder (records deletions) with '--' end-of-options (zsh:886).
    - Stages new folder (records new dir + rewritten filenames) with '--' (zsh:887).
    - Stages machine-labels.tsv (zsh:888).
    - No-changes guard: skips commit when nothing is staged (zsh:889-892).
    - Commit message: "Rename computer: '{old_name}' -> '{new_name}'" (zsh:893).
    - warn-and-continue on push failure (zsh:901-910).

    Args:
        catalog_repo: Path to the catalog git repository.
        old_name:     Original computer folder name.
        new_name:     New computer folder name after rename.
    """
    if not _git_available():
        return

    if not _is_git_repo(catalog_repo):
        return

    # Stage old folder path — records deletions even if dir is gone (zsh:886)
    subprocess.run(
        ["git", "add", "-A", "--", f"{old_name}/"],
        cwd=catalog_repo,
        capture_output=True,
    )
    # Stage new folder path — records new dir + any rewritten filenames (zsh:887)
    subprocess.run(
        ["git", "add", "-A", "--", f"{new_name}/"],
        cwd=catalog_repo,
        capture_output=True,
    )
    # Stage map file (zsh:888)
    subprocess.run(
        ["git", "add", "--", "machine-labels.tsv"],
        cwd=catalog_repo,
        capture_output=True,
    )

    # No-changes guard (zsh:889-892)
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
        print(
            f"  The commit is saved locally; the folder has ALREADY been renamed"
            f" ('{old_name}/' -> '{new_name}/'). Do NOT re-run --rename. Resolve with:"
        )
        print(f"    cd {catalog_repo} && git pull --rebase && git push")
        print()


def git_commit_convert(
    catalog_repo: Path,
    md_path: Path,
    txt_path: Path,
) -> None:
    """Stage the new .md and the deleted .txt, then commit and push.

    Mirrors git_commit_rename pattern. Stages exactly two individual file
    paths (new .md + deleted .txt) rather than directory paths.

    - _git_available() + _is_git_repo() guards.
    - relative_to() guard: if either path is outside catalog_repo, warn and return.
    - Two git add -A -- <relpath> calls for the individual file paths.
    - No-changes guard: skip commit when nothing staged.
    - warn-and-continue on commit failure and push failure.

    Args:
        catalog_repo: Path to the catalog git repository (heuristic: txt_path.parent.parent).
        md_path:      Absolute path of the newly-written .md file.
        txt_path:     Absolute path of the removed .txt file.
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

    # Stage the new .md (git add -A records the new file; '--' = leading-dash safety)
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

    # No-changes guard (mirrors git_commit_rename pattern)
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

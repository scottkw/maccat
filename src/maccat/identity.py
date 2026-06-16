"""Computer identity: folder selection, validation, machine-label TSV, rename.

Provides the computer-selecting-flag resolver, the always-shown interactive
computer-folder selection menu, atomic machine-labels.tsv management, and the
rename-machine workflow.

Zsh analogs:
  validate_computer_name         update-list.sh lines 117–141
  validate_computer_name_quiet   update-list.sh lines 156–175
  parse_arguments (subset)       update-list.sh lines 199–268  (flag-alias + mutual-exclusion)
  select_computer                update-list.sh lines 308–490
  upsert_machine_label           update-list.sh lines 557–606
  rename_machine                 update-list.sh lines 637–923
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path

from maccat.naming import make_catalog_filename, parse_catalog_filename

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_computer_name(val: str) -> None:
    """Fatal validator — raises SystemExit with an actionable message.

    Used for --computer flag values at resolve time (mirrors
    update-list.sh lines 117–141 which call ``exit 1``).

    Four rules (same as validate_computer_name_quiet):
    1. Must be non-empty.
    2. Must not have leading or trailing whitespace.
    3. Must not contain ``/``, ``[``, or ``]``.
    4. Must not contain TAB or newline.
    """
    if not val:
        raise SystemExit("ERROR: computer name must not be empty")
    if val != val.strip():
        raise SystemExit(
            f"ERROR: computer name must not have leading or trailing whitespace (got '{val}')"
        )
    if any(c in val for c in "/[]"):
        raise SystemExit(
            f"ERROR: computer name must not contain /, [, or ] (got '{val}')"
        )
    if "\t" in val or "\n" in val:
        raise SystemExit("ERROR: computer name must not contain tab or newline characters")


def validate_computer_name_quiet(val: str) -> str | None:
    """Non-fatal validator — returns error message string, or None if valid.

    Used inside interactive re-prompt loops where catching an error and
    re-prompting is preferred over exiting (mirrors update-list.sh lines
    156–175 which call ``return 1`` and echo a reason).
    """
    if not val:
        return "ERROR: computer name must not be empty"
    if val != val.strip():
        return (
            f"ERROR: computer name must not have leading or trailing whitespace (got '{val}')"
        )
    if any(c in val for c in "/[]"):
        return f"ERROR: computer name must not contain /, [, or ] (got '{val}')"
    if "\t" in val or "\n" in val:
        return "ERROR: computer name must not contain tab or newline characters"
    return None


# ---------------------------------------------------------------------------
# Flag resolver  (OPS-02 / SC3 — pure, no argparse, no TTY)
# ---------------------------------------------------------------------------


def resolve_computer_selection(
    *,
    computer: str | None,
) -> str | None:
    """Map the --computer flag to a folder name (or None for interactive fallback).

    Validates and returns the supplied computer name, or returns None when no
    name was supplied (caller falls back to the select_computer menu).

    - If computer is falsy (None or "")  → return None (interactive fallback).
    - Otherwise                          → call validate_computer_name(computer)
                                           and return computer.

    NOTE: The --rename × selecting-flag combination guard belongs to cli.py
    (it depends on argparse Namespace state and is not a concern of this function).
    """
    if not computer:
        return None
    validate_computer_name(computer)
    return computer


# ---------------------------------------------------------------------------
# TSV parsing  (single source of truth — WR-03)
# ---------------------------------------------------------------------------


def _iter_tsv_entries(map_file: Path) -> list[tuple[str, str]]:
    """Parse machine-labels.tsv into (host, label) data tuples.

    Single shared TSV reader so the three former copies (folder discovery,
    saved-folder lookup, rename map-update) cannot drift (WR-03). Skips:
    - blank lines
    - comment lines (start with ``#``)
    - lines without a TAB separator
    - lines whose host OR label column is empty (matches zsh
      ``[[ -z "$map_host" || -z "$map_label" ]] && continue``,
      update-list.sh line 376)

    Returns an empty list when the file is absent or unreadable as a file.
    """
    if not map_file.is_file():
        return []
    entries: list[tuple[str, str]] = []
    for line in map_file.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        host, label = line.split("\t", 1)
        if not host or not label:
            continue
        entries.append((host, label))
    return entries


# ---------------------------------------------------------------------------
# Folder discovery  (shared by select_computer and rename_machine)
# ---------------------------------------------------------------------------


def discover_computer_folders(catalog_repo: Path) -> list[str]:
    """Return sorted, deduplicated list of computer folder names.

    Two sources, merged (update-list.sh lines 344–394, 644–686):
    a) Top-level dirs in catalog_repo that contain at least one
       ``mac-software-list-*.txt`` file.
    b) machine column values from machine-labels.tsv (skips comment lines,
       blank lines, and lines without a TAB separator).

    Result is alphabetically sorted. No saved-default promotion — that is
    handled by select_computer when building its menu.
    """
    seen: set[str] = set()
    computers: list[str] = []

    # Source a: dirs with catalog files
    for d in sorted(catalog_repo.iterdir()):
        if not d.is_dir():
            continue
        if any(d.glob("mac-software-list-*.txt")):
            if d.name not in seen:
                computers.append(d.name)
                seen.add(d.name)

    # Source b: TSV map values (folders not yet on disk may still be listed)
    map_file = catalog_repo / "machine-labels.tsv"
    for _host, label in _iter_tsv_entries(map_file):
        if label not in seen:
            computers.append(label)
            seen.add(label)

    return sorted(computers)


# ---------------------------------------------------------------------------
# Machine-label TSV  (OPS-05)
# ---------------------------------------------------------------------------


def _atomic_write_lines(path: Path, lines: list[str], tmp_dir: Path) -> None:
    """Atomically write ``lines`` to ``path`` via tempfile + POSIX rename.

    Builds the complete content in a temp file in ``tmp_dir`` (same filesystem
    as ``path`` so the rename is atomic), then renames it over ``path`` in a
    single syscall. On ANY failure the temp file is removed so a crash leaves
    at most a stray ``.tmp`` file and never a partially-written ``path``.

    Used by upsert_machine_label and rename_machine's TSV update so the
    cleanup-on-failure behaviour lives in exactly one place (CR-01, IN-02).
    """
    fd, tmp = tempfile.mkstemp(dir=tmp_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(lines)
        Path(tmp).rename(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def upsert_machine_label(catalog_repo: Path, folder: str) -> None:
    """Atomically update machine-labels.tsv with hostname → folder mapping.

    Creates the file with a 3-line header if absent. Preserves existing
    comment and blank lines verbatim. Replaces the current host's entry if
    found, appends a new entry if not. Write is atomic: tempfile + rename.

    Zsh analog: update-list.sh lines 557–606.
    """
    map_file = catalog_repo / "machine-labels.tsv"
    current_host = socket.gethostname()

    # Build the full desired content in memory (header if absent + merged
    # entries), then perform ONE atomic mkstemp + rename. The zsh original
    # builds the entire file (header + entries) into a single temp file and
    # renames once; it never does a separate header write followed by a
    # read-after-write (which would leave a header-only partial state and a
    # TOCTOU window if interrupted between the two syscalls). See CR-01.
    header_lines = [
        "# Mac Software List — hostname to computer-folder map\n",
        "# Format: hostname\tcomputer-folder\n",
        "# One entry per line. Lines beginning with # and blank lines are ignored.\n",
    ]

    if map_file.exists():
        lines = map_file.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = list(header_lines)

    found = False
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped == "":
            # Blank line — preserve verbatim
            out.append("\n")
        elif stripped.startswith("#"):
            # Comment line — preserve verbatim
            out.append(line if line.endswith("\n") else line + "\n")
        else:
            host = stripped.split("\t", 1)[0]
            if host == current_host:
                out.append(f"{current_host}\t{folder}\n")
                found = True
            else:
                out.append(line if line.endswith("\n") else line + "\n")
    if not found:
        out.append(f"{current_host}\t{folder}\n")

    # Single atomic write: tempfile.mkstemp + os.fdopen + Path.rename
    # (POSIX-atomic). Clean up the temp file if anything fails so a crash
    # leaves at most a stray .tmp and never a partially-written map_file.
    _atomic_write_lines(map_file, out, catalog_repo)
    print(f"  Saved computer folder mapping: {current_host} -> {folder}")


# ---------------------------------------------------------------------------
# Computer selection menu  (OPS-01, OPS-02, OPS-08)
# ---------------------------------------------------------------------------


def select_computer(
    catalog_repo: Path,
    *,
    computer_name: str | None = None,
) -> str | None:
    """Select (or create) a computer folder for this catalog run.

    Flag path (computer_name is not None):
        mkdir -p the folder, call upsert_machine_label, print announcement,
        return the name. No menu shown. TTY guard is NOT applied here because
        the caller already resolved the name.

    Interactive path (computer_name is None):
        1. Non-TTY guard: raise SystemExit immediately when stdin is not a TTY.
        2. TSV lookup: find this host's saved_folder (remembered default).
        3. Discovery: call discover_computer_folders; promote saved_folder to
           position 0 if present.
        4. Always-shown numbered menu with Create-new and Quit entries.
        5. Input loop: EOF → routed through the Quit branch (prints
           "No catalog written." then returns None, matching zsh); q/quit →
           Quit; empty input with saved_folder → return saved_folder; empty
           without → re-prompt; invalid → re-prompt.
        6. Quit branch: print "No catalog written." return None.
        7. Create-new branch: prompt for name, validate, mkdir, upsert, return.
        8. Existing branch: upsert, return chosen name.

    Zsh analog: update-list.sh lines 308–490.
    """
    # --- Flag path ---
    if computer_name is not None:
        (catalog_repo / computer_name).mkdir(parents=True, exist_ok=True)
        upsert_machine_label(catalog_repo, computer_name)
        print(f"Computer: {computer_name} (from command-line argument)")
        return computer_name

    # --- Interactive path ---

    # Non-TTY guard (update-list.sh lines 337–340): check BEFORE any input()
    if not sys.stdin.isatty():
        raise SystemExit(
            'ERROR: No computer selected and stdin is not a TTY. Pass --computer "Name".'
        )

    # TSV lookup for saved_folder (update-list.sh lines 319–334)
    current_host = socket.gethostname()
    saved_folder = ""
    map_file = catalog_repo / "machine-labels.tsv"
    for host, label in _iter_tsv_entries(map_file):
        if host == current_host:
            saved_folder = label
            break

    # Folder discovery (update-list.sh lines 343–394)
    computers = discover_computer_folders(catalog_repo)

    # Promote saved_folder to position 0 if present (update-list.sh lines 383–394)
    if saved_folder and saved_folder in computers:
        computers = [saved_folder] + [c for c in computers if c != saved_folder]

    # Menu indices (1-based, matching zsh)
    create_new_idx = len(computers) + 1
    quit_idx = len(computers) + 2

    print("")
    print("Select a computer:")
    print("")
    for i, name in enumerate(computers, start=1):
        if saved_folder and name == saved_folder:
            print(f"  {i}) {name}   (this machine — default)")
        else:
            print(f"  {i}) {name}")
    print(f"  {create_new_idx}) Create new computer")
    print(f"  {quit_idx}) Quit")
    print("")

    # Input loop (update-list.sh lines 419–460)
    choice: str | int
    while True:
        if saved_folder:
            prompt = f"Enter your choice [1-{quit_idx}, or Enter for the default]: "
        else:
            prompt = f"Enter your choice [1-{quit_idx}]: "

        try:
            choice = input(prompt)
        except EOFError:
            # EOF (Ctrl-D / closed stdin) → route through the Quit branch,
            # matching zsh which sets choice="$quit_idx" on EOF and falls
            # through to the Quit handler that prints "No catalog written."
            # (update-list.sh lines 425–426, 463–465). See WR-02.
            choice = str(quit_idx)
            break

        lc = choice.lower()
        if lc in ("q", "quit"):
            choice = str(quit_idx)

        if choice == "":
            if saved_folder:
                # Resolve Enter to the saved folder's index
                if saved_folder not in computers:
                    raise SystemExit(
                        f"ERROR: saved default '{saved_folder}' is not in the computer list."
                    )
                choice = str(computers.index(saved_folder) + 1)
            else:
                print("No default for this machine — please enter a number.")
                continue

        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= quit_idx:
                break
        print(f"ERROR: Invalid choice '{choice}'. Please enter 1-{quit_idx}.")

    n = int(choice)

    # Branch on choice (update-list.sh lines 463–489)
    if n == quit_idx:
        print("No catalog written.")
        return None

    if n == create_new_idx:
        # Create-new re-prompt loop
        while True:
            try:
                new_name = input("Enter a name for the new computer: ")
            except EOFError:
                print("No catalog written.")
                return None
            err = validate_computer_name_quiet(new_name)
            if err is None:
                break
            print(err)
        # Select-or-create: mkdir + upsert + announce
        (catalog_repo / new_name).mkdir(parents=True, exist_ok=True)
        upsert_machine_label(catalog_repo, new_name)
        print(f"Computer: {new_name}")
        return new_name

    # Existing computer selected (update-list.sh line 485)
    selected = computers[n - 1]
    upsert_machine_label(catalog_repo, selected)
    print(f"Computer: {selected}")
    return selected


# ---------------------------------------------------------------------------
# Rename machine  (OPS-07)
# ---------------------------------------------------------------------------


def rename_machine(catalog_repo: Path, *, auto_commit: bool = False) -> None:
    """Rename a computer: folder move + opt-out filename rewrite + TSV update.

    TTY guard: raise SystemExit when stdin is not a TTY (rename requires
    interactive prompts).

    Guards (in order, mirror update-list.sh lines 747–766):
    1. No-op: new == old → WARNING, return.
    2. Folder-not-found: old_dir not a dir → WARNING, return.
    3. Refuse-clobber (HARD): new_dir exists → SystemExit (never merge).

    After folder move, prompts for opt-out filename rewrite (default YES).
    TSV map update is unconditional (runs even if filenames not rewritten).

    Git commit section is a stub — Phase 16 wires the actual commit.

    Zsh analog: update-list.sh lines 637–923.
    """
    # TTY guard (update-list.sh lines 638–641)
    if not sys.stdin.isatty():
        raise SystemExit(
            "ERROR: --rename requires an interactive terminal (stdin is not a TTY)."
            " Cannot prompt for computer names."
        )

    # Folder discovery — no saved-default promotion for rename picker
    computers = discover_computer_folders(catalog_repo)

    if not computers:
        print("No computers found. Nothing to rename.")
        return

    quit_idx = len(computers) + 1

    print("")
    print("Select the computer to rename:")
    print("")
    for i, name in enumerate(computers, start=1):
        print(f"  {i}) {name}")
    print(f"  {quit_idx}) Quit")
    print("")

    # Selection loop
    choice: str
    while True:
        try:
            choice = input(f"Enter your choice [1-{quit_idx}]: ")
        except EOFError:
            print("Nothing renamed.")
            return

        lc = choice.lower()
        if lc in ("q", "quit"):
            choice = str(quit_idx)

        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= quit_idx:
                break
        print(f"ERROR: Invalid choice '{choice}'. Please enter 1-{quit_idx}.")

    n = int(choice)
    if n == quit_idx:
        print("Nothing renamed.")
        return

    old_name = computers[n - 1]

    # New name prompt (update-list.sh lines 730–745)
    print("")
    while True:
        try:
            new_name = input(f"Enter new name for '{old_name}': ")
        except EOFError:
            print("Nothing renamed.")
            return
        err = validate_computer_name_quiet(new_name)
        if err is None:
            break
        print(err)

    # Guard 1: No-op (update-list.sh lines 748–750)
    if new_name == old_name:
        print(
            f"WARNING: New name is the same as the old name ('{old_name}'). Nothing renamed."
        )
        return

    old_dir = catalog_repo / old_name
    new_dir = catalog_repo / new_name

    # Guard 2: Folder-not-found (update-list.sh lines 758–761) — warn + return
    if not old_dir.is_dir():
        print(
            f"WARNING: Computer folder '{old_name}' not found in {catalog_repo}."
            " Nothing renamed."
        )
        return

    # Guard 3: Refuse-clobber (HARD — update-list.sh lines 763–766) — SystemExit
    if new_dir.exists():
        raise SystemExit(
            f"ERROR: A computer named '{new_name}' already exists."
            " Refusing to merge. Nothing renamed."
        )

    # Folder move — archive/ subfolder moves with it (single rename call).
    # Guard against cross-device moves (EXDEV), permission errors, or a race
    # where new_dir was created between the clobber-check above and this
    # rename. A bare Path.rename would abort with a traceback after the user
    # has already committed to the rename interactively, leaving inconsistent
    # state. Exit with an actionable message instead (WR-04).
    try:
        old_dir.rename(new_dir)
    except OSError as exc:
        raise SystemExit(
            f"ERROR: Could not rename folder '{old_name}' to '{new_name}': {exc}."
            " Nothing renamed."
        )
    print(f"  Renamed folder: {old_name}/ -> {new_name}/")

    # Opt-out filename rewrite (update-list.sh lines 773–826)
    # Default is YES (empty input = yes)
    try:
        ans = input(
            f"Rewrite all existing catalogs in '{new_name}' to '[{new_name}]'? [Y/n]: "
        ).strip().lower()
    except EOFError:
        ans = ""  # EOF = accept default (yes)

    rewrite = ans in ("", "y", "yes")

    if rewrite:
        rewrite_dirs = [new_dir, new_dir / "archive"]
        for rewrite_dir in rewrite_dirs:
            if not rewrite_dir.is_dir():
                continue
            for file_path in rewrite_dir.glob("mac-software-list-*.txt"):
                if not file_path.is_file():
                    continue
                cf = parse_catalog_filename(file_path.name)
                if cf is None:
                    print(
                        f"  WARNING: Could not parse timestamp from: {file_path.name} — skipping"
                    )
                    continue
                # Only rewrite files whose label equals old_name exactly
                # (skip mixed-label transition files)
                if cf.machine != old_name:
                    continue
                new_filename = make_catalog_filename(new_name, cf.timestamp)
                dest = rewrite_dir / new_filename
                # Collision guard: never overwrite existing catalog
                if dest.exists():
                    print(f"  WARNING: Destination already exists, skipping: {new_filename}")
                    continue
                file_path.rename(dest)
                print(f"  Renamed: {file_path.name} -> {new_filename}")

    # TSV map update — UNCONDITIONAL (runs regardless of rewrite choice)
    # (update-list.sh lines 833–864)
    map_file = catalog_repo / "machine-labels.tsv"
    if map_file.is_file():
        lines = map_file.read_text(encoding="utf-8").splitlines(keepends=True)
        out: list[str] = []
        for line in lines:
            stripped = line.rstrip("\n")
            if stripped == "":
                out.append("\n")
            elif stripped.startswith("#"):
                out.append(line if line.endswith("\n") else line + "\n")
            elif "\t" in stripped and stripped.split("\t", 1)[1] == old_name:
                # Replace this row's folder column with new_name
                host_col = stripped.split("\t", 1)[0]
                out.append(f"{host_col}\t{new_name}\n")
            else:
                out.append(line if line.endswith("\n") else line + "\n")

        _atomic_write_lines(map_file, out, catalog_repo)
        print(f"  Updated machine-labels.tsv: '{old_name}' -> '{new_name}'")

    # Wire rename git commit [zsh:867-910] — Phase 16
    if auto_commit:
        from maccat import gitops
        gitops.git_commit_rename(catalog_repo, old_name, new_name)

"""Config resolution, XDG path, tomllib loading, and git-repo validation.

Provides the catalog-repo path resolution chain (CFG-01 through CFG-06):
  --catalog-dir flag > MACCAT_CATALOG_DIR env > config.toml > clear error

Config path: ${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml
Constructed directly — does NOT use platformdirs (which returns
~/Library/Application Support on macOS, not the XDG path).

TOML schema: flat key ``catalog_dir = "/abs/path"`` (no [catalog] table).
Written by hand-emitting TOML (tomllib is read-only) with proper escaping.

Zsh analog: update-list.sh has no config file — the catalog was always inferred
from SCRIPT_DIR. The Python tool requires explicit config because the catalog
repo is not co-located with the source.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# XDG config path
# ---------------------------------------------------------------------------


def _default_config_path() -> Path:
    """Return the default config file path, honoring XDG_CONFIG_HOME.

    Constructs: ${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml
    Never uses platformdirs (which returns ~/Library/Application Support on macOS).
    Never uses Path(__file__).parent or os.getcwd().
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    return base / "maccat" / "config.toml"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Resolved configuration values loaded from config.toml.

    catalog_dir is None when the config file is absent or has no catalog_dir key.
    """

    catalog_dir: Path | None = None


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------


def load_config(config_path: Path | None = None) -> Config:
    """Read config.toml and return a Config instance.

    Args:
        config_path: Override the config file path (used in tests). When None,
                     uses _default_config_path().

    Returns:
        Config with catalog_dir populated from the file, or Config() if the
        file is absent.

    Raises:
        tomllib.TOMLDecodeError: If the file exists but contains invalid TOML.
    """
    path = config_path if config_path is not None else _default_config_path()
    if not path.exists():
        return Config()
    with open(path, "rb") as f:  # tomllib requires binary mode
        raw = tomllib.load(f)
    raw_dir = raw.get("catalog_dir")
    if raw_dir:
        return Config(catalog_dir=Path(raw_dir).expanduser())
    return Config()


# ---------------------------------------------------------------------------
# Resolve catalog repo path (CFG-01 precedence chain)
# ---------------------------------------------------------------------------


def resolve_catalog_repo(flag_val: str | None, config: Config) -> Path:
    """Resolve the catalog-repo path using the three-level precedence chain.

    Precedence (CFG-01, locked):
    1. flag_val (--catalog-dir CLI flag): if truthy → expand + resolve.
       NEVER written back to config file (CFG-03).
    2. MACCAT_CATALOG_DIR env var: if truthy → expand + resolve.
    3. config.catalog_dir: if truthy → expand + resolve.
    4. All absent → raise SystemExit with actionable multi-line error.

    Args:
        flag_val: Value of --catalog-dir from the CLI (or None if not passed).
        config:   Loaded Config instance (from load_config).

    Returns:
        Resolved absolute Path to the catalog repo.

    Raises:
        SystemExit: When no source provides a value.
    """
    # Level 1: --catalog-dir flag
    if flag_val:
        return Path(flag_val).expanduser().resolve()

    # Level 2: MACCAT_CATALOG_DIR env var
    env_val = os.environ.get("MACCAT_CATALOG_DIR")
    if env_val:
        return Path(env_val).expanduser().resolve()

    # Level 3: config file
    if config.catalog_dir:
        return config.catalog_dir.expanduser().resolve()

    # Level 4: nothing configured — actionable error
    raise SystemExit(
        "ERROR: No catalog directory configured.\n"
        "Configure it using one of:\n"
        "  1. --catalog-dir /path/to/catalog-repo\n"
        "  2. export MACCAT_CATALOG_DIR=/path/to/catalog-repo\n"
        "  3. Run `maccat config init` to write a persistent config file."
    )


# ---------------------------------------------------------------------------
# Git-repo validation (CFG-06)
# ---------------------------------------------------------------------------


def _is_git_repo(path: Path) -> bool:
    """Return True if ``path`` is itself the top-level of a git repository.

    ``git rev-parse --git-dir`` succeeds anywhere INSIDE a working tree,
    including a parent repo — so a plain subdirectory that merely lives under
    an unrelated git checkout would pass and subsequent commits would land in
    the wrong repository. This tool's core action is auto-commit/push, so we
    require ``path`` to be the repo top-level: ``git rev-parse
    --show-toplevel`` must resolve to ``path`` itself (the zsh tool always
    used SCRIPT_DIR, i.e. the repo root). See WR-06.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    toplevel = result.stdout.strip()
    if not toplevel:
        return False
    try:
        return Path(toplevel).resolve() == path.resolve()
    except OSError:
        return False


def _has_git_remote(path: Path) -> bool:
    """Return True if the repo has at least one remote configured."""
    result = subprocess.run(
        ["git", "remote"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def validate_catalog_repo(catalog_repo: Path) -> None:
    """Fail fast if catalog_repo is missing or not a git repo.

    Warn-and-continue if no remote is configured (CFG-06).

    Args:
        catalog_repo: The resolved catalog repo path to validate.

    Raises:
        SystemExit: When the directory is missing or is not a git repo.
    """
    if not catalog_repo.is_dir():
        raise SystemExit(
            f"ERROR: Catalog directory not found: {catalog_repo}\n"
            "Run `maccat config init` to configure a valid catalog repo."
        )
    if not _is_git_repo(catalog_repo):
        raise SystemExit(
            f"ERROR: {catalog_repo} is not a git repository.\n"
            "Run `maccat config init` to configure a valid catalog repo."
        )
    if not _has_git_remote(catalog_repo):
        print(
            f"  WARNING: No git remote configured in {catalog_repo}."
            " Changes will not be pushed."
        )


# ---------------------------------------------------------------------------
# TOML write helpers
# ---------------------------------------------------------------------------


def _toml_string(s: str) -> str:
    """Escape a string for a TOML basic string value (double-quoted).

    Escapes backslash first (order matters), then double-quote.
    TOML spec: basic strings use \\ for backslash and \" for double-quote.
    """
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def write_config(config_path: Path, catalog_dir: Path) -> None:
    """Atomically write a config.toml with a single catalog_dir entry.

    Creates parent directories if needed. Write is atomic: tempfile + rename.
    A crash leaves at most a .tmp file; config.toml is never partially written.

    Args:
        config_path: Destination path for config.toml.
        catalog_dir: The catalog repo path to write as the catalog_dir value.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"catalog_dir = {_toml_string(str(catalog_dir))}\n"
    fd, tmp = tempfile.mkstemp(dir=config_path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    Path(tmp).rename(config_path)


# ---------------------------------------------------------------------------
# config init  (CFG-04)
# ---------------------------------------------------------------------------


def config_init(config_path: Path | None = None) -> None:
    """Interactive first-run setup: prompt for catalog repo path, validate, write.

    TTY guard: raises SystemExit immediately when stdin is not a TTY.
    EOF (Ctrl-D): prints a newline and raises SystemExit("Aborted.") — never
    loops on closed stdin.

    Validates the entered path:
    - Must be an existing directory.
    - Must be a git repository (git rev-parse --git-dir).
    Re-prompts with an actionable error message on validation failure.

    On success: writes config.toml atomically and prints confirmation.

    Args:
        config_path: Override the config file path (used in tests). When None,
                     uses _default_config_path().
    """
    if not sys.stdin.isatty():
        raise SystemExit("ERROR: `maccat config init` requires an interactive terminal.")

    path = config_path if config_path is not None else _default_config_path()
    print(f"Config file: {path}")

    while True:
        try:
            raw = input("Enter the path to your catalog repository: ")
        except EOFError:
            # Print the prompt-terminating newline separately so the exit
            # value carries only the clean message — keeps presentation out
            # of control flow (WR-05).
            print()
            raise SystemExit("Aborted.")

        catalog_path = Path(raw).expanduser().resolve()

        if not catalog_path.is_dir():
            print(
                f"  ERROR: Directory not found: {catalog_path}\n"
                "  Please enter a valid path to an existing directory."
            )
            continue

        if not _is_git_repo(catalog_path):
            print(
                f"  ERROR: {catalog_path} is not a git repository.\n"
                "  Please enter the path to a git repository."
            )
            continue

        write_config(path, catalog_path)
        print(f"Config written to: {path}")
        break


# ---------------------------------------------------------------------------
# config show  (CFG-04)
# ---------------------------------------------------------------------------


def config_show(
    flag_val: str | None,
    config: Config,
    config_path: Path | None = None,
) -> None:
    """Print the resolved effective config, showing which source won.

    Uses the same precedence logic as resolve_catalog_repo but WITHOUT raising
    on absence — just detects which source (if any) provides a value.

    Output:
      "Catalog repo: {value}   [from: --catalog-dir flag]"  (if flag wins)
      "Catalog repo: {value}   [from: MACCAT_CATALOG_DIR env var]"  (if env wins)
      "Catalog repo: {value}   [from: config file]"  (if config wins)
      "Catalog repo: (not configured)"  (if no source)
      "Config file:  {path}"  (always)
      "  Run `maccat config init` to configure."  (only when not configured)

    Args:
        flag_val:    Value of --catalog-dir from the CLI (or None).
        config:      Loaded Config instance (from load_config).
        config_path: Override the config file path (used in tests). When None,
                     uses _default_config_path().
    """
    path = config_path if config_path is not None else _default_config_path()

    if flag_val:
        value = Path(flag_val).expanduser().resolve()
        print(f"Catalog repo: {value}   [from: --catalog-dir flag]")
    else:
        env_val = os.environ.get("MACCAT_CATALOG_DIR")
        if env_val:
            value_env = Path(env_val).expanduser().resolve()
            print(f"Catalog repo: {value_env}   [from: MACCAT_CATALOG_DIR env var]")
        elif config.catalog_dir:
            value_cfg = config.catalog_dir.expanduser().resolve()
            print(f"Catalog repo: {value_cfg}   [from: config file]")
        else:
            print("Catalog repo: (not configured)")

    print(f"Config file:  {path}")

    if not flag_val and not os.environ.get("MACCAT_CATALOG_DIR") and not config.catalog_dir:
        print("  Run `maccat config init` to configure.")


# ---------------------------------------------------------------------------
# resolve_archive_days  (OPS-08 / zsh analog: resolve_archive_retention)
# ---------------------------------------------------------------------------


def resolve_archive_days(flag_val: int | None, *, default: int = 30) -> int:
    """Resolve the archive retention period in days.

    Zsh analog: update-list.sh lines 511–541 (resolve_archive_retention).

    Precedence:
    1. flag_val (--archive-days): if not None → announce and return.
    2. Non-TTY: print default with note and return (never prompt on non-TTY).
    3. Interactive: prompt with bracketed default; empty OR EOF (Ctrl-D) →
       default; non-empty → validate int >= 1 (raise SystemExit on invalid).

    WR-04: EOF at this prompt keeps the default (zsh parity). The zsh
    `resolve_archive_retention` uses `read -r input`, which on EOF leaves
    `input` empty and falls through to the "empty → keep default" branch
    (update-list.sh:527-531). It does NOT abort the run.

    Args:
        flag_val: Value of --archive-days from the CLI (or None if not passed).
        default:  Default retention days (30, matching ARCHIVE_AGE_DAYS in zsh).

    Returns:
        Retention period in days as a positive integer.

    Raises:
        SystemExit: When user enters a non-integer or a value < 1.
    """
    if flag_val is not None:
        # WR-01 (iter 2): the flag path must enforce the same positive-integer
        # contract as the interactive path and the zsh tool, which rejects any
        # value < 1 at parse time (update-list.sh:230-233). argparse's
        # type=int otherwise lets 0 and negatives through, and a negative value
        # pushes the prune cutoff into the future (retention.py:34), deleting
        # archives that should be kept.
        if flag_val < 1:
            raise SystemExit(
                f"ERROR: Archive retention must be at least 1 day (got {flag_val})."
            )
        print(f"Archive retention: {flag_val} days")
        return flag_val

    if not sys.stdin.isatty():
        print(f"Archive retention: {default} days (non-interactive, using default)")
        return default

    # Interactive prompt
    try:
        raw = input(f"Archive retention period in days [{default}]: ").strip()
    except EOFError:
        # WR-04: EOF (Ctrl-D) keeps the default — matches zsh `read -r` EOF
        # semantics (update-list.sh:527-531), which falls through to "empty →
        # keep default" rather than aborting the run.
        print()
        return default

    if not raw:
        return default

    try:
        days = int(raw)
    except ValueError:
        raise SystemExit(f"ERROR: '{raw}' is not a valid integer.")

    if days < 1:
        raise SystemExit(f"ERROR: Archive retention must be at least 1 day (got {days}).")

    return days

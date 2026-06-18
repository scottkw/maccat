"""CLI entry point — argparse parser and end-to-end run orchestration.

Wires every module built in phases 13-15 and 16-01 into a runnable CLI.

The orchestration order in run() is NON-NEGOTIABLE (mirrors update-list.sh
lines 2443-2505):
  parse args → config → validate repo → (--rename short-circuit) →
  select computer → git_pull → capture timestamp → generate catalog →
  retain_newest_per_host → prune_old_archives → git_commit_and_push

All maccat.* imports are DEFERRED inside function bodies so that importing
this module is always safe at Python interpreter startup (mirrors the lazy
import pattern in collectors/__init__.py and identity.py:627).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the maccat ArgumentParser.

    Flags:
      --version        Print 'maccat <version>' and exit 0 (PKG-05).
      --help           Print usage and exit 0 (PKG-05).
      --catalog-dir    Override catalog repo path (CFG-03: never written back).
      Selecting-flag group (mutually exclusive):
        --computer     Use named folder.
      --rename         Enter rename-machine workflow.
      --archive-days   Override archive retention period in days.
      --no-commit      Skip git commit/push.

    Subcommands:
      config init      Interactive first-run setup.
      config show      Print effective config with source annotation.
      reinstall        Generate reinstall.sh from a catalog.
    """
    from maccat import __version__

    parser = argparse.ArgumentParser(
        prog="maccat",
        description="Mac software catalog generator",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"maccat {__version__}",
    )

    parser.add_argument(
        "--catalog-dir",
        metavar="PATH",
        dest="catalog_dir",
        default=None,
        help="Override catalog repo path (flag value is never written back to config)",
    )

    # Mutually exclusive selecting-flag group (single member; kept for extensibility)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--computer",
        metavar="NAME",
        default=None,
        dest="computer",
        help="Use named computer folder",
    )

    parser.add_argument(
        "--rename",
        action="store_true",
        default=False,
        help="Enter rename-machine workflow (short-circuits catalog generation)",
    )

    parser.add_argument(
        "--archive-days",
        type=int,
        metavar="N",
        dest="archive_days",
        default=None,
        help="Override archive retention period in days",
    )

    parser.add_argument(
        "--no-commit",
        action="store_true",
        default=False,
        dest="no_commit",
        help="Skip git commit and push",
    )

    # Subcommands: config init / config show
    subparsers = parser.add_subparsers(dest="subcommand")
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management subcommands",
    )
    config_sub = config_parser.add_subparsers(dest="config_subcommand")
    config_sub.add_parser("init", help="Interactive first-run setup")
    config_sub.add_parser("show", help="Print effective configuration")

    reinstall_parser = subparsers.add_parser(
        "reinstall",
        help="Generate reinstall.sh from a catalog",
    )
    reinstall_parser.add_argument(
        "--from",
        metavar="PATH",
        dest="from_path",
        default=None,
        help="Explicit catalog file path (skips computer picker)",
    )
    # WR-03: mirror the top-level --computer flag onto the reinstall subparser
    # so the documented post-subcommand placement (`maccat reinstall --computer
    # NAME`) is accepted, not rejected with "unrecognized arguments".
    #
    # Both flags share dest="computer". argparse parses the top-level flag
    # first (it precedes the subcommand token) and the subparser flag second
    # (it follows the subcommand token), each writing into the same namespace
    # attribute in left-to-right order. The subparser flag therefore wins when
    # both are given. CRITICAL: the subparser flag's default MUST be
    # argparse.SUPPRESS — a plain `default=None` would unconditionally clobber
    # a value set by the top-level flag (`maccat --computer NAME reinstall`)
    # back to None during subparser parsing. SUPPRESS makes the subparser leave
    # the attribute untouched unless --computer is actually supplied after the
    # subcommand, giving clean "subparser value wins, else top-level value
    # survives" precedence.
    reinstall_parser.add_argument(
        "--computer",
        metavar="NAME",
        dest="computer",
        default=argparse.SUPPRESS,
        help=(
            "Pre-select a computer folder for the picker "
            "(may also be given before the subcommand: "
            "`maccat --computer NAME reinstall`; the value after the "
            "subcommand takes precedence if both are given)"
        ),
    )

    return parser


def run() -> None:
    """Parse args and execute the end-to-end catalog-generation workflow.

    Orchestration order (NON-NEGOTIABLE, mirrors update-list.sh:2443-2505):

      1. parse args (argparse)
      2. config subcommand dispatch (config init / config show)
      3. --rename × selecting-flag guard
      4a. load_config
      4b. reinstall --from dispatch (early exit — no repo needed)
      4c. resolve_catalog_repo → validate_catalog_repo
      4d. reinstall picker dispatch (after repo validated)
      5. --rename short-circuit: git_pull → rename_machine → return
      6. resolve_computer_selection → select_computer (interactive fallback)
      7. resolve_archive_days
      8. git_pull
      9. CAPTURE timestamp (AFTER git_pull — generate-then-sweep invariant)
      10. make_catalog_filename → mkdir → CatalogWriter → generate sections
      11. retain_newest_per_host
      12. prune_old_archives
      13. git_commit_and_push (unless --no-commit)
    """
    # ------------------------------------------------------------------
    # Deferred imports (all maccat.* modules live here — PKG-03)
    # ------------------------------------------------------------------
    import socket

    from maccat import __version__, gitops
    from maccat.catalog.markdown import render_markdown_catalog
    from maccat.catalog.writer import CatalogWriter
    from maccat.collectors import get_registry
    from maccat.collectors.base import Section
    from maccat.config import (
        config_init,
        config_show,
        load_config,
        resolve_archive_days,
        resolve_catalog_repo,
        validate_catalog_repo,
    )
    from maccat.identity import (
        rename_machine,
        resolve_computer_selection,
        select_computer,
    )
    from maccat.naming import make_catalog_filename
    from maccat.retention import prune_old_archives, retain_newest_per_host

    # ------------------------------------------------------------------
    # 1. Parse args
    # ------------------------------------------------------------------
    parser = _build_parser()
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 2. Config subcommand dispatch
    # ------------------------------------------------------------------
    if args.subcommand == "config":
        # WR-03: reject top-level selecting/rename flags on the config
        # subcommand. argparse parses them under the shared parser, so without
        # this guard the early return below would silently discard them
        # (e.g. `maccat --rename config show` would dump config instead of
        # renaming). Fail loudly so the user's intent is never dropped.
        if any([args.rename, args.computer]):
            sys.exit(
                "ERROR: --rename and --computer cannot be combined with the 'config' subcommand."
            )
        # WR-01: do NOT load_config() before branching. `config init` is the
        # command a user runs to repair a corrupt config — load_config() would
        # raise tomllib.TOMLDecodeError on a malformed file and crash the very
        # command meant to fix it. Only `show` needs a loaded config.
        if args.config_subcommand == "init":
            config_init()
            return
        elif args.config_subcommand == "show":
            config_show(args.catalog_dir, load_config(), None)
            return
        else:
            # bare `maccat config` with no sub-subcommand
            parser.print_help()
            sys.exit(1)

    # ------------------------------------------------------------------
    # 3. --rename × selecting-flag guard (update-list.sh:270-277)
    #    This guard is in cli.py ONLY — identity.py:99-101 excludes it.
    # ------------------------------------------------------------------
    if args.rename and bool(args.computer):
        sys.exit(
            "ERROR: --rename cannot be combined with --computer."
        )

    # ------------------------------------------------------------------
    # 4a. Config load (always safe — returns Config() when absent)
    #     PKG-03: NEVER infer from __file__ or cwd
    # ------------------------------------------------------------------
    cfg = load_config()

    # ------------------------------------------------------------------
    # 4b. Reinstall --from dispatch (early exit — no repo needed)
    #     Must run before resolve_catalog_repo, which raises SystemExit
    #     when no repo is configured. --from mode bypasses the repo entirely.
    # ------------------------------------------------------------------
    if args.subcommand == "reinstall" and args.from_path is not None:
        if args.rename:
            sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
        from maccat.reinstall.cli import run_reinstall
        run_reinstall(args)
        return

    # ------------------------------------------------------------------
    # 4c. Resolve + validate catalog repo (required for ALL remaining paths:
    #     picker-mode reinstall, --rename, and catalog generation)
    # ------------------------------------------------------------------
    catalog_repo: Path = resolve_catalog_repo(args.catalog_dir, cfg)
    validate_catalog_repo(catalog_repo)
    auto_commit = not args.no_commit

    # ------------------------------------------------------------------
    # 4d. Reinstall picker dispatch (after repo validated — picker needs it)
    #     Before --rename short-circuit (step 5).
    # ------------------------------------------------------------------
    if args.subcommand == "reinstall":
        if args.rename:
            sys.exit("ERROR: --rename cannot be combined with the 'reinstall' subcommand.")
        from maccat.reinstall.cli import run_reinstall
        run_reinstall(args, catalog_repo=catalog_repo)
        return

    # ------------------------------------------------------------------
    # 5. --rename short-circuit (update-list.sh:2447-2451)
    #    git_pull → rename_machine → RETURN (before generate/retain/prune)
    # ------------------------------------------------------------------
    if args.rename:
        gitops.git_pull(catalog_repo)
        rename_machine(catalog_repo, auto_commit=auto_commit)
        return

    # ------------------------------------------------------------------
    # 6. Computer selection
    # ------------------------------------------------------------------
    computer_pre = resolve_computer_selection(computer=args.computer)
    computer = select_computer(catalog_repo, computer_name=computer_pre)
    if computer is None:
        # User chose Quit — no catalog written, no git ops
        return

    # ------------------------------------------------------------------
    # 7. Archive retention period
    # ------------------------------------------------------------------
    archive_days = resolve_archive_days(args.archive_days)

    # ------------------------------------------------------------------
    # 8. Git pull (zsh:2465)
    # ------------------------------------------------------------------
    gitops.git_pull(catalog_repo)

    # ------------------------------------------------------------------
    # 9. CAPTURE timestamp AFTER git_pull (generate-then-sweep invariant)
    #    The just-written catalog will always be newer than the cutoff from
    #    retain_newest_per_host, so it survives the sweep. (zsh:2469)
    # ------------------------------------------------------------------
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")

    # ------------------------------------------------------------------
    # 10. Generate catalog (zsh:2471-2490 generate_catalog)
    # ------------------------------------------------------------------
    all_sections: list[Section] = []
    for collector in get_registry():
        result = collector.collect()
        all_sections.extend(result.sections)

    content = render_markdown_catalog(
        all_sections,
        computer=computer,
        hostname=socket.gethostname(),
        generated=generated_iso,
        maccat_version=__version__,
    )

    filename = make_catalog_filename(computer, timestamp)          # zsh:2471
    output_file = catalog_repo / computer / filename               # zsh:2474
    (catalog_repo / computer).mkdir(parents=True, exist_ok=True)  # zsh:2477

    with CatalogWriter(output_file) as w:                         # zsh:2480
        w.write_raw(content)

    # ------------------------------------------------------------------
    # 11. Retention sweep (zsh:2492)
    # ------------------------------------------------------------------
    retain_newest_per_host(catalog_repo / computer)

    # ------------------------------------------------------------------
    # 12. Prune old archives (zsh:2495)
    # ------------------------------------------------------------------
    prune_old_archives(catalog_repo / computer / "archive", archive_days)

    # ------------------------------------------------------------------
    # 13. Git commit/push (zsh:2499)
    # ------------------------------------------------------------------
    if auto_commit:
        gitops.git_commit_and_push(catalog_repo, computer, timestamp)
    else:
        print()
        print("Git auto-commit is disabled (--no-commit flag was used).")
        print("To commit manually, run:")
        print(
            f"  cd {catalog_repo} && git add -A -- \"{computer}/\" && "
            f"git add -- machine-labels.tsv 2>/dev/null; "
            f"git commit -m 'Added catalog' && git push"
        )

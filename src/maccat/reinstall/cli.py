"""Reinstall subcommand orchestrator.

Provides :func:`run_reinstall`, which drives the complete pipeline:
  1. Resolve the catalog file path (``--from PATH`` or interactive picker).
  2. Parse the catalog into a :class:`~maccat.reinstall.parser.ParsedCatalog`.
  3. Render the ``reinstall.sh`` script string via the emitter.
  4. Write the script to ``<cwd>/reinstall.sh`` with mode ``0o644``.
  5. Print the absolute path of the written file to stdout.

All maccat.reinstall.* imports are deferred inside :func:`run_reinstall`'s
body per PKG-03 (lazy import pattern).  No subprocess calls are made — the
script is written to disk and its path is printed; the caller is expected to
review and run it manually.
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path


def run_reinstall(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> None:
    """Generate ``reinstall.sh`` and write it to the current working directory.

    Orchestrates the full reinstall pipeline:

    1. :func:`~maccat.reinstall.picker.resolve_catalog_path` — resolves the
       catalog file from ``--from PATH`` or the interactive computer picker.
       Returns ``None`` when the user quits the picker; in that case this
       function returns cleanly without writing any file.
    2. :func:`~maccat.reinstall.parser.parse_catalog` — parses the catalog.
    3. :func:`~maccat.reinstall.emitter.emit_reinstall_script` — renders the
       script string (starts with ``#!/usr/bin/env bash``, includes provenance
       header with source filename and generation date).
    4. ``Path.cwd() / "reinstall.sh"`` — write path, computed inside this
       function so that ``monkeypatch.chdir`` in tests affects it correctly.
    5. ``os.chmod(output_path, 0o644)`` — explicit mode set; not relying on
       umask (Pitfall 3 in RESEARCH.md).
    6. ``print(str(output_path.resolve()))`` — absolute path for caller use.

    The file is NOT made executable and is NEVER subprocess-run.

    Args:
        args:         Parsed argparse Namespace (must have ``.from_path`` and
                      ``.computer`` attributes).
        catalog_repo: Resolved catalog repo path, or ``None`` when ``--from``
                      is supplied (``--from`` mode is repo-agnostic).
    """
    # Deferred imports per PKG-03
    from maccat.reinstall.emitter import emit_reinstall_script
    from maccat.reinstall.parser import parse_catalog
    from maccat.reinstall.picker import resolve_catalog_path

    catalog_path = resolve_catalog_path(args, catalog_repo=catalog_repo)
    if catalog_path is None:
        # User quit the interactive picker — no file written, exit cleanly
        return

    catalog = parse_catalog(catalog_path)
    script = emit_reinstall_script(
        catalog,
        source_name=catalog_path.name,
        generated=date.today().strftime("%Y-%m-%d"),
    )

    output_path = Path.cwd() / "reinstall.sh"
    output_path.write_text(script, encoding="utf-8")
    os.chmod(output_path, 0o644)
    print(str(output_path.resolve()))

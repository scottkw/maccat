"""Smoke tests for the dist/maccat.pyz zipapp artifact (PKG-03).

These tests verify:
  - The .pyz runs from an unrelated cwd (--version, --help) — PKG-03 cwd-independence
  - The archive contains no .so or .dylib files (pure Python, no C extensions)
  - The catalog repo is never resolved from __file__ inside the .pyz (PKG-03 safety)
  - The maccat package is correctly bundled under maccat/ (not at archive root)

All tests skip cleanly when dist/maccat.pyz has not been built.
Run `bash scripts/build-pyz.sh` to build the artifact.
"""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

# Module-level reference to the built artifact.
# Path is relative to this test file's location (tests/ → repo root → dist/).
PYZ = Path(__file__).parent.parent / "dist" / "maccat.pyz"


def _require_pyz() -> None:
    """Skip the calling test if dist/maccat.pyz has not been built."""
    if not PYZ.exists():
        pytest.skip("dist/maccat.pyz not built; run scripts/build-pyz.sh first")


def test_pyz_version_from_unrelated_cwd(tmp_path: Path) -> None:
    """PKG-03: .pyz --version runs correctly from an unrelated cwd (not the repo root).

    Acceptance: success criterion 1 — cwd-independence.
    """
    _require_pyz()
    result = subprocess.run(
        [sys.executable, str(PYZ), "--version"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--version failed from {tmp_path!r}:\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert "maccat" in result.stdout, (
        f"Expected 'maccat' in stdout, got: {result.stdout!r}"
    )


def test_pyz_help_from_unrelated_cwd(tmp_path: Path) -> None:
    """PKG-05: .pyz --help exits 0 from an unrelated cwd.

    Acceptance: --help works from any directory.
    """
    _require_pyz()
    result = subprocess.run(
        [sys.executable, str(PYZ), "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--help failed from {tmp_path!r}:\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )


def test_pyz_no_so_dylib() -> None:
    """PKG-03: the .pyz archive must contain no .so or .dylib files.

    maccat is pure Python (zero C-extension runtime dependencies).
    Native libs would prevent the .pyz from running on other macOS machines.
    """
    _require_pyz()
    zf = zipfile.ZipFile(str(PYZ))
    names = zf.namelist()
    zf.close()
    bad = [n for n in names if n.endswith(".so") or n.endswith(".dylib")]
    assert bad == [], f"Unexpected native libs in .pyz: {bad}"


def test_pyz_no_file_relative_catalog(tmp_path: Path) -> None:
    """PKG-03: without any config, the .pyz must exit nonzero with 'catalog' in output.

    Inside a .pyz, __file__ resolves to a path INSIDE the zip archive (e.g.
    /path/to/maccat.pyz/maccat/cli.py) — it has no relation to any catalog repo.
    The catalog repo must ONLY come from MACCAT_CATALOG_DIR env, config file, or
    --catalog-dir flag.  A __file__-relative fallback would silently fail or
    produce a misleading error.

    This test isolates the run: HOME → tmp_path (no real ~/.config/maccat/config.toml)
    and strips MACCAT_CATALOG_DIR from the environment.
    """
    _require_pyz()
    # Build a stripped environment: keep only PATH, TERM, HOME.
    # Point HOME to tmp_path so no real ~/.config/maccat/config.toml is found.
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "TERM")}
    env["HOME"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, str(PYZ)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Expected nonzero exit when no catalog config is present, "
        f"but got returncode=0.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    output = (result.stdout + result.stderr).lower()
    assert "catalog" in output, (
        "Expected actionable 'catalog' mention in error output, got:\n"
        f"  stdout: {result.stdout!r}\n"
        f"  stderr: {result.stderr!r}"
    )


def test_pyz_maccat_package_importable_from_pyz() -> None:
    """The maccat package is bundled at maccat/ (not archive root) — import works.

    Acceptance: maccat/ is a top-level subdirectory in the archive, so
    sys.path.insert(0, str(PYZ)) lets Python find maccat/__init__.py correctly.
    """
    _require_pyz()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, {str(PYZ)!r}); "
            "import maccat; print(maccat.__version__)",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Failed to import maccat from .pyz:\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    from maccat import __version__ as expected_version

    assert expected_version in result.stdout, (
        f"Expected '{expected_version}' (maccat.__version__) in stdout, "
        f"got: {result.stdout!r}"
    )

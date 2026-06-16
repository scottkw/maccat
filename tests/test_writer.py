"""Tests for maccat.catalog.writer — CatalogWriter context manager.

Byte-level contract: write_section("Homebrew Packages") must produce exactly
  b"\\nHomebrew Packages\\n" + b"-" * 36 + b"\\n"
Verified against real catalog file hex dump (update-list.sh:1075-1078).
"""
from __future__ import annotations

from pathlib import Path

from maccat.catalog.writer import CatalogWriter


class TestWriteSectionBytes:
    def test_write_section_bytes_exact(self, tmp_path: Path) -> None:
        """Byte-level parity: write_section matches update-list.sh write_section() bytes."""
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Homebrew Packages")

        file_bytes = output.read_bytes()
        expected = b"\nHomebrew Packages\n" + b"-" * 36 + b"\n"
        assert file_bytes == expected, (
            f"Byte mismatch!\n"
            f"  Expected: {expected!r}\n"
            f"  Got:      {file_bytes!r}"
        )

    def test_write_section_36_dashes(self, tmp_path: Path) -> None:
        """Separator must be exactly 36 dashes — not 34, not 40."""
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Test Section")

        content = output.read_text(encoding="utf-8")
        lines = content.split("\n")
        # Find the dash separator line (third token: \n, title, dashes, ...)
        dash_line = [ln for ln in lines if ln.startswith("-")][0]
        assert len(dash_line) == 36, f"Expected 36 dashes, got {len(dash_line)}: {dash_line!r}"
        assert dash_line == "-" * 36


class TestSectionBoundary:
    def test_single_blank_line_between_sections(self, tmp_path: Path) -> None:
        """After write_section + write_lines + write_section: exactly ONE blank line between.

        File pattern must be: ...item1\\n\\nSection B\\n...
        NOT:                  ...item1\\n\\n\\nSection B\\n...
        """
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Section A")
            w.write_lines(["item1", "item2"])
            w.write_section("Section B")
            w.write_lines(["item3"])

        content = output.read_text(encoding="utf-8")

        # No double blank lines anywhere
        assert "\n\n\n" not in content, (
            f"Double blank line found in output:\n{content!r}"
        )

        # Exactly one blank line between last item of Section A and Section B title
        assert "item2\n\nSection B\n" in content, (
            f"Expected 'item2\\n\\nSection B\\n' in output:\n{content!r}"
        )

    def test_write_lines_single_newline_per_line(self, tmp_path: Path) -> None:
        """write_lines must write exactly one \\n per line — no extra newlines."""
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Section")
            w.write_lines(["  (none found)"])

        content = output.read_text(encoding="utf-8")
        # The "  (none found)" line must be followed by exactly one newline
        assert "  (none found)\n" in content
        # Must NOT be followed by two newlines (unless a new section follows)
        assert "  (none found)\n\n" not in content


class TestAtomicWrite:
    def test_atomic_write_on_exception(self, tmp_path: Path) -> None:
        """On exception in context, final path must NOT exist (partial write not committed)."""
        output = tmp_path / "catalog.txt"
        try:
            with CatalogWriter(output) as w:
                w.write_section("Partial Section")
                raise RuntimeError("simulated crash")
        except RuntimeError:
            pass

        assert not output.exists(), (
            f"Output file should NOT exist after exception, but it does: {output}"
        )

    def test_atomic_write_success(self, tmp_path: Path) -> None:
        """On clean exit, final path must exist and be non-empty."""
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Complete Section")
            w.write_lines(["item1"])

        assert output.exists(), "Output file should exist after clean exit"
        assert output.stat().st_size > 0, "Output file should be non-empty"

    def test_atomic_write_tmp_file_gone_after_success(self, tmp_path: Path) -> None:
        """After clean exit, no .maccat-*.tmp file should remain in the directory."""
        output = tmp_path / "catalog.txt"
        with CatalogWriter(output) as w:
            w.write_section("Section")

        tmp_files = list(tmp_path.glob(".maccat-*.tmp"))
        assert tmp_files == [], f"Tmp file not cleaned up: {tmp_files}"

    def test_atomic_write_tmp_file_gone_after_exception(self, tmp_path: Path) -> None:
        """After exception, no .maccat-*.tmp file should remain (must be unlinked)."""
        output = tmp_path / "catalog.txt"
        try:
            with CatalogWriter(output) as w:
                w.write_section("Partial")
                raise ValueError("crash")
        except ValueError:
            pass

        tmp_files = list(tmp_path.glob(".maccat-*.tmp"))
        assert tmp_files == [], f"Tmp file not cleaned up after exception: {tmp_files}"

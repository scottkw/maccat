"""Atomic catalog file writer — CatalogWriter context manager.

Byte-exact equivalent of the OUTPUT_FILE append pattern in update-list.sh.
write_section() matches update-list.sh:1075-1078 byte-for-byte:
  echo "\\n$1" → \\n + title + \\n
  echo "----..." → 36 × 0x2d + \\n

Atomic write: uses tempfile.mkstemp + rename so no partial catalog is ever
committed to git (crash mid-write leaves no trace at the final path).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import IO


class CatalogWriter:
    """Context manager that writes a catalog file atomically (tmp + rename).

    Usage::

        with CatalogWriter(Path("personal/catalog-2026.txt")) as w:
            w.write_section("Homebrew Packages")
            w.write_lines(flush_section(items))

    On clean exit: tmp file is renamed to the final path (atomic on POSIX/macOS).
    On exception: tmp file is deleted; final path is never created.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fh: IO[str] | None = None  # set in __enter__
        self._tmp_path: Path | None = None

    def __enter__(self) -> CatalogWriter:
        fd, tmp = tempfile.mkstemp(
            dir=self._path.parent, prefix=".maccat-", suffix=".tmp"
        )
        self._tmp_path = Path(tmp)
        self._fh = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._fh:
            self._fh.close()
        if exc_type is None and self._tmp_path is not None:
            self._tmp_path.rename(self._path)
        elif self._tmp_path is not None and self._tmp_path.exists():
            self._tmp_path.unlink()

    def write_section(self, title: str) -> None:
        """Byte-exact equivalent of update-list.sh write_section().

        Emits: \\n + title + \\n + ("-" * 36) + \\n
        The leading \\n produces the blank line between sections.
        Separator is EXACTLY 36 ASCII dashes (0x2d × 36) — verified by hex dump.
        """
        assert self._fh is not None, "write_section called outside context manager"
        self._fh.write(f"\n{title}\n")
        self._fh.write("-" * 36 + "\n")

    def write_lines(self, lines: list[str]) -> None:
        """Append sorted lines (from flush_section) — each line gets exactly one trailing \\n.

        No extra newlines are added beyond the per-line \\n. The blank line between
        sections is provided by write_section's leading \\n, not by this method.
        """
        assert self._fh is not None, "write_lines called outside context manager"
        for line in lines:
            self._fh.write(line + "\n")

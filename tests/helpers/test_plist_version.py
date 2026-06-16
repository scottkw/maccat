"""Tests for maccat.helpers.plist_version.get_plist_version.

Covers: VER-03 / VER-04 behavior cases — plist key precedence, graceful
degradation for missing/empty/corrupt/binary files.
"""
from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from maccat.helpers.plist_version import get_plist_version


class TestPlistVersion:
    def test_returns_bundle_short_version(self, tmp_path: Path) -> None:
        """XML plist with CFBundleShortVersionString returns that value."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {"CFBundleShortVersionString": "3.8.4"},
                fmt=plistlib.FMT_XML,
            )
        )
        assert get_plist_version(plist_file) == "3.8.4"

    def test_falls_back_to_bundle_version(self, tmp_path: Path) -> None:
        """XML plist with only CFBundleVersion returns that value."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {"CFBundleVersion": "42"},
                fmt=plistlib.FMT_XML,
            )
        )
        assert get_plist_version(plist_file) == "42"

    def test_returns_empty_when_neither_key(self, tmp_path: Path) -> None:
        """XML plist with neither version key returns empty string."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {"CFBundleIdentifier": "com.example.app"},
                fmt=plistlib.FMT_XML,
            )
        )
        assert get_plist_version(plist_file) == ""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent path returns empty string."""
        absent = tmp_path / "NoSuchFile.plist"
        assert get_plist_version(absent) == ""

    def test_zero_byte_file_returns_empty(self, tmp_path: Path) -> None:
        """Zero-byte file returns empty string (not a valid plist)."""
        empty_file = tmp_path / "Empty.plist"
        empty_file.write_bytes(b"")
        assert get_plist_version(empty_file) == ""

    def test_binary_plist_returns_version(self, tmp_path: Path) -> None:
        """Binary plist with CFBundleShortVersionString returns version string."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {"CFBundleShortVersionString": "1.2.3"},
                fmt=plistlib.FMT_BINARY,
            )
        )
        assert get_plist_version(plist_file) == "1.2.3"

    def test_corrupt_data_returns_empty(self, tmp_path: Path) -> None:
        """Corrupt/non-plist data returns empty string without raising."""
        corrupt = tmp_path / "Corrupt.plist"
        corrupt.write_bytes(b"not a plist at all\x00\xff")
        assert get_plist_version(corrupt) == ""

    def test_determinism(self, tmp_path: Path) -> None:
        """Two calls with the same path return identical results."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {"CFBundleShortVersionString": "2.0.0"},
                fmt=plistlib.FMT_XML,
            )
        )
        first = get_plist_version(plist_file)
        second = get_plist_version(plist_file)
        assert first == second == "2.0.0"

    def test_short_version_takes_precedence_over_bundle_version(
        self, tmp_path: Path
    ) -> None:
        """When both keys exist, CFBundleShortVersionString wins."""
        plist_file = tmp_path / "Info.plist"
        plist_file.write_bytes(
            plistlib.dumps(
                {
                    "CFBundleShortVersionString": "3.0.0",
                    "CFBundleVersion": "300",
                },
                fmt=plistlib.FMT_XML,
            )
        )
        assert get_plist_version(plist_file) == "3.0.0"

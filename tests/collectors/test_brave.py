"""Tests for maccat.collectors.brave."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

import maccat.collectors.brave as brave_mod
from maccat.collectors.brave import BRAVE_COMPONENT_DENYLIST, BraveCollector
from maccat.collectors.chromium import COMPONENT_DENYLIST

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_ext(profile_ext_dir: Path, ext_id: str, version: str, name: str) -> None:
    """Build a synthetic Chromium extension directory with a minimal manifest.json."""
    ver_dir = profile_ext_dir / ext_id / version
    ver_dir.mkdir(parents=True)
    (ver_dir / "manifest.json").write_text(
        json.dumps({"name": name, "version": version}),
        encoding="utf-8",
    )


# ===========================================================================
# TestBraveCollect — basic collection
# ===========================================================================


class TestBraveCollect:
    def test_collects_default_profile(self, tmp_path: Path) -> None:
        """Extension in Default/Extensions is collected."""
        base = tmp_path / "Brave"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "abcdefghijklmnopabcdefghijklmnop", "1.0.0_0", "My Brave Ext")
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert len(result.sections) == 1
        assert any("My Brave Ext" in item for item in result.sections[0].items)

    def test_collects_multiple_profiles(self, tmp_path: Path) -> None:
        """Items from Default and Profile 1 are accumulated."""
        base = tmp_path / "Brave"
        default_ext = base / "Default" / "Extensions"
        default_ext.mkdir(parents=True)
        _make_ext(default_ext, "aaaabbbbccccddddaaaabbbbccccdddd", "1.0.0_0", "Default Brave Ext")
        profile1_ext = base / "Profile 1" / "Extensions"
        profile1_ext.mkdir(parents=True)
        _make_ext(profile1_ext, "eeeeffff0000111122223333444455556666", "2.0.0_0", "Profile1 Brave Ext")
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        all_items = result.sections[0].items
        assert any("Default Brave Ext" in item for item in all_items)
        assert any("Profile1 Brave Ext" in item for item in all_items)

    def test_brave_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Brave Browser Extensions'."""
        base = tmp_path / "Brave"
        base.mkdir()
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert result.sections[0].title == "Brave Browser Extensions"

    def test_brave_raw_is_false(self, tmp_path: Path) -> None:
        """Section.raw is False — flush_section by Phase 16 orchestrator."""
        base = tmp_path / "Brave"
        base.mkdir()
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert result.sections[0].raw is False


# ===========================================================================
# TestBraveExclusions — denylist, Temp, underscore
# ===========================================================================


class TestBraveExclusions:
    def test_skips_component_extension(self, tmp_path: Path) -> None:
        """Extensions in BRAVE_COMPONENT_DENYLIST are excluded."""
        base = tmp_path / "Brave"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        denied_id = next(iter(BRAVE_COMPONENT_DENYLIST))
        _make_ext(ext_dir, denied_id, "1.0.0_0", "Component Ext")
        _make_ext(ext_dir, "aaaabbbbccccddddaaaabbbbccccdddd", "1.0.0_0", "Real Brave Ext")
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        items = result.sections[0].items
        assert not any("Component Ext" in item for item in items)
        assert any("Real Brave Ext" in item for item in items)

    def test_skips_temp_directory(self, tmp_path: Path) -> None:
        """A directory named 'Temp' is excluded from collection."""
        base = tmp_path / "Brave"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "Temp", "1.0.0_0", "Temp Ext")
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert not any("Temp Ext" in item for item in result.sections[0].items)

    def test_skips_underscore_directory(self, tmp_path: Path) -> None:
        """Directories starting with '_' (e.g. _metadata) are excluded."""
        base = tmp_path / "Brave"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "_metadata", "1.0.0_0", "Meta Ext")
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert not any("Meta Ext" in item for item in result.sections[0].items)

    def test_version_sort_tail_used(self, tmp_path: Path) -> None:
        """Collector selects highest version directory via version_sort_tail (sort -V)."""
        base = tmp_path / "Brave"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        ext_id = "aaaabbbbccccddddaaaabbbbccccdddd"
        low_ver = ext_dir / ext_id / "1.0.0_0"
        low_ver.mkdir(parents=True)
        (low_ver / "manifest.json").write_text(
            json.dumps({"name": "Old Brave Version", "version": "1.0.0"}),
            encoding="utf-8",
        )
        high_ver = ext_dir / ext_id / "2.0.0_0"
        high_ver.mkdir(parents=True)
        (high_ver / "manifest.json").write_text(
            json.dumps({"name": "New Brave Version", "version": "2.0.0"}),
            encoding="utf-8",
        )
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        items = result.sections[0].items
        assert any("New Brave Version" in item for item in items), (
            "version_sort_tail must select the highest version dir"
        )
        assert not any("Old Brave Version" in item for item in items)


# ===========================================================================
# TestBraveDegradation — CAT-06: absent Brave dir
# ===========================================================================


class TestBraveDegradation:
    def test_brave_not_installed(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """When _BASE does not exist, NOTE is printed to stderr and items is []."""
        missing_base = tmp_path / "NoBrave"
        with patch.object(BraveCollector, "_base", new=missing_base):
            result = BraveCollector().collect()
        assert result.sections[0].items == []
        captured = capsys.readouterr()
        assert "NOTE" in captured.err
        assert "Brave Browser" in captured.err

    def test_profile_iterdir_oserror_degrades(self, tmp_path: Path) -> None:
        """If a profile's Extensions dir iterdir() raises OSError, degrade to [] not raise."""
        ext_root = tmp_path / "Extensions"
        ext_root.mkdir()
        collector = BraveCollector()
        with patch.object(Path, "iterdir", side_effect=OSError("boom")):
            items = collector._collect_profile(ext_root)  # must not raise
        assert items == []

    def test_ext_dir_iterdir_oserror_skips_that_ext(self, tmp_path: Path) -> None:
        """If one extension dir iterdir() raises mid-scan, that ext is skipped, run continues."""
        ext_root = tmp_path / "Extensions"
        good_id = "abcdefghijklmnopabcdefghijklmnop"
        _make_ext(ext_root, good_id, "1.0.0_0", "Good Ext")
        bad_dir = ext_root / "bbbbccccddddeeeebbbbccccddddeeee"
        bad_dir.mkdir(parents=True)

        real_iterdir = Path.iterdir

        def flaky_iterdir(self: Path):  # type: ignore[no-untyped-def]
            if self == bad_dir:
                raise OSError("vanished mid-scan")
            return real_iterdir(self)

        collector = BraveCollector()
        with patch.object(Path, "iterdir", flaky_iterdir):
            items = collector._collect_profile(ext_root)  # must not raise
        assert any("Good Ext" in item for item in items)


# ===========================================================================
# TestBraveNativeMessagingOnly — presence-detection rule
# ===========================================================================


class TestBraveNativeMessagingOnly:
    def test_base_dir_without_profiles_returns_empty_silently(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Base dir exists with only NativeMessagingHosts/ — items=[], no NOTE in stderr.

        Documents the profile-enumeration presence-detection rule: the NOTE fires only
        when base dir does not exist at all, not when it exists but has no profile-level
        Extensions dirs.
        """
        base = tmp_path / "Brave"
        (base / "NativeMessagingHosts").mkdir(parents=True)
        with patch.object(BraveCollector, "_base", new=base):
            result = BraveCollector().collect()
        assert result.sections[0].items == []
        captured = capsys.readouterr()
        assert "NOTE" not in captured.err


# ===========================================================================
# Module-level constant checks
# ===========================================================================


def test_brave_module_title_constant() -> None:
    """brave_mod._TITLE is the correct string constant."""
    assert brave_mod._TITLE == "Brave Browser Extensions"


def test_brave_component_denylist_count() -> None:
    """BRAVE_COMPONENT_DENYLIST has exactly 20 IDs."""
    assert len(BRAVE_COMPONENT_DENYLIST) == 20


def test_brave_component_denylist_is_frozenset() -> None:
    """BRAVE_COMPONENT_DENYLIST is a frozenset."""
    assert isinstance(BRAVE_COMPONENT_DENYLIST, frozenset)


def test_brave_denylist_is_superset_of_component_denylist() -> None:
    """BraveCollector._denylist includes all COMPONENT_DENYLIST IDs."""
    assert COMPONENT_DENYLIST <= BraveCollector._denylist

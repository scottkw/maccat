"""Tests for maccat.collectors.chrome.

Behavioral spec: update-list.sh lines 2074–2137 (collect_chrome_extensions).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

import maccat.collectors.chrome as chrome_mod
from maccat.collectors.chrome import COMPONENT_DENYLIST, ChromeCollector

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_ext(profile_ext_dir: Path, ext_id: str, version: str, name: str) -> None:
    """Build a synthetic Chrome extension directory with a minimal manifest.json."""
    ver_dir = profile_ext_dir / ext_id / version
    ver_dir.mkdir(parents=True)
    (ver_dir / "manifest.json").write_text(
        json.dumps({"name": name, "version": version}),
        encoding="utf-8",
    )


# ===========================================================================
# ChromeCollect — basic collection
# ===========================================================================


class TestChromeCollect:
    def test_collects_default_profile(self, tmp_path: Path) -> None:
        """Extension in Default/Extensions is collected."""
        base = tmp_path / "Chrome"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "abcdefghijklmnopabcdefghijklmnop", "1.0.0_0", "My Extension")
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        assert len(result.sections) == 1
        assert any("My Extension" in item for item in result.sections[0].items)

    def test_collects_multiple_profiles(self, tmp_path: Path) -> None:
        """Items from Default and Profile 1 are accumulated."""
        base = tmp_path / "Chrome"
        default_ext = base / "Default" / "Extensions"
        default_ext.mkdir(parents=True)
        _make_ext(default_ext, "aaaabbbbccccddddaaaabbbbccccdddd", "1.0.0_0", "Default Ext")
        profile1_ext = base / "Profile 1" / "Extensions"
        profile1_ext.mkdir(parents=True)
        _make_ext(profile1_ext, "eeeeffff0000111122223333444455556666", "2.0.0_0", "Profile1 Ext")
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        all_items = result.sections[0].items
        assert any("Default Ext" in item for item in all_items)
        assert any("Profile1 Ext" in item for item in all_items)

    def test_chrome_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Google Chrome Extensions'."""
        base = tmp_path / "Chrome"
        base.mkdir()
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        assert result.sections[0].title == "Google Chrome Extensions"

    def test_chrome_raw_is_false(self, tmp_path: Path) -> None:
        """Section.raw is False — flush_section by Phase 16 orchestrator."""
        base = tmp_path / "Chrome"
        base.mkdir()
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        assert result.sections[0].raw is False


# ===========================================================================
# ChromeExclusions — denylist, Temp, underscore
# ===========================================================================


class TestChromeExclusions:
    def test_skips_component_extension(self, tmp_path: Path) -> None:
        """Extensions in COMPONENT_DENYLIST are excluded."""
        base = tmp_path / "Chrome"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        # Pick one ID from the denylist
        denied_id = next(iter(COMPONENT_DENYLIST))
        _make_ext(ext_dir, denied_id, "1.0.0_0", "Component Ext")
        # Also add a non-denied extension to prove the profile is visited
        _make_ext(ext_dir, "aaaabbbbccccddddaaaabbbbccccdddd", "1.0.0_0", "Real Ext")
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        items = result.sections[0].items
        assert not any("Component Ext" in item for item in items)
        assert any("Real Ext" in item for item in items)

    def test_skips_temp_directory(self, tmp_path: Path) -> None:
        """A directory named 'Temp' is excluded from collection."""
        base = tmp_path / "Chrome"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "Temp", "1.0.0_0", "Temp Ext")
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        assert not any("Temp Ext" in item for item in result.sections[0].items)

    def test_skips_underscore_directory(self, tmp_path: Path) -> None:
        """Directories starting with '_' (e.g. _metadata) are excluded."""
        base = tmp_path / "Chrome"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        _make_ext(ext_dir, "_metadata", "1.0.0_0", "Meta Ext")
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        assert not any("Meta Ext" in item for item in result.sections[0].items)

    def test_version_sort_tail_used(self, tmp_path: Path) -> None:
        """Collector selects highest version directory via version_sort_tail (sort -V)."""
        base = tmp_path / "Chrome"
        ext_dir = base / "Default" / "Extensions"
        ext_dir.mkdir(parents=True)
        ext_id = "aaaabbbbccccddddaaaabbbbccccdddd"
        # Create two version directories — the higher one has the name we verify
        low_ver = ext_dir / ext_id / "1.0.0_0"
        low_ver.mkdir(parents=True)
        (low_ver / "manifest.json").write_text(
            json.dumps({"name": "Old Version", "version": "1.0.0"}),
            encoding="utf-8",
        )
        high_ver = ext_dir / ext_id / "2.0.0_0"
        high_ver.mkdir(parents=True)
        (high_ver / "manifest.json").write_text(
            json.dumps({"name": "New Version", "version": "2.0.0"}),
            encoding="utf-8",
        )
        with patch.object(chrome_mod, "_BASE", base):
            result = ChromeCollector().collect()
        items = result.sections[0].items
        # Must pick the higher version (2.0.0_0), not the lower (1.0.0_0)
        assert any("New Version" in item for item in items), (
            "version_sort_tail must select the highest version dir"
        )
        assert not any("Old Version" in item for item in items)


# ===========================================================================
# ChromeDegradation — CAT-06: absent Chrome dir
# ===========================================================================


class TestChromeDegradation:
    def test_chrome_not_installed(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """When _BASE does not exist, NOTE is printed to stderr and items is []."""
        missing_base = tmp_path / "NoChrome"
        with patch.object(chrome_mod, "_BASE", missing_base):
            result = ChromeCollector().collect()
        assert result.sections[0].items == []
        captured = capsys.readouterr()
        assert "NOTE" in captured.err
        assert "Google Chrome" in captured.err

    # --- CAT-06 shape-guard regressions (WR-07) ---

    def test_profile_iterdir_oserror_degrades(self, tmp_path: Path) -> None:
        """If a profile's Extensions dir iterdir() raises OSError, degrade to [] not raise."""
        ext_root = tmp_path / "Extensions"
        ext_root.mkdir()
        collector = ChromeCollector()
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

        collector = ChromeCollector()
        with patch.object(Path, "iterdir", flaky_iterdir):
            items = collector._collect_profile(ext_root)  # must not raise
        assert any("Good Ext" in item for item in items)

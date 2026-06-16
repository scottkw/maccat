"""Tests for maccat.collectors.setapp and maccat.collectors.webapps.

Behavioral spec: update-list.sh lines 2267-2284.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from maccat.collectors.setapp import SetappCollector
from maccat.collectors.webapps import WebAppsCollector

# ---------------------------------------------------------------------------
# SetappCollector
# ---------------------------------------------------------------------------


class TestSetappCollector:
    def test_setapp_includes_setapp_root_itself(self, tmp_path: Path) -> None:
        """Pitfall C: find includes start path — 'Setapp' must appear in items."""
        base = tmp_path / "Setapp"
        base.mkdir()
        (base / "MyApp.app").mkdir()
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "Setapp" in items, f"'Setapp' root entry missing from items: {items}"
        assert "MyApp.app" in items

    def test_setapp_sorted_output(self, tmp_path: Path) -> None:
        """Multiple subdirs are returned in sorted order, including the root entry."""
        base = tmp_path / "Setapp"
        base.mkdir()
        (base / "Zorro.app").mkdir()
        (base / "Alfred.app").mkdir()
        (base / "Bartender.app").mkdir()
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert items == sorted(items), f"Items not sorted: {items}"
        assert items == ["Alfred.app", "Bartender.app", "Setapp", "Zorro.app"]

    def test_setapp_absent_returns_fallback(self, tmp_path: Path) -> None:
        """BASE does not exist — items == fallback message, raw is True (CAT-06)."""
        absent = tmp_path / "Setapp"  # not created
        with patch.object(SetappCollector, "BASE", absent):
            result = SetappCollector().collect()
        section = result.sections[0]
        assert section.items == ["Setapp is not installed or detected."]
        assert section.raw is True

    def test_setapp_raw_is_true(self, tmp_path: Path) -> None:
        """Any collect() call returns section with raw=True."""
        base = tmp_path / "Setapp"
        base.mkdir()
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        assert result.sections[0].raw is True

    def test_setapp_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Setapp Applications'."""
        base = tmp_path / "Setapp"
        base.mkdir()
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        assert result.sections[0].title == "Setapp Applications"

    def test_setapp_only_includes_directories(self, tmp_path: Path) -> None:
        """Non-directory entries (files) inside BASE are excluded."""
        base = tmp_path / "Setapp"
        base.mkdir()
        (base / "App.app").mkdir()
        (base / "readme.txt").write_text("ignored", encoding="utf-8")
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "readme.txt" not in items
        assert "App.app" in items


# ---------------------------------------------------------------------------
# WebAppsCollector
# ---------------------------------------------------------------------------


class TestWebAppsCollector:
    def test_webapps_includes_applications_root_itself(self, tmp_path: Path) -> None:
        """Pitfall C: find includes start path — 'Applications' must appear in items."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "Firefox.app").mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Applications" in items, f"'Applications' root missing from items: {items}"
        assert "Firefox.app" in items

    def test_webapps_excludes_setapp_dir(self, tmp_path: Path) -> None:
        """Dirs matching 'Setapp*' are excluded from items."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "Setapp").mkdir()
        (base / "SetappExtra").mkdir()
        (base / "Firefox.app").mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Setapp" not in items
        assert "SetappExtra" not in items
        assert "Firefox.app" in items

    def test_webapps_excludes_app_store_dirs(self, tmp_path: Path) -> None:
        """Dirs matching '*App Store*' are excluded from items."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "App Store.app").mkdir()
        (base / "Firefox.app").mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "App Store.app" not in items
        assert "Firefox.app" in items

    def test_webapps_sorted_output(self, tmp_path: Path) -> None:
        """Items are in sorted order (Applications root falls into sorted position)."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "Zoom.app").mkdir()
        (base / "1Password.app").mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert items == sorted(items), f"Items not sorted: {items}"

    def test_webapps_raw_is_true(self, tmp_path: Path) -> None:
        """section.raw is True."""
        base = tmp_path / "Applications"
        base.mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        assert result.sections[0].raw is True

    def test_webapps_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Web-installed Applications'."""
        base = tmp_path / "Applications"
        base.mkdir()
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        assert result.sections[0].title == "Web-installed Applications"

    def test_webapps_only_includes_directories(self, tmp_path: Path) -> None:
        """Non-directory entries (files) are excluded (only dirs match -type d in find)."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "App.app").mkdir()
        (base / "readme.txt").write_text("ignored", encoding="utf-8")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "readme.txt" not in items
        assert "App.app" in items

    def test_webapps_always_available(self) -> None:
        """WebAppsCollector.available() always returns True (no guard in zsh)."""
        assert WebAppsCollector().available() is True

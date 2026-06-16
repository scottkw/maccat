"""Tests for maccat.collectors.setapp and maccat.collectors.webapps.

Behavioral spec: VER-03 (Setapp versioned), VER-04 (WebApps versioned),
VER-05 (graceful degradation), VER-06 (determinism / ordering preserved).
"""
from __future__ import annotations

import plistlib
from pathlib import Path
from unittest.mock import patch

from maccat.collectors.setapp import SetappCollector
from maccat.collectors.webapps import WebAppsCollector

# ---------------------------------------------------------------------------
# Shared plist fixture helper
# ---------------------------------------------------------------------------


def _write_plist(
    app_dir: Path,
    short_ver: str | None = None,
    bundle_ver: str | None = None,
) -> None:
    """Write a minimal XML Info.plist into app_dir/Contents/.

    Only the keys whose values are not None are written.
    """
    contents_dir = app_dir / "Contents"
    contents_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    if short_ver is not None:
        data["CFBundleShortVersionString"] = short_ver
    if bundle_ver is not None:
        data["CFBundleVersion"] = bundle_ver
    plist_bytes = plistlib.dumps(data, fmt=plistlib.FMT_XML)
    (contents_dir / "Info.plist").write_bytes(plist_bytes)


# ---------------------------------------------------------------------------
# SetappCollector
# ---------------------------------------------------------------------------


class TestSetappCollector:
    def test_setapp_includes_setapp_root_itself(self, tmp_path: Path) -> None:
        """Pitfall C: find includes start path — 'Setapp' must appear in items."""
        base = tmp_path / "Setapp"
        base.mkdir()
        app_dir = base / "MyApp.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="1.0")
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "Setapp" in items, f"'Setapp' root entry missing from items: {items}"
        assert "MyApp.app (1.0)" in items

    def test_setapp_sorted_output(self, tmp_path: Path) -> None:
        """Multiple subdirs are returned in sorted order, including the root entry."""
        base = tmp_path / "Setapp"
        base.mkdir()
        for name, ver in [("Zorro.app", "2.0"), ("Alfred.app", "1.5"), ("Bartender.app", "4.2")]:
            app_dir = base / name
            app_dir.mkdir()
            _write_plist(app_dir, short_ver=ver)
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert items == sorted(items), f"Items not sorted: {items}"
        # Versioned items should appear in sorted order
        assert "Alfred.app (1.5)" in items
        assert "Bartender.app (4.2)" in items
        assert "Zorro.app (2.0)" in items

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
        app_dir = base / "App.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="3.0")
        (base / "readme.txt").write_text("ignored", encoding="utf-8")
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "readme.txt" not in items
        assert "App.app (3.0)" in items


# ---------------------------------------------------------------------------
# SetappCollector — versioning and degradation
# ---------------------------------------------------------------------------


class TestSetappVersioning:
    def test_app_with_short_version(self, tmp_path: Path) -> None:
        """App with CFBundleShortVersionString emits 'AppName.app (version)'."""
        base = tmp_path / "Setapp"
        base.mkdir()
        app_dir = base / "Bear.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="3.8.4")
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "Bear.app (3.8.4)" in items

    def test_app_with_bundle_version_fallback(self, tmp_path: Path) -> None:
        """App with only CFBundleVersion emits 'AppName.app (bundleversion)'."""
        base = tmp_path / "Setapp"
        base.mkdir()
        app_dir = base / "OldApp.app"
        app_dir.mkdir()
        _write_plist(app_dir, bundle_ver="42")
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "OldApp.app (42)" in items

    def test_app_missing_plist_degrades(self, tmp_path: Path) -> None:
        """App dir with no Contents/Info.plist emits bare name without error."""
        base = tmp_path / "Setapp"
        base.mkdir()
        (base / "Ghostly.app").mkdir()  # no plist written
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "Ghostly.app" in items
        # Should not have version parens
        assert not any("Ghostly.app (" in item for item in items)

    def test_container_entry_name_only(self, tmp_path: Path) -> None:
        """'Setapp' root entry is always name-only (no plist lookup on container dir)."""
        base = tmp_path / "Setapp"
        base.mkdir()
        # Even if someone created a Contents/Info.plist inside the base dir itself,
        # the root entry is prepended as BASE.name — no _versioned_entry call
        contents = base / "Contents"
        contents.mkdir()
        (contents / "Info.plist").write_bytes(
            plistlib.dumps({"CFBundleShortVersionString": "99.0"}, fmt=plistlib.FMT_XML)
        )
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "Setapp" in items
        assert "Setapp (99.0)" not in items

    def test_determinism(self, tmp_path: Path) -> None:
        """Two consecutive collect() calls on the same fixture return identical items."""
        base = tmp_path / "Setapp"
        base.mkdir()
        for name, ver in [("Craft.app", "1.2"), ("Tot.app", "4.0")]:
            app_dir = base / name
            app_dir.mkdir()
            _write_plist(app_dir, short_ver=ver)
        with patch.object(SetappCollector, "BASE", base):
            collector = SetappCollector()
            items_1 = collector.collect().sections[0].items
            items_2 = collector.collect().sections[0].items
        assert items_1 == items_2, f"Non-deterministic: {items_1!r} != {items_2!r}"

    def test_zero_byte_plist_degrades(self, tmp_path: Path) -> None:
        """App dir with a zero-byte Info.plist emits bare name without error."""
        base = tmp_path / "Setapp"
        base.mkdir()
        app_dir = base / "ZeroApp.app"
        app_dir.mkdir()
        contents = app_dir / "Contents"
        contents.mkdir()
        (contents / "Info.plist").write_bytes(b"")  # zero-byte
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert "ZeroApp.app" in items
        assert not any("ZeroApp.app (" in item for item in items)

    def test_sort_order_after_annotation(self, tmp_path: Path) -> None:
        """Sort is applied AFTER version annotation so sort key reflects 'Name (ver)' strings."""
        base = tmp_path / "Setapp"
        base.mkdir()
        # "Acme.app (1.0)" and "Zoom.app (2.0)" — sort order by annotated string
        for name, ver in [("Zoom.app", "2.0"), ("Acme.app", "1.0")]:
            app_dir = base / name
            app_dir.mkdir()
            _write_plist(app_dir, short_ver=ver)
        with patch.object(SetappCollector, "BASE", base):
            result = SetappCollector().collect()
        items = result.sections[0].items
        assert items == sorted(items)
        assert items.index("Acme.app (1.0)") < items.index("Zoom.app (2.0)")


# ---------------------------------------------------------------------------
# WebAppsCollector
# ---------------------------------------------------------------------------


class TestWebAppsCollector:
    def test_webapps_includes_applications_root_itself(self, tmp_path: Path) -> None:
        """Pitfall C: find includes start path — 'Applications' must appear in items."""
        base = tmp_path / "Applications"
        base.mkdir()
        app_dir = base / "Firefox.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="121.0")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Applications" in items, f"'Applications' root missing from items: {items}"
        assert "Firefox.app (121.0)" in items

    def test_webapps_excludes_setapp_dir(self, tmp_path: Path) -> None:
        """Dirs matching 'Setapp*' are excluded from items."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "Setapp").mkdir()
        (base / "SetappExtra").mkdir()
        app_dir = base / "Firefox.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="121.0")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Setapp" not in items
        assert "SetappExtra" not in items
        assert "Firefox.app (121.0)" in items

    def test_webapps_excludes_app_store_dirs(self, tmp_path: Path) -> None:
        """Dirs matching '*App Store*' are excluded from items."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "App Store.app").mkdir()
        app_dir = base / "Firefox.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="121.0")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "App Store.app" not in items
        assert "Firefox.app (121.0)" in items

    def test_webapps_sorted_output(self, tmp_path: Path) -> None:
        """Items are in sorted order (Applications root falls into sorted position)."""
        base = tmp_path / "Applications"
        base.mkdir()
        for name, ver in [("Zoom.app", "5.0"), ("1Password.app", "8.0")]:
            app_dir = base / name
            app_dir.mkdir()
            _write_plist(app_dir, short_ver=ver)
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
        app_dir = base / "App.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="1.0")
        (base / "readme.txt").write_text("ignored", encoding="utf-8")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "readme.txt" not in items
        assert "App.app (1.0)" in items

    def test_webapps_always_available(self) -> None:
        """WebAppsCollector.available() always returns True (no guard in zsh)."""
        assert WebAppsCollector().available() is True


# ---------------------------------------------------------------------------
# WebAppsCollector — versioning and degradation
# ---------------------------------------------------------------------------


class TestWebAppsVersioning:
    def test_app_with_short_version(self, tmp_path: Path) -> None:
        """App with CFBundleShortVersionString emits 'AppName.app (version)'."""
        base = tmp_path / "Applications"
        base.mkdir()
        app_dir = base / "Chrome.app"
        app_dir.mkdir()
        _write_plist(app_dir, short_ver="120.0.6099.130")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Chrome.app (120.0.6099.130)" in items

    def test_app_with_bundle_version_fallback(self, tmp_path: Path) -> None:
        """App with only CFBundleVersion emits 'AppName.app (bundleversion)'."""
        base = tmp_path / "Applications"
        base.mkdir()
        app_dir = base / "OldApp.app"
        app_dir.mkdir()
        _write_plist(app_dir, bundle_ver="1234")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "OldApp.app (1234)" in items

    def test_app_missing_plist_degrades(self, tmp_path: Path) -> None:
        """App dir with no Contents/Info.plist emits bare name without error."""
        base = tmp_path / "Applications"
        base.mkdir()
        (base / "NoPlist.app").mkdir()  # no plist
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "NoPlist.app" in items
        assert not any("NoPlist.app (" in item for item in items)

    def test_root_entry_name_only(self, tmp_path: Path) -> None:
        """'Applications' root entry is always name-only (no _versioned_entry call)."""
        base = tmp_path / "Applications"
        base.mkdir()
        # Even if the Applications dir itself had a Contents/Info.plist, the root
        # entry is prepended as BASE.name without going through _versioned_entry
        contents = base / "Contents"
        contents.mkdir()
        (contents / "Info.plist").write_bytes(
            plistlib.dumps({"CFBundleShortVersionString": "99.0"}, fmt=plistlib.FMT_XML)
        )
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Applications" in items
        assert "Applications (99.0)" not in items

    def test_determinism(self, tmp_path: Path) -> None:
        """Two consecutive collect() calls on the same fixture return identical items."""
        base = tmp_path / "Applications"
        base.mkdir()
        for name, ver in [("Slack.app", "4.35.126"), ("Zoom.app", "5.17.6")]:
            app_dir = base / name
            app_dir.mkdir()
            _write_plist(app_dir, short_ver=ver)
        with patch.object(WebAppsCollector, "BASE", base):
            collector = WebAppsCollector()
            items_1 = collector.collect().sections[0].items
            items_2 = collector.collect().sections[0].items
        assert items_1 == items_2, f"Non-deterministic: {items_1!r} != {items_2!r}"

    def test_zero_byte_plist_degrades(self, tmp_path: Path) -> None:
        """App dir with a zero-byte Info.plist emits bare name without error."""
        base = tmp_path / "Applications"
        base.mkdir()
        app_dir = base / "ZeroApp.app"
        app_dir.mkdir()
        contents = app_dir / "Contents"
        contents.mkdir()
        (contents / "Info.plist").write_bytes(b"")  # zero-byte
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "ZeroApp.app" in items
        assert not any("ZeroApp.app (" in item for item in items)

    def test_corrupt_plist_degrades(self, tmp_path: Path) -> None:
        """App dir with a binary-garbage Info.plist emits bare name without error."""
        base = tmp_path / "Applications"
        base.mkdir()
        app_dir = base / "Garbled.app"
        app_dir.mkdir()
        contents = app_dir / "Contents"
        contents.mkdir()
        (contents / "Info.plist").write_bytes(b"\x00\x01\x02\x03garbage")
        with patch.object(WebAppsCollector, "BASE", base):
            result = WebAppsCollector().collect()
        items = result.sections[0].items
        assert "Garbled.app" in items
        assert not any("Garbled.app (" in item for item in items)

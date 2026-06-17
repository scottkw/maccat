"""Tests for maccat.collectors.safari.

Behavioral spec: Phase 29 BRW-04 — Safari Extensions via pluginkit + plistlib.
"""
from __future__ import annotations

import plistlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import maccat.collectors.safari as safari_mod
from maccat.collectors.safari import SafariCollector, _parse_pluginkit_output

# ---------------------------------------------------------------------------
# Verbatim live-captured fixture from 29-CONTEXT.md §Specific Ideas
# ---------------------------------------------------------------------------

_BITWARDEN_FIXTURE = """\
     com.bitwarden.desktop.safari(2026.5.0)
            Path = /Applications/Bitwarden.app/Contents/PlugIns/safari.appex
            UUID = 5AFDA995-8D64-43CA-B696-154F57ABF85B
       Timestamp = 2026-06-08 02:49:27 +0000
             SDK = com.apple.Safari.web-extension
   Parent Bundle = /Applications/Bitwarden.app
"""


def _require_pluginkit() -> None:
    """Skip the calling test if /usr/bin/pluginkit is not present (keeps CI green)."""
    if not Path("/usr/bin/pluginkit").exists():
        pytest.skip("/usr/bin/pluginkit not present on this machine")


def _make_appex(
    tmp_path: Path,
    bundle_id: str,
    display_name: str,
    version: str,
    name: str = "",
) -> Path:
    """Create a minimal .appex bundle under tmp_path with an Info.plist.

    Returns the appex Path (tmp_path / "safari.appex").
    The plist contains CFBundleDisplayName (if display_name is set),
    CFBundleShortVersionString, and CFBundleIdentifier.
    """
    appex = tmp_path / "safari.appex"
    contents = appex / "Contents"
    contents.mkdir(parents=True)
    plist: dict[str, str] = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleShortVersionString": version,
    }
    if display_name:
        plist["CFBundleDisplayName"] = display_name
    if name:
        plist["CFBundleName"] = name
    (contents / "Info.plist").write_bytes(
        plistlib.dumps(plist, fmt=plistlib.FMT_XML)
    )
    return appex


# ---------------------------------------------------------------------------
# TestSafariParsePluginkitOutput
# ---------------------------------------------------------------------------


class TestSafariParsePluginkitOutput:
    def test_parse_extracts_bitwarden_path(self) -> None:
        result = _parse_pluginkit_output(_BITWARDEN_FIXTURE)
        assert result == [
            Path("/Applications/Bitwarden.app/Contents/PlugIns/safari.appex")
        ]

    def test_parse_empty_string(self) -> None:
        assert _parse_pluginkit_output("") == []

    def test_parse_no_appex_lines(self) -> None:
        output = "com.example.ext(1.0)\n  UUID = abc\n"
        assert _parse_pluginkit_output(output) == []


# ---------------------------------------------------------------------------
# TestSafariCollect
# ---------------------------------------------------------------------------


class TestSafariCollect:
    def test_collect_bitwarden(self, tmp_path: Path) -> None:
        appex = _make_appex(
            tmp_path,
            bundle_id="com.bitwarden.desktop.safari",
            display_name="Bitwarden",
            version="2026.5.0",
        )
        fixture = (
            f"     com.bitwarden.desktop.safari(2026.5.0)\n"
            f"            Path = {appex}\n"
            f"            UUID = 5AFDA995-8D64-43CA-B696-154F57ABF85B\n"
        )
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()

        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture

        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()

        assert result.sections[0].items == [
            "Bitwarden (2026.5.0) [com.bitwarden.desktop.safari]"
        ]

    def test_section_title(self, tmp_path: Path) -> None:
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = ""
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert result.sections[0].title == "Safari Extensions"

    def test_section_raw_false(self, tmp_path: Path) -> None:
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = ""
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert result.sections[0].raw is False


# ---------------------------------------------------------------------------
# TestSafariDegradation
# ---------------------------------------------------------------------------


class TestSafariDegradation:
    def test_pluginkit_absent(self, tmp_path: Path) -> None:
        with patch.object(safari_mod, "_PLUGINKIT", tmp_path / "no-pluginkit"):
            result = SafariCollector().collect()
        assert result.sections[0].items == []

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 1
        mock_r.stdout = ""
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert result.sections[0].items == []

    def test_empty_stdout(self, tmp_path: Path) -> None:
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = ""
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert result.sections[0].items == []

    def test_bad_plist_skipped(self, tmp_path: Path) -> None:
        # First entry: a non-existent appex (no plist)
        missing_appex = tmp_path / "missing.appex"

        # Second entry: a valid appex with a proper plist
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        valid_appex = _make_appex(
            valid_dir,
            bundle_id="com.valid.ext",
            display_name="ValidExt",
            version="1.0.0",
        )

        fixture = (
            f"            Path = {missing_appex}\n"
            f"            Path = {valid_appex}\n"
        )
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        # Only the valid extension should be present
        assert len(result.sections[0].items) == 1
        assert "ValidExt" in result.sections[0].items[0]

    def test_oserror_on_subprocess(self, tmp_path: Path) -> None:
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", side_effect=OSError("exec failed")),
        ):
            result = SafariCollector().collect()
        assert result.sections[0].items == []


# ---------------------------------------------------------------------------
# TestSafariNameResolution
# ---------------------------------------------------------------------------


class TestSafariNameResolution:
    def test_display_name_wins(self, tmp_path: Path) -> None:
        """CFBundleDisplayName takes precedence even when CFBundleName="safari"."""
        appex = _make_appex(
            tmp_path,
            bundle_id="com.bitwarden.desktop.safari",
            display_name="Bitwarden",
            version="1.0",
            name="safari",
        )
        fixture = f"            Path = {appex}\n"
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert len(result.sections[0].items) == 1
        assert result.sections[0].items[0].startswith("Bitwarden ")

    def test_bundle_name_safari_rejected(self, tmp_path: Path) -> None:
        """CFBundleName='safari' is never used as name — falls back to bundle_id."""
        appex_path = tmp_path / "safari.appex"
        contents = appex_path / "Contents"
        contents.mkdir(parents=True)
        plist: dict[str, str] = {
            "CFBundleIdentifier": "com.example.safariext",
            "CFBundleShortVersionString": "2.0",
            "CFBundleName": "safari",
        }
        (contents / "Info.plist").write_bytes(
            plistlib.dumps(plist, fmt=plistlib.FMT_XML)
        )

        fixture = f"            Path = {appex_path}\n"
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert len(result.sections[0].items) == 1
        # Name must NOT be "safari"
        item = result.sections[0].items[0]
        assert not item.startswith("safari ")

    def test_appex_own_bundle_name_used(self, tmp_path: Path) -> None:
        """No CFBundleDisplayName but a legit non-'safari' CFBundleName on the
        appex itself resolves to that name — not the bundle id (WR-01)."""
        appex = _make_appex(
            tmp_path,
            bundle_id="com.bitwarden.desktop.safari",
            display_name="",
            version="2026.5.0",
            name="Bitwarden",
        )
        fixture = f"            Path = {appex}\n"
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert len(result.sections[0].items) == 1
        item = result.sections[0].items[0]
        assert item.startswith("Bitwarden ")
        assert "com.bitwarden.desktop.safari" not in item.split("[", 1)[0]

    def test_identifier_fallback(self, tmp_path: Path) -> None:
        """When no display name is available, CFBundleIdentifier is used as name."""
        appex_path = tmp_path / "ext.appex"
        contents = appex_path / "Contents"
        contents.mkdir(parents=True)
        plist: dict[str, str] = {
            "CFBundleIdentifier": "com.example.noname",
            "CFBundleShortVersionString": "3.0",
        }
        (contents / "Info.plist").write_bytes(
            plistlib.dumps(plist, fmt=plistlib.FMT_XML)
        )

        fixture = f"            Path = {appex_path}\n"
        fake_pluginkit = tmp_path / "pluginkit"
        fake_pluginkit.touch()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = fixture
        with (
            patch.object(safari_mod, "_PLUGINKIT", fake_pluginkit),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = SafariCollector().collect()
        assert len(result.sections[0].items) == 1
        assert "com.example.noname" in result.sections[0].items[0]


# ---------------------------------------------------------------------------
# TestSafariSmoke — live-gated; skipped when pluginkit absent
# ---------------------------------------------------------------------------


class TestSafariSmoke:
    def test_live_pluginkit_returns_paths_without_raising(self) -> None:
        """Run real pluginkit (no mocks) and verify no exception is raised.

        Skipped automatically when /usr/bin/pluginkit is not present so that
        CI environments (no Safari) remain green.
        """
        _require_pluginkit()
        result = SafariCollector().collect()
        assert result.sections[0].title == "Safari Extensions"
        for item in result.sections[0].items:
            assert isinstance(item, str)

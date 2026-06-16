"""Tests for maccat.collectors.firefox.

Behavioral spec: update-list.sh lines 2154–2206 (collect_firefox_extensions).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

import maccat.collectors.firefox as ff_mod
from maccat.collectors.firefox import FirefoxCollector

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_ff_profile(
    ff_dir: Path,
    profile_rel: str,
    addons: list[dict],  # type: ignore[type-arg]
    ini_lines: str | None = None,
) -> None:
    """Build Firefox profiles.ini + one profile's extensions.json."""
    ff_dir.mkdir(parents=True, exist_ok=True)
    ini_path = ff_dir / "profiles.ini"
    if ini_lines is None:
        ini_content = f"[Profile0]\nPath={profile_rel}\n"
    else:
        ini_content = ini_lines
    ini_path.write_text(ini_content, encoding="utf-8")
    profile_dir = ff_dir / profile_rel
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "extensions.json").write_text(
        json.dumps({"addons": addons}),
        encoding="utf-8",
    )


def _app_profile_addon(
    id_: str = "addon@test.com",
    name: str = "Test Addon",
    version: str = "1.0",
) -> dict:  # type: ignore[type-arg]
    return {
        "id": id_,
        "version": version,
        "location": "app-profile",
        "defaultLocale": {"name": name},
    }


# ===========================================================================
# FirefoxCollect — basic collection
# ===========================================================================


class TestFirefoxCollect:
    def test_collects_from_profile(self, tmp_path: Path) -> None:
        """Extension from a profile's extensions.json is collected."""
        ff_dir = tmp_path / "Firefox"
        _make_ff_profile(
            ff_dir,
            "Profiles/abc.default",
            [_app_profile_addon(name="My Addon")],
        )
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        assert len(result.sections) == 1
        assert any("My Addon" in item for item in result.sections[0].items)

    def test_firefox_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Firefox Extensions'."""
        ff_dir = tmp_path / "Firefox"
        ff_dir.mkdir()
        # No profiles.ini — degraded path returns 1 empty section
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        assert result.sections[0].title == "Firefox Extensions"

    def test_firefox_raw_is_false(self, tmp_path: Path) -> None:
        """Section.raw is False — flush_section by Phase 16 orchestrator."""
        ff_dir = tmp_path / "Firefox"
        ff_dir.mkdir()
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        assert result.sections[0].raw is False


# ===========================================================================
# FirefoxLocationFilter — app-profile only
# ===========================================================================


class TestFirefoxLocationFilter:
    def test_location_filter_excludes_app_builtin(self, tmp_path: Path) -> None:
        """app-builtin addons are excluded from output."""
        ff_dir = tmp_path / "Firefox"
        builtin = {
            "id": "builtin@firefox.com",
            "version": "1.0",
            "location": "app-builtin",
            "defaultLocale": {"name": "Builtin Addon"},
        }
        _make_ff_profile(ff_dir, "Profiles/test.default", [builtin])
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        assert not any("Builtin Addon" in item for item in result.sections[0].items)

    def test_location_filter_includes_only_app_profile(self, tmp_path: Path) -> None:
        """Mixed locations: only app-profile entries appear in output."""
        ff_dir = tmp_path / "Firefox"
        addons = [
            _app_profile_addon(id_="user@ext", name="User Ext"),
            {
                "id": "system@ext",
                "version": "1.0",
                "location": "app-builtin-addons",
                "defaultLocale": {"name": "System Ext"},
            },
        ]
        _make_ff_profile(ff_dir, "Profiles/test.default", addons)
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        items = result.sections[0].items
        assert any("User Ext" in item for item in items)
        assert not any("System Ext" in item for item in items)

    def test_null_id_skipped(self, tmp_path: Path) -> None:
        """Addons with id=None or id='null' are skipped."""
        ff_dir = tmp_path / "Firefox"
        addons = [
            {
                "id": None,
                "version": "1.0",
                "location": "app-profile",
                "defaultLocale": {"name": "Null ID"},
            },
            {
                "id": "null",
                "version": "1.0",
                "location": "app-profile",
                "defaultLocale": {"name": "String Null"},
            },
            _app_profile_addon(id_="real@ext", name="Real Ext"),
        ]
        _make_ff_profile(ff_dir, "Profiles/test.default", addons)
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        items = result.sections[0].items
        assert not any("Null ID" in item for item in items)
        assert not any("String Null" in item for item in items)
        assert any("Real Ext" in item for item in items)

    def test_name_fallback_to_id(self, tmp_path: Path) -> None:
        """When defaultLocale.name is absent/null, addon id is used as name."""
        ff_dir = tmp_path / "Firefox"
        addon_no_name = {
            "id": "my-addon@example.com",
            "version": "2.0",
            "location": "app-profile",
            "defaultLocale": {},
        }
        _make_ff_profile(ff_dir, "Profiles/test.default", [addon_no_name])
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        items = result.sections[0].items
        assert any("my-addon@example.com" in item for item in items)


# ===========================================================================
# FirefoxProfileParsing — CRLF, multi-profile dedup
# ===========================================================================


class TestFirefoxProfileParsing:
    def test_crlf_path_handling(self, tmp_path: Path) -> None:
        """profiles.ini with Windows CRLF line endings parses Path= correctly (no trailing \\r)."""
        ff_dir = tmp_path / "Firefox"
        ff_dir.mkdir(parents=True)
        # Write CRLF-encoded profiles.ini (Pitfall E)
        (ff_dir / "profiles.ini").write_bytes(b"[Profile0]\r\nPath=Profiles/abc\r\n")
        profile_dir = ff_dir / "Profiles" / "abc"
        profile_dir.mkdir(parents=True)
        (profile_dir / "extensions.json").write_text(
            json.dumps({"addons": [_app_profile_addon(name="CRLF Addon")]}),
            encoding="utf-8",
        )
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        # If CRLF not handled, path would be "Profiles/abc\r" — profile dir missing -> []
        assert any("CRLF Addon" in item for item in result.sections[0].items), (
            "splitlines() must strip \\r from CRLF-encoded profiles.ini path values"
        )

    def test_cross_profile_dedup(self, tmp_path: Path) -> None:
        """Two profiles both containing same addon: collect() accumulates items from both.

        Note: items before flush_section MAY contain duplicates — that is correct behavior.
        flush_section (called by Phase 16 orchestrator) handles deduplication at write time.
        This test verifies collect() INCLUDES the addon (not that it deduplicates early).
        """
        ff_dir = tmp_path / "Firefox"
        ff_dir.mkdir(parents=True)
        # Two profile entries in profiles.ini
        ini = "[Profile0]\nPath=Profiles/p1\n[Profile1]\nPath=Profiles/p2\n"
        (ff_dir / "profiles.ini").write_text(ini, encoding="utf-8")
        addon = _app_profile_addon(id_="shared@ext", name="Shared Addon")
        for rel in ("Profiles/p1", "Profiles/p2"):
            p = ff_dir / rel
            p.mkdir(parents=True)
            (p / "extensions.json").write_text(
                json.dumps({"addons": [addon]}), encoding="utf-8"
            )
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()
        items = result.sections[0].items
        # The addon must be present (accumulated from at least one profile)
        assert any("Shared Addon" in item for item in items)


# ===========================================================================
# FirefoxDegradation — CAT-06: absent Firefox / profiles.ini
# ===========================================================================


class TestFirefoxDegradation:
    def test_firefox_not_installed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When profiles.ini does not exist, NOTE is printed to stderr and items is []."""
        missing_dir = tmp_path / "NoFirefox"
        with patch.object(ff_mod, "_FF_DIR", missing_dir):
            result = FirefoxCollector().collect()
        assert result.sections[0].items == []
        captured = capsys.readouterr()
        assert "NOTE" in captured.err
        assert "Firefox" in captured.err

    # --- CAT-06 shape-guard regressions (CR-01 / IN-03) ---

    def test_non_dict_addon_element_degrades(self, tmp_path: Path) -> None:
        """A non-dict addon element (string/number/null) is skipped, not raised."""
        ff_dir = tmp_path / "Firefox"
        _make_ff_profile(
            ff_dir,
            "Profiles/abc.default",
            ["just-a-string", 99, None, _app_profile_addon(name="Good Addon")],
        )
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()  # must not raise
        items = result.sections[0].items
        assert any("Good Addon" in item for item in items)
        assert len(items) == 1

    def test_non_dict_default_locale_degrades(self, tmp_path: Path) -> None:
        """A non-dict defaultLocale falls back to id, not an AttributeError (IN-03)."""
        ff_dir = tmp_path / "Firefox"
        addon = {
            "id": "addon@x.com",
            "version": "2.0",
            "location": "app-profile",
            "defaultLocale": "not-a-dict",
        }
        _make_ff_profile(ff_dir, "Profiles/abc.default", [addon])
        with patch.object(ff_mod, "_FF_DIR", ff_dir):
            result = FirefoxCollector().collect()  # must not raise
        items = result.sections[0].items
        # name falls back to the id
        assert any("addon@x.com" in item for item in items)

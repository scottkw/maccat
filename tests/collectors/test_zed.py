"""Tests for maccat.collectors.zed.

Behavioral spec: Phase 27 BRW-03 — Zed Extensions from index.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import maccat.collectors.zed as zed_mod
from maccat.collectors.zed import ZedCollector

# ===========================================================================
# ZedCollect — basic collection
# ===========================================================================


class TestZedCollect:
    def test_zed_returns_one_section(self, tmp_path: Path) -> None:
        """collect() always returns exactly 1 section."""
        missing = tmp_path / "index.json"
        with patch.object(zed_mod, "_INDEX", missing):
            result = ZedCollector().collect()
        assert len(result.sections) == 1

    def test_zed_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Zed Extensions'."""
        missing = tmp_path / "index.json"
        with patch.object(zed_mod, "_INDEX", missing):
            result = ZedCollector().collect()
        assert result.sections[0].title == "Zed Extensions"

    def test_zed_collects_extension_name_version_id(self, tmp_path: Path) -> None:
        """Clean entry with name, version, and id is formatted as 'name (version) [id]'."""
        index = tmp_path / "index.json"
        index.write_text(
            json.dumps({
                "extensions": {
                    "html": {
                        "manifest": {"name": "HTML", "version": "0.3.1"},
                        "dev": False,
                    }
                }
            }),
            encoding="utf-8",
        )
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()
        items = result.sections[0].items
        assert len(items) == 1
        assert items[0] == "HTML (0.3.1) [html]"


# ===========================================================================
# ZedDevFilter — BRW-03 dev extension exclusion
# ===========================================================================


class TestZedDevFilter:
    def test_zed_excludes_dev_extensions(self, tmp_path: Path) -> None:
        """Entries with dev=True are excluded; dev=False entries are included."""
        index = tmp_path / "index.json"
        index.write_text(
            json.dumps({
                "extensions": {
                    "html": {
                        "manifest": {"name": "HTML", "version": "0.3.1"},
                        "dev": False,
                    },
                    "my-local": {
                        "manifest": {"name": "Local Dev", "version": "0.1.0"},
                        "dev": True,
                    },
                }
            }),
            encoding="utf-8",
        )
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()
        items = result.sections[0].items
        assert any("HTML" in item for item in items)
        assert not any("Local Dev" in item for item in items)

    def test_zed_includes_entry_without_dev_key(self, tmp_path: Path) -> None:
        """Entry with no 'dev' key is treated as dev=False and included."""
        index = tmp_path / "index.json"
        index.write_text(
            json.dumps({
                "extensions": {
                    "rust": {
                        "manifest": {"name": "Rust", "version": "1.0.0"},
                        # no "dev" key
                    },
                }
            }),
            encoding="utf-8",
        )
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()
        items = result.sections[0].items
        assert any("Rust" in item for item in items)


# ===========================================================================
# ZedDegradation — graceful degradation for absent, malformed, missing fields
# ===========================================================================


class TestZedDegradation:
    def test_zed_absent_index_returns_empty(self, tmp_path: Path) -> None:
        """When _INDEX does not exist, items == [], title == 'Zed Extensions', no exception."""
        missing = tmp_path / "index.json"
        with patch.object(zed_mod, "_INDEX", missing):
            result = ZedCollector().collect()
        assert len(result.sections) == 1
        assert result.sections[0].title == "Zed Extensions"
        assert result.sections[0].items == []

    def test_zed_absent_index_prints_note(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When _INDEX does not exist, NOTE is printed to stderr."""
        missing = tmp_path / "index.json"
        with patch.object(zed_mod, "_INDEX", missing):
            ZedCollector().collect()
        captured = capsys.readouterr()
        assert "NOTE" in captured.err
        assert "Zed" in captured.err

    def test_zed_malformed_index_returns_empty(self, tmp_path: Path) -> None:
        """When _INDEX contains malformed JSON, items == [], no exception raised."""
        index = tmp_path / "index.json"
        index.write_text("{not: valid json", encoding="utf-8")
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()
        assert result.sections[0].items == []

    def test_zed_missing_manifest_uses_ext_id_as_name(self, tmp_path: Path) -> None:
        """Entry with no 'manifest' key uses ext_id as name fallback; no exception."""
        index = tmp_path / "index.json"
        index.write_text(
            json.dumps({
                "extensions": {
                    "bare-id": {},  # no manifest key
                }
            }),
            encoding="utf-8",
        )
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()  # must not raise
        items = result.sections[0].items
        assert any("bare-id" in item for item in items)

    def test_zed_non_dict_extension_entry_skips(self, tmp_path: Path) -> None:
        """Non-dict extension value is skipped, valid entries still collected."""
        index = tmp_path / "index.json"
        index.write_text(
            json.dumps({
                "extensions": {
                    "bad-entry": "not-a-dict",
                    "good": {
                        "manifest": {"name": "Good", "version": "1.0.0"},
                        "dev": False,
                    },
                }
            }),
            encoding="utf-8",
        )
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()  # must not raise
        items = result.sections[0].items
        assert any("Good" in item for item in items)

    def test_zed_empty_extensions_object_returns_empty(self, tmp_path: Path) -> None:
        """index.json with 'extensions: {}' returns items == []."""
        index = tmp_path / "index.json"
        index.write_text(json.dumps({"extensions": {}}), encoding="utf-8")
        with patch.object(zed_mod, "_INDEX", index):
            result = ZedCollector().collect()
        assert result.sections[0].items == []

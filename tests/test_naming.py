"""Tests for maccat.naming — parse_catalog_filename, make_catalog_filename.

Behavioral spec: update-list.sh filename convention (lines 964–965, 982–983).
The regex derives from the zsh parameter expansion that extracts host and ts
from catalog filenames; see parse_catalog_filename docstring.
"""
from __future__ import annotations

import pytest

from maccat.naming import CatalogFilename, make_catalog_filename, parse_catalog_filename

# ---------------------------------------------------------------------------
# parse_catalog_filename
# ---------------------------------------------------------------------------


class TestParseCatalogFilename:
    def test_valid_filename_returns_dataclass(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000.txt")
        assert result is not None
        assert isinstance(result, CatalogFilename)

    def test_machine_field_populated_correctly(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000.txt")
        assert result is not None
        assert result.machine == "personal"

    def test_timestamp_field_populated_correctly(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000.txt")
        assert result is not None
        assert result.timestamp == "20260614120000"

    def test_filename_field_preserved(self) -> None:
        fname = "mac-software-list-[personal]-20260614120000.txt"
        result = parse_catalog_filename(fname)
        assert result is not None
        assert result.filename == fname

    def test_spaces_in_machine_name_allowed(self) -> None:
        result = parse_catalog_filename("mac-software-list-[My Computer]-20260614120000.txt")
        assert result is not None
        assert result.machine == "My Computer"

    def test_non_matching_name_returns_none(self) -> None:
        result = parse_catalog_filename("not-a-catalog.txt")
        assert result is None

    def test_non_matching_name_never_raises(self) -> None:
        """parse_catalog_filename must return None, never raise, for any non-matching input."""
        try:
            result = parse_catalog_filename("not-a-catalog.txt")
        except Exception as exc:
            pytest.fail(f"parse_catalog_filename raised unexpectedly: {exc!r}")
        assert result is None

    def test_brackets_in_machine_name_returns_none(self) -> None:
        """validate_computer_name blocks bracket characters; regex [^\\[\\]]+ enforces this."""
        result = parse_catalog_filename("mac-software-list-[bad[bracket]]-20260614120000.txt")
        assert result is None

    def test_13_digit_timestamp_returns_none(self) -> None:
        result = parse_catalog_filename("mac-software-list-[host]-2026061400.txt")
        assert result is None

    def test_15_digit_timestamp_returns_none(self) -> None:
        result = parse_catalog_filename("mac-software-list-[host]-202606141200000.txt")
        assert result is None

    def test_gitkeep_not_matched(self) -> None:
        result = parse_catalog_filename(".gitkeep")
        assert result is None

    def test_empty_machine_label_returns_none(self) -> None:
        """Empty [] brackets not allowed — [^\\[\\]]+ requires at least one char."""
        result = parse_catalog_filename("mac-software-list-[]-20260614120000.txt")
        assert result is None

    def test_frozen_dataclass_is_immutable(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000.txt")
        assert result is not None
        with pytest.raises((AttributeError, TypeError)):
            result.machine = "other"  # type: ignore[misc]

    def test_frozen_dataclass_is_hashable(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000.txt")
        assert result is not None
        # Must be usable as a dict key and in sets
        _ = {result: True}
        _ = {result}

    def test_missing_txt_extension_returns_none(self) -> None:
        result = parse_catalog_filename("mac-software-list-[personal]-20260614120000")
        assert result is None

    def test_wrong_prefix_returns_none(self) -> None:
        result = parse_catalog_filename("software-list-[personal]-20260614120000.txt")
        assert result is None


# ---------------------------------------------------------------------------
# make_catalog_filename
# ---------------------------------------------------------------------------


class TestMakeCatalogFilename:
    def test_output_format(self) -> None:
        result = make_catalog_filename("personal", "20260614120000")
        assert result == "mac-software-list-[personal]-20260614120000.txt"

    def test_round_trip(self) -> None:
        """make then parse → same machine and timestamp."""
        machine = "personal"
        ts = "20260614120000"
        filename = make_catalog_filename(machine, ts)
        parsed = parse_catalog_filename(filename)
        assert parsed is not None
        assert parsed.machine == machine
        assert parsed.timestamp == ts

    def test_round_trip_with_spaces(self) -> None:
        """Machine names with spaces survive the round trip."""
        machine = "My Computer"
        ts = "20260614120000"
        filename = make_catalog_filename(machine, ts)
        parsed = parse_catalog_filename(filename)
        assert parsed is not None
        assert parsed.machine == machine
        assert parsed.timestamp == ts

    def test_returns_string(self) -> None:
        result = make_catalog_filename("office", "20260614120000")
        assert isinstance(result, str)

    def test_brackets_wrap_machine(self) -> None:
        result = make_catalog_filename("personal", "20260614120000")
        assert "[personal]" in result

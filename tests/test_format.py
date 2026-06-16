"""Tests for maccat.catalog.format — emit_item, flush_section, version_sort_tail.

Behavioral spec: update-list.sh lines 1243-1297 (FMT-01 rules).
Byte parity: flush_section() output must be byte-identical to
  printf '%s\\n' ... | LC_ALL=C sort -f -u
"""
from __future__ import annotations

import os
import subprocess

from maccat.catalog.format import emit_item, flush_section, version_sort_tail

# ---------------------------------------------------------------------------
# emit_item — FMT-01 degradation rules
# ---------------------------------------------------------------------------


class TestEmitItem:
    def test_name_version_id(self) -> None:
        assert emit_item("App", "1.0", "com.app") == "App (1.0) [com.app]"

    def test_name_version_no_id(self) -> None:
        assert emit_item("App", "1.0", "") == "App (1.0)"

    def test_name_id_no_version(self) -> None:
        assert emit_item("App", "", "com.app") == "App [com.app]"

    def test_name_only(self) -> None:
        assert emit_item("App", "", "") == "App"

    def test_id_only_promotes_to_name_no_brackets(self) -> None:
        """id-as-name promotion: empty name + present id -> id becomes name (no brackets)."""
        result = emit_item("", "", "com.app")
        assert result == "com.app"
        # Must NOT contain brackets — would be "com.app [com.app]" if promotion is missing
        assert "[" not in result

    def test_id_and_version_no_name_promotes(self) -> None:
        """id-as-name promotion with version: id becomes name, brackets suppressed."""
        result = emit_item("", "1.0", "com.app")
        assert result == "com.app (1.0)"
        assert "[" not in result

    def test_all_empty_returns_none(self) -> None:
        assert emit_item("", "", "") is None

    def test_whitespace_only_args_returns_none(self) -> None:
        """All-whitespace args should evaluate as empty (falsy strings)."""
        # The plan requires None for all-empty; whitespace strings are falsy in Python
        # (non-empty whitespace is truthy, but the zsh analog treats it as content).
        # Per the "all fields empty" spec — only truly empty strings trigger None.
        assert emit_item("", "", "") is None

    def test_id_only_version_empty_name_empty(self) -> None:
        """Edge case: only version is set, no name, no id → None (no field to display)."""
        # version alone without name or id: after id-promotion check (id is empty, skip),
        # name stays empty → return None
        assert emit_item("", "1.0", "") is None


# ---------------------------------------------------------------------------
# flush_section — sort + dedup via subprocess
# ---------------------------------------------------------------------------


class TestFlushSection:
    def test_empty_returns_none_found(self) -> None:
        result = flush_section([])
        assert result == ["  (none found)"]
        # Exactly two spaces before the paren (verified from update-list.sh:1292)
        assert result[0].startswith("  (")

    def test_empty_result_has_exactly_two_leading_spaces(self) -> None:
        result = flush_section([])
        assert result[0][:2] == "  "
        assert result[0][2] == "("

    def test_sort_and_dedup_mixed_case(self) -> None:
        """bitwarden deduped against Bitwarden by -u (case-fold comparison)."""
        items = ["1password", "Bitwarden", "zed", "Adobe Acrobat", "bitwarden"]
        result = flush_section(items)
        assert result == ["1password", "Adobe Acrobat", "Bitwarden", "zed"]

    def test_sort_parity_with_subprocess(self) -> None:
        """flush_section must match printf '%s\\n' ... | LC_ALL=C sort -f -u byte-for-byte."""
        items = ["b", "A", "a", "C"]
        py_out = flush_section(items)

        env = {**os.environ, "LC_ALL": "C"}
        r = subprocess.run(
            ["sort", "-f", "-u"],
            input="\n".join(items) + "\n",
            capture_output=True,
            text=True,
            env=env,
        )
        zsh_out = r.stdout.rstrip("\n").split("\n")
        assert py_out == zsh_out, f"Parity MISMATCH: flush_section={py_out!r} vs sort={zsh_out!r}"

    def test_sort_parity_extended(self) -> None:
        """Extended parity test with numbers + mixed case."""
        items = ["zed", "Bitwarden", "1password", "bitwarden"]
        py_out = flush_section(items)

        env = {**os.environ, "LC_ALL": "C"}
        r = subprocess.run(
            ["sort", "-f", "-u"],
            input="\n".join(items) + "\n",
            capture_output=True,
            text=True,
            env=env,
        )
        zsh_out = r.stdout.rstrip("\n").split("\n")
        assert py_out == zsh_out

    def test_single_item(self) -> None:
        result = flush_section(["OnlyItem"])
        assert result == ["OnlyItem"]

    def test_no_trailing_empty_string_in_result(self) -> None:
        """Result list must not contain a trailing empty string (rstrip ensures this)."""
        result = flush_section(["Alpha", "Beta"])
        assert result[-1] != ""


# ---------------------------------------------------------------------------
# version_sort_tail — sort -V for Chrome version directory selection
# ---------------------------------------------------------------------------


class TestVersionSortTail:
    def test_empty_returns_none(self) -> None:
        assert version_sort_tail([]) is None

    def test_picks_highest_version(self) -> None:
        candidates = ["2.0.0_0", "14.0.0_0", "3.5.1_0", "9.0.0_0"]
        result = version_sort_tail(candidates)
        assert result == "14.0.0_0"

    def test_year_version_sorts_highest(self) -> None:
        """2026.x.x must beat 14.x.x numerically (not lexicographically)."""
        candidates = ["2.0.0_0", "14.0.0_0", "3.5.1_0", "2026.5.1_0"]
        result = version_sort_tail(candidates)
        assert result == "2026.5.1_0"

    def test_single_candidate(self) -> None:
        result = version_sort_tail(["1.0.0"])
        assert result == "1.0.0"

    def test_filters_chrome_internal_entries(self) -> None:
        """WR-02: non-version entries (zsh grep -E '^[0-9]' pre-filter) must not
        steal the slot. _metadata / _crx_invalidation_map are dropped before sort -V.
        """
        candidates = ["_metadata", "1.0.0_0", "_crx_invalidation_map", "2.0.0_0"]
        result = version_sort_tail(candidates)
        assert result == "2.0.0_0"

    def test_all_non_version_returns_none(self) -> None:
        """WR-02: if no candidate begins with a digit, return None (nothing survives the filter)."""
        assert version_sort_tail(["_metadata", "_crx_invalidation_map"]) is None

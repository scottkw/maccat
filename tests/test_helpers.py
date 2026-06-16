"""
Unit tests for json_io.json_get, chrome_name.chrome_ext_name,
and vsc_name.resolve_vsc_ext_name.

Tests are organized per helper and cover all fallback paths, including
the VS Code NLS dotted-key distinction (Pitfall 3 from RESEARCH.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from maccat.helpers.json_io import json_get

# ---------------------------------------------------------------------------
# json_get
# ---------------------------------------------------------------------------


class TestJsonGet:
    def test_missing_file_returns_default(self, tmp_path: Path) -> None:
        assert json_get(tmp_path / "nonexistent.json", "name") == ""

    def test_missing_file_returns_custom_default(self, tmp_path: Path) -> None:
        assert json_get(tmp_path / "missing.json", "name", default="fallback") == "fallback"

    def test_empty_key_returns_default(self, tmp_json) -> None:
        f = tmp_json({"name": "Foo"})
        assert json_get(f, "") == ""

    def test_top_level_string_key(self, tmp_json) -> None:
        f = tmp_json({"name": "Foo"})
        assert json_get(f, "name") == "Foo"

    def test_nested_dotted_key(self, tmp_json) -> None:
        f = tmp_json({"author": {"name": "Bar"}})
        assert json_get(f, "author.name") == "Bar"

    def test_non_string_leaf_converted_to_str(self, tmp_json) -> None:
        f = tmp_json({"count": 42})
        assert json_get(f, "count") == "42"

    def test_malformed_json_returns_default(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{not valid json", encoding="utf-8")
        assert json_get(f, "name") == ""

    def test_missing_nested_key_returns_default(self, tmp_json) -> None:
        f = tmp_json({"a": {"b": "c"}})
        assert json_get(f, "a.x") == ""

    def test_key_traversal_stops_at_non_dict(self, tmp_json) -> None:
        # "a" is a string, so "a.b" cannot traverse further
        f = tmp_json({"a": "string_value"})
        assert json_get(f, "a.b") == ""

    def test_boolean_leaf_converted_to_str(self, tmp_json) -> None:
        f = tmp_json({"enabled": True})
        assert json_get(f, "enabled") == "True"

    def test_deeply_nested_traversal(self, tmp_json) -> None:
        f = tmp_json({"x": {"y": {"z": "deep"}}})
        assert json_get(f, "x.y.z") == "deep"


# ---------------------------------------------------------------------------
# chrome_ext_name
# ---------------------------------------------------------------------------


class TestChromeExtName:
    """
    Test chrome_ext_name() with various manifest configurations.

    Fixture directory structure mirrors the real Chrome profile layout:
      <ext_id>/<version>/manifest.json
      <ext_id>/<version>/_locales/<locale>/messages.json
    """

    def _make_ext(
        self,
        tmp_path: Path,
        ext_id: str = "abcdefghijklmnopqrstuvwxyz012345",
        version: str = "1.0.0_0",
        manifest: dict | None = None,
        locales: dict[str, dict] | None = None,
    ) -> Path:
        """Build a minimal Chrome extension directory, return path to manifest.json."""
        ver_dir = tmp_path / ext_id / version
        ver_dir.mkdir(parents=True)
        manifest_path = ver_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest or {}), encoding="utf-8")
        if locales:
            for locale, messages in locales.items():
                locale_dir = ver_dir / "_locales" / locale
                locale_dir.mkdir(parents=True)
                (locale_dir / "messages.json").write_text(
                    json.dumps(messages), encoding="utf-8"
                )
        return manifest_path

    def test_plain_name_returned_as_is(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        manifest = self._make_ext(tmp_path, manifest={"name": "My Extension"})
        assert chrome_ext_name(manifest) == "My Extension"

    def test_empty_name_falls_back_to_ext_id(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        ext_id = "abcdefghijklmnopqrstuvwxyz012345"
        manifest = self._make_ext(tmp_path, ext_id=ext_id, manifest={"name": ""})
        assert chrome_ext_name(manifest) == ext_id

    def test_msg_placeholder_resolved_from_messages_json(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        manifest = self._make_ext(
            tmp_path,
            manifest={"name": "__MSG_extName__"},
            locales={"en": {"extName": {"message": "Real Name"}}},
        )
        assert chrome_ext_name(manifest) == "Real Name"

    def test_msg_placeholder_case_insensitive_lookup(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        # Manifest key is uppercase; messages.json key is lowercase
        manifest = self._make_ext(
            tmp_path,
            manifest={"name": "__MSG_EXTNAME__"},
            locales={"en": {"extname": {"message": "Case Folded"}}},
        )
        assert chrome_ext_name(manifest) == "Case Folded"

    def test_msg_placeholder_missing_locales_dir_falls_back_to_ext_id(
        self, tmp_path: Path
    ) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        ext_id = "abcdefghijklmnopqrstuvwxyz012345"
        # No locales kwarg — _locales/ directory not created
        manifest = self._make_ext(
            tmp_path, ext_id=ext_id, manifest={"name": "__MSG_extName__"}
        )
        assert chrome_ext_name(manifest) == ext_id

    def test_msg_placeholder_key_absent_in_messages_falls_back_to_ext_id(
        self, tmp_path: Path
    ) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        ext_id = "abcdefghijklmnopqrstuvwxyz012345"
        manifest = self._make_ext(
            tmp_path,
            ext_id=ext_id,
            manifest={"name": "__MSG_extName__"},
            locales={"en": {"otherKey": {"message": "Something Else"}}},
        )
        assert chrome_ext_name(manifest) == ext_id

    def test_empty_msg_key_treated_as_plain_name(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        # "__MSG__" has zero chars between __MSG_ and __; len guard should treat as plain
        ext_id = "abcdefghijklmnopqrstuvwxyz012345"
        manifest = self._make_ext(
            tmp_path, ext_id=ext_id, manifest={"name": "__MSG__"}
        )
        # "__MSG__" is non-empty so it returns as a plain name (not ext_id)
        result = chrome_ext_name(manifest)
        # Must not return blank; either "__MSG__" or ext_id is acceptable per spec
        assert result in ("__MSG__", ext_id)
        assert result != ""

    def test_uses_default_locale_from_manifest(self, tmp_path: Path) -> None:
        from maccat.helpers.chrome_name import chrome_ext_name

        manifest = self._make_ext(
            tmp_path,
            manifest={"name": "__MSG_appName__", "default_locale": "fr"},
            locales={"fr": {"appName": {"message": "Mon Extension"}}},
        )
        assert chrome_ext_name(manifest) == "Mon Extension"

    def test_case_collision_keeps_first_match_like_head_1(
        self, tmp_path: Path
    ) -> None:
        """WR-02: case-colliding keys must resolve to the FIRST in file order.

        zsh's `jq to_entries[] | select(...) | .value.message | head -1` keeps
        the first match in JSON document order. A lowercase-keyed dict
        comprehension would keep the LAST colliding key — a byte-parity break.
        Python preserves insertion order, which matches jq's input order.
        """
        from maccat.helpers.chrome_name import chrome_ext_name

        # appName appears before APPNAME in document order; FIRST must win.
        manifest = self._make_ext(
            tmp_path,
            manifest={"name": "__MSG_appName__"},
            locales={
                "en": {
                    "appName": {"message": "FIRST"},
                    "APPNAME": {"message": "SECOND"},
                }
            },
        )
        assert chrome_ext_name(manifest) == "FIRST"

    def test_non_string_message_degrades_to_ext_id(self, tmp_path: Path) -> None:
        """WR-02: a non-string .value.message would make jq -r emit multi-line
        JSON whose first line head -1 captures; str(value) cannot reproduce
        that. Degrade to ext_id instead of leaking a Python repr.
        """
        from maccat.helpers.chrome_name import chrome_ext_name

        ext_id = "abcdefghijklmnopqrstuvwxyz012345"
        manifest = self._make_ext(
            tmp_path,
            ext_id=ext_id,
            manifest={"name": "__MSG_extName__"},
            locales={"en": {"extName": {"message": {"nested": "obj"}}}},
        )
        result = chrome_ext_name(manifest)
        assert result == ext_id
        # Must NOT leak a Python dict/list repr
        assert "{" not in result
        assert "nested" not in result


# ---------------------------------------------------------------------------
# resolve_vsc_ext_name
# ---------------------------------------------------------------------------


class TestResolveVscExtName:
    """
    Test resolve_vsc_ext_name() with various package.json configurations.

    Also explicitly demonstrates Pitfall 3: json_get() returns "" for keys
    containing literal dots, while nls.get() returns the correct value.
    """

    def test_plain_display_name_returned_as_is(self, tmp_json) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg = tmp_json({"displayName": "My Extension"}, filename="package.json")
        assert resolve_vsc_ext_name(pkg, "ext-id") == "My Extension"

    def test_missing_display_name_returns_ext_id(self, tmp_json) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg = tmp_json({"name": "some-ext"}, filename="package.json")
        assert resolve_vsc_ext_name(pkg, "ext-id") == "ext-id"

    def test_nls_placeholder_with_dotted_key_resolved_flat(
        self, tmp_path: Path
    ) -> None:
        """
        Key contains a literal dot: "extension.title".

        Direct flat lookup via nls.get("extension.title") must succeed.
        json_get(nls_file, "extension.title") must return "" (Pitfall 3 demo).
        """
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg_json = tmp_path / "package.json"
        nls_file = tmp_path / "package.nls.json"

        pkg_json.write_text(
            json.dumps({"displayName": "%extension.title%"}), encoding="utf-8"
        )
        nls_file.write_text(
            json.dumps({"extension.title": "Real Name"}), encoding="utf-8"
        )

        # The actual function must resolve it correctly
        assert resolve_vsc_ext_name(pkg_json, "ext-id") == "Real Name"

        # Pitfall 3 demonstration: json_get dotted-path traversal fails here
        assert json_get(nls_file, "extension.title") == "", (
            "json_get() must return '' for dotted keys in flat NLS files (Pitfall 3)"
        )

        # Flat lookup works correctly
        nls_data = json.loads(nls_file.read_text(encoding="utf-8"))
        assert nls_data.get("extension.title") == "Real Name"

    def test_nls_placeholder_missing_key_returns_ext_id(self, tmp_path: Path) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg_json = tmp_path / "package.json"
        nls_file = tmp_path / "package.nls.json"

        pkg_json.write_text(
            json.dumps({"displayName": "%missingKey%"}), encoding="utf-8"
        )
        nls_file.write_text(json.dumps({"otherKey": "Something"}), encoding="utf-8")

        assert resolve_vsc_ext_name(pkg_json, "ext-id") == "ext-id"

    def test_nls_placeholder_missing_nls_file_returns_ext_id(
        self, tmp_path: Path
    ) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            json.dumps({"displayName": "%key%"}), encoding="utf-8"
        )
        # package.nls.json is not created

        assert resolve_vsc_ext_name(pkg_json, "ext-id") == "ext-id"

    def test_empty_percent_placeholder_not_treated_as_nls(
        self, tmp_path: Path
    ) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        # "%%" has zero chars between % and %; len guard must treat as plain string
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(json.dumps({"displayName": "%%"}), encoding="utf-8")
        # "%%": len("%%") == 2, not > 2 — plain string, returned as-is
        assert resolve_vsc_ext_name(pkg_json, "ext-id") == "%%"

    def test_simple_nls_key_without_dot(self, tmp_path: Path) -> None:
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg_json = tmp_path / "package.json"
        nls_file = tmp_path / "package.nls.json"

        pkg_json.write_text(
            json.dumps({"displayName": "%appTitle%"}), encoding="utf-8"
        )
        nls_file.write_text(
            json.dumps({"appTitle": "Simple Title"}), encoding="utf-8"
        )

        assert resolve_vsc_ext_name(pkg_json, "ext-id") == "Simple Title"

    def test_nls_v2_object_value_degrades_to_ext_id(self, tmp_path: Path) -> None:
        """WR-01: a VS Code NLS v2 object value ({"message": ...}) is a non-string.

        zsh's `jq -r '.[$k] // ""'` would emit pretty-printed multi-line JSON,
        which str(dict) cannot reproduce. Rather than emit a divergent Python
        repr, degrade to ext_id (only a flat string is a usable display name).
        """
        from maccat.helpers.vsc_name import resolve_vsc_ext_name

        pkg_json = tmp_path / "package.json"
        nls_file = tmp_path / "package.nls.json"

        pkg_json.write_text(
            json.dumps({"displayName": "%appTitle%"}), encoding="utf-8"
        )
        nls_file.write_text(
            json.dumps({"appTitle": {"message": "Hello", "comment": ["x"]}}),
            encoding="utf-8",
        )

        result = resolve_vsc_ext_name(pkg_json, "ext-id")
        assert result == "ext-id"
        # Must NOT leak a Python dict repr
        assert "{" not in result
        assert "message" not in result

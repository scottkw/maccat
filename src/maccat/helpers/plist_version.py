"""Shared plist version helper — VER-03 / VER-04.

Reads a version string from a macOS app bundle's Info.plist using stdlib
``plistlib`` (handles both XML and binary plists natively).

Shared by SetappCollector and WebAppsCollector to avoid duplicating the
same plist-read + key-precedence + graceful-degradation logic in both
collectors.

Key precedence (per 22-CONTEXT.md §.app version extraction decisions):
    1. CFBundleShortVersionString  (human-readable marketing version, e.g. "3.8.4")
    2. CFBundleVersion             (build number / bundle version, e.g. "42")
    3. ""                          (neither key present, or any error)

Never raises — returns "" on any failure so callers can use truthiness
to detect absence without special-casing errors.
"""
from __future__ import annotations

import plistlib
from pathlib import Path


def get_plist_version(path: Path) -> str:
    """Return the version string from a macOS Info.plist file.

    Args:
        path: Filesystem path to the Info.plist file (XML or binary).

    Returns:
        The version string, or "" if the version cannot be determined.
        Never raises an exception.

    Examples:
        >>> get_plist_version(Path("/Applications/Foo.app/Contents/Info.plist"))
        '3.8.4'
        >>> get_plist_version(Path("/nonexistent.plist"))
        ''
    """
    try:
        # is_file() + stat() are syscalls that can race (TOCTOU) with an app
        # update unlinking the file mid-scan — keep them inside the guard so a
        # FileNotFoundError still degrades to "" (never raises).
        if not path.is_file() or path.stat().st_size == 0:
            return ""
        with path.open("rb") as fh:
            data = plistlib.load(fh)
    except Exception:  # noqa: BLE001 — catches plistlib.InvalidFileException,
        # OSError, PermissionError, struct.error, and any other parse failure
        return ""

    # A valid plist root may be a list/str/number, not a dict — only a dict
    # carries the version keys. Anything else degrades to "" (never raises).
    if not isinstance(data, dict):
        return ""

    # Key precedence: CFBundleShortVersionString > CFBundleVersion.
    # Truthiness skips an explicitly-empty value so it falls through to the next key.
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        value = data.get(key)
        if value:
            return str(value)

    return ""

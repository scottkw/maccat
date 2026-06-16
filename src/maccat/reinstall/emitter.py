"""Reinstall script emitter — renders a ParsedCatalog into a complete reinstall.sh string.

This module makes no process calls: it builds the script text entirely in Python and
returns a str. The caller (Phase 26) writes the string to disk and sets mode 0o644;
it is never auto-executed.

Injection-safety design (two-function gate):
- quote_for_script(): the SOLE path catalog-derived values enter shell command position.
  Wraps shlex.quote(), which neutralizes all shell metacharacters.
- safe_comment_value(): the SOLE path catalog-derived values enter # comment context.
  Strips embedded newlines — shlex.quote() preserves newlines inside single-quotes, and
  a newline in a # cataloged: comment would break the comment line and expose the text
  after the newline as a live shell command.
"""
from __future__ import annotations

import shlex
from collections.abc import Callable

from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection

# ---------------------------------------------------------------------------
# Injection-safety helpers
# ---------------------------------------------------------------------------


def quote_for_script(value: str) -> str:
    """Wrap shlex.quote — the SOLE path catalog values enter shell command position.

    Use this for every catalog-derived value in a shell argument context.
    Do NOT use this for # comment context — use safe_comment_value() instead.
    """
    return shlex.quote(value)


def safe_comment_value(value: str) -> str:
    """Strip embedded newlines before inserting a value into a # comment.

    shlex.quote() neutralizes metacharacters in command position but does NOT
    strip embedded newlines. A newline inside a single-quoted token is
    syntactically valid bash (the shell reads across the line break), but when
    that same value appears in a # cataloged: comment, the newline ends the
    comment and exposes the remainder as a live shell command.

    This is the ONLY path a catalog value may reach comment (non-command) context.
    """
    return value.replace("\n", " ").replace("\r", " ")


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _should_skip(section: ParsedSection) -> bool:
    """Return True for degraded sections and legitimately empty sections.

    Handles both the WR-05 header section ("Installed Mac Software List" with
    items=[], degraded=False) and any degraded source section (items may be empty,
    degraded=True).  The parser does not filter these; the emitter skips them here.
    """
    return section.degraded or len(section.items) == 0


def _checklist_display(item: ParsedItem) -> str:
    """Return the display string for a manual checklist item.

    Format: '  - name (version)' when version is present, '  - name' otherwise.
    Both name and version pass through safe_comment_value to strip any embedded
    newlines before they reach the echo argument context.
    """
    name = safe_comment_value(item.name)
    if item.version:
        return f"  - {name} ({safe_comment_value(item.version)})"
    return f"  - {name}"


def _brew_block(section: ParsedSection) -> str:
    """Render Homebrew Packages section as universal idempotency guard lines.

    Each item emits:
      brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n>
    where <n> = quote_for_script(item.name).  An optional '# cataloged: <version>'
    comment is appended when the item has a version.

    A section-top NOTE warns that a name which is both a formula and a cask may
    need explicit --formula or --cask disambiguation.
    """
    lines: list[str] = [
        'echo "=== Homebrew Packages ==="',
        "# NOTE: A name that is both a formula and a cask may need explicit --formula or"
        " --cask; brew install auto-detects in most cases.",
    ]
    for item in section.items:
        n = quote_for_script(item.name)
        # Graceful degradation: a genuine `brew install` failure (network error,
        # renamed/removed formula, formula-vs-cask ambiguity) must NOT abort the
        # rest of the restore under `set -Eeuo pipefail`. The trailing
        # `|| echo WARN` neutralizes the non-zero exit of the install while still
        # surfacing the failure. (`brew list` returning non-zero for a not-yet-
        # installed package is expected and consumed by the `||` chain.)
        warn = quote_for_script(f"  WARN: brew install failed: {item.name}")
        guard = (
            f"brew list {n} &>/dev/null || brew list --cask {n} &>/dev/null"
            f" || brew install {n} || echo {warn}"
        )
        if item.version:
            guard += f"  # cataloged: {safe_comment_value(item.version)}"
        lines.append(guard)
    return "\n".join(lines)


def _mas_block(section: ParsedSection) -> str:
    """Render App Store Applications section.

    Items with an id emit 'mas install <id>  # cataloged: <version> — <name>'.
    Items without an id (pre-MAS-01 catalogs) appear in an inline manual checklist
    under an 'App Store Applications (no ID — install manually):' heading.
    """
    auto_lines: list[str] = []
    manual_items: list[ParsedItem] = []

    for item in section.items:
        if item.id is not None:
            qid = quote_for_script(item.id)
            # mas list rows begin with the numeric id followed by whitespace.
            # `mas install` returns non-zero when the app is already installed or
            # the user is not signed in; guarding with `command -v mas` + a
            # `mas list | grep -q` idempotency check (and consuming the non-zero
            # exit via && short-circuit / ! negation) keeps re-runs from aborting
            # the whole script under `set -Eeuo pipefail`. Mirrors the editor guard.
            grep_pat = quote_for_script(f"^{item.id} ")
            line = (
                f"command -v mas >/dev/null && "
                f"! mas list | grep -q {grep_pat} && "
                f"mas install {qid}"
            )
            if item.version:
                line += (
                    f"  # cataloged: {safe_comment_value(item.version)}"
                    f" — {safe_comment_value(item.name)}"
                )
            else:
                line += f"  # cataloged: {safe_comment_value(item.name)}"
            auto_lines.append(line)
        else:
            manual_items.append(item)

    lines: list[str] = ['echo "=== App Store Applications ==="']
    lines.extend(auto_lines)

    if manual_items:
        lines.append(
            'echo "App Store Applications (no ID — install manually):"'
        )
        for item in manual_items:
            lines.append(f"echo {shlex.quote(_checklist_display(item))}")

    return "\n".join(lines)


def _editor_ext_block(section: ParsedSection, *, editor: str) -> str:
    """Render a VS Code or Cursor extension section.

    Each item with an id emits a three-part &&-chain guard:
      command -v <editor> >/dev/null &&
      ! <editor> --list-extensions | grep -qi '^<id>$' &&
      <editor> --install-extension <id>

    The marketplace id is lowercased before quoting (canonical form).
    Items without an id fall back to an echo checklist line.
    An optional '# cataloged: <version>' comment is appended when present.

    Note (WR-03): the 'echo "=== <title> ==="' banner is emitted unconditionally,
    even when the editor is absent on the target machine (every guard line then
    short-circuits at `command -v <editor>`). An empty banner with no install
    output therefore means the editor was not installed — this is intentional and
    keeps the renderer's structure parallel with the brew/mas blocks rather than
    duplicating the per-line `command -v` guard at the section level.
    """
    lines: list[str] = [f'echo "=== {section.title} ==="']
    for item in section.items:
        if item.id is None:
            lines.append(f"echo {shlex.quote(_checklist_display(item))}")
            continue
        low_id = item.id.lower()
        install_id = quote_for_script(low_id)
        grep_pat = quote_for_script(f"^{low_id}$")
        line = (
            f"command -v {editor} >/dev/null && "
            f"! {editor} --list-extensions | grep -qi {grep_pat} && "
            f"{editor} --install-extension {install_id}"
        )
        if item.version:
            line += f"  # cataloged: {safe_comment_value(item.version)}"
        lines.append(line)
    return "\n".join(lines)


def _manual_checklist_block(section: ParsedSection) -> str:
    """Render a manual-checklist section as echo statements.

    Format:
      echo 'SectionTitle:'
      echo '  - item name (version)'
      ...
    The echo arguments are shlex.quote()-wrapped so item text cannot break the script.
    """
    lines: list[str] = [f"echo {shlex.quote(section.title + ':')}"]
    for item in section.items:
        lines.append(f"echo {shlex.quote(_checklist_display(item))}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section routing map
# ---------------------------------------------------------------------------

SECTION_SOURCE_MAP: dict[str, Callable[[ParsedSection], str]] = {
    "Homebrew Packages": _brew_block,
    "App Store Applications": _mas_block,
    "VS Code Extensions": lambda section: _editor_ext_block(section, editor="code"),
    "Cursor Extensions": lambda section: _editor_ext_block(section, editor="cursor"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_reinstall_script(
    catalog: ParsedCatalog,
    *,
    source_name: str,
    generated: str,
) -> str:
    """Render a ParsedCatalog into a complete reinstall.sh script string.

    Args:
        catalog:     Parsed catalog from reinstall.parser.parse_catalog().
        source_name: Human-readable catalog filename for the provenance header.
                     Embedded newlines are stripped (safe_comment_value).
        generated:   Generation date string for the provenance header
                     (e.g. "2026-06-16").

    Returns:
        Complete script string starting with '#!/usr/bin/env bash'.
        Guaranteed to pass bash -n (syntax check).
        Every catalog-derived value in command position is shlex.quote()-wrapped
        via quote_for_script().  Values in # comment context pass through
        safe_comment_value() to strip embedded newlines.
        No process calls are made — this function is pure text construction.
    """
    header = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -Eeuo pipefail",
            "",
            f"# Generated from: {safe_comment_value(source_name)}",
            f"# Generated on:   {safe_comment_value(generated)}",
            "# Review this script before running — it is NOT auto-executed.",
            "",
        ]
    )

    blocks: list[str] = [header]
    manual_sections: list[ParsedSection] = []

    for section in catalog.sections:
        if _should_skip(section):
            continue
        renderer = SECTION_SOURCE_MAP.get(section.title)
        if renderer is not None:
            blocks.append(renderer(section))
        else:
            manual_sections.append(section)

    if manual_sections:
        blocks.append('echo ""')
        blocks.append('echo "=== Manual Checklist ==="')
        blocks.append('echo "The following items require manual installation."')
        for section in manual_sections:
            blocks.append(_manual_checklist_block(section))

    return "\n\n".join(blocks) + "\n"

---
phase: 30-markdown-emitter-md-plumbing
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/maccat/catalog/markdown.py
  - src/maccat/catalog/writer.py
  - src/maccat/cli.py
  - src/maccat/naming.py
  - src/maccat/retention.py
  - src/maccat/identity.py
  - src/maccat/reinstall/picker.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-06-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 30 introduces a markdown catalog emitter (`markdown.py`), migrates all file-path patterns to `.md`, and wires the emitter into the CLI. The `.txt` → `.md` glob migration is complete and consistent across `naming.py`, `retention.py`, `identity.py`, and `reinstall/picker.py`. The emitter's table-rendering logic is correct for the full range of collector output shapes (brew, mas, setapp, extension collectors). Determinism is maintained: `render_frontmatter` uses fixed key order, `flush_section` delegates to `LC_ALL=C sort -f -u` for non-raw sections, and raw sections preserve collector-native order.

One critical bug breaks the Phase 31 round-trip contract: the YAML frontmatter embeds `computer` and `hostname` as bare unquoted scalars, but `validate_computer_name` permits colons in computer names, and `socket.gethostname()` is used without any sanitization. A colon followed by a space in either value produces structurally invalid YAML that every compliant parser will reject with `ScannerError`. This was demonstrated experimentally.

Two warnings follow: a missing backslash-before-pipe escape in `_escape_cell` (low real-world frequency but specification non-compliance that will bite on round-trip parse), and a stale `.txt` extension in the `CatalogWriter` docstring example (migration artifact).

## Critical Issues

### CR-01: YAML frontmatter injection — unquoted `computer` and `hostname` scalars

**File:** `src/maccat/catalog/markdown.py:126-132`

**Issue:** `render_frontmatter` embeds `computer` and `hostname` as bare unquoted YAML scalars. `validate_computer_name` explicitly allows colons (only `/`, `[`, `]`, tab, and newline are rejected). A computer name such as `"My: Work"` produces:

```yaml
computer: My: Work
```

A compliant YAML parser raises `ScannerError: mapping values are not allowed here` on this line. Phase 31 (the planned catalog round-trip parser) will fail to ingest any catalog written with such a computer name. The same failure applies to `hostname`: `socket.gethostname()` is passed directly without any sanitisation, and a hostname such as `my-host: 1` (legal `/etc/hostname` content on macOS) produces the identical breakage. Only `generated` is currently double-quoted; `computer`, `hostname`, and `maccat_version` are not.

Verified experimentally:

```python
import yaml
yaml.safe_load("hostname: my-host: 1")
# yaml.scanner.ScannerError: mapping values are not allowed here
yaml.safe_load("computer: My: Work")
# yaml.scanner.ScannerError: mapping values are not allowed here
```

**Fix:** Double-quote all four scalar values in `render_frontmatter`, matching the existing `generated` treatment. Backslash-escape any embedded double-quote in the value so the YAML remains valid:

```python
def _yaml_quote(value: str) -> str:
    """Wrap value in double quotes, escaping embedded double-quotes and backslashes."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

def render_frontmatter(
    computer: str,
    hostname: str,
    generated: str,
    maccat_version: str,
) -> str:
    return (
        "---\n"
        f"computer: {_yaml_quote(computer)}\n"
        f"hostname: {_yaml_quote(hostname)}\n"
        f'generated: "{generated}"\n'
        f"maccat_version: {_yaml_quote(maccat_version)}\n"
        "---\n"
    )
```

If maintaining the current unquoted style for `maccat_version` is desired (version strings are safe), at minimum `computer` and `hostname` must be quoted, as those are the values that accept arbitrary user/system content.

---

## Warnings

### WR-01: `_escape_cell` does not escape backslash before pipe — breaks table on `\|` in cell values

**File:** `src/maccat/catalog/markdown.py:67-73`

**Issue:** `_escape_cell` replaces `|` with `\|` but does not first escape backslash characters. When a cell value contains a literal `\|` (backslash immediately followed by pipe), the replacement turns it into `\\|`. In CommonMark, `\\` is an escaped backslash (renders as `\`), and the following `|` is then a bare unescaped pipe that the parser treats as a column delimiter — the table structure breaks despite `_escape_cell` being called.

Concrete example: a cell value `a\|b` (4 chars: `a`, `\`, `|`, `b`) after `_escape_cell`:

```
a\\|b   ← \\ = escaped backslash (literal \), then bare | splits the column
```

Although backslash-pipe combinations are rare in macOS tool names, they can appear in:
- MCP server names from `~/.claude.json` (JSON object keys — no constraints on content)
- Skill/agent names read from YAML frontmatter `name:` fields

This is a specification non-compliance that will produce a silently broken table without any error raised. It will also cause the Phase 31 parser to read wrong column data for affected rows.

**Fix:**

```python
def _escape_cell(value: str) -> str:
    """Escape backslashes and pipe characters in a table cell value."""
    return value.replace("\\", "\\\\").replace("|", r"\|")
```

Backslash must be escaped first; reversing the order would double-escape the newly introduced backslashes.

---

### WR-02: Stale `.txt` extension in `CatalogWriter` docstring (migration artifact)

**File:** `src/maccat/catalog/writer.py:25`

**Issue:** The class docstring example still uses a `.txt` extension after the phase 30 `.txt` → `.md` migration:

```python
with CatalogWriter(Path("MyMac/catalog-2026.txt")) as w:
```

This contradicts every other reference in the codebase (naming conventions, glob patterns, `_FILENAME_RE`) and will mislead the next developer reading the class-level documentation. It also means the docstring no longer round-trips: `parse_catalog_filename` applied to `"catalog-2026.txt"` returns `None`.

**Fix:** Update the example to use the correct naming convention:

```python
with CatalogWriter(Path("MyMac/mac-software-list-[MyMac]-20260618120000.md")) as w:
```

---

## Info

### IN-01: `prune_old_archives` prints a spurious message on normal first run

**File:** `src/maccat/retention.py:113-115`

**Issue:** When the archive directory does not yet exist (expected on first run of any computer folder), `prune_old_archives` prints:

```
  No archive directory found — nothing to prune.
```

This appears as normal output on every first run and every run before 60+ days of catalogs have accumulated. It is not a warning condition; it is the expected steady-state for new installs. The message creates noise and may mislead users into thinking something is wrong.

**Fix:** Return silently when the archive directory is absent — no print needed. Only print if an archive directory exists but is unreadable (that would be a genuine warning):

```python
def prune_old_archives(archive_dir: Path, archive_days: int) -> None:
    if not archive_dir.is_dir():
        return   # normal: no archives yet
    ...
```

---

_Reviewed: 2026-06-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

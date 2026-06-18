# Phase 30: Markdown Emitter & `.md` Plumbing — Research

**Researched:** 2026-06-18
**Domain:** Python stdlib, catalog format change, file glob/retention, git staging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Frontmatter is a standard `---`-fenced YAML block at the very top of the file.
- Frontmatter keys are snake_case: `computer`, `hostname`, `generated`, `maccat_version`.
- `generated` value is an ISO-8601 local timestamp (e.g. `2026-06-18T12:34:56`).
- The `#` title text stays `# Installed Mac Software List`.
- Each source renders as a `##` heading followed by a three-column markdown table with the
  header row `Name | Version | ID` (exact casing per MD-03).
- A missing version or ID renders as an empty, space-padded cell — no `-`/`—` placeholder.
- A literal `|` appearing in any cell value is escaped as `\|`.
- **Raw sections (Homebrew formulae/casks, mas) render as the same 3-column table** — their
  current verbatim lines are split into name / version / ID columns.
- A source with no items renders a plain `(none found)` line under its `##` heading — no empty
  table (MD-04).
- Section order preserves the current collector-registry order (no reordering).
- Items within a table keep the existing `LC_ALL=C sort -f -u` ordering/dedup for non-raw
  sections. Raw sections keep their natural ordering. Do NOT switch to Python built-in sort.
- One blank line precedes each `##` heading for clean markdown rendering.
- Two consecutive runs must produce byte-identical `.md` output modulo the `generated` timestamp.
- Filename target: `mac-software-list-[computer]-YYYYMMDDHHMMSS.md`.
- A stray legacy `.txt` in a folder must be ignored by `.md` retention.

### Claude's Discretion

- Exact module layout for the markdown emitter (extend `catalog/format.py` vs a new
  `catalog/markdown.py`).
- The YAML-serialization approach (hand-rolled vs minimal), guided by stdlib-only constraint.
- How CatalogWriter / generate loop in `cli.py` is adapted.

### Deferred Ideas (OUT OF SCOPE)

- Reinstall parser reading the markdown format and the round-trip contract test — Phase 31.
- `maccat convert --from PATH` upgrading legacy `.txt` catalogs — Phase 32.
- Bulk/folder-wide conversion, dual-format reinstall, per-source variable columns, JSON/HTML
  output — explicitly out of scope for v3.0.0.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MD-01 | Catalog generation writes `.md` file; filename pattern `mac-software-list-[computer]-YYYYMMDDHHMMSS.md` | `naming.py` extension change: `_FILENAME_RE` regex + `make_catalog_filename()` |
| MD-02 | Catalog opens with YAML frontmatter (computer, hostname, generated, maccat_version) + `# Installed Mac Software List` title | Hand-rolled YAML; `socket.gethostname()` for hostname; `datetime.now()` for generated; `maccat.__version__` for version |
| MD-03 | Every source renders as `##` section + 3-column `Name \| Version \| ID` table; empty cell for missing values | All collector items are either `emit_item`-shaped or Homebrew-shaped; both parse cleanly via `ITEM_RE`-style regex |
| MD-04 | Empty source renders `(none found)` under its `##` heading | Items=[] path: write `(none found)` plain line instead of empty table |
| MD-05 | Deterministic + stably sorted; never contains secrets (FMT-01/03/04 upheld) | Sort discipline preserved; FMT-03 invariant lives in collectors, not the emitter |
| FILE-01 | Newest-per-computer retention + archive prune on `.md` (`.txt` glob replaced, not duplicated) | Three `.txt` glob sites in `retention.py` (lines 64, 75, 118); one in `identity.py` (line 158); one in identity `rename_machine` (line 549) |
| FILE-02 | git pull → generate → commit/push stages `.md`; `--no-commit` still skips git | `gitops.git_commit_and_push` uses `git add -A -- {computer}/` which is extension-agnostic — no change needed there; but `naming.py` drives the filename the commit message references |
</phase_requirements>

---

## Summary

This phase is a format-only change: the output of `maccat generate` moves from plain text to a
markdown file. The 22 data sources, the collector interfaces, and the orchestration order are
all unchanged. The changes are narrowly scoped to six files: `naming.py`, `retention.py`,
`identity.py`, `cli.py`, a new (or extended) markdown emitter module, and the test suite.

The central design question — how to get structured name/version/id columns from collector
items — is resolved by the existing `ITEM_RE` regex in `reinstall/parser.py`. All collector
items are either `emit_item`-shaped strings (name, name (ver), name [id], name (ver) [id]) or
Homebrew-shaped strings (name (ver), name (ver1 ver2 ...)). The same right-anchored regex that
the reinstall parser already uses cleanly extracts name/version/id from every item line. The
markdown emitter therefore re-parses each pre-formatted string into three columns rather than
threading new structured data through all 16 collectors.

The `.txt`-keyed behavior lives in five glob sites: three in `retention.py`, one in the computer
folder discovery in `identity.py`, and one in the `rename_machine` rewrite loop in `identity.py`.
All five must be updated to `.md`. The `gitops.py` staging command `git add -A -- {computer}/`
is extension-agnostic and requires no change. `CatalogWriter` is format-agnostic (it writes
whatever bytes are handed to it) and needs no structural change.

**Primary recommendation:** Create `src/maccat/catalog/markdown.py` as a thin, pure module
(no subprocess calls, no side effects) that provides `render_markdown_catalog()`. The `cli.py`
generate loop replaces the current `CatalogWriter` + `write_section` / `write_lines` calls with
a single call to `render_markdown_catalog()` that returns the full string, then hands it to
`CatalogWriter` as `w.write_raw(content)` (or writes via the file handle directly). This keeps
the format logic co-located and trivially testable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Markdown rendering (frontmatter + table building) | New `catalog/markdown.py` module | — | Pure formatting logic; isolated from I/O for testability |
| Filename pattern (`.md` extension) | `naming.py` | — | Single source of truth for filename pattern |
| File-level retention + archive glob | `retention.py` | — | Owns the two-pass sweep and the archive prune |
| Computer folder discovery glob | `identity.py` | — | `discover_computer_folders()` glob at line 158 |
| Rename-machine file rewrite glob | `identity.py` | — | `rename_machine()` glob at line 549 |
| Orchestration (catalog generation) | `cli.py` | — | Calls naming, CatalogWriter, collectors, retention, gitops |
| Git staging | `gitops.py` | — | Extension-agnostic `git add -A -- {computer}/` — no change needed |
| Test coverage for format change | `tests/test_naming.py`, `tests/test_cli.py`, new `tests/test_markdown_emitter.py` | — | Must update `.txt`-anchored assertions |

---

## Standard Stack

### Core (stdlib only — no new dependencies)
| Module | Purpose |
|--------|---------|
| `re` | Already used in `reinstall/parser.py` for `ITEM_RE`; reuse same regex in markdown emitter to split item lines |
| `socket` | `socket.gethostname()` — already used in `identity.py` (line 209) for hostname |
| `datetime` | `datetime.now()` for `generated` ISO-8601 timestamp — already used in `cli.py` |
| `subprocess` | `flush_section()` already uses `LC_ALL=C sort -f -u`; unchanged |

No new packages. `pyproject.toml` stays: `# Zero runtime deps — stdlib only`. [VERIFIED: pyproject.toml inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
Collector.collect()
   ↓ Section.items (list[str]: emit_item strings or Homebrew strings)
render_markdown_catalog(sections, *, computer, hostname, generated, maccat_version)
   ├── render_frontmatter()      → "---\n...\n---\n"
   ├── render_title()             → "# Installed Mac Software List\n"
   └── for each Section:
         ├── render_section_heading(title)  → "\n## title\n"
         ├── if section.raw=True and items are degradation lines → "(none found)\n"
         ├── if not items (after flush) → "(none found)\n"
         ├── else → render_table(items, raw=section.raw)
         │     ├── "| Name | Version | ID |\n| --- | --- | --- |\n"
         │     └── for each item:
         │           ├── parse_item_to_columns(line) → (name, version, id)
         │           └── "| {name} | {version} | {id} |\n"
         └── (non-raw: flush_section sort+dedup BEFORE table render)
   ↓
str (complete .md content)
   ↓
CatalogWriter.write_raw(content)  (new method, or direct fh.write)
   ↓
mac-software-list-[computer]-YYYYMMDDHHMMSS.md   (atomic tmp+rename)
```

### Recommended Module Structure

```
src/maccat/catalog/
├── format.py        # unchanged: emit_item, flush_section, version_sort_tail
├── writer.py        # minor: add write_raw(content: str) method or reuse write_lines
└── markdown.py      # NEW: render_markdown_catalog(), render_frontmatter(), render_table()
```

### Pattern 1: Hand-Rolled YAML Frontmatter (stdlib-only)

**What:** Write the four frontmatter keys as fixed-order plain strings wrapped in `---` fences.

**Why not PyYAML:** The project mandates stdlib-only. PyYAML is not installed in the project
venv. [VERIFIED: `venv/bin/pip list` — no `PyYAML` entry]

**YAML safety analysis:** [VERIFIED: direct Python testing]
- `computer`: validated by `validate_computer_name()` — excludes `[`, `]`, `/`; spaces allowed but safe as bare YAML scalars.
- `hostname`: `socket.gethostname()` — dots OK, no YAML-special characters in practice.
- `maccat_version`: semantic version string `2.1.0` — safe.
- `generated`: ISO-8601 `2026-06-18T12:34:56` — contains `:` characters. In YAML 1.1 (used by PyYAML default), this is auto-cast to a datetime object. **Must be double-quoted** to ensure round-trip safety for the Phase 31 parser.

**Implementation:** [ASSUMED — pattern derived from codebase conventions, not an external doc]

```python
# Source: catalog/markdown.py (new file)
def render_frontmatter(
    computer: str,
    hostname: str,
    generated: str,
    maccat_version: str,
) -> str:
    """YAML frontmatter block. Keys in fixed order for byte-determinism.
    generated is double-quoted to prevent YAML 1.1 datetime auto-cast.
    """
    return (
        "---\n"
        f"computer: {computer}\n"
        f"hostname: {hostname}\n"
        f'generated: "{generated}"\n'
        f"maccat_version: {maccat_version}\n"
        "---\n"
    )
```

Key invariant: fixed key order + fixed quoting = byte-deterministic across repeated runs.

### Pattern 2: Splitting Item Lines into Name/Version/ID Columns

**What:** The markdown table needs three columns; collector items are pre-formatted strings.
The cleanest approach is a re-parse using the existing `ITEM_RE` from `reinstall/parser.py`.

**Why re-parse rather than thread structured data through collectors:** Threading would require
changing all 16 collector modules and the `Section` dataclass. Re-parsing adds one regex call
per item, which is negligible. The regex already handles all six `emit_item` shapes and all
Homebrew multi-version shapes. Phase 31 will re-use the same logic for the round-trip contract.

**All item shapes and parse results:** [VERIFIED: direct Python testing with ITEM_RE]

| Item line (example) | Source | name | version | id |
|---|---|---|---|---|
| `git (2.44.0)` | Homebrew | `git` | `2.44.0` | — |
| `python@3.11 (3.11.1 3.11.2)` | Homebrew multi-version | `python@3.11` | `3.11.1 3.11.2` | — |
| `git` | Homebrew (no version) | `git` | — | — |
| `Final Cut Pro (10.7.1) [424389933]` | mas via emit_item | `Final Cut Pro` | `10.7.1` | `424389933` |
| `Final Cut Pro (10.7.1)` | emit_item name+version | `Final Cut Pro` | `10.7.1` | — |
| `Final Cut Pro [424389933]` | emit_item name+id | `Final Cut Pro` | — | `424389933` |
| `Final Cut Pro` | emit_item name only | `Final Cut Pro` | — | — |
| `com.app.id` | emit_item id-promoted | `com.app.id` | — | — |
| `AppName.app (1.2.3)` | Setapp/WebApps | `AppName.app` | `1.2.3` | — |
| `AppName.app` | Setapp/WebApps (no ver) | `AppName.app` | — | — |
| `server-name [stdio]` | MCP emit_item name+id | `server-name` | — | `stdio` |

**Degradation lines** (e.g. `"Homebrew is not installed."`, `"mas (Mac App Store CLI) is not installed."`) are never rendered as table rows. They signal a degraded section and the emitter must render `(none found)` instead.

**`DEGRADATION_LINES` frozenset** already exists in `reinstall/parser.py` — import it or duplicate it in `markdown.py` (duplication preferred to avoid coupling markdown emitter to reinstall module).

```python
# Source: catalog/markdown.py (new file)
import re

# Re-use same regex shape as reinstall/parser.py ITEM_RE
_ITEM_RE = re.compile(
    r"^(?P<name>.+?)"
    r"(?:\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"
    r"|\s+\((?P<version2>[^)]+)\)"
    r"|\s+\[(?P<id2>[^\]]+)\])?"
    r"\s*$"
)

def _parse_columns(line: str) -> tuple[str, str, str]:
    """Return (name, version, id_) from an emit_item-shaped or Homebrew-shaped line.
    All three values are strings; empty string for missing version/id.
    """
    m = _ITEM_RE.match(line)
    if not m:
        return line, "", ""
    name = m.group("name") or ""
    version = m.group("version") or m.group("version2") or ""
    id_ = m.group("id") or m.group("id2") or ""
    return name, version, id_
```

### Pattern 3: Pipe Escaping for Table Cells

**What:** Any `|` in a cell value must be rendered as `\|` to prevent table column breaks.

```python
def _escape_cell(value: str) -> str:
    return value.replace("|", r"\|")
```

**Empty cell convention:** A missing version or ID renders as a single space `" "` (space-padded), not an empty string, to satisfy the CONTEXT.md decision. [ASSUMED — "space-padded" means at least one space character in the cell]

### Pattern 4: Table Rendering

```python
# Source: catalog/markdown.py (new file)
def _render_table(items: list[str]) -> str:
    """Render a list of item lines as a 3-column markdown table.
    items must already be sorted (flush_section applied by caller for non-raw).
    Returns "" if items is empty (caller handles (none found) sentinel).
    """
    rows: list[str] = [
        "| Name | Version | ID |",
        "| --- | --- | --- |",
    ]
    for line in items:
        name, version, id_ = _parse_columns(line)
        rows.append(
            f"| {_escape_cell(name)} | {_escape_cell(version) or ' '} | {_escape_cell(id_) or ' '} |"
        )
    return "\n".join(rows) + "\n"
```

### Pattern 5: `(none found)` for Empty / Degraded Sections

**Trigger:** `flush_section([])` returns `["  (none found)"]` — the emitter intercepts items
that are empty OR consist entirely of known degradation lines.

```python
# In render_markdown_catalog:
if not items or all(line in _DEGRADATION_LINES for line in items):
    section_parts.append("(none found)\n")
else:
    if not section.raw:
        items = flush_section(items)   # sort + dedup
    section_parts.append(_render_table(items))
```

Note: the `(none found)` plain text line is written WITHOUT the two-space indent that the
plain-text format used (`"  (none found)"`). This is a new format — the markdown convention
is just `(none found)` as a paragraph under the heading.

### Pattern 6: `CatalogWriter.write_raw()` (new method)

The current `CatalogWriter` exposes `write_section(title)` and `write_lines(lines)`. The
markdown emitter produces the complete file content as a single string. Two options:

**Option A — add `write_raw(content: str)` to `CatalogWriter`:**
```python
def write_raw(self, content: str) -> None:
    assert self._fh is not None
    self._fh.write(content)
```

**Option B — pass the open file handle to the emitter.** More coupling; Option A preferred.

**Option C — replace CatalogWriter usage in `cli.py` entirely.** The atomic tmp+rename logic
is the only value CatalogWriter adds; preserving it by keeping CatalogWriter and adding
`write_raw` is the minimal, safest change.

**Recommendation: Option A** — add `write_raw()` to `CatalogWriter`. [ASSUMED]

### Pattern 7: `render_markdown_catalog()` Signature

```python
def render_markdown_catalog(
    sections: list[Section],           # from collector results
    *,
    computer: str,
    hostname: str,
    generated: str,                    # 14-digit YYYYMMDDHHMMSS or ISO-8601
    maccat_version: str,
) -> str:
    """Return the complete .md catalog content as a single string."""
```

**`generated` for frontmatter:** The filename uses `YYYYMMDDHHMMSS`; the frontmatter uses
`ISO-8601 local`. Both are derived from the same `datetime.now()` call in `cli.py`:
```python
now = datetime.now()
timestamp = now.strftime("%Y%m%d%H%M%S")      # for filename
generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")   # for frontmatter
```

### Pattern 8: `cli.py` Generate Loop Change

Current (plain-text):
```python
with CatalogWriter(output_file) as w:
    w.write_section("Installed Mac Software List")
    for collector in get_registry():
        result = collector.collect()
        for section in result.sections:
            w.write_section(section.title)
            if section.raw:
                w.write_lines(section.items)
            else:
                w.write_lines(flush_section(section.items))
```

New (markdown):
```python
from maccat.catalog.markdown import render_markdown_catalog

now = datetime.now()
timestamp = now.strftime("%Y%m%d%H%M%S")
generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
hostname = socket.gethostname()

all_sections: list[Section] = []
for collector in get_registry():
    result = collector.collect()
    all_sections.extend(result.sections)

content = render_markdown_catalog(
    all_sections,
    computer=computer,
    hostname=hostname,
    generated=generated_iso,
    maccat_version=__version__,
)

filename = make_catalog_filename(computer, timestamp)   # now .md
output_file = catalog_repo / computer / filename
(catalog_repo / computer).mkdir(parents=True, exist_ok=True)

with CatalogWriter(output_file) as w:
    w.write_raw(content)
```

Note: `socket` must be imported in `cli.py` (deferred import block, or top-level since it's stdlib).

### Anti-Patterns to Avoid

- **Threading structured data through collectors:** Do not change `Section.items` to `list[tuple[str, str, str]]`. The re-parse approach is correct; changing the collector interface would cascade across 16 modules and all their tests.
- **Duplicating `flush_section` inside the markdown emitter:** Call `flush_section()` from `catalog.format` for non-raw sections exactly as before — the sort/dedup is the same operation.
- **PyYAML or any third-party YAML library:** Not available in the project venv; not to be added.
- **Python `sorted()` instead of `flush_section()`:** Explicitly prohibited by the codebase — `LC_ALL=C sort -f -u` subprocess is mandatory.
- **Using `json.dumps` for frontmatter:** JSON is not YAML; values would be JSON-escaped strings. Use plain string f-formatting.
- **Keeping `.txt` glob active in retention:** FILE-01 says replaced, not duplicated. Legacy `.txt` files become invisible to retention (not deleted, not moved — simply not seen by the `.md` glob).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Item line → name/version/id split | New bespoke parser | `ITEM_RE` from `reinstall/parser.py` (duplicate, don't import) | Already proven against all emit_item shapes and Homebrew multi-version; tested in `test_parser_contract.py` |
| Sort + dedup of non-raw items | Python `sorted()` | `flush_section()` from `catalog.format` | LC_ALL=C byte-parity invariant; Python sort diverges for mixed-case names |
| YAML serialization | PyYAML / hand-rolled YAML encoder | Direct f-string with fixed key order and `"..."` for generated | Values have no YAML-unsafe characters except generated (quoted); no library needed |
| Atomic write | Custom write-and-rename | `CatalogWriter` with new `write_raw()` method | Atomic tmp+rename already implemented and tested |

---

## Runtime State Inventory

Step 2.6 SKIPPED — this is a greenfield format-change phase with no external service state, no stored data mutations, no OS-registered state, and no secrets. The rename-machine flow touches `.txt` filenames at `identity.py:549` but that is a code change, not a data migration: files on disk will continue to be named `.txt` until the user runs `maccat convert` (Phase 32). Existing `.txt` catalogs are left untouched by `.md` retention.

---

## Common Pitfalls

### Pitfall 1: YAML 1.1 Datetime Auto-Cast on `generated`
**What goes wrong:** If the `generated` value is written as an unquoted bare scalar (`generated: 2026-06-18T12:34:56`), YAML 1.1 parsers (including PyYAML's `safe_load`) automatically coerce it to a Python `datetime` object, not a string. The Phase 31 parser would receive a `datetime`, not the string it expects.
**Why it happens:** YAML 1.1 has built-in type detection for ISO-8601 timestamps.
**How to avoid:** Always double-quote the `generated` value in the frontmatter: `generated: "2026-06-18T12:34:56"`.
**Warning signs:** Phase 31 parser test fails with `AttributeError: 'datetime.datetime' object has no attribute 'split'` or similar.

### Pitfall 2: Degradation Lines Written as Table Rows
**What goes wrong:** If `"Homebrew is not installed."` is passed to `_render_table()`, it is parsed as a name-only row and appears in the table — creating a confusing output like `| Homebrew is not installed. | | |`.
**Why it happens:** The markdown emitter doesn't distinguish degradation text from real item lines.
**How to avoid:** Before rendering, check if items consist entirely of known degradation lines (or a single `"  (none found)"` sentinel from `flush_section([])`); if so, write `(none found)` plain text under the heading.
**Warning signs:** Table rows containing sentences like "not installed" or "Install it with Homebrew".

### Pitfall 3: Forgetting the `identity.py` Glob Sites
**What goes wrong:** `retention.py` is updated to `.md` but `identity.py`'s two `.txt` glob sites are not. `discover_computer_folders()` (line 158) returns empty folders (no `.md` files match) so the computer picker shows no known computers; the rename rewrite loop (line 549) silently skips all files on rename.
**Why it happens:** `identity.py` is not mentioned in the `## Integration Points` list in CONTEXT.md.
**How to avoid:** Update both `identity.py` glob sites: line 158 (`discover_computer_folders`) and line 549 (`rename_machine` file rewrite).
**Warning signs:** After the change, `maccat --computer ExistingComputer` stops finding the pre-existing computer folders.

### Pitfall 4: Test Suite `.txt` Assertions
**What goes wrong:** `test_cli.py` contains five `glob("mac-software-list-*.txt")` assertions (lines 241, 290, 295, 334, 469). After the extension change these globs return empty lists and all five assertions fail.
**Why it happens:** The tests were written for `.txt`; they verify the generated file exists.
**How to avoid:** Update all five assertion globs to `mac-software-list-*.md`.
**Warning signs:** `test_cli.py` fails with `AssertionError: Expected at least one catalog file`.

### Pitfall 5: `test_naming.py` Hard-Codes `.txt`
**What goes wrong:** `test_naming.py` tests assert `result == "mac-software-list-[personal]-20260614120000.txt"` and similar. After the extension change these literal assertions fail.
**Why it happens:** The tests directly reference the `.txt` output format.
**How to avoid:** Update `test_naming.py` (and `conftest.py`'s `catalog_repo` fixture which calls `make_catalog_filename`) to `.md`.
**Warning signs:** `test_naming.py::TestMakeCatalogFilename::test_output_format` fails.

### Pitfall 6: `conftest.py` Catalog Fixture Stays `.txt`
**What goes wrong:** The `catalog_repo` fixture creates a `.txt` catalog file. After the `.md` regex change, `parse_catalog_filename()` returns `None` for this file. Tests using `catalog_repo` that rely on `discover_computer_folders()` will not find the computer folder.
**Why it happens:** `conftest.py:53` calls `make_catalog_filename` which now generates `.md` — so this is automatically fixed once `naming.py` is updated.
**How to avoid:** Update `naming.py` first; `conftest.py` and `test_retention.py` call `make_catalog_filename()` and inherit the change automatically. Only `test_cli.py`'s literal glob strings need manual updating.

### Pitfall 7: Raw Section Sort vs. Non-Raw
**What goes wrong:** Non-raw sections go through `flush_section()` (sort + dedup). Raw sections are written verbatim. If the markdown emitter applies `flush_section()` to raw sections, Homebrew and mas output is re-sorted in a different order from what the collectors intend.
**Why it happens:** The `section.raw` flag distinguishes the two paths; it must be respected in the markdown emitter exactly as the plain-text loop does.
**How to avoid:** In `render_markdown_catalog()`, apply `flush_section()` only to `not section.raw` sections; write raw section items as-is (after degradation-line check).

### Pitfall 8: Blank Line Before `##` Headings
**What goes wrong:** Missing blank line before `##` results in some markdown renderers treating the heading as body text; GitHub markdown requires the blank line before `##` when it follows content.
**Why it happens:** Forgetting the leading `\n` before each `##` section.
**How to avoid:** The CONTEXT.md decision states "One blank line precedes each `##` heading". Use `f"\n## {title}\n"` as the section heading (the `\n` before `##` provides the blank line when the previous section ends with `\n`).

---

## Code Examples

### Complete Frontmatter (verified byte-exact output)

```python
# Source: direct Python testing (verified 2026-06-18)
def render_frontmatter(computer, hostname, generated_iso, maccat_version):
    return (
        "---\n"
        f"computer: {computer}\n"
        f"hostname: {hostname}\n"
        f'generated: "{generated_iso}"\n'
        f"maccat_version: {maccat_version}\n"
        "---\n"
    )

# Example output:
# ---
# computer: MyMac
# hostname: my-mac.local
# generated: "2026-06-18T12:34:56"
# maccat_version: 2.1.0
# ---
```

### Table with Empty Cells (verified output)

```python
# Source: direct Python testing (verified 2026-06-18)
# Input: git (2.44.0)  -> name='git', version='2.44.0', id=''
# Input: Final Cut Pro (10.7.1) [424389933] -> name='Final Cut Pro', ...
# | git | 2.44.0 |   |
# | Final Cut Pro | 10.7.1 | 424389933 |
```

### Pipe-Escaping Edge Case

```python
# Source: direct Python testing (verified 2026-06-18)
# Input line: "foo | bar (1.0) [foo|bar]"
# parse -> name="foo | bar", version="1.0", id="foo|bar"
# After _escape_cell: "foo \| bar", "1.0", "foo\|bar"
# Output row: | foo \| bar | 1.0 | foo\|bar |
```

### `naming.py` Change (three-line diff)

```python
# Before:
_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)
# ...
return f"mac-software-list-[{machine}]-{timestamp}.txt"

# After:
_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.md$"
)
# ...
return f"mac-software-list-[{machine}]-{timestamp}.md"
```

### `retention.py` Change (three glob sites)

```python
# Lines 64, 75 (retain_newest_per_host):
# Before: for f in target_dir.glob("mac-software-list-*.txt"):
# After:  for f in target_dir.glob("mac-software-list-*.md"):

# Line 118 (prune_old_archives):
# Before: for f in archive_dir.glob("mac-software-list-*.txt"):
# After:  for f in archive_dir.glob("mac-software-list-*.md"):
```

### `identity.py` Change (two glob sites)

```python
# Line 158 (discover_computer_folders):
# Before: if any(d.glob("mac-software-list-*.txt")):
# After:  if any(d.glob("mac-software-list-*.md")):

# Line 549 (rename_machine rewrite loop):
# Before: for file_path in rewrite_dir.glob("mac-software-list-*.txt"):
# After:  for file_path in rewrite_dir.glob("mac-software-list-*.md"):
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Plain-text sections with `----` separator | Markdown with YAML frontmatter + `##` headings + tables | Phase 30 | Breaking format change — `.txt` catalogs not readable by new `reinstall` command |
| `.txt` filename extension | `.md` filename extension | Phase 30 | All retention/discovery globs updated |
| One-line `emit_item` string per item | Three-column `Name \| Version \| ID` table row | Phase 30 | Phase 31 must re-lock round-trip contract against new format |

**Deprecated:**
- `CatalogWriter.write_section(title)` / `CatalogWriter.write_lines(lines)`: the new `write_raw()` method replaces their use in `cli.py` for catalog generation. The old methods remain for backward compatibility (reinstall emitter and tests still use them; no reason to remove).

---

## File Change Inventory

This is a complete list of every file that must change for Phase 30. No other files need modification.

| File | Change Type | What Changes |
|------|-------------|--------------|
| `src/maccat/catalog/markdown.py` | **New file** | `render_markdown_catalog()`, `render_frontmatter()`, `_render_table()`, `_parse_columns()`, `_escape_cell()` |
| `src/maccat/catalog/writer.py` | Minor addition | Add `write_raw(content: str)` method |
| `src/maccat/naming.py` | Regex + format string | `\.txt` → `\.md` in regex; `.txt` → `.md` in `make_catalog_filename` |
| `src/maccat/retention.py` | Three glob strings | `.txt` → `.md` at lines 64, 75, 118 |
| `src/maccat/identity.py` | Two glob strings | `.txt` → `.md` at lines 158, 549 |
| `src/maccat/cli.py` | Generate loop | Replace `write_section`/`write_lines` calls with `render_markdown_catalog` + `write_raw`; add `socket.gethostname()` and `generated_iso` capture |
| `src/maccat/__init__.py` | **No change** | Already `__version__ = "2.1.0"` — bump to `3.0.0` is a separate release task |
| `tests/test_naming.py` | Assertion updates | All `.txt` literal strings → `.md` |
| `tests/conftest.py` | Automatic via naming.py | `make_catalog_filename()` now returns `.md`; no manual edit needed |
| `tests/test_retention.py` | Assertion updates | Explicit `*.txt` assertion strings; `make_catalog_filename()` calls auto-update |
| `tests/test_safety_invariants.py` | Assertion updates | Same as test_retention.py |
| `tests/test_cli.py` | Glob assertion updates | Five `glob("mac-software-list-*.txt")` → `.md` |
| `tests/test_markdown_emitter.py` | **New file** | Unit tests for `render_markdown_catalog`: frontmatter, table rendering, empty/degraded sections, pipe escaping, determinism |

**Files explicitly NOT changed:**
- All 16 `src/maccat/collectors/*.py` — format-only phase, no collector changes
- `src/maccat/gitops.py` — `git add -A -- {computer}/` is extension-agnostic
- `src/maccat/reinstall/parser.py` — old parser remains as-is for Phase 32 convert input
- `src/maccat/reinstall/emitter.py` — reinstall is locked to markdown format in Phase 31
- `tests/reinstall/test_parser_contract.py` — uses `emit_item` line shapes, unchanged

---

## FMT-01 / FMT-03 / FMT-04 Invariants (MD-05)

**FMT-01 (degradation rules):** `emit_item()` remains unchanged. The markdown emitter
re-parses the *output* of `emit_item()` into columns. The degradation rules (id-as-name
promotion, empty → None) all happen before the string reaches the emitter — so FMT-01
continues to hold.

**FMT-03 (identity-only for MCP/AI-CLI):** This invariant is implemented entirely within the
individual collectors (e.g., `claude.py`'s `_collect_mcp()` reads only `.type`, never
`.command`, `.env`, `.args`). The markdown emitter is downstream of collectors and never reads
config files directly. FMT-03 is structurally preserved.

**FMT-04 (determinism):** The markdown emitter must be deterministic. Guarantees:
1. Frontmatter key order is fixed (hand-rolled, not dict).
2. Section order is the collector registry order (unchanged).
3. Item sort is `LC_ALL=C sort -f -u` for non-raw (subprocess, unchanged); raw sections preserve collector-native order.
4. `_render_table()` iterates in list order.
5. The only non-deterministic field is `generated` — tests must inject a fixed timestamp.

**Secret-scan invariant test:** The existing CAT-05 tests in `tests/collectors/test_claude.py`,
`test_codex.py`, `test_opencode.py` assert that no secret values appear in collector output.
These tests operate on the `items` list returned by collectors, not on the final catalog file.
They continue to pass unchanged. A new integration test in `test_markdown_emitter.py` can
assert that a full catalog render of a mocked section with known-good item lines contains no
secret string patterns (belt-and-suspenders).

---

## Determinism Test Strategy

To assert byte-identity across two runs (MD-05):

```python
# Source: [ASSUMED — pattern matches existing timestamp-injection tests in test_cli.py]
def test_render_deterministic(monkeypatch):
    FIXED_TS = "2026-06-18T12:34:56"
    items = [Section(title="Homebrew Packages", items=["git (2.44.0)", "zsh (5.9)"], raw=True)]
    result1 = render_markdown_catalog(
        items, computer="MyMac", hostname="my-mac.local",
        generated=FIXED_TS, maccat_version="2.1.0"
    )
    result2 = render_markdown_catalog(
        items, computer="MyMac", hostname="my-mac.local",
        generated=FIXED_TS, maccat_version="2.1.0"
    )
    assert result1 == result2
    assert result1 == result1.encode().decode()  # UTF-8 roundtrip
```

For the `cli.py`-level test, the pattern already used in `test_cli.py` is to mock
`maccat.gitops.git_pull`, `maccat.gitops.git_commit_and_push`, `maccat.identity.select_computer`,
and `maccat.collectors.get_registry`. The timestamp is read from `datetime.now()` which can be
patched with `unittest.mock.patch('maccat.cli.datetime')` to return a fixed value.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is a code/config-only change. No new external tools, services,
CLIs, databases, or package managers are introduced. All subprocess calls (`sort -f -u`) are
already in use and verified working.

---

## Package Legitimacy Audit

No new packages are installed in this phase. The project remains stdlib-only with zero runtime
dependencies. The Package Legitimacy Gate protocol does not apply.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `write_raw(content: str)` is added to `CatalogWriter` as the preferred integration point | Architecture Patterns (Pattern 6) | Low — alternative is direct `self._fh.write(content)` in cli.py; both achieve the same atomic write |
| A2 | `src/maccat/catalog/markdown.py` is created as a new file rather than extending `format.py` | Standard Stack / Architecture | Low — extending format.py also works; new file is cleaner for testability |
| A3 | Empty-cell convention is a single space `" "` in the cell | Pattern 3: Pipe Escaping | Medium — if Phase 31 parser expects truly empty cells instead, round-trip breaks; needs verification against CONTEXT.md wording |
| A4 | `(none found)` is written without leading spaces (plain `(none found)`, not `  (none found)`) | Pattern 5 | Low — plain line under heading is standard markdown; the two-space indent was an artifact of the plain-text format |
| A5 | `generated_iso` is derived from the same `datetime.now()` call as `timestamp` in `cli.py` (not a separate call) | Pattern 7 | Low — separate calls could yield a one-second drift between filename and frontmatter; same call is correct |

---

## Open Questions (RESOLVED)

1. **`__version__` bump timing** — RESOLVED
   - What we know: `__init__.py` currently reads `2.1.0`; v3.0.0 is the milestone.
   - What's unclear: Does the version bump (`2.1.0` → `3.0.0`) happen in Phase 30, Phase 32 (after all three phases complete), or as a separate release step?
   - Recommendation: Leave `__version__` at `2.1.0` during Phase 30. The planner should create a separate task for the version bump — it belongs in a release phase after all three phases are verified, not woven into the format change.
   - **RESOLVED:** Plans do NOT bump `__version__` in Phase 30; the version bump is deferred to a release step after Phase 32. The markdown frontmatter's `maccat_version` simply reflects whatever `__version__` is at run time.

2. **`test_safety_invariants.py` glob update** — RESOLVED
   - What we know: `test_safety_invariants.py` uses `make_catalog_filename()` (auto-inherits `.md`) and `prune_old_archives()` (inherits `.md` via `retention.py` change).
   - What's unclear: Line 60 in `test_safety_invariants.py` creates a file named `mac-software-list-[alpha]-2026.txt` literally (not via `make_catalog_filename`) specifically to test that the `.txt` file passes the glob but fails the timestamp parse. After the change to `.md`, this file name would NOT match the `.md` glob — the test's premise changes.
   - Recommendation: The planner should include a task to update `test_safety_invariants.py::test_prune_skips_unparseable_filename` to use `mac-software-list-[alpha]-2026.md` as the malformed file (4-digit timestamp, matches glob but fails `parse_catalog_filename`).
   - **RESOLVED:** Plan 30-02 Task 2 updates the literal filename at line 60 to `mac-software-list-[alpha]-2026.md` so the glob-matching-but-unparseable invariant still fires.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection of `src/maccat/catalog/format.py`, `writer.py`, `naming.py`, `retention.py`, `identity.py`, `cli.py`, `gitops.py`, `collectors/base.py`, `collectors/homebrew.py`, `collectors/mas.py`, `collectors/setapp.py`, `collectors/webapps.py`, `collectors/claude.py`, `collectors/__init__.py`, `reinstall/parser.py`, `reinstall/emitter.py` — all implementation details verified by reading source
- `tests/test_naming.py`, `tests/test_retention.py`, `tests/test_safety_invariants.py`, `tests/test_cli.py`, `tests/test_format.py`, `tests/test_writer.py`, `tests/reinstall/test_parser_contract.py` — all test breakage identified by direct inspection
- `pyproject.toml` — no PyYAML dependency confirmed
- `venv/bin/pip list` — PyYAML not installed in project venv confirmed
- Direct Python testing — `ITEM_RE` against all item line shapes, YAML safety of frontmatter values, `datetime.isoformat()` format

### Secondary (MEDIUM confidence)
- YAML 1.1 datetime auto-cast behavior — well-established YAML specification behavior; the `generated` value double-quoting requirement is standard YAML practice

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only confirmed, no new deps
- File change inventory: HIGH — all six source files read and change sites identified exactly
- Architecture: HIGH — patterns derived from existing code; ITEM_RE verified in Python
- Pitfalls: HIGH — each identified from direct code/test inspection
- YAML safety: HIGH — verified by direct Python testing; one MEDIUM claim (datetime cast) is standard YAML spec

**Research date:** 2026-06-18
**Valid until:** Stable — this research is grounded in the current codebase snapshot. Valid until the codebase changes.

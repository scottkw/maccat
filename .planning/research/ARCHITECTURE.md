# Architecture Research

**Domain:** maccat v2.1.0 — Reinstall from Catalog
**Researched:** 2026-06-16
**Confidence:** HIGH (based on direct source reading of all relevant modules)

## Integration Design

### How `reinstall` Fits into the Existing Architecture

The existing `run()` in `cli.py` already has a short-circuit dispatch pattern: `config`
subcommand and `--rename` both dispatch early and return before the 13-step catalog-gen
block. The `reinstall` subcommand follows the same pattern — third short-circuit, resolved
after catalog-repo config and before computer selection.

```
cli.py run():
  1. Parse args
  2. config subcommand → dispatch + return          [existing]
  3. --rename guard
  4. load_config + resolve_catalog_repo             ← reinstall needs this too
  5. reinstall subcommand → dispatch + return       [NEW — insert here]
  6. --rename short-circuit
  7. select_computer
  ... 13-step catalog-gen block continues unchanged
```

The reinstall dispatch must happen AFTER step 4 (catalog repo resolution) because
`reinstall` needs the catalog repo to resolve the computer folder or validate `--from`.
It must happen BEFORE step 6 (`select_computer`) because the interactive picker in
`reinstall/picker.py` calls `select_computer` itself rather than letting the main flow do it.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      cli.py  run()                                   │
│   Subcommand dispatch (config / reinstall / catalog-gen)            │
├───────────────────────────────┬─────────────────────────────────────┤
│  EXISTING (unchanged)         │  NEW                                 │
│  ┌──────────────────────┐     │  ┌────────────────────────────────┐  │
│  │ config.py            │     │  │ reinstall/cli.py               │  │
│  │ resolve_catalog_repo │     │  │ run_reinstall(args, repo)      │  │
│  │ validate_catalog_repo│     │  └────────────┬───────────────────┘  │
│  └──────────────────────┘     │               │                      │
│  ┌──────────────────────┐     │  ┌────────────▼───────────────────┐  │
│  │ identity.py          │ ◄───┤  │ reinstall/picker.py            │  │
│  │ select_computer()    │     │  │ resolve_catalog_path()         │  │
│  │ discover_computer_   │     │  │ (--from PATH or computer-picker│  │
│  │   folders()          │     │  │  + newest-catalog scan)        │  │
│  └──────────────────────┘     │  └────────────┬───────────────────┘  │
│  ┌──────────────────────┐     │               │                      │
│  │ naming.py            │ ◄───┤               │                      │
│  │ parse_catalog_       │     │               │                      │
│  │   filename()         │     │               │                      │
│  └──────────────────────┘     │  ┌────────────▼───────────────────┐  │
│                               │  │ reinstall/parser.py            │  │
│  ┌──────────────────────┐     │  │ parse_catalog(path)            │  │
│  │ catalog/format.py    │ ◄───┤  │  → ParsedCatalog               │  │
│  │ emit_item()          │     │  │  (contract, not called)        │  │
│  │ (contract reference) │     │  └────────────┬───────────────────┘  │
│  └──────────────────────┘     │               │                      │
│                               │  ┌────────────▼───────────────────┐  │
│                               │  │ reinstall/emitter.py           │  │
│                               │  │ emit_reinstall_script(catalog) │  │
│                               │  │  → str (reinstall.sh content)  │  │
│                               │  └────────────────────────────────┘  │
└───────────────────────────────┴─────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `cli.py` `_build_parser()` | Add `reinstall` subparser with `--from` flag | MODIFIED |
| `cli.py` `run()` | Insert reinstall dispatch block at step 5 | MODIFIED |
| `reinstall/__init__.py` | Package marker | NEW |
| `reinstall/cli.py` `run_reinstall()` | Orchestrate: resolve path → parse → emit → write | NEW |
| `reinstall/picker.py` `resolve_catalog_path()` | `--from PATH` short-circuit or interactive select_computer + newest-file scan | NEW |
| `reinstall/parser.py` `parse_catalog()` | Section-boundary state machine + per-line item parser | NEW |
| `reinstall/emitter.py` `emit_reinstall_script()` | Per-source renderers producing the script string | NEW |
| `identity.py` `select_computer()` | Reused verbatim — unchanged | EXISTING (reused) |
| `identity.py` `discover_computer_folders()` | Reused via select_computer | EXISTING (reused) |
| `naming.py` `parse_catalog_filename()` | Reused in picker for newest-catalog scan | EXISTING (reused) |
| `config.py` `resolve_catalog_repo()` | Reused in cli.py dispatch block | EXISTING (reused) |
| `catalog/format.py` `emit_item()` | Contract reference only — not called at reinstall runtime | EXISTING (contract) |

---

## Recommended Project Structure

```
src/maccat/
├── cli.py                    # MODIFIED: add reinstall subcommand + dispatch
├── reinstall/
│   ├── __init__.py           # empty package marker
│   ├── cli.py                # run_reinstall(args, catalog_repo) — thin orchestrator
│   ├── picker.py             # resolve_catalog_path(): --from or select+newest
│   ├── parser.py             # parse_catalog(path) → ParsedCatalog
│   └── emitter.py            # emit_reinstall_script(ParsedCatalog) → str
└── [all existing modules unchanged]
```

### Structure Rationale

- **`reinstall/` subpackage:** Isolates all new code. The existing catalog-gen pipeline
  is untouched except for two wiring points in `cli.py`. Future milestones (catalog
  diffing, etc.) follow the same subpackage pattern.
- **`reinstall/cli.py` vs inlining:** Root `cli.py` has a NON-NEGOTIABLE 13-step order
  comment. Embedding reinstall logic inside `run()` beyond a one-liner dispatch would
  corrupt that invariant. The dispatch is modeled on the existing `config` subcommand
  pattern: one `if args.subcommand == "reinstall": ... return`.
- **`picker.py` separate from `reinstall/cli.py`:** `resolve_catalog_path()` is
  independently testable (no argparse, no TTY side effects on the `--from` path).

---

## (1) Subcommand Integration in `cli.py`

### Parser Changes

```python
# _build_parser() addition — parallel to "config" subparser
reinstall_parser = subparsers.add_parser(
    "reinstall",
    help="Generate reinstall.sh from a catalog",
)
reinstall_parser.add_argument(
    "--from",
    dest="from_path",
    metavar="PATH",
    default=None,
    help="Path to catalog .txt file (omit to use the computer-picker)",
)
```

Note: `from` is a Python keyword. Using `dest="from_path"` and accessing `args.from_path`
throughout is the correct argparse pattern — it handles the keyword conflict cleanly.

### Dispatch Changes in `run()`

Insert between step 4 (validate_catalog_repo) and step 5 (--rename short-circuit):

```python
# After validate_catalog_repo(catalog_repo):
if args.subcommand == "reinstall":
    from maccat.reinstall.cli import run_reinstall
    run_reinstall(args, catalog_repo)
    return
```

The `--rename` guard (step 3) must not fire on the `reinstall` subcommand. The guard
checks `args.rename and bool(args.computer)`. Both are `False` by default for the
`reinstall` subcommand, so no additional guard is needed — but document this in the code.

### Computer selection reuse

`reinstall/picker.py` calls `select_computer()` directly with the same signature used in
the catalog-gen path:

```python
# catalog-gen path (existing):
computer = select_computer(catalog_repo, computer_name=computer_pre)

# reinstall path (new, same call signature):
computer = select_computer(catalog_repo, computer_name=args.computer)
```

The `--computer NAME` flag from the parent parser flows through to `args.computer` for
the reinstall subcommand, giving non-interactive selection for free.

---

## (2) Reverse Parser Architecture (`reinstall/parser.py`)

### The format.py Contract

`emit_item()` in `catalog/format.py` produces exactly four line shapes. The parser must
invert them. This is the primary coupling between existing and new code.

**The four shapes (from `format.py` source, lines 35-43):**

| emit_item inputs | Output shape | Regex to invert |
|-----------------|--------------|-----------------|
| name + version + id | `name (version) [id]` | `^(.+) \((.+)\) \[(.+)\]$` |
| name + version | `name (version)` | `^(.+) \((.+)\)$` |
| name + id | `name [id]` | `^(.+) \[(.+)\]$` |
| name only | `name` | (no parens/brackets — bare string) |
| id only (promoted) | `id` | same as name-only; brackets are suppressed |

**Application order matters:** The full `(version) [id]` regex must be tried before the
`(version)` regex, and `(version)` before `[id]`, because a line like
`name (1.0) [ext.id]` would partially match the shorter patterns. Apply longest-match
first.

**The id-promoted case:** When `emit_item` receives `name=""` and `id_="something"`, it
swaps them, emitting `something` with no brackets. The parser cannot distinguish this from
a bare-name item. This is intentional: the emitter uses `item.id_` (if non-empty) or
`item.name` as the install key per-section. For sections where the id is the install
identifier (VS Code, Cursor), the raw `[id]` bracket is present and parsed. For promoted
ids (rare degraded case) the emitter falls back to the name field.

**Sentinel lines to skip (return None from `_parse_item_line`):**
- `"  (none found)"` — exact string from `flush_section()` when a section is empty.
- Lines matching known degradation messages (e.g. `"Homebrew is not installed."`,
  `"mas CLI is not installed..."`, `"code CLI is not installed."`) — these are not
  installable items. The safest approach: any item line that doesn't match any of the four
  shapes AND starts with an uppercase letter followed by words (heuristic) is treated as a
  degradation message and logged to stderr but not added to parsed items.

### Section Boundary Detection

`CatalogWriter.write_section()` (`catalog/writer.py` lines 67-68) writes:

```
\n{title}\n
------------------------------------\n
```

The 36-dash separator is the reliable boundary marker. The title is the non-empty line
immediately before it. The parser identifies a section by scanning ahead one line.

**Algorithm:**

```python
def parse_catalog(path: Path) -> ParsedCatalog:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: list[ParsedSection] = []
    current_title: str | None = None
    current_items: list[ParsedItem] = []
    i = 0
    while i < len(lines):
        # Section boundary: current line is a candidate title,
        # next line is exactly 36 dashes.
        if (i + 1 < len(lines)
                and lines[i + 1] == "-" * 36
                and lines[i].strip()):
            if current_title is not None:
                sections.append(ParsedSection(current_title, current_items))
            current_title = lines[i]
            current_items = []
            i += 2  # consume title + dashes
            continue
        # Item accumulation within a section
        if current_title is not None and lines[i].strip():
            item = _parse_item_line(lines[i])
            if item is not None:
                current_items.append(item)
        i += 1
    if current_title is not None:
        sections.append(ParsedSection(current_title, current_items))
    return ParsedCatalog(path=path, sections=sections)
```

### Data Structures

```python
@dataclass
class ParsedItem:
    name: str        # text before ( or [, or the full line for bare names
    version: str     # text inside ( ); empty string when absent
    id_: str         # text inside [ ]; empty string when absent
    raw_line: str    # original line, for debugging

@dataclass
class ParsedSection:
    title: str
    items: list[ParsedItem]

@dataclass
class ParsedCatalog:
    path: Path
    sections: list[ParsedSection]

    def section(self, title: str) -> ParsedSection | None:
        """O(1) lookup by title via internal dict."""
        ...
```

### Anti-Drift Contract

`reinstall/parser.py` must document the four line shapes in its module docstring with an
explicit citation to `catalog/format.py:emit_item()`. The regex constants must be named:

```python
# reinstall/parser.py — contract with catalog/format.py:emit_item()
# Any change to emit_item() output shapes MUST be reflected here.
_ITEM_RE_FULL    = re.compile(r"^(.+) \((.+)\) \[(.+)\]$")   # name (ver) [id]
_ITEM_RE_VERSION = re.compile(r"^(.+) \((.+)\)$")             # name (ver)
_ITEM_RE_ID      = re.compile(r"^(.+) \[(.+)\]$")             # name [id]
_SENTINEL        = "  (none found)"
```

A round-trip test must be added to the test suite:
`tests/reinstall/test_parser_contract.py` — call `emit_item()` for all six degradation
variants, run output through `_parse_item_line()`, assert fields match inputs. This test
is the mechanical anti-drift guard.

---

## (3) Script Emitter Architecture (`reinstall/emitter.py`)

### Section-to-Source Mapping

A static dict in `emitter.py` maps section title → source key. This is NOT derived from
the collector registry at runtime (see Anti-Patterns). Unknown titles (from a future
collector) fall through to `"manual"`.

```python
# SECTION_SOURCE_MAP: section title -> ("auto"|"manual", install_key_field)
# install_key_field: "name" | "id_" — which ParsedItem field holds the install key
SECTION_SOURCE_MAP: dict[str, tuple[str, str]] = {
    "Homebrew Packages":           ("auto",   "name"),
    "App Store Applications":      ("manual", "name"),  # no id in catalog — see note
    "Setapp Applications":         ("manual", "name"),
    "Web-installed Applications":  ("manual", "name"),
    "Claude Code Plugins":         ("manual", "name"),
    "Claude Code MCP Servers":     ("manual", "name"),
    "Claude Code Skills & Agents": ("manual", "name"),
    "Codex MCP Servers":           ("manual", "name"),
    "OpenCode Plugins":            ("manual", "name"),
    "OpenCode MCP Servers":        ("manual", "name"),
    "OpenCode Agents":             ("manual", "name"),
    "Gemini CLI Extensions":       ("manual", "name"),
    "Gemini CLI MCP Servers":      ("manual", "name"),
    "VS Code Extensions":          ("auto",   "id_"),
    "Cursor Extensions":           ("auto",   "id_"),
    "Google Chrome Extensions":    ("manual", "name"),
    "Firefox Extensions":          ("manual", "name"),
}
```

### Per-Source Renderers

**Homebrew renderer:**

```bash
brew install git    # cataloged: 2.44.0
brew install python@3.11    # cataloged: 3.11.9
```

Each item: `ParsedItem.name` is the install key (formulae and casks both work with `brew
install`). Version comment from `ParsedItem.version`. No cask/formula distinction needed
— `brew install` handles both.

**VS Code / Cursor renderer (shared, parametrized by CLI name):**

```bash
code --install-extension ms-python.python    # Python (2025.x)
cursor --install-extension anysphere.pyright    # Pyright (1.x)
```

Each item: `ParsedItem.id_` is the extension marketplace ID (the install key).
`ParsedItem.name` and `ParsedItem.version` appear in the comment.

**App Store renderer — MANUAL CHECKLIST ONLY:**

`MasCollector` emits `AppName (version)` — it discards the numeric App Store ID in the
awk pipe (`{print $2, $3}`, skipping column 1 which is the ID). The catalog has no
installable identifier for MAS apps. Emitting `mas install <name>` is wrong; `mas
install` requires the numeric ID. These items must appear in the manual checklist with a
comment explaining the limitation.

**Manual checklist renderer:**

```bash
# Setapp Applications
#   [ ] CleanMyMac X (5.0.1)
#   [ ] Bartender (5.x)

# App Store Applications
# NOTE: App Store IDs are not stored in the catalog. Install manually from the App Store.
#   [ ] Xcode (16.x)

# Claude Code MCP Servers (reconfigure via ~/.claude.json)
#   [ ] my-mcp-server [stdio]
```

Format: `#   [ ] {name} ({version})` when version is present; `#   [ ] {name}` when not.
AI-CLI entries include the transport in brackets where available: `#   [ ] {name} [stdio]`.

### Script Output Structure

```bash
#!/bin/bash
# reinstall.sh — generated by maccat reinstall
# Catalog: mac-software-list-[MacBook]-20260616120000.txt
# Generated: 2026-06-16
#
# REVIEW BEFORE RUNNING.
# This script installs LATEST versions; the cataloged version is shown
# as a comment. Pinning to specific versions is not supported.
#
# Safe to re-run: brew and code/cursor extension installs are idempotent.

set -euo pipefail

# =============================================================================
# AUTO-INSTALL
# =============================================================================

echo "==> Installing Homebrew packages..."
brew install git    # cataloged: 2.44.0
brew install python@3.11    # cataloged: 3.11.9

echo "==> Installing VS Code extensions..."
code --install-extension ms-python.python    # Python (2025.x)

echo "==> Installing Cursor extensions..."
cursor --install-extension anysphere.pyright    # Pyright (1.x)

# =============================================================================
# MANUAL CHECKLIST
# =============================================================================
# Review and reinstall the following items manually.
# Items in this section cannot be auto-installed.

# Setapp Applications
#   [ ] CleanMyMac X (5.0.1)

# App Store Applications
# NOTE: App Store IDs are not stored in the catalog.
# Install manually from the App Store or via: mas install <id>
#   [ ] Xcode (16.x)

# Claude Code MCP Servers (reconfigure via 'claude' settings or ~/.claude.json)
#   [ ] my-mcp-server [stdio]

# Claude Code Skills & Agents
#   [ ] my-skill

# Google Chrome Extensions (reinstall from chrome.google.com/webstore)
#   [ ] uBlock Origin (1.x)
```

### `emit_reinstall_script()` top-level shape

```python
def emit_reinstall_script(catalog: ParsedCatalog, generated_date: str) -> str:
    parts: list[str] = []
    parts.append(_header_block(catalog, generated_date))

    # Auto-install block
    auto_parts: list[str] = []
    brew = catalog.section("Homebrew Packages")
    if brew and brew.items:
        auto_parts.append(_brew_block(brew))
    vscode = catalog.section("VS Code Extensions")
    if vscode and vscode.items:
        auto_parts.append(_editor_ext_block("code", vscode))
    cursor = catalog.section("Cursor Extensions")
    if cursor and cursor.items:
        auto_parts.append(_editor_ext_block("cursor", cursor))
    if auto_parts:
        parts.append(_AUTO_HEADER)
        parts.extend(auto_parts)

    # Manual checklist block
    manual_titles = [
        "App Store Applications",
        "Setapp Applications",
        "Web-installed Applications",
        "Claude Code Plugins",
        "Claude Code MCP Servers",
        "Claude Code Skills & Agents",
        "Codex MCP Servers",
        "OpenCode Plugins",
        "OpenCode MCP Servers",
        "OpenCode Agents",
        "Gemini CLI Extensions",
        "Gemini CLI MCP Servers",
        "Google Chrome Extensions",
        "Firefox Extensions",
    ]
    parts.append(_manual_checklist_block(catalog, manual_titles))

    return "\n".join(parts) + "\n"
```

---

## (4) New Modules, Modified Files, and Build Order

### New vs Modified

| File | Status | What Changes |
|------|--------|-------------|
| `src/maccat/cli.py` | MODIFIED | `_build_parser()`: add reinstall subparser + `--from` flag; `run()`: insert reinstall dispatch block after `validate_catalog_repo` |
| `src/maccat/reinstall/__init__.py` | NEW | Empty package marker |
| `src/maccat/reinstall/cli.py` | NEW | `run_reinstall(args, catalog_repo)` thin orchestrator |
| `src/maccat/reinstall/picker.py` | NEW | `resolve_catalog_path(catalog_repo, from_path, computer_name)` |
| `src/maccat/reinstall/parser.py` | NEW | `parse_catalog(path)`, `ParsedCatalog`, `ParsedSection`, `ParsedItem`, regex constants |
| `src/maccat/reinstall/emitter.py` | NEW | `emit_reinstall_script(catalog)`, per-source renderers, `SECTION_SOURCE_MAP` |
| `src/maccat/catalog/format.py` | UNCHANGED | Parser depends on its output contract — do NOT change `emit_item()` in this milestone |
| `src/maccat/identity.py` | UNCHANGED | `select_computer()` reused as-is |
| `src/maccat/naming.py` | UNCHANGED | `parse_catalog_filename()` reused in picker |
| `src/maccat/config.py` | UNCHANGED | `resolve_catalog_repo()` reused in dispatch |

### Build Order

Dependencies determine sequencing. Each step is independently testable.

**Step 1: `reinstall/parser.py` + `reinstall/__init__.py`**

Dependencies: stdlib (`re`, `dataclasses`, `pathlib`) + `catalog/format.py` (contract
reference only — `format.py` is read but not called). Fully testable with synthetic
catalog text strings.

Tests to write first:
- Round-trip contract: `emit_item(n, v, i)` → line → `_parse_item_line()` → assert
  fields match. All six `emit_item` degradation variants must round-trip.
- Section-boundary detection on fixture catalog text.
- Sentinel-line skipping (`  (none found)`, degradation messages).

**Step 2: `reinstall/picker.py`**

Dependencies: `naming.py` (`parse_catalog_filename`) and `identity.py`
(`select_computer`). Both are stable. The `--from PATH` path is testable without any
mocking; the interactive path mocks `select_computer`.

**Step 3: `reinstall/emitter.py`**

Dependencies: `reinstall/parser.py` (`ParsedCatalog`). Feed a `ParsedCatalog` built from
known fixture data; assert each script section contains the expected lines. The App Store
manual-only behavior must be tested explicitly.

**Step 4: `reinstall/cli.py`**

Dependencies: picker + parser + emitter. Thin orchestrator; integration test with a real
catalog fixture file on disk.

**Step 5: `cli.py` wiring**

Add subparser + dispatch. Integration smoke test: `maccat reinstall --from <fixture>`.
Verify `--rename` guard does not fire on the reinstall subcommand.

---

## Anti-Patterns

### Anti-Pattern 1: Reinferring Section-to-Source Mapping from the Live Collector Registry

**What people do:** Call `get_registry()` at reinstall time to discover section titles,
then cross-reference against parsed sections.

**Why it's wrong:** Reinstall is a read-from-catalog operation. The catalog may have been
generated by an older version of maccat with different or fewer section titles. A static
`SECTION_SOURCE_MAP` in `emitter.py` is explicit, versionable, and testable. Unknown
section titles (from a future collector) degrade gracefully to the manual checklist.

**Do this instead:** Hard-code the 17 known section titles in `SECTION_SOURCE_MAP`.

---

### Anti-Pattern 2: Emitting `mas install` Lines for App Store Apps

**What people do:** Emit `mas install <name>` or try to reconstruct the numeric ID from
the app name.

**Why it's wrong:** `MasCollector._parse_mas_output()` runs `awk '{print $2, $3}'` which
skips column 1 (the numeric App Store ID). The catalog has only `AppName (version)`. `mas
install` requires the numeric ID. `mas search <name>` would require a live network call
and can return multiple results, breaking the "catalog is source of truth" principle.

**Do this instead:** Treat App Store apps as manual-checklist items in v2.1.0 with a
comment: `# NOTE: App Store IDs are not stored in the catalog.`

---

### Anti-Pattern 3: Distinguishing Homebrew Formulae vs Casks for Install Commands

**What people do:** Emit `brew install --cask <name>` vs `brew install <name>` by
attempting to infer type from the item name or a supplementary lookup.

**Why it's wrong:** The Homebrew section in the catalog merges formulae and casks with no
type marker. `brew install <name>` works for both in modern Homebrew. Any heuristic for
cask detection (e.g., presence of `.app` in the name) would be fragile and wrong.

**Do this instead:** Emit `brew install <name>` for all Homebrew items. A future
milestone can add a `[cask]` id marker to the catalog section if the distinction matters.

---

### Anti-Pattern 4: Inlining Reinstall Logic into Root `cli.py`

**What people do:** Add the parse/emit pipeline directly inside `run()` as another branch
of the catalog-gen flow.

**Why it's wrong:** `run()` has a NON-NEGOTIABLE 13-step order comment. Embedding
reinstall logic there muddles the invariants, makes both flows harder to test in
isolation, and violates the existing `config`/`--rename` short-circuit pattern.

**Do this instead:** Dispatch to `reinstall/cli.py:run_reinstall()` as a one-liner
short-circuit: `if args.subcommand == "reinstall": run_reinstall(args, catalog_repo); return`.

---

## Key Coupling: Parser ↔ `catalog/format.py`

`reinstall/parser.py` and `catalog/format.py` share an implicit contract via the four
line shapes. Python's import system cannot enforce this coupling. Two mechanical safeguards:

1. **Docstring citation:** `reinstall/parser.py` module docstring must list all four
   shapes with explicit reference: `# Contract with catalog/format.py:emit_item()`.
2. **Round-trip test:** `tests/reinstall/test_parser_contract.py` calls `emit_item()` for
   all six degradation variants and asserts `_parse_item_line()` inverts them. Any future
   change to `emit_item()` that breaks this test is a breaking change requiring a parser
   update.

---

## Sources

- Direct source reading (all confidence HIGH):
  - `src/maccat/catalog/format.py` — emit_item() degradation rules, all four line shapes
  - `src/maccat/catalog/writer.py` — write_section() boundary format (36 dashes, leading newline)
  - `src/maccat/cli.py` — existing subcommand dispatch pattern, 13-step orchestration order
  - `src/maccat/identity.py` — select_computer() signature, resolve_computer_selection()
  - `src/maccat/collectors/base.py` — Section, CollectorResult data types
  - `src/maccat/collectors/__init__.py` — all 17 section titles and their canonical order
  - `src/maccat/collectors/homebrew.py` — brew list --versions output format
  - `src/maccat/collectors/mas.py` — awk {print $2, $3}: MAS ID discarded, no id in catalog
  - `src/maccat/collectors/vscode.py` — emit_item(name, version, marketplace_id) confirmed
  - `src/maccat/collectors/claude.py` — FMT-03 secret-safety: MCP entries are name+transport only
  - `src/maccat/collectors/setapp.py` — raw-write, name-only or name+version
  - `src/maccat/naming.py` — parse_catalog_filename() for newest-catalog scan
  - `src/maccat/config.py` — resolve_catalog_repo() signature
  - `.planning/PROJECT.md` — v2.1.0 milestone spec, key decisions (FMT-03, never-auto-execute,
    manual-checklist-only for AI-CLI, install-latest-with-version-comment)

---

*Architecture research for: maccat v2.1.0 Reinstall from Catalog*
*Researched: 2026-06-16*

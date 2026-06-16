# Phase 15: Collectors — Research

**Researched:** 2026-06-14
**Domain:** Pure Python port of 12 source collectors at byte-parity with `update-list.sh`
**Confidence:** HIGH — all findings derived directly from reading `update-list.sh` line-by-line (the untouched zsh parity reference) and the existing Phase 13/14 built artifacts.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All implementation choices are at Claude's discretion — this is a byte-parity port with no
user-facing design freedom. The zsh collector functions ARE the spec (cited line numbers above);
replicate their discovery method, parsing, fallback messages, and output format exactly. Use the
Phase 13 output-format + name-resolution layer. Collector module organization (one module per
source, or a `Collector` ABC + registry as the prior research recommends) is at Claude's discretion
— prefer the research-recommended structure if it eases the byte-parity tests and the Phase-16
section-order registry.

Hard non-negotiables (from requirements + the existing zsh behavior):
- **CAT-05 (secrets):** MCP-server collectors emit name + transport ONLY — NEVER env, headers,
  args, command, or url. This is the single most important safety invariant of the phase.
- **CAT-06 (degradation):** every optional source checks availability (`command -v` / path exists)
  and writes the zsh-exact fallback (`(none found)` or the specific message) — never aborts the run.
- **CAT-03 (sort, from Phase 13):** ordering goes through `LC_ALL=C sort -f -u` (and `sort -V` for
  Chrome version-directory selection) — never Python `sorted()`.
- **Section order** must match `generate_catalog` exactly (success criterion 4).
- Prefer a tool's own CLI for discovery where one exists (`code --list-extensions`,
  `gemini extensions list`, etc.) and fall back to parsing on-disk config/manifests where no CLI
  exists — mirror whatever the zsh function actually does for each source.

### Claude's Discretion

Collector module organization (one file per source in `collectors/`, Collector ABC + registry,
test structure).

### Deferred Ideas (OUT OF SCOPE)

- End-to-end run orchestration + section-order registry wiring + git — Phase 16.
- Golden-output byte-parity fixtures/tests — Phase 17.
- New collectors beyond current parity (Safari/Edge/Brave/Zed; CHR-02/FF-02 enabled-state; CDX-02
  Codex plugins) — out of scope (future milestone).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAT-01 | All collectors re-implemented — Homebrew formulae/casks, App Store (mas), Setapp, web /Applications, four AI CLIs (Claude Code, Codex, OpenCode, Gemini), VS Code, Cursor, Chrome (all profiles), Firefox (all profiles) | Each collector section below documents exact discovery method, paths, fields, and fallback messages |
| CAT-05 | No secrets written — MCP entries emit name + transport only (never env/headers/args/command/url) | MCP Transport Safety section documents exact whitelist and zero-touch-fields rule |
| CAT-06 | Graceful degradation — absent source/tool writes `(none found)` / fallback message, never aborts | Per-collector fallback messages documented verbatim; degraded_result() pattern established |
</phase_requirements>

---

## Summary

Phase 15 ports 12 independent source collectors from `update-list.sh` to `src/maccat/collectors/`.
Every collector is a pure port — the zsh function bodies are the complete spec; nothing is
re-designed. The Phase 13 output-format layer (`emit_item`, `flush_section`, `version_sort_tail`,
`CatalogWriter`) and name-resolution helpers (`json_io`, `chrome_name`, `vsc_name`) are already
built and must be reused without re-implementation.

The three most important facts about this phase:

1. **The first four collectors (Homebrew, App Store, Setapp, Web) bypass `emit_item`/`flush_section`
   entirely.** They write directly to the output file (or stream lines to it). The Python port must
   replicate this raw-write behavior, NOT route these through the Item/flush_section pipeline.

2. **Every MCP collector (Claude MCP, Codex MCP, OpenCode MCP, Gemini MCP) must emit `name [transport]`
   only — transport clamped to the `stdio|http|sse` whitelist, all other fields left completely
   unread.** This is CAT-05. It is the single hardest invariant to test: a collector that passes
   content tests but reads `.command` or `.env` is a secret-leak bug.

3. **The Collector ABC + registry pattern is the right choice.** It makes Phase-16 section-order
   wiring trivial (the REGISTRY in `collectors/__init__.py` IS the order), makes per-collector unit
   testing clean (mock `collect()`, swap one collector), and each collector file is independently
   reviewable for CAT-05 compliance.

**Primary recommendation:** One Python module per collector source in `src/maccat/collectors/`,
`Collector` ABC in `base.py`, ordered `REGISTRY` in `__init__.py`, unit-test every collector in
`tests/collectors/test_*.py` with subprocess/filesystem mocking.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Homebrew formulae/casks | CLI subprocess (`brew`) | None | brew is the authoritative source; no manifest to parse |
| App Store apps | CLI subprocess (`mas`) | None | mas is the only programmatic source |
| Setapp apps | Filesystem (`/Applications/Setapp/`) | None | No CLI; directory scan is the method |
| Web-installed apps | Filesystem (`/Applications/` scan) | None | Direct find equivalent |
| Claude plugins | Filesystem (`~/.claude/plugins/installed_plugins.json`) | None | JSON manifest parse; no CLI for plugin listing |
| Claude MCP | Filesystem (`~/.claude.json`) | None | JSON parse; only `.key` + `.value.type` |
| Claude Skills/Agents | Filesystem (`~/.claude/skills/`, `~/.claude/agents/`) | None | Directory + YAML frontmatter grep |
| Codex MCP | CLI subprocess (`codex mcp list --json`) | TOML grep fallback (`~/.codex/config.toml`) | CLI preferred; section-header-only grep fallback |
| OpenCode Plugins | Filesystem (`~/.config/opencode/opencode.json`) | None | JSON parse of `.plugin[]` array |
| OpenCode MCP | Filesystem (`~/.config/opencode/opencode.json`) | None | JSON parse of `.mcp` object; name + type only |
| OpenCode Agents | Filesystem (`~/.config/opencode/agents/*.md`) | None | YAML frontmatter grep |
| Gemini Extensions | Filesystem (`~/.gemini/extensions/*/gemini-extension.json`) | None | JSON manifest parse |
| Gemini MCP | Filesystem (`~/.gemini/config/mcp_config.json`) | None | JSON parse; -s guard for empty file; name + type only |
| VS Code Extensions | CLI subprocess (`code --list-extensions --show-versions`) | Filesystem (`~/.vscode/extensions/extensions.json`) | CLI preferred; file fallback |
| Cursor Extensions | CLI subprocess (`cursor --list-extensions --show-versions`) | Filesystem (`~/.cursor/extensions/extensions.json`) | CLI preferred; file fallback |
| Chrome Extensions | Filesystem (`~/Library/Application Support/Google/Chrome/`) | None | All profiles; component denylist; `version_sort_tail` |
| Firefox Extensions | Filesystem (`~/Library/Application Support/Firefox/profiles.ini`) | None | All profiles via profiles.ini; `app-profile` filter |

---

## Standard Stack

### Core (already built — reuse, do not re-implement)

| Module | Location | Purpose | Status |
|--------|----------|---------|--------|
| `emit_item` | `src/maccat/catalog/format.py` | FMT-01 line formatting | BUILT Phase 13 |
| `flush_section` | `src/maccat/catalog/format.py` | `LC_ALL=C sort -f -u` + `(none found)` | BUILT Phase 13 |
| `version_sort_tail` | `src/maccat/catalog/format.py` | `sort -V` for Chrome version dirs | BUILT Phase 13 |
| `CatalogWriter` | `src/maccat/catalog/writer.py` | Atomic output; `write_section`, `write_lines` | BUILT Phase 13 |
| `json_get` | `src/maccat/helpers/json_io.py` | Dotted-path JSON extractor | BUILT Phase 13 |
| `chrome_ext_name` | `src/maccat/helpers/chrome_name.py` | `__MSG_key__` resolver | BUILT Phase 13 |
| `resolve_vsc_ext_name` | `src/maccat/helpers/vsc_name.py` | `%nls_key%` resolver | BUILT Phase 13 |

### New in Phase 15

| Module | Location | Purpose |
|--------|----------|---------|
| `Collector` ABC | `src/maccat/collectors/base.py` | Abstract base; `collect()` → `CollectorResult`; `available()` |
| `Section` / `CollectorResult` dataclasses | `src/maccat/collectors/base.py` | Section title + items list; multi-section results |
| One module per source | `src/maccat/collectors/{homebrew,mas,setapp,webapps,claude,codex,opencode,gemini,vscode,cursor,chrome,firefox}.py` | Each implements `Collector` |
| `REGISTRY` | `src/maccat/collectors/__init__.py` | Ordered list of `Collector` instances; defines section order |

### No New Runtime Dependencies

Zero. All collectors use: `subprocess`, `pathlib`, `json`, `re`, `os` — all stdlib. The Phase 13
helpers (`json_io`, `chrome_name`, `vsc_name`) are already written and tested.

---

## Package Legitimacy Audit

No new packages are installed in this phase. All dependencies are stdlib or already-installed
dev tools from Phase 13 (`pytest`, `ruff`, `mypy`).

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### Collector ABC and Registry

```python
# src/maccat/collectors/base.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Section:
    title: str
    items: list[str]  # raw emit_item() output lines, NOT yet sorted


@dataclass
class CollectorResult:
    sections: list[Section]
    warnings: list[str] = field(default_factory=list)


class Collector:
    """Abstract base. Subclasses implement collect()."""

    def collect(self) -> CollectorResult:
        raise NotImplementedError

    def available(self) -> bool:
        """Override to gate on tool presence or directory existence."""
        return True

    def degraded_result(self, title: str, note: str = "") -> CollectorResult:
        """Standard empty-section result; items=[] causes flush_section → '  (none found)'."""
        return CollectorResult(sections=[Section(title=title, items=[])])
```

```python
# src/maccat/collectors/__init__.py
# REGISTRY is the single source of truth for section order (Phase 16 consumes this).
from maccat.collectors.homebrew import HomebrewCollector
from maccat.collectors.mas import MasCollector
# ... (all 12 imports)

REGISTRY: list[Collector] = [
    HomebrewCollector(),
    MasCollector(),
    SetappCollector(),
    WebAppsCollector(),
    ClaudeCollector(),       # yields 3 sections
    CodexCollector(),        # yields 1 section
    OpenCodeCollector(),     # yields 3 sections
    GeminiCollector(),       # yields 2 sections
    VSCodeCollector(),
    CursorCollector(),
    ChromeCollector(),
    FirefoxCollector(),
]
```

### Multi-Section Collectors

Claude, Codex, OpenCode, and Gemini collectors each emit multiple sections in one `collect()` call.
A `CollectorResult` already supports `sections: list[Section]`. The Phase-16 orchestrator iterates
`for section in result.sections`.

Design choice: group by source tool (all Claude sections in `claude.py`), not by section type.
This keeps the CAT-05 compliance boundary clear — one file = one tool's secrets policy.

### Recommended Project Structure

```
src/maccat/collectors/
├── __init__.py       # REGISTRY (ordered)
├── base.py           # Collector ABC, Section, CollectorResult
├── homebrew.py       # HomebrewCollector
├── mas.py            # MasCollector
├── setapp.py         # SetappCollector
├── webapps.py        # WebAppsCollector
├── claude.py         # ClaudeCollector (3 sections: plugins, MCP, skills/agents)
├── codex.py          # CodexCollector (1 section: MCP)
├── opencode.py       # OpenCodeCollector (3 sections: plugins, MCP, agents)
├── gemini.py         # GeminiCollector (2 sections: extensions, MCP)
├── vscode.py         # VSCodeCollector
├── cursor.py         # CursorCollector
├── chrome.py         # ChromeCollector
└── firefox.py        # FirefoxCollector

tests/collectors/
├── test_homebrew.py
├── test_mas.py
├── test_setapp.py
├── test_webapps.py
├── test_claude.py
├── test_codex.py
├── test_opencode.py
├── test_gemini.py
├── test_vscode.py
├── test_cursor.py
├── test_chrome.py
└── test_firefox.py
```

---

## Per-Collector Specification

This section documents every collector's exact zsh behavior. All line number citations refer to
`update-list.sh`. [VERIFIED: direct read of update-list.sh]

---

### Collector 1: Homebrew Packages

**Zsh location:** `generate_catalog` lines 2233–2242
**Section title:** `"Homebrew Packages"`
**Discovery method:** CLI subprocess — `brew list --formula` then `brew list --cask`

**CRITICAL — raw-write pattern (not emit_item):**
The zsh appends raw subprocess output directly to `$OUTPUT_FILE` with `>> "$OUTPUT_FILE"`.
This means: no `emit_item`, no `flush_section`, no `(none found)`. The Python port must replicate
this raw-line behavior exactly.

```zsh
brew list --formula >> "$OUTPUT_FILE"
brew list --cask >> "$OUTPUT_FILE"
```

**Availability check:** `command -v brew`

**Fallback message (written to output file, not stdout):**
```
Homebrew is not installed.
```
Note: this goes INTO the catalog file (`>> "$OUTPUT_FILE"`), not to stdout.
The `WARNING:` on stdout is for the user's terminal; it does NOT appear in the file.

**Subprocess:** `["brew", "list", "--formula"]` and `["brew", "list", "--cask"]`, stdout captured,
written to the section verbatim. Each line from brew is a package name, one per line.

**Python approach:** `collect()` returns two concatenated lists of lines — formulae then casks,
no sorting (brew's output order is preserved; the zsh does not sort this section). Fallback:
a single-item list `["Homebrew is not installed."]`.

**No emit_item/flush_section:** This collector bypasses the Item pipeline entirely.
The orchestrator writes these lines directly via `CatalogWriter.write_lines()`.

---

### Collector 2: App Store Applications

**Zsh location:** `generate_catalog` lines 2249–2260
**Section title:** `"App Store Applications"`
**Discovery method:** CLI subprocess — `mas list 2>/dev/null | awk '{print $2, $3}'`

**CRITICAL — raw-write pattern:**
Like Homebrew, this uses `>> "$OUTPUT_FILE"` after awk post-processing. The awk extracts
columns 2 and 3 from `mas list` output (skipping the numeric App Store ID in column 1).

**`mas list` output format:** `<id>  <AppName> (<version>)`
**After awk `'{print $2, $3}'`:** `AppName (version)` — a space-joined columns 2 and 3.

**Availability check:** `command -v mas`

**Fallback messages (written to catalog file):**
```
mas (Mac App Store CLI) is not installed.
Install it with Homebrew: brew install mas
```
Both lines go into the file. Two separate file writes.

**Fallback when mas fails (non-zero exit):**
```
Could not retrieve App Store list.
```

**Python approach:** Run `["mas", "list"]`, capture stdout, apply Python equivalent of
`awk '{print $2, $3}'` (split on whitespace, take elements at index 1 and 2, join with space),
write lines. Fallback: two-line list. No emit_item/flush_section.

---

### Collector 3: Setapp Applications

**Zsh location:** `generate_catalog` lines 2267–2274
**Section title:** `"Setapp Applications"`
**Discovery method:** Filesystem — `find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} \; | sort`

**Availability check:** `[[ -d "/Applications/Setapp" ]]`

**Fallback message (written to catalog file):**
```
Setapp is not installed or detected.
```

**Python approach:** `Path("/Applications/Setapp").iterdir()`, filter dirs, basename only,
sort (plain Python `sorted()` is acceptable here — the zsh also just does `sort`, not
`LC_ALL=C sort -f -u`; this section is sorted but not deduplicated via flush_section).

**Important:** The `/Applications/Setapp` directory itself is included in the `find` output
(find includes the start path). The zsh produces it as a line in the output. Python's `iterdir()`
skips the directory itself. Verify whether the zsh actually includes "Setapp" as an entry —
`find "/Applications/Setapp" -maxdepth 1 -type d` includes the root dir itself as the first
result, so "Setapp" IS in the output. The Python port must include it.

Actually, re-examining: `find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} \;`
produces "Setapp" as the first line (the start path), then each subdirectory. The pipe to `sort`
then sorts all names including "Setapp" itself. The Python equivalent must list the directory
itself AND its subdirectory contents, then sort. Use `[Path("/Applications/Setapp")] + list(...)`.

---

### Collector 4: Web-installed Applications

**Zsh location:** `generate_catalog` lines 2281–2284
**Section title:** `"Web-installed Applications"`
**Discovery method:** Filesystem —
```zsh
find "/Applications" -maxdepth 1 -type d \
    -not -path "/Applications/Setapp*" \
    -not -path "/Applications/*App Store*" \
    -exec basename {} \; | sort
```

**Always runs** — no availability check.

**Exclusions:**
- Paths matching `/Applications/Setapp*` (Setapp's directory)
- Paths matching `/Applications/*App Store*` (Mac App Store artifacts)

**Note:** `/Applications` itself is included by find (the start path). After `basename`, this
produces `"Applications"` as a line. The Python port must include this.

**Python approach:** Iterate `Path("/Applications").iterdir()`, filter to dirs, exclude
`Setapp*` and `*App Store*` patterns, also include `/Applications` itself (as `"Applications"`),
sort, write lines. No emit_item/flush_section.

---

### Collector 5: Claude Code Plugins

**Zsh function:** `collect_claude_plugins` (lines 1594–1626)
**Section title:** `"Claude Code Plugins"`
**Discovery method:** Filesystem — `~/.claude/plugins/installed_plugins.json`

**Schema:**
```json
{
  "plugins": {
    "name@marketplace": [{"version": "1.0.0", ...}, ...],
    ...
  }
}
```
Key is `"name@marketplace"`. Version is `value[0].version`.

**Extract fields:**
- `name` = part before first `@` in key: `key.split("@", 1)[0]`
- `version` = `plugins[key][0].version` (or `""` if absent)
- `id` = the full key (`"name@marketplace"`)

**emit_item call:** `emit_item(name, version, key)` → `"name (version) [name@marketplace]"`

**Availability check:** file existence `Path("~/.claude/plugins/installed_plugins.json").expanduser()`

**Fallback:** file absent → `flush_section([])` → `"  (none found)"` (no separate message)

**Python approach:**
```python
data = json.loads(path.read_text())
plugins = data.get("plugins", {})
for key, versions in plugins.items():
    name = key.split("@", 1)[0]
    version = versions[0].get("version", "") if versions else ""
    line = emit_item(name, version, key)
    if line:
        items.append(line)
```

---

### Collector 6: Claude Code MCP Servers

**Zsh function:** `collect_claude_mcp` (lines 1638–1681)
**Section title:** `"Claude Code MCP Servers"`
**Discovery method:** Filesystem — `~/.claude.json` (root-level JSON config)

**Schema (relevant fields only — CAT-05):**
```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "...",    ← NEVER READ
      "args": [...],       ← NEVER READ
      "env": {...}         ← NEVER READ
    }
  }
}
```

**Extract fields (ONLY these two):**
- `name` = key in `mcpServers` object
- `transport` = `entry.get("type", "stdio")`

**Transport whitelist:** `stdio | http | sse`. Any other value → `"stdio"`.

**emit_item call:** `emit_item(name, "", transport)` → `"name [transport]"`
(version is empty string; transport goes in the id field so it gets brackets)

**Availability check:** `Path("~/.claude.json").expanduser().is_file()`

**Fallback:** file absent → `flush_section([])` → `"  (none found)"`

**CAT-05 guard pattern:**
```python
transport = entry.get("type", "stdio")  # ONLY .type — never .command, .env, .args, .url
if transport not in ("stdio", "http", "sse"):
    transport = "stdio"
line = emit_item(name, "", transport)
```

---

### Collector 7: Claude Code Skills & Agents

**Zsh function:** `collect_claude_skills_agents` (lines 1692–1731)
**Section title:** `"Claude Code Skills & Agents"`
**Discovery method:** Filesystem, two sub-sources combined into one section.

**Skills — `~/.claude/skills/`:**
- One subdirectory per skill
- Name: `grep '^name:' SKILL.md | head -1 | sed ...`  → strip `name:` prefix + trim quotes
- Python: open `SKILL.md`, find first line starting with `name:`, strip `name:` and leading
  whitespace, strip surrounding double-quotes
- Fallback name: `basename(skill_dir)` if no name found

**Agents — `~/.claude/agents/*.md`:**
- Each `.md` file is an agent
- Name: same grep pattern on the `.md` file itself
- Fallback name: `Path(f).stem` (filename without `.md`)

**emit_item call:** `emit_item(name, "", "")` → bare `"name"` only (no version, no id)

**Availability checks:**
- Skills: `Path("~/.claude/skills").expanduser().is_dir()` — if not dir, skip silently
- Agents: `Path("~/.claude/agents").expanduser().is_dir()` — if not dir, skip silently
- If BOTH absent, `flush_section([])` → `"  (none found)"`

**Name extraction (Python equivalent of the grep+sed pattern):**
```python
import re

def _read_yaml_name(path: Path) -> str:
    """Extract 'name:' value from YAML frontmatter — first matching line only."""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("name:"):
                # strip 'name:' prefix, leading whitespace, and surrounding double-quotes
                return line[len("name:"):].strip().strip('"')
    except OSError:
        pass
    return ""
```

---

### Collector 8: Codex MCP Servers

**Zsh function:** `collect_codex_mcp` (lines 1748–1790)
**Section title:** `"Codex MCP Servers"`
**Discovery method:** CLI first (`codex mcp list --json`), TOML file fallback

**Primary path — CLI:**
```python
result = subprocess.run(["codex", "mcp", "list", "--json"], capture_output=True, text=True)
# returns JSON array: [{"name": "...", "type": "stdio", ...}, ...]
# empty array [] → skip to fallback
```
Extract: `name` = `entry["name"]`, `transport` = `entry.get("type", "stdio")`.
Transport whitelist: `stdio | http | sse`.

**Fallback path — TOML grep (when codex absent OR CLI returns `[]`):**
```zsh
grep '^\[mcp_servers\.' "$codex_config" | sed ... | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' | tr -d '"'
```
Python equivalent: parse `~/.codex/config.toml` lines for `[mcp_servers.NAME]` headers ONLY.
Extract NAME from between `[mcp_servers.` and `]`. Transport defaults to `"stdio"` for all.

**CRITICAL CAT-05 note for TOML fallback:** Only section header lines (`^\[mcp_servers\.`) are
ever read. Value lines (containing `command`, `env`, `args`, `url`, `headers`) are explicitly
skipped. The Python port must replicate this — read the raw file as text and extract only
section header names, never parse the TOML values.

**Availability:** `shutil.which("codex")` or `Path("~/.codex/config.toml").expanduser().is_file()`

**Fallback:** both absent → `flush_section([])` → `"  (none found)"`

---

### Collector 9: OpenCode Plugins

**Zsh function:** `collect_opencode_plugins` (lines 1802–1847)
**Section title:** `"OpenCode Plugins"`
**Source file:** `~/.config/opencode/opencode.json`

**Schema:**
```json
{"plugin": ["name@source", "other@src", ...]}
```

**Extract:** For each entry in `.plugin[]`:
- `name` = part before first `@`: `entry.split("@", 1)[0]`
- **Path/URL guard:** if no `@` found AND entry contains `/`, skip with WARNING to stderr

**emit_item call:** `emit_item(name, "", "")` → bare `"name"`

**Availability:** file existence

**Fallback:** file absent or `.plugin` is null/missing → `flush_section([])` → `"  (none found)"`

**Python approach:**
```python
plugins = data.get("plugin") or []
for entry in plugins:
    name = entry.split("@", 1)[0]
    if name == entry and "/" in entry:
        # path/URL guard — warn to stderr, skip
        continue
    if not name:
        continue
    items.append(emit_item(name, "", ""))
```

---

### Collector 10: OpenCode MCP Servers

**Zsh function:** `collect_opencode_mcp` (lines 1861–1917)
**Section title:** `"OpenCode MCP Servers"`
**Source file:** `~/.config/opencode/opencode.json` (same file as plugins)

**Schema (relevant fields only — CAT-05):**
```json
{
  "mcp": {
    "server-name": {
      "type": "stdio",
      "command": "...",   ← NEVER READ
      "env": {...}        ← NEVER READ
    }
  }
}
```

**Null check:** The zsh checks `if [[ -z "$mcp_check" ]]` after `jq -r '.mcp // empty'`.
Python: `if not data.get("mcp"):` — empty dict, null, or absent all → `flush_section([])`.

**Extract:** `name` = key, `transport` = `entry.get("type", "stdio")`.
Transport whitelist: `stdio | http | sse`.

**emit_item:** `emit_item(name, "", transport)` → `"name [transport]"`

---

### Collector 11: OpenCode Agents

**Zsh function:** `collect_opencode_agents` (lines 1930–1953)
**Section title:** `"OpenCode Agents"`
**Discovery method:** Filesystem — `~/.config/opencode/agents/*.md`

**Same pattern as Claude agents:** grep `^name:` from YAML frontmatter; fallback to stem.

**Availability:** `Path("~/.config/opencode/agents").expanduser().is_dir()`

**Fallback:** dir absent → `flush_section([])` → `"  (none found)"`

---

### Collector 12: Gemini CLI Extensions

**Zsh function:** `collect_gemini_extensions` (lines 1970–1996)
**Section title:** `"Gemini CLI Extensions"`
**Discovery method:** Filesystem — `~/.gemini/extensions/*/gemini-extension.json`

**Schema:**
```json
{"name": "extension-name", "version": "1.0.0", ...}
```

**Extract via `json_get` helper (already built):**
- `name` = `json_get(manifest, "name")` — fallback to `basename(ext_dir)` if empty
- `version` = `json_get(manifest, "version")`

**emit_item:** `emit_item(name, version, "")` → `"name (version)"`

**Availability:** `Path("~/.gemini/extensions").expanduser().is_dir()`

**Note:** `extension-enablement.json` in the same directory is explicitly NOT read — all
installed extensions are cataloged regardless of enabled state (CHR-02/FF-02 analogue).

---

### Collector 13: Gemini CLI MCP Servers

**Zsh function:** `collect_gemini_mcp` (lines 2016–2059)
**Section title:** `"Gemini CLI MCP Servers"`
**Source file:** `~/.gemini/config/mcp_config.json`

**CRITICAL — empty-file guard:**
The zsh uses `[[ -s "$mcp_config" ]]` (file exists AND has nonzero size). A plain `-f` check is
wrong — the file CAN EXIST but be 0 bytes. Python must check `path.is_file() and path.stat().st_size > 0`.

**Schema:**
```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "...",   ← NEVER READ
      "env": {...}        ← NEVER READ
    }
  }
}
```

**Extract:** `name` = key in `.mcpServers`, `transport` = `.value.get("type", "stdio")`.
Transport whitelist: `stdio | http | sse`.

**emit_item:** `emit_item(name, "", transport)` → `"name [transport]"`

**Fallback:** file absent OR 0 bytes → `flush_section([])` → `"  (none found)"`

---

### Collector 14: VS Code Extensions

**Zsh function:** `collect_vscode_extensions` (lines 1387–1476)
**Section title:** `"VS Code Extensions"`
**Source dirs:** `~/.vscode/extensions/` + `~/.vscode/extensions/extensions.json`

**Two-path logic (mirror exactly):**

**Path A — CLI preferred:**
```python
result = subprocess.run(["code", "--list-extensions", "--show-versions"], ...)
# Output: one line per extension: "publisher.name@version"
```
For each line:
- `id` = part before last `@`: `line.rsplit("@", 1)[0]`
- `version` = part after last `@`: `line.rsplit("@", 1)[1]`
- If `id == version` (no `@` found): skip malformed line
- Still need `extensions.json` for `relativeLocation` → `package.json` path
- Load `extensions.json`, find entry with `identifier.id == id`, get `relativeLocation`
- `pkg_json` = `ext_dir / rel_loc / "package.json"`
- `display_name` = `resolve_vsc_ext_name(pkg_json, id)` — uses Phase 13 helper
- If `rel_loc` not found: `display_name = id`

**Path B — file fallback (when `code` CLI absent OR returns empty):**
```
WARNING message: "code CLI returned empty list. Falling back to extensions.json."
```
This warning is written to stdout (terminal), NOT to the catalog file.

Parse `~/.vscode/extensions/extensions.json` directly:
```python
entries = json.loads(ext_json_path.read_text())
for entry in entries:
    id_ = entry.get("identifier", {}).get("id", "")
    version = entry.get("version", "")
    rel_loc = entry.get("relativeLocation", "")
    pkg_json = ext_dir / rel_loc / "package.json"
    display_name = resolve_vsc_ext_name(pkg_json, id_)
    items.append(emit_item(display_name, version, id_))
```

**Availability:** No CLI AND no `extensions.json` →
```
NOTE: VS Code not installed or no extensions found.
```
(written to stdout, NOT the catalog) + `flush_section([])`.

**Note on `extensions.json` loading:** The zsh uses `jq -r '.[] | ...'` which iterates an array.
Python: `json.loads(path.read_text())` returns a list.

---

### Collector 15: Cursor Extensions

**Zsh function:** `collect_cursor_extensions` (lines 1494–1583)
**Section title:** `"Cursor Extensions"`

**Identical to VS Code** with these substitutions:
- `ext_dir` = `~/.cursor/extensions/`
- CLI: `cursor --list-extensions --show-versions`
- WARNING message: `"cursor CLI returned empty list. Falling back to extensions.json."`
- NOTE message: `"Cursor not installed or no extensions found."`

The Python module can share the core logic via a private helper function:

```python
def _collect_editor_extensions(
    ext_dir: Path,
    cli_name: str,
    section_title: str,
) -> tuple[list[str], list[str]]:
    """Shared logic for VS Code and Cursor. Returns (items, warnings)."""
    ...
```

---

### Collector 16: Google Chrome Extensions

**Zsh function:** `collect_chrome_extensions` (lines 2074–2137)
**Section title:** `"Google Chrome Extensions"`
**Base dir:** `~/Library/Application Support/Google/Chrome`

**Profile enumeration (exact order from zsh line 2089):**
```zsh
for profile_dir in "$chrome_base/Default" "$chrome_base"/Profile\ */; do
```
Python equivalent:
```python
base = Path.home() / "Library/Application Support/Google/Chrome"
profile_dirs = [base / "Default"]
profile_dirs += sorted(base.glob("Profile */"))  # glob preserves ordering; sort for determinism
```
Only process profile dirs where `profile_dir / "Extensions"` is a directory.

**Extension iteration per profile:**
```python
for ext_dir in (profile / "Extensions").iterdir():
    if not ext_dir.is_dir():
        continue
    ext_id = ext_dir.name
    if ext_id == "Temp":
        continue
    if ext_id.startswith("_"):
        continue
    if ext_id in COMPONENT_DENYLIST:
        continue
    # version directory selection
    candidates = [d.name for d in ext_dir.iterdir() if d.is_dir()]
    ver_dir = version_sort_tail(candidates)  # Phase 13 helper
    if not ver_dir:
        continue
    manifest = ext_dir / ver_dir / "manifest.json"
    if not manifest.is_file():
        continue
    name = chrome_ext_name(manifest)  # Phase 13 helper
    version = json_get(manifest, "version")
    items.append(emit_item(name, version, ext_id))
```

**Component extension denylist (10 IDs — inline constant, never a file):**
```python
COMPONENT_DENYLIST = frozenset({
    "nmmhkkegccagdldgiimedpiccmgmieda",
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi",
    "aapocclcgogkmnckokdopfmhonfmgoek",
    "blpcfgokakmgnkcojhhkbfbldkacnbeo",
    "felcaaldnbdncclmgdcncolpebgiejap",
    "aohghmighlieiainnegkcijnfilokake",
    "apdfllckaahabafndbhieahigkjlhalf",
    "pjkljhegncpnkpknbcohdijeoejaedia",
    "mhjfbmdgcfjbbpaeojofohoefgiehjai",
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm",
})
```

**Cross-profile dedup:** `flush_section` is called ONCE after all profile loops. Items accumulate
across all profiles; sort -f -u deduplicates identically-named extensions that appear in multiple
profiles.

**Availability:** base dir existence. Fallback message (stdout NOT catalog):
```
NOTE: Google Chrome not installed.
```
Plus `flush_section([])` → `"  (none found)"` in file.

---

### Collector 17: Firefox Extensions

**Zsh function:** `collect_firefox_extensions` (lines 2154–2206)
**Section title:** `"Firefox Extensions"`
**Firefox dir:** `~/Library/Application Support/Firefox`
**Profiles source:** `profiles.ini` in that dir

**Profile enumeration:**
```python
profiles_ini = ff_dir / "profiles.ini"
# grep '^Path=' lines, extract values, strip \r
```
Each `Path=` value is a relative path from `ff_dir`. E.g., `Profiles/abc123.default`.
Build: `ff_dir / rel_path / "extensions.json"`.

**extensions.json schema (relevant fields):**
```json
{
  "addons": [
    {
      "id": "addon@id",
      "version": "1.0",
      "location": "app-profile",
      "defaultLocale": {"name": "Extension Name"}
    }
  ]
}
```

**Location filter:** Only include entries where `location == "app-profile"`.
Exclude: `"app-builtin"`, `"app-builtin-addons"` (system add-ons).

**Extract per entry:**
- `name` = `addon.get("defaultLocale", {}).get("name")` — fallback to `id` if null/absent
- `version` = `addon.get("version", "")`
- `id_` = `addon.get("id", "")`
- Skip if `id_` is empty or `"null"`

**emit_item:** `emit_item(name, version, id_)` → `"name (version) [id]"`

**Cross-profile dedup:** Same as Chrome — accumulate items across all profiles, one `flush_section`
call at the end.

**Availability:** `profiles_ini.is_file()`. Fallback message (stdout):
```
NOTE: Firefox not installed.
```

---

## MCP Transport Safety (CAT-05)

This section is the definitive reference for the single most important safety invariant.

### The Rule

For all four MCP collectors (Claude MCP, Codex MCP, OpenCode MCP, Gemini MCP):

**Read ONLY:**
- The server name (object key)
- The `type` field (transport label)

**NEVER read:**
- `command` — executable path + may reveal secrets
- `args` — command arguments may contain tokens
- `env` — environment variables ARE secrets (API keys, tokens)
- `url` — may contain bearer tokens in query strings
- `headers` — bearer tokens, auth headers

### Transport Extraction Pattern

```python
# For all MCP collectors — this is the ONLY json access permitted:
for name, server_cfg in mcp_servers.items():
    transport = server_cfg.get("type", "stdio")  # ONLY .type
    if transport not in ("stdio", "http", "sse"):
        transport = "stdio"
    line = emit_item(name, "", transport)
    if line:
        items.append(line)
```

### Secret-Check Grep (success criterion 3)

The output file must produce zero hits for:
```bash
grep -Ei 'token|Bearer|sk-|ghp_|key=|Authorization' catalog.txt
```

### Per-Collector MCP Source Mapping

| Collector | Config File | JSON Path to Servers | Transport Field |
|-----------|-------------|---------------------|-----------------|
| Claude MCP | `~/.claude.json` | `.mcpServers` | `.value.type` |
| Codex MCP (CLI) | n/a | `.[].name` + `.[].type` | `.[].type` |
| Codex MCP (TOML) | `~/.codex/config.toml` | `[mcp_servers.NAME]` headers only | defaults to `"stdio"` |
| OpenCode MCP | `~/.config/opencode/opencode.json` | `.mcp` | `.value.type` |
| Gemini MCP | `~/.gemini/config/mcp_config.json` | `.mcpServers` | `.value.type` |

---

## Subprocess Safety and Mocking Strategy

### Collectors That Shell Out

| Collector | Commands | Mock Strategy |
|-----------|----------|---------------|
| Homebrew | `["brew", "list", "--formula"]`, `["brew", "list", "--cask"]` | `subprocess.run` monkeypatch |
| App Store | `["mas", "list"]` | `subprocess.run` monkeypatch |
| VS Code | `["code", "--list-extensions", "--show-versions"]` | `shutil.which` + `subprocess.run` monkeypatch |
| Cursor | `["cursor", "--list-extensions", "--show-versions"]` | `shutil.which` + `subprocess.run` monkeypatch |
| Codex MCP | `["codex", "mcp", "list", "--json"]` | `shutil.which` + `subprocess.run` monkeypatch |

### Shell=False (Required)

All subprocess calls use the list form and `shell=False` (default). No `os.system()`,
no shell string interpolation. This is a security constraint, not just style.

### CI Mocking Pattern

All collectors that call external tools MUST be mockable so tests run on CI without the
tools installed:

```python
# In tests/collectors/test_homebrew.py
import subprocess
from unittest.mock import patch, MagicMock

def test_homebrew_collect(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = "git\nnode\n"
    mock_result.returncode = 0
    with patch("shutil.which", return_value="/usr/local/bin/brew"), \
         patch("subprocess.run", return_value=mock_result):
        collector = HomebrewCollector()
        result = collector.collect()
    # assert section contents
```

### Filesystem-Only Collectors

Claude plugins, Claude skills/agents, OpenCode plugins/agents, Gemini extensions/MCP,
Chrome, Firefox, Setapp, Web apps — all parse the filesystem only. Tests use `tmp_path`
fixture to create synthetic directory structures. No subprocess mocking needed.

---

## Section Order and REGISTRY

The canonical section order (from `generate_catalog`, lines 2220–2313) is:

```
1.  Installed Mac Software List   ← header section
2.  Homebrew Packages
3.  App Store Applications
4.  Setapp Applications
5.  Web-installed Applications
6.  Claude Code Plugins
7.  Claude Code MCP Servers
8.  Claude Code Skills & Agents
9.  Codex MCP Servers
10. OpenCode Plugins
11. OpenCode MCP Servers
12. OpenCode Agents
13. Gemini CLI Extensions
14. Gemini CLI MCP Servers
15. VS Code Extensions
16. Cursor Extensions
17. Google Chrome Extensions
18. Firefox Extensions
```

Section 1 (header) is not a collector — it is a write_section call by the orchestrator.
Sections 2–18 map to 12 collector classes (some yielding multiple sections).

The `REGISTRY` list in `collectors/__init__.py` must produce sections in exactly this order.
Multi-section collectors (Claude → 3, OpenCode → 3, Gemini → 2) must return their sections
in the correct internal order within their `CollectorResult`.

**Phase 16 consumes REGISTRY** to iterate collectors and write sections. Phase 15 must get
the order right. A test that verifies `[section.title for c in REGISTRY for s in c.collect().sections]`
matches the expected list is a Phase-15 deliverable.

---

## Raw-Write vs. emit_item/flush_section Split

This is the most important architectural distinction in this phase.

### Collectors that bypass emit_item/flush_section (raw write)

| Collector | Raw output | Notes |
|-----------|-----------|-------|
| Homebrew | `brew list --formula` then `brew list --cask` output verbatim | No sort, no dedup |
| App Store | `mas list \| awk '{print $2, $3}'` output verbatim | No sort, no dedup |
| Setapp | `find \| sort` — sorted by find+sort pipeline | Python: `sorted()` acceptable |
| Web-installed | `find \| sort` — sorted by find+sort pipeline | Python: `sorted()` acceptable |

For these four, `collect()` returns a `Section` whose items list contains the raw output lines.
The Phase-16 orchestrator writes them with `write_lines()` WITHOUT calling `flush_section()`.

This requires a marker on `Section` to indicate whether `flush_section` should be called:

```python
@dataclass
class Section:
    title: str
    items: list[str]
    raw: bool = False  # if True, orchestrator writes items directly without flush_section
```

### Collectors that use emit_item/flush_section (standard pipeline)

All AI CLI collectors, VS Code, Cursor, Chrome, Firefox — emit_item builds lines, flush_section
sorts and deduplicates. `section.raw = False` (default).

---

## Common Pitfalls (Phase 15 Specific)

### Pitfall A: Routing Homebrew/mas/Setapp/Web through flush_section

**What goes wrong:** The zsh writes these sections by raw `>> "$OUTPUT_FILE"` — not through the
`emit_item`/`flush_section` pipeline. If the Python port runs these through `flush_section`, the
output will be sorted/deduplicated differently than the zsh reference. Homebrew formulae are
output in brew's own order; `flush_section` would re-sort them differently.

**How to avoid:** Use `section.raw = True` for these four collectors. The Phase-16 orchestrator
writes them with `write_lines()` only, not `flush_section()`.

**Warning signs:** Homebrew section in Python output has different line order than zsh reference.

---

### Pitfall B: Missing the Gemini mcp_config.json empty-file guard

**What goes wrong:** `[[ -f path ]]` is True for a 0-byte file. The zsh explicitly uses
`[[ -s path ]]` for `mcp_config.json` because the file can exist but be empty. Python's
`path.is_file()` returns True for empty files. Passing an empty file to `json.loads()` raises
`json.JSONDecodeError`, which must be caught — but the zsh catches this at the guard level,
not in a try/except.

**How to avoid:**
```python
mcp_path = Path.home() / ".gemini/config/mcp_config.json"
if not mcp_path.is_file() or mcp_path.stat().st_size == 0:
    return self.degraded_result(title)
```

---

### Pitfall C: Including `/Applications` and `/Applications/Setapp` as entries

The `find` commands in the zsh include the start directory itself (e.g., `find "/Applications" -maxdepth 1 -type d` produces `/Applications` as its first result, which `basename` converts to `"Applications"`). Python's `Path.iterdir()` does NOT include the directory itself.

For byte parity, both `WebAppsCollector` and `SetappCollector` must prepend the root directory's basename to their output before sorting, to match what `find` + `basename` produces.

Verify this against the actual zsh output during Phase 17 golden fixture creation.

---

### Pitfall D: VS Code relativeLocation path construction

The zsh builds the path as `"$ext_dir/$rel_loc/package.json"`. If `rel_loc` begins with
the extension ID and version (e.g., `"ms-python.python-2025.1.0-linux-x64"`), the full path
is `~/.vscode/extensions/ms-python.python-2025.1.0-linux-x64/package.json`. This is the path
passed to `resolve_vsc_ext_name`. If `rel_loc` is empty (not found in extensions.json), use
`ext_id` as `display_name` directly (no resolve_vsc_ext_name call).

---

### Pitfall E: Firefox profiles.ini `\r` in Path= values

The zsh strips `\r` with `tr -d '\r'` when reading `Path=` values from `profiles.ini`. The file
uses Windows-style CRLF line endings on some Firefox versions. Python's text-mode file reading
with universal newlines (`newline=None`, the default) handles this automatically. But an explicit
`path.read_text().splitlines()` is safer than `.split("\n")` which would leave `\r` at line ends.

---

### Pitfall F: CAT-05 regression via json_get

`json_get(file, "command")` on an MCP config file would extract the command field.
The MCP collectors MUST NOT call `json_get` for any field except `type`. A reviewer should be
able to inspect each MCP collector and verify that the ONLY `json_get` or `.get()` calls on
server config entries are for `"type"`.

---

### Pitfall G: Codex TOML fallback reads value lines

The grep pattern `^\[mcp_servers\.` matches ONLY section headers. A naive Python TOML parser
(`tomllib.loads`) would parse the entire file and give access to all values including `command`,
`env`, etc. The TOML fallback MUST use text-file grep (not `tomllib`) to avoid touching secret
values. Only section header NAME is extracted.

---

## Code Examples

### MCP Collector Template (CAT-05 compliant)

```python
# Source: zsh update-list.sh:1638-1681 (collect_claude_mcp)
from pathlib import Path
import json
from maccat.catalog.format import emit_item, flush_section
from maccat.collectors.base import Collector, CollectorResult, Section

_TRANSPORT_WHITELIST = frozenset({"stdio", "http", "sse"})

class ClaudeMCPCollector(Collector):
    TITLE = "Claude Code MCP Servers"
    _config = Path.home() / ".claude.json"

    def available(self) -> bool:
        return self._config.is_file()

    def collect(self) -> CollectorResult:
        if not self.available():
            return self.degraded_result(self.TITLE)
        try:
            data = json.loads(self._config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self.degraded_result(self.TITLE)

        items: list[str] = []
        for name, cfg in (data.get("mcpServers") or {}).items():
            # CAT-05: ONLY .type — no .command, .env, .args, .url, .headers
            transport = cfg.get("type", "stdio")
            if transport not in _TRANSPORT_WHITELIST:
                transport = "stdio"
            line = emit_item(name, "", transport)
            if line:
                items.append(line)
        return CollectorResult(sections=[Section(title=self.TITLE, items=items)])
```

### Filesystem Collector with Null-Glob-Equivalent

```python
# Source: zsh update-list.sh:1692-1731 (collect_claude_skills_agents)
def _collect_skills(skills_dir: Path) -> list[str]:
    items: list[str] = []
    if not skills_dir.is_dir():
        return items
    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        skill_md = skill_path / "SKILL.md"
        name = _read_yaml_name(skill_md) if skill_md.is_file() else ""
        if not name:
            name = skill_path.name
        line = emit_item(name, "", "")
        if line:
            items.append(line)
    return items
```

### Chrome Extension Collector with version_sort_tail

```python
# Source: zsh update-list.sh:2074-2137 (collect_chrome_extensions)
from maccat.catalog.format import emit_item, version_sort_tail
from maccat.helpers.chrome_name import chrome_ext_name
from maccat.helpers.json_io import json_get

COMPONENT_DENYLIST = frozenset({
    "nmmhkkegccagdldgiimedpiccmgmieda",
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi",
    "aapocclcgogkmnckokdopfmhonfmgoek",
    "blpcfgokakmgnkcojhhkbfbldkacnbeo",
    "felcaaldnbdncclmgdcncolpebgiejap",
    "aohghmighlieiainnegkcijnfilokake",
    "apdfllckaahabafndbhieahigkjlhalf",
    "pjkljhegncpnkpknbcohdijeoejaedia",
    "mhjfbmdgcfjbbpaeojofohoefgiehjai",
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm",
})

def _collect_profile(extensions_dir: Path) -> list[str]:
    items: list[str] = []
    for ext_dir in extensions_dir.iterdir():
        if not ext_dir.is_dir():
            continue
        ext_id = ext_dir.name
        if ext_id == "Temp" or ext_id.startswith("_") or ext_id in COMPONENT_DENYLIST:
            continue
        candidates = [d.name for d in ext_dir.iterdir() if d.is_dir()]
        ver_dir = version_sort_tail(candidates)  # Phase 13 helper
        if not ver_dir:
            continue
        manifest = ext_dir / ver_dir / "manifest.json"
        if not manifest.is_file():
            continue
        name = chrome_ext_name(manifest)
        version = json_get(manifest, "version")
        line = emit_item(name, version, ext_id)
        if line:
            items.append(line)
    return items
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `find "/Applications" -maxdepth 1 -type d` includes `/Applications` itself as first result, producing `"Applications"` in output | Collector 4 (Web-installed) | Python port would miss one line; golden parity test would catch it |
| A2 | `find "/Applications/Setapp" -maxdepth 1 -type d` includes `/Applications/Setapp` itself, producing `"Setapp"` in output | Collector 3 (Setapp) | Same as A1 |
| A3 | Codex `codex mcp list --json` returns a JSON array of `{"name": "...", "type": "..."}` objects | Collector 8 | CLI fallback path is always available; worst case all Codex MCP degrades to TOML fallback |
| A4 | `mas list` output format is `<id>  <AppName> (<version>)` (id in col 1, name in col 2, version in col 3) | Collector 2 | awk `{print $2, $3}` would produce wrong fields |

---

## Open Questions (RESOLVED)

> Q1 (find start-directory inclusion) — RESOLVED: implemented per the POSIX assumption (Pitfall C in every collector plan, root basename explicitly prepended); definitive golden-fixture verification deferred to Phase 17 per Assumptions Log A1/A2.
> Q2 (VS Code `@` delimiter) — RESOLVED: split extension lines on the LAST `@` via `rsplit("@", 1)`.
> Q3 (`claude mcp list` vs `~/.claude.json`) — RESOLVED: parse `~/.claude.json` directly (file parse), not via the CLI.

1. **Do `find` commands include the start directory itself in this specific usage?**
   - What we know: POSIX `find path` includes `path` itself as the first match. The zsh behavior
     produces "Applications" and "Setapp" as entries in the respective sections.
   - What's unclear: This should be verified against the actual zsh output during Phase 17 golden
     fixture creation. The Phase 17 golden fixtures will definitively resolve this.
   - Recommendation: Implement BOTH versions (with and without root) and gate behind the golden
     fixture. Assume inclusion for now (it's the POSIX standard behavior).

2. **VS Code `code --list-extensions --show-versions` — does it `@`-delimit with the last `@`?**
   - What we know: `code --list-extensions --show-versions` outputs `publisher.extension@version`.
     The zsh splits on the last `@` using `${line%@*}` (strip from last `@`) and `${line##*@}`.
   - What's unclear: Publisher names or extension names that contain `@` (rare but possible).
   - Recommendation: Use Python `line.rsplit("@", 1)` to replicate `${line%@*}` / `${line##*@}`.

3. **STATE.md Open Question: `claude mcp list --json` vs `~/.claude.json` parsing**
   - The zsh uses `~/.claude.json` directly (file parse, not CLI). This is already confirmed.
     The STATE.md note about verifying `claude mcp list --json` is resolved: the zsh does NOT
     use a `claude` CLI call for MCP listing — it parses `~/.claude.json` directly.
     The Python port must also parse `~/.claude.json` directly.

---

## Environment Availability

| Dependency | Required By | Available on dev machine | Fallback |
|------------|------------|--------------------------|---------|
| `brew` | HomebrewCollector | Yes (macOS with Homebrew) | Mocked in tests; graceful degrade in production |
| `mas` | MasCollector | Yes (via brew) | Mocked in tests; graceful degrade |
| `code` CLI | VSCodeCollector | Yes (VS Code installed) | extensions.json fallback |
| `cursor` CLI | CursorCollector | Yes (Cursor installed) | extensions.json fallback |
| `codex` CLI | CodexMCPCollector | Yes | TOML grep fallback |
| `~/.claude.json` | ClaudeMCPCollector | Yes | flush_section (none found) |
| `~/.vscode/extensions/` | VSCodeCollector | Yes | flush_section (none found) |
| `~/Library/.../Google/Chrome` | ChromeCollector | Yes | flush_section (none found) |
| `~/Library/.../Firefox` | FirefoxCollector | Unknown on dev machine | flush_section (none found) |
| `pytest` | All tests | Yes (Phase 13 dev dep) | — |

All dependencies have graceful fallback paths. No missing dependency blocks execution.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed, Phase 13) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| Quick run command | `./venv/bin/pytest tests/collectors/ -x -q` |
| Full suite command | `./venv/bin/pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAT-01 | All collectors produce output for their section | unit | `pytest tests/collectors/ -x` | No — Wave 0 |
| CAT-05 | MCP collectors never emit secrets | unit (grep on output) | `pytest tests/collectors/test_claude.py tests/collectors/test_codex.py tests/collectors/test_opencode.py tests/collectors/test_gemini.py -k mcp -x` | No — Wave 0 |
| CAT-06 | Absent source → `(none found)`, no abort | unit | `pytest tests/collectors/ -k absent -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `./venv/bin/pytest tests/collectors/ -x -q` (collector tests only)
- **Per wave merge:** `./venv/bin/pytest -x -q` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/collectors/__init__.py` — empty package marker
- [ ] `tests/collectors/test_homebrew.py` — covers Homebrew + mas availability/degrade
- [ ] `tests/collectors/test_setapp.py` — covers Setapp + Web-installed
- [ ] `tests/collectors/test_claude.py` — covers plugins, MCP (CAT-05), skills/agents
- [ ] `tests/collectors/test_codex.py` — covers CLI path, TOML fallback, CAT-05
- [ ] `tests/collectors/test_opencode.py` — covers plugins, MCP (CAT-05), agents
- [ ] `tests/collectors/test_gemini.py` — covers extensions, MCP + empty-file guard, CAT-05
- [ ] `tests/collectors/test_vscode.py` — covers CLI path, JSON fallback, NLS resolution
- [ ] `tests/collectors/test_cursor.py` — covers same as VS Code with different paths
- [ ] `tests/collectors/test_chrome.py` — covers all profiles, denylist, version_sort_tail
- [ ] `tests/collectors/test_firefox.py` — covers profiles.ini, location filter, dedup

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | n/a — read-only tool, no auth |
| V3 Session Management | No | n/a |
| V4 Access Control | No | n/a |
| V5 Input Validation | Partial | MCP transport whitelist (`stdio|http|sse`); OpenCode plugin path/URL guard |
| V6 Cryptography | No | n/a |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| MCP secret leakage via `.env`/`.command` | Information Disclosure | Read ONLY `.type` field; whitelist transport values |
| Subprocess injection via user-controlled paths | Elevation of Privilege | `shell=False` always; list form subprocess calls |
| Chrome/Firefox extension reading wrong version dir | Tampering | `version_sort_tail` via `sort -V` subprocess |
| OpenCode plugin path/URL in `.plugin[]` array | Information Disclosure | Skip entries without `@` separator that contain `/` |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `jq`/`plutil` subprocess chain for JSON parsing | Python `json.loads()` directly | Phase 13 decision | Simpler, faster, no jq dependency |
| `LC_ALL=C sort -f -u` via shell | subprocess call to system `sort` | Phase 13 decision | Byte-identical output guaranteed |
| Single-file Zsh script with `>> "$OUTPUT_FILE"` side effects | `Collector.collect()` returns data; orchestrator writes | This phase | Unit-testable collectors |

---

## Sources

### Primary (HIGH confidence)

- `update-list.sh` — full read of all 12 collector functions; exact line numbers cited throughout.
  This is the byte-parity spec and is the only authoritative source. [VERIFIED: direct read]
- `src/maccat/catalog/format.py` — confirmed `emit_item`, `flush_section`, `version_sort_tail`
  are built and match the contracts documented above. [VERIFIED: direct read]
- `src/maccat/catalog/writer.py` — confirmed `CatalogWriter`, `write_section`, `write_lines`
  are built with correct `newline="\n"` and atomic semantics. [VERIFIED: direct read]
- `src/maccat/helpers/` — confirmed `json_io.py`, `chrome_name.py`, `vsc_name.py` are built
  and tested (54 tests passing). [VERIFIED: direct read of SUMMARY files]
- `.planning/phases/13-*/13-03-SUMMARY.md` — confirmed Phase 13 helper API contracts.
  [VERIFIED: direct read]
- `.planning/phases/14-*/14-04-SUMMARY.md` — confirmed Phase 14 config.py is built.
  [VERIFIED: direct read]

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — Collector ABC + registry design; stale package name
  (maclist → maccat, already translated above). [CITED: planning artifact]
- `.planning/research/PITFALLS.md` — Pitfalls 1, 2, 3 (sort, version_sort, trailing newline);
  all confirmed from direct zsh read. [CITED: planning artifact]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all reused from Phase 13 (built and tested)
- Per-collector specs: HIGH — derived from direct line-by-line read of `update-list.sh`
- Architecture (Collector ABC): HIGH — confirmed from prior research; simple and testable
- CAT-05 transport safety: HIGH — exact field access documented from zsh source
- Pitfalls: HIGH — derived from actual zsh source and prior milestone defect records
- Open questions (find root-dir inclusion): MEDIUM — POSIX standard but must be verified
  against golden fixtures in Phase 17

**Research date:** 2026-06-14
**Valid until:** Until `update-list.sh` is modified (the file is explicitly untouched — indefinite)

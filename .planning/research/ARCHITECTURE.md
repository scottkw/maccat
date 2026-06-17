# Architecture Research: v2.2.0 Broader Coverage — New Collector Integration

**Domain:** maccat collector extension — Chromium shared abstraction + Edge/Brave/Zed/Safari/Codex Plugins
**Researched:** 2026-06-17
**Confidence:** HIGH

All findings are grounded in direct source reads. File paths and line references point to
the current codebase under `src/maccat/`.

---

## Standard Architecture

### System Overview

```
cli.py: run()
  └── get_registry()  [collectors/__init__.py]
        │
        ├── HomebrewCollector, MasCollector, SetappCollector, WebAppsCollector
        ├── ClaudeCollector, CodexCollector(*), OpenCodeCollector, GeminiCollector
        ├── VSCodeCollector, CursorCollector, ZedCollector(NEW)
        ├── ChromeCollector(*), EdgeCollector(NEW), BraveCollector(NEW)
        ├── SafariCollector(NEW), FirefoxCollector
        │
        (*) CodexCollector: MODIFIED — yields 2 sections instead of 1
        (*) ChromeCollector: REFACTORED — becomes thin subclass of ChromiumBaseCollector

Each Collector.collect() → CollectorResult(sections=[Section(...)])

cli.py orchestration loop (lines 318-327):
  for collector in get_registry():
      result = collector.collect()
      for section in result.sections:
          w.write_section(section.title)
          if section.raw:
              w.write_lines(section.items)
          else:
              w.write_lines(flush_section(section.items))

reinstall/emitter.py SECTION_SOURCE_MAP (lines 230-235):
  → new browser/editor/Codex sections NOT in map
  → fall through to _manual_checklist_block()
  → no changes to emitter.py needed
```

### Component Responsibilities

| Component | Responsibility | File / Status |
|-----------|----------------|---------------|
| `ChromiumBaseCollector` | Parameterized Chromium extension scan (name, base path, denylist) | `collectors/chromium.py` NEW |
| `ChromeCollector` | Chrome-specific paths/title via ChromiumBaseCollector | `collectors/chrome.py` REFACTORED |
| `EdgeCollector` | Edge-specific paths/title via ChromiumBaseCollector | `collectors/edge.py` NEW |
| `BraveCollector` | Brave-specific paths/title via ChromiumBaseCollector | `collectors/brave.py` NEW |
| `ZedCollector` | Reads installed extensions JSON from `~/.config/zed/extensions/` | `collectors/zed.py` NEW |
| `SafariCollector` | Shells out to `pluginkit -mAvvv -p com.apple.Safari.extension` | `collectors/safari.py` NEW |
| `CodexCollector` | MODIFIED: yields 2 sections (MCP Servers + Plugins) | `collectors/codex.py` MODIFIED |
| Registry | Ordered list including all new collectors in catalog section order | `collectors/__init__.py` MODIFIED |
| Reinstall parser | Section-title-agnostic state machine; new sections parse automatically | `reinstall/parser.py` NO CHANGE |
| Reinstall emitter | Routes sections to renderers; new sections fall through to checklist | `reinstall/emitter.py` NO CHANGE |

---

## Recommended Project Structure

```
src/maccat/collectors/
├── base.py               # Collector/Section/CollectorResult — unchanged
├── chromium.py           # NEW: ChromiumBaseCollector (parameterized shared logic)
├── chrome.py             # REFACTORED: thin subclass of ChromiumBaseCollector
├── edge.py               # NEW: thin subclass of ChromiumBaseCollector
├── brave.py              # NEW: thin subclass of ChromiumBaseCollector
├── zed.py                # NEW: ZedCollector standalone
├── safari.py             # NEW: SafariCollector standalone
├── codex.py              # MODIFIED: collect() returns 2 sections
├── __init__.py           # MODIFIED: register new collectors in section order
└── [existing: claude, cursor, firefox, gemini, homebrew, mas, opencode, setapp, vscode, webapps]

tests/collectors/
├── test_chromium.py      # NEW: shared base logic tests
├── test_chrome.py        # MODIFIED: update patch target post-refactor
├── test_edge.py          # NEW: mirrors test_chrome.py structure
├── test_brave.py         # NEW: mirrors test_chrome.py structure
├── test_zed.py           # NEW
├── test_safari.py        # NEW — mocks subprocess.run for pluginkit
└── test_codex.py         # MODIFIED: cover new Codex Plugins section
```

### Structure Rationale

- **`collectors/chromium.py`** — The 3-browser threshold (Chrome, Edge, Brave) satisfies
  the project's "3 real examples before abstracting" rule (CLAUDE.md). All profile-scan
  logic, `COMPONENT_DENYLIST`, `version_sort_tail` selection, and `chrome_ext_name`
  resolution live here once. Thin subclasses supply only browser name + base path.
- **Separate `edge.py` / `brave.py`** rather than a single auto-discovery module — each
  browser gets its own file for clarity, independent patchability in tests, and a clean
  `available()` gate on its specific base directory.
- **`codex.py` extended, not split** — mirrors how `claude.py` (lines 177-185) and
  `gemini.py` return multiple sections from one collector. Adding a second Section to
  `CodexCollector.collect()` is a two-function change with no cross-module impact.

---

## Architectural Patterns

### Pattern 1: Parameterized Chromium Base Collector

**What:** Extract the full body of `chrome.py`'s `_collect_profile` and `collect` into
`chromium.py:ChromiumBaseCollector`, parameterized by `_browser_name: str`, `_base: Path`,
and `_denylist: frozenset[str]`. Chrome, Edge, and Brave subclass it with only those
constants different.

**When to use:** 3+ collectors share identical traversal logic with only path/title
differing — satisfied here by Chrome, Edge, and Brave.

**Integration points from actual source:**

`chrome.py` today:
- `_BASE = Path.home() / "Library/Application Support/Google/Chrome"` (line 32)
- `_TITLE = "Google Chrome Extensions"` (line 33)
- `COMPONENT_DENYLIST: frozenset[str]` (lines 19-30) — 10 component IDs
- `_collect_profile(extensions_dir)` — iterates `Extensions/<id>/<ver>/manifest.json`,
  calls `chrome_ext_name`, `json_get`, `emit_item`, `version_sort_tail` (lines 50-82)
- `collect()` — enumerates Default + `Profile */` dirs, aggregates items (lines 84-103)
- `available()` inherited from `Collector` base — returns `True` unconditionally

**Proposed `chromium.py` (base class):**

```python
class ChromiumBaseCollector(Collector):
    """Shared Chromium extension scan, parameterized by browser name and base path.

    Subclasses set _browser_name, _base, and optionally _denylist.
    """

    _browser_name: str = ""
    _base: Path = Path()
    _denylist: frozenset[str] = frozenset()

    @property
    def _title(self) -> str:
        return f"{self._browser_name} Extensions"

    def available(self) -> bool:
        return self._base.is_dir()

    def collect(self) -> CollectorResult:
        if not self._base.is_dir():
            print(f"  NOTE: {self._browser_name} not installed.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=self._title, items=[])])
        all_items: list[str] = []
        profile_dirs: list[Path] = [self._base / "Default"]
        profile_dirs += sorted(self._base.glob("Profile */"))
        for profile in profile_dirs:
            ext_root = profile / "Extensions"
            if not ext_root.is_dir():
                continue
            all_items.extend(self._collect_profile(ext_root))
        return CollectorResult(sections=[Section(title=self._title, items=all_items)])

    def _collect_profile(self, extensions_dir: Path) -> list[str]:
        # Identical logic to current chrome.py lines 50-82, using self._denylist
        ...
```

**Thin subclasses:**

```python
# chrome.py
_BASE = Path.home() / "Library/Application Support/Google/Chrome"

class ChromeCollector(ChromiumBaseCollector):
    _browser_name = "Google Chrome"
    _base = _BASE
    _denylist = COMPONENT_DENYLIST

# edge.py
_BASE = Path.home() / "Library/Application Support/Microsoft Edge"

class EdgeCollector(ChromiumBaseCollector):
    _browser_name = "Microsoft Edge"
    _base = _BASE
    _denylist = COMPONENT_DENYLIST  # same IDs — all Chromium browsers share these

# brave.py
_BASE = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"

class BraveCollector(ChromiumBaseCollector):
    _browser_name = "Brave"
    _base = _BASE
    _denylist = COMPONENT_DENYLIST
```

**Section titles produced:**
- `"Google Chrome Extensions"` — matches existing catalog output (no format change)
- `"Microsoft Edge Extensions"` — new
- `"Brave Extensions"` — new

**`available()` per browser:**
- Chrome: `Path(".../Google/Chrome").is_dir()`
- Edge: `Path(".../Microsoft Edge").is_dir()`
- Brave: `Path(".../BraveSoftware/Brave-Browser").is_dir()`

**`COMPONENT_DENYLIST` placement:** Move the constant to `chromium.py`. Re-export from
`chrome.py` for backward compatibility with existing tests that import it via
`from maccat.collectors.chrome import COMPONENT_DENYLIST` (line 14 of `test_chrome.py`):

```python
# chrome.py — backward-compat re-export
from maccat.collectors.chromium import COMPONENT_DENYLIST
__all__ = ["ChromeCollector", "COMPONENT_DENYLIST"]
```

**Test patch target migration:** `test_chrome.py` patches `chrome_mod._BASE` via
`patch.object(chrome_mod, "_BASE", ...)` (established in tests like `test_collects_default_profile`).
After the refactor, `ChromeCollector._base = _BASE` reads from the module-level `_BASE`
constant in `chrome.py` at class-definition time. The patch must override the class attribute
itself — the simplest approach is to keep `_BASE` as a module-level constant in each
subclass file so `patch.object(chrome_mod, "_BASE", ...)` continues to work. The base class
reads `self._base` — if the subclass is defined as `_base = _BASE`, patching the module
constant after class definition does NOT retroactively change the class attribute. The correct
patch target post-refactor is `patch.object(ChromeCollector, "_base", new=tmp_path)`.
Update `test_chrome.py` accordingly; document this in `test_chromium.py`.

---

### Pattern 2: Multi-Section Collector (CodexCollector Extension)

**What:** `CodexCollector.collect()` currently returns 1 section ("Codex MCP Servers",
line 119 of `codex.py`). Extend to return 2 sections, matching the `ClaudeCollector`
multi-section pattern.

**Reference from actual source:**

`claude.py` lines 177-185:
```python
def collect(self) -> CollectorResult:
    return CollectorResult(
        sections=[
            self._collect_plugins(),
            self._collect_mcp(),
            self._collect_skills_agents(),
        ]
    )
```

`codex.py` today (lines 105-119):
```python
def collect(self) -> CollectorResult:
    items: list[str] = []
    if shutil.which("codex"):
        items = self._collect_via_cli()
    if not items and _TOML_PATH.is_file():
        items = self._collect_via_toml()
    return CollectorResult(sections=[Section(title=_TITLE, items=items)])
```

**Proposed extension:**

Add module-level constants:
```python
_MCP_TITLE = "Codex MCP Servers"      # rename from _TITLE (same string value)
_PLUGINS_TITLE = "Codex Plugins"      # new
_PLUGINS_PATH = Path.home() / ".codex/plugins.json"   # verify path before implementing
```

Refactor existing logic into `_collect_mcp(self) -> Section` (rename from inline in
`collect()`). Add `_collect_plugins(self) -> Section` mirroring `ClaudeCollector._collect_plugins`
structure (lines 75-100 of `claude.py`).

Change `collect()`:
```python
def collect(self) -> CollectorResult:
    return CollectorResult(
        sections=[
            self._collect_mcp(),
            self._collect_plugins(),
        ]
    )
```

Section order: MCP Servers first (position 8 in current catalog), Plugins second (new
position 9). This matches the Codex-as-AI-CLI ordering convention: MCPs before plugins,
consistent with Claude's Plugins → MCP Servers → Skills order being tool-specific rather
than universal.

**Caveat:** The Codex plugin system path (`~/.codex/plugins.json` or equivalent) must be
confirmed against an actual Codex installation before implementation (see Pitfall 1).

---

### Pattern 3: Standalone New Collectors (Zed + Safari)

**What:** New collectors that share no logic with existing collectors. Each is a single
file implementing `Collector` directly, following the established graceful-degradation pattern.

#### 3a: ZedCollector

**File:** `collectors/zed.py`

**Data source:** `~/.config/zed/extensions/installed_extensions.json`

JSON structure (from Zed open-source documentation and source): a top-level object where
keys are extension IDs and values are objects with `"version"` and other metadata fields.
Example: `{"some-extension-id": {"version": "1.2.3", ...}, ...}`

This is the installed-extensions index. `extension.toml` lives inside each extension's
source directory and is for authoring — the installed index is JSON. No `tomllib` needed.

**Helpers used:** `json.loads()` directly (same pattern as `claude.py` lines 84-99). The
`json_io.py:json_get()` helper handles dotted keys but is less natural for top-level
object iteration; use `json.loads()` + `.items()` directly.

**emit_item call:** `emit_item(name, version, ext_id)` — name from `meta.get("name", ext_id)`,
version from `meta.get("version", "")`, id is the dict key.

**Proposed structure:**

```python
_BASE = Path.home() / ".config/zed/extensions"
_INSTALLED = _BASE / "installed_extensions.json"
_TITLE = "Zed Extensions"

class ZedCollector(Collector):
    def available(self) -> bool:
        return _INSTALLED.is_file()

    def collect(self) -> CollectorResult:
        if not _INSTALLED.is_file():
            print("  NOTE: Zed not installed or no extensions found.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])
        try:
            data = json.loads(_INSTALLED.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])
        if not isinstance(data, dict):
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])
        items: list[str] = []
        for ext_id, meta in data.items():
            version = ""
            name = ext_id  # fallback
            if isinstance(meta, dict):
                version = str(meta.get("version", ""))
                name = str(meta.get("name", ext_id)) or ext_id
            line = emit_item(name, version, ext_id)
            if line:
                items.append(line)
        return CollectorResult(sections=[Section(title=_TITLE, items=items)])
```

No new helpers. No new imports beyond what `codex.py` already uses.

#### 3b: SafariCollector

**File:** `collectors/safari.py`

**Data source:** `pluginkit -mAvvv -p com.apple.Safari.extension`

`pluginkit` is `/usr/bin/pluginkit` — a macOS built-in present on macOS 10.10+. It enumerates
PlugIn-based extensions registered with the system, including Safari extensions packaged as
app extensions inside `.app` bundles.

**Subprocess pattern:** mirrors `codex.py` lines 53-61:
```python
result = subprocess.run(
    ["pluginkit", "-mAvvv", "-p", "com.apple.Safari.extension"],
    capture_output=True, text=True, shell=False,
)
```

**Output format (approximate, subject to macOS version variation):**
```
com.example.SomeApp.Extension (1.0)
    Path = /Applications/SomeApp.app/Contents/PlugIns/SomeExtension.appex
    Flags = [  ]
    Display Name = Some App Extension
    ...
```

The bundle identifier appears on the first line of each block (before the path/flags lines).
The display name and version are embedded in the block. The exact format is undocumented
and varies — the parser must treat every field as optional.

**Parser approach:** Extract bundle ID from lines matching `^[a-z0-9.]+\s+\(.*\)` or
similar; extract display name from `Display Name =` lines; extract version from `\(x.y.z\)`
suffix on the first line. Degrade: if display name absent, use bundle ID. If version absent,
emit name-only.

**Graceful degradation contract:**
- Non-zero exit OR empty stdout → `items=[]`, no error printed (zero extensions is valid)
- `pluginkit` absent → `items=[]` + NOTE to stderr
- Parse error on any block → skip that block, continue

**Proposed structure:**

```python
_TITLE = "Safari Extensions"

class SafariCollector(Collector):
    def available(self) -> bool:
        return bool(shutil.which("pluginkit"))

    def collect(self) -> CollectorResult:
        if not shutil.which("pluginkit"):
            print("  NOTE: pluginkit not available.", file=sys.stderr)
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])
        result = subprocess.run(
            ["pluginkit", "-mAvvv", "-p", "com.apple.Safari.extension"],
            capture_output=True, text=True, shell=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return CollectorResult(sections=[Section(title=_TITLE, items=[])])
        items = _parse_pluginkit_output(result.stdout)
        return CollectorResult(sections=[Section(title=_TITLE, items=items)])


def _parse_pluginkit_output(output: str) -> list[str]:
    """Parse pluginkit -mAvvv output into emit_item lines.

    Treats every field as optional. Degrades to name-only or id-only on missing fields.
    Never raises.
    """
    ...
```

`_parse_pluginkit_output` is the highest-risk function in the milestone — it must be
validated against real `pluginkit` output before finalizing (see Pitfall 2).

---

## Data Flow

### Catalog Generation with New Collectors

```
cli.py: run() line 318
  │
  └── for collector in get_registry():
        result = collector.collect()     ← never raises (graceful degradation)
        for section in result.sections:
          w.write_section(section.title) ← title written unconditionally
          w.write_lines(flush_section(section.items))
                        ↑
                        if items=[] → emits "  (none found)"
                        if browser not installed → items=[] → "(none found)"
```

### Reinstall Pipeline (unchanged)

```
reinstall/parser.py:parse_catalog()
  │  ← title-agnostic state machine (lines 166-232)
  │  ← reads ANY section title — no hardcoded title list
  │
  └── ParsedCatalog containing (new sections parsed automatically):
        ParsedSection("Microsoft Edge Extensions", items=[...])
        ParsedSection("Brave Extensions", items=[...])
        ParsedSection("Zed Extensions", items=[...])
        ParsedSection("Safari Extensions", items=[...])
        ParsedSection("Codex Plugins", items=[...])

reinstall/emitter.py:emit_reinstall_script()
  │
  ├── SECTION_SOURCE_MAP.get(section.title)  ← new titles NOT in map (lines 230-235)
  │                                          ← fall through to manual_sections list
  └── _manual_checklist_block(section)       ← echoed as manual checklist
                                             ← correct: browser exts + Codex plugins
                                                cannot be auto-installed (MAN-01)
```

### Registry Insertion Order

Current registry (`collectors/__init__.py` lines 57-70):
```
1.  HomebrewCollector
2.  MasCollector
3.  SetappCollector
4.  WebAppsCollector
5.  ClaudeCollector        → 3 sections (5, 6, 7)
6.  CodexCollector         → 1 section  (8)
7.  OpenCodeCollector      → 3 sections (9, 10, 11)
8.  GeminiCollector        → 2 sections (12, 13)
9.  VSCodeCollector        → section 14
10. CursorCollector        → section 15
11. ChromeCollector        → section 16
12. FirefoxCollector       → section 17
```

**Proposed new registry order** (22 sections from 16 collectors):
```
1.  HomebrewCollector
2.  MasCollector
3.  SetappCollector
4.  WebAppsCollector
5.  ClaudeCollector        → 3 sections (5, 6, 7)
6.  CodexCollector         → 2 sections (8="Codex MCP Servers", 9="Codex Plugins") [MODIFIED]
7.  OpenCodeCollector      → 3 sections (10, 11, 12)
8.  GeminiCollector        → 2 sections (13, 14)
9.  VSCodeCollector        → section 15
10. CursorCollector        → section 16
11. ZedCollector           → section 17  [NEW]
12. ChromeCollector        → section 18
13. EdgeCollector          → section 19  [NEW]
14. BraveCollector         → section 20  [NEW]
15. SafariCollector        → section 21  [NEW]
16. FirefoxCollector       → section 22
```

**Ordering rationale:**
- AI-CLI tools (Claude, Codex, OpenCode, Gemini) grouped first after system software —
  matches existing order.
- Editors (VS Code, Cursor, Zed) grouped contiguously — natural affinity, existing
  VS Code + Cursor ordering preserved, Zed inserted after.
- Browsers grouped at the end (Chrome, Edge, Brave, Safari, Firefox) — matches existing
  Chrome + Firefox ordering; Chromium-family browsers contiguous (18, 19, 20) for catalog
  readability; Safari between Brave and Firefox.
- CodexCollector stays at registry position 6 — its second Section ("Codex Plugins")
  appears immediately after "Codex MCP Servers" in the output without any registry change,
  because `collect()` returns both Sections in a single `CollectorResult`.

**Registry code change (`collectors/__init__.py`):**

```python
def get_registry() -> list[Collector]:
    from maccat.collectors.brave import BraveCollector    # NEW
    from maccat.collectors.chrome import ChromeCollector
    from maccat.collectors.edge import EdgeCollector      # NEW
    from maccat.collectors.safari import SafariCollector  # NEW
    from maccat.collectors.zed import ZedCollector        # NEW
    # ... existing imports unchanged ...

    return [
        HomebrewCollector(),
        MasCollector(),
        SetappCollector(),
        WebAppsCollector(),
        ClaudeCollector(),       # 3 sections
        CodexCollector(),        # 2 sections [was 1]
        OpenCodeCollector(),     # 3 sections
        GeminiCollector(),       # 2 sections
        VSCodeCollector(),
        CursorCollector(),
        ZedCollector(),          # NEW
        ChromeCollector(),
        EdgeCollector(),         # NEW
        BraveCollector(),        # NEW
        SafariCollector(),       # NEW
        FirefoxCollector(),
    ]
```

---

## Reinstall Impact Assessment

**Parser (`reinstall/parser.py`): NO CHANGES NEEDED.**

The state machine (lines 166-232) identifies sections by the `SEPARATOR` constant (36
dashes, line 41), not by hardcoded title names. All five new section titles are parsed
into `ParsedSection` objects automatically with zero code changes. Confirmed by reading
the full parser source.

**Emitter (`reinstall/emitter.py`): NO CHANGES NEEDED.**

`SECTION_SOURCE_MAP` (lines 230-235) maps 4 known section titles to specific renderers:
```python
SECTION_SOURCE_MAP: dict[str, Callable[[ParsedSection], str]] = {
    "Homebrew Packages": _brew_block,
    "App Store Applications": _mas_block,
    "VS Code Extensions": lambda section: _editor_ext_block(section, editor="code"),
    "Cursor Extensions": lambda section: _editor_ext_block(section, editor="cursor"),
}
```

New section titles not present in this dict fall through to `manual_sections` (lines 281-295):
```python
renderer = SECTION_SOURCE_MAP.get(section.title)
if renderer is not None:
    blocks.append(renderer(section))
else:
    manual_sections.append(section)
```

This is the correct behavior for all v2.2.0 additions:
- "Microsoft Edge Extensions", "Brave Extensions", "Safari Extensions", "Google Chrome
  Extensions", "Firefox Extensions" — browser extensions have no CLI installer
- "Zed Extensions" — no CLI installer
- "Codex Plugins" — falls through (same as "Claude Code Plugins" and all other AI-CLI
  plugins, which already fall through)

The MAN-01 decision from v2.1.0 ("Setapp/web/browser/AI-CLI sources emitted as a manual
checklist only — no fabricated installs") explicitly governs all v2.2.0 additions.

**Conclusion: the reinstall pipeline requires zero changes for v2.2.0.** The additive-only
architecture of the parser/emitter was designed to accommodate exactly this scenario.

---

## Anti-Patterns

### Anti-Pattern 1: Duplicating `_collect_profile` in Edge and Brave

**What people do:** Copy `chrome.py` to `edge.py` and `brave.py`, changing only `_BASE`
and the section title string.

**Why it's wrong:** Three identical copies of the 32-line `_collect_profile` logic means
three places to fix any bug in version selection, denylist filtering, or `chrome_ext_name`
resolution. The project's "3 real examples before abstracting" rule is now satisfied — copy
is the wrong answer.

**Do this instead:** Introduce `chromium.py:ChromiumBaseCollector`. Each subclass is 3
lines. Total new code is less than one copy of `_collect_profile`.

---

### Anti-Pattern 2: Separate Collector File for Codex Plugins

**What people do:** Create `codex_plugins.py:CodexPluginsCollector` as a new registry
entry alongside the existing `CodexCollector`.

**Why it's wrong:** Creates two registry entries for one logical source. Diverges from the
established multi-section pattern that `claude.py` (3 sections), `opencode.py` (3 sections),
and `gemini.py` (2 sections) all follow. The `get_registry()` docstring annotates each
collector with its section count — a second Codex collector breaks that convention.

**Do this instead:** Add `_collect_plugins(self) -> Section` to `CodexCollector` and
extend `collect()` to return both sections, exactly as `ClaudeCollector` does (lines
177-185 of `claude.py`).

---

### Anti-Pattern 3: `COMPONENT_DENYLIST` Remaining Only in `chrome.py` After Refactor

**What people do:** Leave `COMPONENT_DENYLIST` in `chrome.py` after extracting
`ChromiumBaseCollector` to `chromium.py`, then import it from `chrome.py` in `edge.py`
and `brave.py`.

**Why it's wrong:** Creates a directional import dependency from `edge.py`/`brave.py`
onto `chrome.py`. The denylist is a Chromium-level constant — all Chromium browsers share
the same pre-installed component extension IDs. It belongs in the base module.

**Do this instead:** Move `COMPONENT_DENYLIST` to `chromium.py`. Re-export it from
`chrome.py` for backward compatibility with `test_chrome.py` line 14
(`from maccat.collectors.chrome import COMPONENT_DENYLIST`).

---

### Anti-Pattern 4: Using `tomllib` for Zed Extension Discovery

**What people do:** Assume Zed uses TOML for its installed-extensions index because
individual extension metadata (`extension.toml`) is TOML.

**Why it's wrong:** The installed-extensions index at
`~/.config/zed/extensions/installed_extensions.json` is JSON. `extension.toml` is the
authoring manifest inside an extension's source tree — not the installed-extensions index.
`tomllib` would also require Python 3.11+ (the project targets 3.10+).

**Do this instead:** Use `json.loads()` on `installed_extensions.json`. Same pattern as
`codex.py` and `claude.py`.

---

### Anti-Pattern 5: Assuming `pluginkit` Has a Stable Parseable Format

**What people do:** Write `_parse_pluginkit_output` assuming a fixed column layout
across macOS versions.

**Why it's wrong:** `pluginkit` is an undocumented internal tool with no public API
contract. Output format can differ across macOS versions. Non-zero exit occurs on machines
with no Safari extensions (valid state, not an error).

**Do this instead:** Treat every field as optional. Use `try/except Exception` around
the full parse. If a block has no `Display Name`, use the bundle ID. If version is absent,
emit name-only. If exit code is non-zero, return `items=[]` silently. Validate against real
`pluginkit` output before shipping. This is the highest-risk collector — build it last.

---

## Build Order (Phase Dependencies)

```
Phase A: Chromium shared-collector refactor + Edge + Brave
  Dependencies: none (touches existing chrome.py, creates new files)
  ├── Create collectors/chromium.py (ChromiumBaseCollector, COMPONENT_DENYLIST)
  ├── Refactor collectors/chrome.py to thin subclass (re-export COMPONENT_DENYLIST)
  ├── Create collectors/edge.py (EdgeCollector)
  ├── Create collectors/brave.py (BraveCollector)
  ├── Update collectors/__init__.py: import + register EdgeCollector, BraveCollector
  ├── Update tests/collectors/test_chrome.py: fix patch targets
  └── Create tests/collectors/test_chromium.py, test_edge.py, test_brave.py

Phase B: Zed (independent — no dependency on Phase A)
  ├── Create collectors/zed.py (ZedCollector)
  ├── Update collectors/__init__.py: register ZedCollector before ChromeCollector
  └── Create tests/collectors/test_zed.py

Phase C: Codex Plugins (independent — no dependency on A or B)
  ├── CONFIRM Codex plugins data path before writing any code
  ├── Extend collectors/codex.py: _collect_mcp(), _collect_plugins(), updated collect()
  └── Update tests/collectors/test_codex.py: cover new section

Phase D: Safari (last — highest risk, isolated failure)
  ├── Create collectors/safari.py (SafariCollector + _parse_pluginkit_output)
  ├── VALIDATE _parse_pluginkit_output against real pluginkit output on macOS
  ├── Update collectors/__init__.py: register SafariCollector between BraveCollector and FirefoxCollector
  └── Create tests/collectors/test_safari.py (mocks subprocess.run)
```

**Rationale for this order:**

1. **Phase A first** — touches an existing collector (`chrome.py`) and its test file.
   Must land before Edge/Brave, which are built against the verified base class.
   Low behavioral risk (Chrome output is unchanged) but must be completed and tested
   before proceeding.

2. **Phases B and C are independent** — Zed (new file only) and Codex Plugins (extends
   existing file) have no dependencies on each other or on the Chromium refactor. Either
   can be built in parallel with or after Phase A.

3. **Phase D last** — Safari uses `pluginkit`, an undocumented subprocess tool. If the
   output format proves unworkable on the developer's macOS version, Safari can be
   deferred without blocking any other collector. The isolated last placement contains
   the risk to a single phase.

4. **Registry changes are incremental** — Phase A adds Edge/Brave to the registry; Phase B
   adds Zed; Phase C makes no registry change (CodexCollector is already registered);
   Phase D adds Safari. Each phase's registry update is a localized change.

---

## Integration Points

### New Files and Modified Files

| File | Status | Integration Point |
|------|--------|-------------------|
| `src/maccat/collectors/chromium.py` | CREATE | Base class; imported by chrome.py, edge.py, brave.py |
| `src/maccat/collectors/chrome.py` | MODIFY | Becomes thin subclass; re-exports COMPONENT_DENYLIST |
| `src/maccat/collectors/edge.py` | CREATE | Thin subclass; registered in get_registry() |
| `src/maccat/collectors/brave.py` | CREATE | Thin subclass; registered in get_registry() |
| `src/maccat/collectors/zed.py` | CREATE | Standalone; registered in get_registry() |
| `src/maccat/collectors/safari.py` | CREATE | Standalone; registered in get_registry() |
| `src/maccat/collectors/codex.py` | MODIFY | collect() returns 2 sections |
| `src/maccat/collectors/__init__.py` | MODIFY | Import + register new collectors in section order |
| `tests/collectors/test_chromium.py` | CREATE | Tests for shared base logic + patch target docs |
| `tests/collectors/test_chrome.py` | MODIFY | Update patch targets post-refactor |
| `tests/collectors/test_edge.py` | CREATE | Mirrors test_chrome.py structure |
| `tests/collectors/test_brave.py` | CREATE | Mirrors test_chrome.py structure |
| `tests/collectors/test_zed.py` | CREATE | New |
| `tests/collectors/test_safari.py` | CREATE | New; mocks subprocess.run |
| `tests/collectors/test_codex.py` | MODIFY | Cover new Codex Plugins section |

### Modules That Do NOT Change

| Module | Why unchanged |
|--------|--------------|
| `collectors/base.py` | `Collector`, `Section`, `CollectorResult` contract is sufficient as-is |
| `helpers/chrome_name.py` | Reused by all Chromium collectors via `ChromiumBaseCollector._collect_profile`; no changes needed |
| `helpers/json_io.py` | Used by Zed and Chromium collectors; no changes needed |
| `helpers/plist_version.py` | Not needed for extension collectors |
| `helpers/vsc_name.py` | VS Code/Cursor specific; unchanged |
| `catalog/format.py` | `emit_item`, `flush_section`, `version_sort_tail` unchanged |
| `reinstall/parser.py` | Title-agnostic state machine; new sections parse automatically |
| `reinstall/emitter.py` | New sections fall through to manual checklist; no changes needed |
| `cli.py` | `run()` calls `get_registry()` dynamically; new collectors appear automatically |

---

## Open Pitfalls

**Pitfall 1 — Codex plugins data path is unconfirmed.**
The `_collect_plugins()` implementation path (proposed as `~/.codex/plugins.json`) must
be confirmed against an actual Codex installation or the Codex GitHub source before any
code is written. If no plugin system exists in the currently installed Codex, implement
`_collect_plugins()` to return `Section(title="Codex Plugins", items=[])` with a NOTE
to stderr, treating it as a forward-looking stub. Do not fabricate a path.

**Pitfall 2 — `pluginkit` output format for Safari extensions is undocumented.**
`pluginkit -mAvvv -p com.apple.Safari.extension` output has not been validated against the
developer's current macOS version. On a machine with no Safari extensions installed, the
output may be empty or non-zero. Build `_parse_pluginkit_output` with fully mocked
`subprocess.run` in tests, then validate manually against real `pluginkit` output.
This is the one collector where a live smoke test is essential before finalizing the parser.

**Pitfall 3 — Chrome test patch target changes after refactor.**
`test_chrome.py` patches `chrome_mod._BASE` (module-level constant, `chrome.py` line 32).
After refactoring, `ChromeCollector._base = _BASE` is set at class-definition time.
`patch.object(chrome_mod, "_BASE", ...)` does NOT retroactively update the class attribute.
The correct post-refactor patch is `patch.object(ChromeCollector, "_base", new=...)`.
Document this in `test_chromium.py` and update all affected test cases in `test_chrome.py`.

**Pitfall 4 — `COMPONENT_DENYLIST` export backward compatibility.**
`test_chrome.py` line 14: `from maccat.collectors.chrome import COMPONENT_DENYLIST`.
After moving the constant to `chromium.py`, `chrome.py` must re-export it:
```python
from maccat.collectors.chromium import COMPONENT_DENYLIST
__all__ = ["ChromeCollector", "COMPONENT_DENYLIST"]
```
Without this, the import in `test_chrome.py` raises `ImportError` with no obvious cause.

---

## Sources

All findings are grounded in direct source reads — no web research needed for this
architecture document.

- `src/maccat/collectors/chrome.py` — full body read; parameterization design derived from
  this source (lines 19-103)
- `src/maccat/collectors/base.py` — `Collector`, `Section`, `CollectorResult` contract
- `src/maccat/collectors/__init__.py` — registry order, section counts, deferred import
  pattern (lines 1-70)
- `src/maccat/collectors/codex.py` — single-section pattern (lines 105-122); multi-section
  extension design modeled on `claude.py`
- `src/maccat/collectors/claude.py` — multi-section pattern (lines 177-185); `_collect_plugins`
  pattern (lines 75-100)
- `src/maccat/cli.py` — orchestration loop using `get_registry()` (lines 315-327); no changes
  needed confirmed
- `src/maccat/reinstall/parser.py` — title-agnostic state machine confirmed (lines 166-232);
  `SEPARATOR` constant (line 41)
- `src/maccat/reinstall/emitter.py` — `SECTION_SOURCE_MAP` (lines 230-235); manual fallthrough
  logic (lines 281-295)
- `src/maccat/helpers/chrome_name.py` — shared helper reused by all Chromium collectors
- `src/maccat/helpers/json_io.py` — `json_get` pattern for Zed design
- `src/maccat/helpers/plist_version.py` — not needed for extension collectors (confirmed)
- `tests/collectors/test_chrome.py` — `patch.object(chrome_mod, "_BASE", ...)` pattern
  (lines 43-46); `COMPONENT_DENYLIST` import (line 14); post-refactor impact analyzed

---
*Architecture research for: maccat v2.2.0 — Edge / Brave / Zed / Safari / Codex Plugins*
*Researched: 2026-06-17*

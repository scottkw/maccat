# Phase 15: Collectors — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 28 (14 source + 14 test)
**Analogs found:** 28 / 28

Each new file has TWO analogs:
1. The exact zsh function in `update-list.sh` — the byte-parity spec.
2. The Phase 13/14 Python structural analog — the code style/test/import pattern to copy.

---

## File Classification

| New File | Role | Data Flow | Zsh Analog (line) | Python Structural Analog | Match Quality |
|----------|------|-----------|-------------------|--------------------------|---------------|
| `src/maccat/collectors/__init__.py` | registry | — | `generate_catalog` :2220 (section order) | `src/maccat/catalog/__init__.py` | role-match |
| `src/maccat/collectors/base.py` | utility | — | `_section_lines` global + `flush_section` pattern | `src/maccat/catalog/format.py` (dataclass style) | role-match |
| `src/maccat/collectors/homebrew.py` | collector | request-response | `generate_catalog` :2233–2242 | `src/maccat/catalog/format.py` (subprocess pattern) | exact |
| `src/maccat/collectors/mas.py` | collector | request-response | `generate_catalog` :2249–2260 | `src/maccat/catalog/format.py` (subprocess pattern) | exact |
| `src/maccat/collectors/setapp.py` | collector | file-I/O | `generate_catalog` :2267–2274 | `src/maccat/helpers/json_io.py` (filesystem pattern) | role-match |
| `src/maccat/collectors/webapps.py` | collector | file-I/O | `generate_catalog` :2281–2284 | `src/maccat/helpers/json_io.py` (filesystem pattern) | role-match |
| `src/maccat/collectors/claude.py` | collector | file-I/O | `collect_claude_plugins` :1594, `collect_claude_mcp` :1638, `collect_claude_skills_agents` :1692 | `src/maccat/helpers/chrome_name.py` (JSON parse + fallback) | exact |
| `src/maccat/collectors/codex.py` | collector | request-response | `collect_codex_mcp` :1748 | `src/maccat/catalog/format.py` (subprocess + fallback) | exact |
| `src/maccat/collectors/opencode.py` | collector | file-I/O | `collect_opencode_plugins` :1802, `collect_opencode_mcp` :1861, `collect_opencode_agents` :1930 | `src/maccat/helpers/json_io.py` (JSON parse + fallback) | exact |
| `src/maccat/collectors/gemini.py` | collector | file-I/O | `collect_gemini_extensions` :1970, `collect_gemini_mcp` :2016 | `src/maccat/helpers/json_io.py` (JSON parse + fallback) | exact |
| `src/maccat/collectors/vscode.py` | collector | request-response | `collect_vscode_extensions` :1387 | `src/maccat/helpers/vsc_name.py` (NLS resolution) | exact |
| `src/maccat/collectors/cursor.py` | collector | request-response | `collect_cursor_extensions` :1494 | `src/maccat/collectors/vscode.py` (shared helper) | exact |
| `src/maccat/collectors/chrome.py` | collector | file-I/O | `collect_chrome_extensions` :2074 | `src/maccat/helpers/chrome_name.py` | exact |
| `src/maccat/collectors/firefox.py` | collector | file-I/O | `collect_firefox_extensions` :2154 | `src/maccat/helpers/chrome_name.py` | role-match |
| `tests/collectors/__init__.py` | test config | — | — | `tests/__init__.py` | exact |
| `tests/collectors/test_homebrew.py` | test | — | zsh :2233–2260 behavior | `tests/test_format.py` (class-per-behavior, mock subprocess) | exact |
| `tests/collectors/test_setapp.py` | test | — | zsh :2267–2284 behavior | `tests/test_helpers.py` (tmp_path filesystem fixture) | exact |
| `tests/collectors/test_claude.py` | test | — | zsh :1594–1731 behavior | `tests/test_helpers.py` (tmp_path + JSON fixture) | exact |
| `tests/collectors/test_codex.py` | test | — | zsh :1748–1790 behavior | `tests/test_format.py` (mock subprocess) | exact |
| `tests/collectors/test_opencode.py` | test | — | zsh :1802–1953 behavior | `tests/test_helpers.py` (tmp_path + JSON fixture) | exact |
| `tests/collectors/test_gemini.py` | test | — | zsh :1970–2059 behavior | `tests/test_helpers.py` (tmp_path + JSON fixture) | exact |
| `tests/collectors/test_vscode.py` | test | — | zsh :1387–1476 behavior | `tests/test_helpers.py` (tmp_path + NLS fixture) | exact |
| `tests/collectors/test_cursor.py` | test | — | zsh :1494–1583 behavior | `tests/collectors/test_vscode.py` (same fixture structure) | exact |
| `tests/collectors/test_chrome.py` | test | — | zsh :2074–2137 behavior | `tests/test_helpers.py` (tmp_path filesystem fixture) | exact |
| `tests/collectors/test_firefox.py` | test | — | zsh :2154–2206 behavior | `tests/test_helpers.py` (tmp_path filesystem fixture) | exact |

---

## Pattern Assignments

---

### `src/maccat/collectors/base.py` (utility — ABC + dataclasses)

**Zsh analog:** `_section_lines` global array (`update-list.sh:1278`) + `flush_section` empty-check pattern (:1290)
**Python structural analog:** `src/maccat/catalog/format.py` (module header + `from __future__ import annotations` convention)

**Full module pattern** — copy `from __future__ import annotations` + `dataclass` import convention from `src/maccat/catalog/format.py` lines 1–13, then apply this structure:

```python
# src/maccat/collectors/base.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Section:
    title: str
    items: list[str]        # raw emit_item() output lines — NOT yet sorted
    raw: bool = False       # if True, orchestrator writes items directly (no flush_section)
                            # raw=True: Homebrew, App Store, Setapp, Web-installed


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

    def degraded_result(self, title: str) -> CollectorResult:
        """Standard empty-section result. items=[] causes flush_section → '  (none found)'."""
        return CollectorResult(sections=[Section(title=title, items=[])])
```

**Key constraints:**
- `Section.raw = False` is the default — the four raw-write collectors (Homebrew, mas, Setapp, Web) override to `raw=True`.
- `degraded_result()` always returns `items=[]`; the orchestrator calls `flush_section([])` → `"  (none found)"`.
- No imports from `maccat.catalog.*` here — base must not pull format dependencies.

---

### `src/maccat/collectors/__init__.py` (registry)

**Zsh analog:** `generate_catalog` lines 2220–2313 (section call order)
**Python structural analog:** `src/maccat/catalog/__init__.py` (empty `__init__` with explicit `__all__`)

**Full module pattern:**

```python
# src/maccat/collectors/__init__.py
from __future__ import annotations

from maccat.collectors.base import Collector
from maccat.collectors.chrome import ChromeCollector
from maccat.collectors.claude import ClaudeCollector
from maccat.collectors.codex import CodexCollector
from maccat.collectors.cursor import CursorCollector
from maccat.collectors.firefox import FirefoxCollector
from maccat.collectors.gemini import GeminiCollector
from maccat.collectors.homebrew import HomebrewCollector
from maccat.collectors.mas import MasCollector
from maccat.collectors.opencode import OpenCodeCollector
from maccat.collectors.setapp import SetappCollector
from maccat.collectors.vscode import VSCodeCollector
from maccat.collectors.webapps import WebAppsCollector

# REGISTRY is the single source of truth for canonical section order.
# Phase 16 iterates this list to write all sections.
# Order MUST match generate_catalog in update-list.sh lines 2220-2313.
REGISTRY: list[Collector] = [
    HomebrewCollector(),
    MasCollector(),
    SetappCollector(),
    WebAppsCollector(),
    ClaudeCollector(),       # yields 3 sections: Plugins, MCP Servers, Skills & Agents
    CodexCollector(),        # yields 1 section: MCP Servers
    OpenCodeCollector(),     # yields 3 sections: Plugins, MCP Servers, Agents
    GeminiCollector(),       # yields 2 sections: Extensions, MCP Servers
    VSCodeCollector(),
    CursorCollector(),
    ChromeCollector(),
    FirefoxCollector(),
]
```

---

### `src/maccat/collectors/homebrew.py` (collector, raw-write)

**Zsh analog:** `generate_catalog` lines 2233–2242
**Python structural analog:** `src/maccat/catalog/format.py` (subprocess pattern, lines 58–73)

**Imports pattern** (copy from `src/maccat/catalog/format.py` lines 1–12):
```python
from __future__ import annotations

import shutil
import subprocess

from maccat.collectors.base import Collector, CollectorResult, Section
```

**Availability check pattern** (copy `command -v brew` → `shutil.which`):
```python
def available(self) -> bool:
    return shutil.which("brew") is not None
```

**Core raw-write pattern** (zsh :2233–2242 — `>> "$OUTPUT_FILE"` directly, no emit_item):
```python
TITLE = "Homebrew Packages"

def collect(self) -> CollectorResult:
    if not self.available():
        # Fallback message goes INTO the section body (zsh writes to $OUTPUT_FILE)
        return CollectorResult(sections=[Section(
            title=self.TITLE,
            items=["Homebrew is not installed."],
            raw=True,
        )])
    formulae = self._run(["brew", "list", "--formula"])
    casks = self._run(["brew", "list", "--cask"])
    lines = formulae + casks
    if not lines:
        lines = []
    return CollectorResult(sections=[Section(title=self.TITLE, items=lines, raw=True)])

def _run(self, cmd: list[str]) -> list[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return result.stdout.rstrip("\n").split("\n") if result.stdout.strip() else []
```

**Critical constraint:** `raw=True` on every `Section` for this collector. The orchestrator writes `items` with `write_lines()` without calling `flush_section()`. Brew output order is preserved — no sort, no dedup.

**Fallback message parity** — the WARNING to stdout is separate from the catalog:
```python
# Zsh: WARNING goes to terminal (stdout), NOT to $OUTPUT_FILE
# Python: print to stderr; catalog section gets the exact zsh fallback message
import sys
if not self.available():
    print("  WARNING: brew not found.", file=sys.stderr)
    return CollectorResult(sections=[Section(title=self.TITLE, items=["Homebrew is not installed."], raw=True)])
```

---

### `src/maccat/collectors/mas.py` (collector, raw-write)

**Zsh analog:** `generate_catalog` lines 2249–2260
**Python structural analog:** `src/maccat/collectors/homebrew.py` (same subprocess + raw pattern)

**Zsh awk equivalence** (copy this Python translation):
```python
# zsh: mas list 2>/dev/null | awk '{print $2, $3}'
# Python equivalent — split on whitespace, extract index 1 and 2, join with space
def _parse_mas_output(self, stdout: str) -> list[str]:
    lines = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            lines.append(f"{parts[1]} {parts[2]}")
    return lines
```

**Two-line fallback** (both lines go into catalog — separate items):
```python
["mas (Mac App Store CLI) is not installed.", "Install it with Homebrew: brew install mas"]
```

**Non-zero exit fallback** (single item):
```python
["Could not retrieve App Store list."]
```

**raw=True** on all returned Sections — same reason as Homebrew.

---

### `src/maccat/collectors/setapp.py` (collector, raw-write)

**Zsh analog:** `generate_catalog` lines 2267–2274
**Python structural analog:** `src/maccat/helpers/json_io.py` (filesystem existence check pattern, lines 25–26)

**Root-dir inclusion pattern** (Pitfall C — `find` includes start path):
```python
# zsh: find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} \; | sort
# find includes the start path itself → produces "Setapp" as an entry
base = Path("/Applications/Setapp")
entries = [base.name]  # include "Setapp" itself (the start path)
entries += [p.name for p in base.iterdir() if p.is_dir()]
entries.sort()
```

**Availability check:**
```python
def available(self) -> bool:
    return Path("/Applications/Setapp").is_dir()
```

**Fallback message:**
```python
["Setapp is not installed or detected."]
```

**raw=True** — zsh pipes `find | sort` directly to file.

---

### `src/maccat/collectors/webapps.py` (collector, raw-write)

**Zsh analog:** `generate_catalog` lines 2281–2284
**Python structural analog:** `src/maccat/collectors/setapp.py` (same root-dir-inclusion + sort pattern)

**Exclusion + root-inclusion pattern** (Pitfall C):
```python
# zsh: find "/Applications" -maxdepth 1 -type d \
#          -not -path "/Applications/Setapp*" \
#          -not -path "/Applications/*App Store*" \
#          -exec basename {} \; | sort
import fnmatch
base = Path("/Applications")
entries = [base.name]  # "Applications" — find includes start path
for p in base.iterdir():
    if not p.is_dir():
        continue
    if fnmatch.fnmatch(p.name, "Setapp*"):
        continue
    if fnmatch.fnmatch(p.name, "*App Store*"):
        continue
    entries.append(p.name)
entries.sort()
```

**No availability check** — always runs (zsh has no guard for /Applications).
**raw=True** — zsh pipes directly to file.

---

### `src/maccat/collectors/claude.py` (collector, multi-section, CAT-05 for MCP)

**Zsh analogs:**
- Plugins: `collect_claude_plugins` lines 1594–1626
- MCP: `collect_claude_mcp` lines 1638–1681 — **CAT-05 boundary**
- Skills/Agents: `collect_claude_skills_agents` lines 1692–1731

**Python structural analog:** `src/maccat/helpers/chrome_name.py` (JSON parse + fallback chain, lines 1–42)

**Imports pattern** (copy from `src/maccat/helpers/chrome_name.py` lines 1–6):
```python
from __future__ import annotations

import json
import re
from pathlib import Path

from maccat.catalog.format import emit_item, flush_section
from maccat.collectors.base import Collector, CollectorResult, Section
```

**Plugins collect pattern** (zsh :1594–1626):
```python
_PLUGINS_PATH = Path.home() / ".claude/plugins/installed_plugins.json"
_PLUGINS_TITLE = "Claude Code Plugins"

def _collect_plugins(self) -> Section:
    if not self._PLUGINS_PATH.is_file():
        return Section(title=self._PLUGINS_TITLE, items=[])
    try:
        data = json.loads(self._PLUGINS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Section(title=self._PLUGINS_TITLE, items=[])
    items: list[str] = []
    for key, versions in (data.get("plugins") or {}).items():
        name = key.split("@", 1)[0]
        version = versions[0].get("version", "") if versions else ""
        line = emit_item(name, version, key)
        if line:
            items.append(line)
    return Section(title=self._PLUGINS_TITLE, items=items)
```

**MCP collect pattern — CAT-05 compliant** (zsh :1638–1681):
```python
_CLAUDE_JSON = Path.home() / ".claude.json"
_MCP_TITLE = "Claude Code MCP Servers"
_TRANSPORT_WHITELIST = frozenset({"stdio", "http", "sse"})

def _collect_mcp(self) -> Section:
    if not self._CLAUDE_JSON.is_file():
        return Section(title=self._MCP_TITLE, items=[])
    try:
        data = json.loads(self._CLAUDE_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Section(title=self._MCP_TITLE, items=[])
    items: list[str] = []
    for name, cfg in (data.get("mcpServers") or {}).items():
        # CAT-05: ONLY .type — NEVER .command, .env, .args, .url, .headers
        transport = cfg.get("type", "stdio")
        if transport not in self._TRANSPORT_WHITELIST:
            transport = "stdio"
        line = emit_item(name, "", transport)
        if line:
            items.append(line)
    return Section(title=self._MCP_TITLE, items=items)
```

**Skills/Agents collect pattern** (zsh :1692–1731 — YAML frontmatter grep):
```python
_SKILLS_DIR = Path.home() / ".claude/skills"
_AGENTS_DIR = Path.home() / ".claude/agents"
_SKILLS_TITLE = "Claude Code Skills & Agents"

def _read_yaml_name(self, path: Path) -> str:
    """Extract 'name:' value from YAML frontmatter — first matching line only.
    Mirrors: grep '^name:' SKILL.md | head -1 | sed 's/^name: *//;s/"//g'
    """
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("name:"):
                return line[len("name:"):].strip().strip('"')
    except OSError:
        pass
    return ""

def _collect_skills_agents(self) -> Section:
    items: list[str] = []
    # Skills: one subdirectory per skill, read SKILL.md
    if self._SKILLS_DIR.is_dir():
        for skill_dir in sorted(self._SKILLS_DIR.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            name = self._read_yaml_name(skill_md) if skill_md.is_file() else ""
            if not name:
                name = skill_dir.name
            line = emit_item(name, "", "")
            if line:
                items.append(line)
    # Agents: individual .md files
    if self._AGENTS_DIR.is_dir():
        for agent_md in sorted(self._AGENTS_DIR.glob("*.md")):
            name = self._read_yaml_name(agent_md)
            if not name:
                name = agent_md.stem
            line = emit_item(name, "", "")
            if line:
                items.append(line)
    return Section(title=self._SKILLS_TITLE, items=items)
```

**collect() wrapper** — returns all three sections in order:
```python
def collect(self) -> CollectorResult:
    return CollectorResult(sections=[
        self._collect_plugins(),
        self._collect_mcp(),
        self._collect_skills_agents(),
    ])
```

---

### `src/maccat/collectors/codex.py` (collector, CAT-05 for MCP)

**Zsh analog:** `collect_codex_mcp` lines 1748–1790
**Python structural analog:** `src/maccat/collectors/homebrew.py` (subprocess + fallback) + `src/maccat/collectors/claude.py` (CAT-05 transport pattern)

**Two-path logic** (zsh :1748 — CLI first, TOML grep fallback):
```python
import shutil

_TITLE = "Codex MCP Servers"
_TOML_PATH = Path.home() / ".codex/config.toml"
_TRANSPORT_WHITELIST = frozenset({"stdio", "http", "sse"})

def collect(self) -> CollectorResult:
    items: list[str] = []

    if shutil.which("codex"):
        items = self._collect_via_cli()

    if not items and self._TOML_PATH.is_file():
        items = self._collect_via_toml()

    return CollectorResult(sections=[Section(title=self._TITLE, items=items)])

def _collect_via_cli(self) -> list[str]:
    import json, subprocess
    result = subprocess.run(
        ["codex", "mcp", "list", "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(entries, list) or not entries:
        return []
    items: list[str] = []
    for entry in entries:
        name = entry.get("name", "")
        # CAT-05: ONLY .type
        transport = entry.get("type", "stdio")
        if transport not in self._TRANSPORT_WHITELIST:
            transport = "stdio"
        line = emit_item(name, "", transport)
        if line:
            items.append(line)
    return items

def _collect_via_toml(self) -> list[str]:
    # CAT-05: read ONLY section headers — never parse TOML values
    # Mirrors: grep '^\[mcp_servers\.' config.toml | sed ...
    import re
    items: list[str] = []
    try:
        text = self._TOML_PATH.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        m = re.match(r'^\[mcp_servers\.(.*)\]$', line.strip())
        if m:
            name = m.group(1).strip('"')
            transport = "stdio"  # default — value lines are never read (CAT-05)
            item = emit_item(name, "", transport)
            if item:
                items.append(item)
    return items
```

**CAT-05 invariant:** `_collect_via_toml` reads only `^\[mcp_servers\.NAME\]` header lines. Value lines (`command`, `env`, `args`) are skipped by the regex match — never parsed via `tomllib`.

---

### `src/maccat/collectors/opencode.py` (collector, multi-section, CAT-05 for MCP)

**Zsh analogs:**
- Plugins: `collect_opencode_plugins` lines 1802–1847
- MCP: `collect_opencode_mcp` lines 1861–1917 — **CAT-05 boundary**
- Agents: `collect_opencode_agents` lines 1930–1953

**Python structural analog:** `src/maccat/collectors/claude.py` (same multi-section + JSON parse + CAT-05 pattern)

**Shared config file path** (all three sub-collectors read the same file):
```python
_CONFIG_PATH = Path.home() / ".config/opencode/opencode.json"
```

**Plugins pattern** (zsh :1802 — `plugin[]` array + path/URL guard):
```python
def _collect_plugins(self) -> Section:
    title = "OpenCode Plugins"
    data = self._load_config()
    if data is None:
        return Section(title=title, items=[])
    items: list[str] = []
    for entry in (data.get("plugin") or []):
        name = entry.split("@", 1)[0]
        # path/URL guard: entry has no @ AND contains / → skip (warn to stderr)
        if name == entry and "/" in entry:
            import sys
            print(f"  WARNING: skipping OpenCode plugin path/URL: {entry}", file=sys.stderr)
            continue
        if not name:
            continue
        line = emit_item(name, "", "")
        if line:
            items.append(line)
    return Section(title=title, items=items)
```

**MCP pattern — CAT-05** (zsh :1861):
```python
def _collect_mcp(self) -> Section:
    title = "OpenCode MCP Servers"
    data = self._load_config()
    if data is None or not data.get("mcp"):
        return Section(title=title, items=[])
    items: list[str] = []
    for name, cfg in data["mcp"].items():
        # CAT-05: ONLY .type
        transport = cfg.get("type", "stdio")
        if transport not in _TRANSPORT_WHITELIST:
            transport = "stdio"
        line = emit_item(name, "", transport)
        if line:
            items.append(line)
    return Section(title=title, items=items)
```

**Agents pattern** (zsh :1930 — same YAML frontmatter grep as Claude agents):
```python
_AGENTS_DIR = Path.home() / ".config/opencode/agents"

def _collect_agents(self) -> Section:
    title = "OpenCode Agents"
    if not self._AGENTS_DIR.is_dir():
        return Section(title=title, items=[])
    items: list[str] = []
    for agent_md in sorted(self._AGENTS_DIR.glob("*.md")):
        name = self._read_yaml_name(agent_md)
        if not name:
            name = agent_md.stem
        line = emit_item(name, "", "")
        if line:
            items.append(line)
    return Section(title=title, items=items)
```

**Config loader helper** (shared by all three sub-collectors — load once, reuse):
```python
def _load_config(self) -> dict | None:
    if not self._CONFIG_PATH.is_file():
        return None
    try:
        return json.loads(self._CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
```

---

### `src/maccat/collectors/gemini.py` (collector, multi-section, CAT-05 for MCP)

**Zsh analogs:**
- Extensions: `collect_gemini_extensions` lines 1970–1996
- MCP: `collect_gemini_mcp` lines 2016–2059 — **CAT-05 boundary** + **empty-file guard**

**Python structural analog:** `src/maccat/helpers/json_io.py` (JSON parse + never-raises pattern, lines 25–42)

**Extensions pattern** (zsh :1970 — `json_get` for name + version):
```python
from maccat.helpers.json_io import json_get

_EXT_DIR = Path.home() / ".gemini/extensions"
_EXT_TITLE = "Gemini CLI Extensions"

def _collect_extensions(self) -> Section:
    if not self._EXT_DIR.is_dir():
        return Section(title=self._EXT_TITLE, items=[])
    items: list[str] = []
    for ext_dir in sorted(self._EXT_DIR.iterdir()):
        if not ext_dir.is_dir():
            continue
        manifest = ext_dir / "gemini-extension.json"
        if not manifest.is_file():
            continue
        name = json_get(manifest, "name") or ext_dir.name  # fallback to basename
        version = json_get(manifest, "version")
        line = emit_item(name, version, "")
        if line:
            items.append(line)
    return Section(title=self._EXT_TITLE, items=items)
```

**MCP pattern — CAT-05 + empty-file guard** (Pitfall B — `[[ -s ]]` not `[[ -f ]]`):
```python
_MCP_PATH = Path.home() / ".gemini/config/mcp_config.json"
_MCP_TITLE = "Gemini CLI MCP Servers"

def _collect_mcp(self) -> Section:
    # Pitfall B: use -s equivalent (is_file AND size > 0), not just is_file()
    if not self._MCP_PATH.is_file() or self._MCP_PATH.stat().st_size == 0:
        return Section(title=self._MCP_TITLE, items=[])
    try:
        data = json.loads(self._MCP_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Section(title=self._MCP_TITLE, items=[])
    items: list[str] = []
    for name, cfg in (data.get("mcpServers") or {}).items():
        # CAT-05: ONLY .type
        transport = cfg.get("type", "stdio")
        if transport not in _TRANSPORT_WHITELIST:
            transport = "stdio"
        line = emit_item(name, "", transport)
        if line:
            items.append(line)
    return Section(title=self._MCP_TITLE, items=items)
```

---

### `src/maccat/collectors/vscode.py` (collector, two-path CLI/file fallback)

**Zsh analog:** `collect_vscode_extensions` lines 1387–1476
**Python structural analog:** `src/maccat/helpers/vsc_name.py` (NLS resolution), `src/maccat/catalog/format.py` (subprocess pattern)

**Imports pattern:**
```python
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from maccat.catalog.format import emit_item, flush_section
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.vsc_name import resolve_vsc_ext_name
```

**Shared helper** (used by both VSCodeCollector and CursorCollector):
```python
def _collect_editor_extensions(
    ext_dir: Path,
    cli_name: str,
    section_title: str,
) -> tuple[list[str], list[str]]:
    """Shared logic for VS Code and Cursor. Returns (items, warnings).

    Path A: CLI --list-extensions --show-versions (preferred)
    Path B: extensions.json fallback (when CLI absent or returns empty)
    """
    ext_json = ext_dir / "extensions.json"
    items: list[str] = []
    warnings: list[str] = []

    # Path A — CLI
    cli_lines: list[str] = []
    if shutil.which(cli_name):
        result = subprocess.run(
            [cli_name, "--list-extensions", "--show-versions"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            cli_lines = result.stdout.strip().splitlines()

    if cli_lines:
        # Load extensions.json for relativeLocation (needed for display name)
        ext_meta: dict[str, dict] = {}
        if ext_json.is_file():
            try:
                entries = json.loads(ext_json.read_text(encoding="utf-8"))
                for entry in entries:
                    id_ = entry.get("identifier", {}).get("id", "")
                    if id_:
                        ext_meta[id_.lower()] = entry
            except (json.JSONDecodeError, OSError):
                pass

        for raw in cli_lines:
            parts = raw.rsplit("@", 1)  # mirrors zsh ${line%@*} / ${line##*@}
            if len(parts) != 2:
                continue
            id_, version = parts[0], parts[1]
            meta = ext_meta.get(id_.lower(), {})
            rel_loc = meta.get("relativeLocation", "")
            if rel_loc:
                pkg_json = ext_dir / rel_loc / "package.json"
                display_name = resolve_vsc_ext_name(pkg_json, id_)
            else:
                display_name = id_
            line = emit_item(display_name, version, id_)
            if line:
                items.append(line)
        return items, warnings

    # Path B — extensions.json fallback
    if not ext_json.is_file():
        print(f"  NOTE: {cli_name.capitalize()} not installed or no extensions found.", file=sys.stderr)
        return [], warnings

    print(f"  {cli_name} CLI returned empty list. Falling back to extensions.json.", file=sys.stderr)
    try:
        entries = json.loads(ext_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], warnings
    for entry in entries:
        id_ = entry.get("identifier", {}).get("id", "")
        version = entry.get("version", "")
        rel_loc = entry.get("relativeLocation", "")
        pkg_json = ext_dir / rel_loc / "package.json"
        display_name = resolve_vsc_ext_name(pkg_json, id_)
        line = emit_item(display_name, version, id_)
        if line:
            items.append(line)
    return items, warnings
```

**VSCodeCollector.collect():**
```python
class VSCodeCollector(Collector):
    TITLE = "VS Code Extensions"
    _EXT_DIR = Path.home() / ".vscode/extensions"

    def collect(self) -> CollectorResult:
        items, warnings = _collect_editor_extensions(self._EXT_DIR, "code", self.TITLE)
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=items)],
            warnings=warnings,
        )
```

---

### `src/maccat/collectors/cursor.py` (collector — mirrors vscode.py)

**Zsh analog:** `collect_cursor_extensions` lines 1494–1583
**Python structural analog:** `src/maccat/collectors/vscode.py` (identical, different paths)

```python
class CursorCollector(Collector):
    TITLE = "Cursor Extensions"
    _EXT_DIR = Path.home() / ".cursor/extensions"

    def collect(self) -> CollectorResult:
        from maccat.collectors.vscode import _collect_editor_extensions
        items, warnings = _collect_editor_extensions(self._EXT_DIR, "cursor", self.TITLE)
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=items)],
            warnings=warnings,
        )
```

Only substitution from VS Code: `ext_dir = ~/.cursor/extensions`, `cli_name = "cursor"`.

---

### `src/maccat/collectors/chrome.py` (collector, multi-profile)

**Zsh analog:** `collect_chrome_extensions` lines 2074–2137
**Python structural analog:** `src/maccat/helpers/chrome_name.py` (manifest parse), `src/maccat/catalog/format.py` (`version_sort_tail`)

**Imports pattern:**
```python
from __future__ import annotations

import sys
from pathlib import Path

from maccat.catalog.format import emit_item, flush_section, version_sort_tail
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.chrome_name import chrome_ext_name
from maccat.helpers.json_io import json_get
```

**Component denylist** (inline constant — never a file, never an env var):
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

**Profile enumeration + cross-profile dedup** (zsh :2089 — Default first, then Profile *):
```python
_BASE = Path.home() / "Library/Application Support/Google/Chrome"
_TITLE = "Google Chrome Extensions"

def collect(self) -> CollectorResult:
    if not self._BASE.is_dir():
        print("  NOTE: Google Chrome not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=self._TITLE, items=[])])

    # All items across all profiles — flush_section deduplicates at the end
    all_items: list[str] = []

    # Enumerate: Default first, then sorted "Profile *" dirs
    profile_dirs = [self._BASE / "Default"]
    profile_dirs += sorted(self._BASE.glob("Profile */"))

    for profile in profile_dirs:
        ext_root = profile / "Extensions"
        if not ext_root.is_dir():
            continue
        all_items.extend(self._collect_profile(ext_root))

    return CollectorResult(sections=[Section(title=self._TITLE, items=all_items)])

def _collect_profile(self, extensions_dir: Path) -> list[str]:
    items: list[str] = []
    for ext_dir in extensions_dir.iterdir():
        if not ext_dir.is_dir():
            continue
        ext_id = ext_dir.name
        if ext_id == "Temp" or ext_id.startswith("_") or ext_id in COMPONENT_DENYLIST:
            continue
        candidates = [d.name for d in ext_dir.iterdir() if d.is_dir()]
        ver_dir = version_sort_tail(candidates)  # Phase 13 helper — mandatory for parity
        if not ver_dir:
            continue
        manifest = ext_dir / ver_dir / "manifest.json"
        if not manifest.is_file():
            continue
        name = chrome_ext_name(manifest)     # Phase 13 helper
        version = json_get(manifest, "version")  # Phase 13 helper
        line = emit_item(name, version, ext_id)
        if line:
            items.append(line)
    return items
```

---

### `src/maccat/collectors/firefox.py` (collector, multi-profile via profiles.ini)

**Zsh analog:** `collect_firefox_extensions` lines 2154–2206
**Python structural analog:** `src/maccat/collectors/chrome.py` (multi-profile + cross-profile dedup)

**profiles.ini parse** (Pitfall E — use `.splitlines()` not `.split("\n")` for CRLF safety):
```python
_FF_DIR = Path.home() / "Library/Application Support/Firefox"
_TITLE = "Firefox Extensions"

def _get_profile_paths(self) -> list[Path]:
    profiles_ini = self._FF_DIR / "profiles.ini"
    if not profiles_ini.is_file():
        return []
    paths: list[Path] = []
    # splitlines() handles CRLF automatically (Pitfall E)
    for line in profiles_ini.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Path="):
            rel = line[len("Path="):]
            paths.append(self._FF_DIR / rel)
    return paths
```

**Extension parse** (location filter = "app-profile" only):
```python
def _collect_profile(self, profile_dir: Path) -> list[str]:
    ext_json = profile_dir / "extensions.json"
    if not ext_json.is_file():
        return []
    try:
        data = json.loads(ext_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    items: list[str] = []
    for addon in (data.get("addons") or []):
        if addon.get("location") != "app-profile":
            continue  # exclude app-builtin, app-builtin-addons
        id_ = addon.get("id", "")
        if not id_ or id_ == "null":
            continue
        name = (addon.get("defaultLocale") or {}).get("name") or id_
        version = addon.get("version", "")
        line = emit_item(name, version, id_)
        if line:
            items.append(line)
    return items
```

---

## Test Pattern Assignments

All test files follow the same structural pattern from `tests/test_format.py` and `tests/test_helpers.py`. Copy from those files.

---

### `tests/collectors/__init__.py`

Empty file — mirrors `tests/__init__.py`. Required so pytest discovers the `tests/collectors/` subpackage.

---

### Test file structure (copy from `tests/test_format.py` lines 1–16)

**Header pattern** — all collector test files:
```python
"""Tests for maccat.collectors.<name>.

Behavioral spec: update-list.sh lines XXXX–YYYY (collect_XXX).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from maccat.collectors.<name> import <ClassName>
```

**Class-per-behavior pattern** (copy from `tests/test_format.py` lines 19–162):
```python
class TestHomebrewCollector:
    def test_collects_formulae_and_casks(self) -> None: ...
    def test_absent_brew_returns_fallback_message(self) -> None: ...
    def test_nonzero_exit_returns_empty(self) -> None: ...

class TestHomebrewDegradation:
    def test_raw_flag_is_true(self) -> None: ...
    def test_brew_absent_section_raw_true(self) -> None: ...
```

---

### `tests/collectors/test_homebrew.py` (subprocess mock pattern)

**Subprocess mock pattern** (copy from `tests/test_format.py` lines 85–99 style, adapted):
```python
def test_homebrew_collect(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.stdout = "git\nnode\n"
    mock_result.returncode = 0
    with patch("shutil.which", return_value="/usr/local/bin/brew"), \
         patch("subprocess.run", return_value=mock_result):
        collector = HomebrewCollector()
        result = collector.collect()
    assert len(result.sections) == 1
    assert result.sections[0].raw is True
    assert "git" in result.sections[0].items
```

**Degradation test pattern** (copy `tmp_json` fixture style from `tests/conftest.py`):
```python
def test_absent_brew_fallback(self) -> None:
    with patch("shutil.which", return_value=None):
        collector = HomebrewCollector()
        result = collector.collect()
    assert result.sections[0].items == ["Homebrew is not installed."]
    assert result.sections[0].raw is True
```

---

### `tests/collectors/test_claude.py` (CAT-05 MCP secret test + filesystem mock)

**MCP secret grep test** (success criterion 3 from CONTEXT.md — this is a Phase-15 deliverable):
```python
import re

SECRET_PATTERN = re.compile(r'token|Bearer|sk-|ghp_|key=|Authorization', re.IGNORECASE)

def test_mcp_never_emits_secrets(tmp_path: Path) -> None:
    """CAT-05: collector must emit name + transport only — zero secret fields."""
    config = tmp_path / ".claude.json"
    config.write_text(json.dumps({
        "mcpServers": {
            "my-server": {
                "type": "stdio",
                "command": "/usr/local/bin/server",
                "args": ["--token", "sk-secret-token-12345"],
                "env": {"ANTHROPIC_API_KEY": "sk-ant-secret"},
            }
        }
    }), encoding="utf-8")
    # Monkeypatch the path that the collector reads
    with patch.object(ClaudeCollector, "_CLAUDE_JSON", config):
        result = ClaudeCollector().collect()
    mcp_section = next(s for s in result.sections if "MCP" in s.title)
    full_output = "\n".join(mcp_section.items)
    assert not SECRET_PATTERN.search(full_output), \
        f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
    assert "my-server" in full_output
    assert "stdio" in full_output
```

**Filesystem fixture pattern** (copy `tmp_json` + directory layout style from `tests/test_helpers.py` lines 72–80):
```python
def test_plugins_collect(tmp_path: Path) -> None:
    plugins_json = tmp_path / "installed_plugins.json"
    plugins_json.write_text(json.dumps({
        "plugins": {
            "my-plugin@registry": [{"version": "1.2.3"}]
        }
    }), encoding="utf-8")
    with patch.object(ClaudeCollector, "_PLUGINS_PATH", plugins_json):
        result = ClaudeCollector().collect()
    plugins_section = result.sections[0]
    assert any("my-plugin" in item for item in plugins_section.items)
    assert any("1.2.3" in item for item in plugins_section.items)
```

---

### `tests/collectors/test_gemini.py` (empty-file guard test)

**Pitfall B — empty-file guard test** (critical regression guard):
```python
def test_mcp_empty_file_returns_none_found(tmp_path: Path) -> None:
    """Pitfall B: 0-byte mcp_config.json must NOT trigger json.JSONDecodeError."""
    mcp_path = tmp_path / "mcp_config.json"
    mcp_path.write_bytes(b"")  # 0 bytes
    with patch.object(GeminiCollector, "_MCP_PATH", mcp_path):
        result = GeminiCollector().collect()
    mcp_section = next(s for s in result.sections if "MCP" in s.title)
    assert mcp_section.items == []  # flush_section will produce (none found)
```

---

### `tests/collectors/test_codex.py` (TOML grep — no tomllib)

**TOML fallback test — verify text-only parse (no tomllib)**:
```python
def test_toml_fallback_reads_only_section_headers(tmp_path: Path) -> None:
    """CAT-05 + Pitfall G: TOML fallback must extract names from headers only."""
    config_toml = tmp_path / "config.toml"
    config_toml.write_text(
        "[mcp_servers.my-server]\n"
        'command = "/usr/local/bin/server"\n'
        'env = {ANTHROPIC_API_KEY = "sk-ant-secret"}\n'
        "[mcp_servers.other]\n"
        'command = "other"\n',
        encoding="utf-8"
    )
    with patch("shutil.which", return_value=None), \
         patch.object(CodexCollector, "_TOML_PATH", config_toml):
        result = CodexCollector().collect()
    section = result.sections[0]
    full_output = "\n".join(section.items)
    assert "my-server" in full_output
    assert "other" in full_output
    assert "sk-ant-secret" not in full_output  # CAT-05
    assert "command" not in full_output         # CAT-05
```

---

### `tests/collectors/test_chrome.py` (filesystem fixture — profile layout)

**Profile directory fixture pattern** (copy `tmp_path` dir-creation style from `tests/test_helpers.py`):
```python
def _make_ext(profile_ext_dir: Path, ext_id: str, version: str, name: str) -> None:
    """Build a synthetic Chrome extension directory."""
    ver_dir = profile_ext_dir / ext_id / version
    ver_dir.mkdir(parents=True)
    (ver_dir / "manifest.json").write_text(
        json.dumps({"name": name, "version": version}),
        encoding="utf-8"
    )

def test_collects_default_profile(tmp_path: Path) -> None:
    base = tmp_path / "Chrome"
    ext_dir = base / "Default" / "Extensions"
    ext_dir.mkdir(parents=True)
    _make_ext(ext_dir, "abcdefghijklmnopabcdefghijklmnop", "1.0.0_0", "My Extension")
    with patch.object(ChromeCollector, "_BASE", base):
        result = ChromeCollector().collect()
    assert any("My Extension" in item for item in result.sections[0].items)
```

---

## Shared Patterns

### CAT-05 Transport Safety (MCP collectors)
**Source:** `src/maccat/collectors/claude.py` `_collect_mcp()` (see Pattern Assignments above)
**Apply to:** `claude.py`, `codex.py`, `opencode.py`, `gemini.py`
**Invariant:** For every MCP config object, call `.get("type", "stdio")` ONLY. No other field on the server config is read. The only permitted `json_get` calls on server config entries are for `"type"`. Enforce with a code comment.

```python
# CAT-05: ONLY .type — NEVER .command, .env, .args, .url, .headers
transport = cfg.get("type", "stdio")
if transport not in _TRANSPORT_WHITELIST:
    transport = "stdio"
```

**Transport whitelist** (same constant in every MCP collector — do not import from a shared location, each module owns its own copy for independent review):
```python
_TRANSPORT_WHITELIST = frozenset({"stdio", "http", "sse"})
```

---

### Graceful Degradation (CAT-06)
**Source:** `src/maccat/helpers/json_io.py` lines 25–42 (never-raises pattern)
**Apply to:** All 12 collector modules
**Pattern:** Every `json.loads()` / `Path.read_text()` / `subprocess.run()` call is wrapped in a try/except that returns a degraded result. Never propagate OSError, JSONDecodeError, or CalledProcessError.

```python
# Pattern: return degraded_result on any error; never raise from collect()
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError, UnicodeDecodeError):
    return self.degraded_result(title)
```

---

### Subprocess Safety (shell=False)
**Source:** `src/maccat/catalog/format.py` lines 58–65 (subprocess.run list form)
**Apply to:** `homebrew.py`, `mas.py`, `vscode.py`, `cursor.py`, `codex.py`

```python
# Always: list form, shell=False (default), capture_output=True, text=True
result = subprocess.run(
    ["brew", "list", "--formula"],
    capture_output=True,
    text=True,
    # shell=False is the default — never override to shell=True
)
```

---

### Phase 13 Helpers (reuse — never reimplement)
**Source:** Built modules in `src/maccat/helpers/`
**Apply to:** All collectors that need JSON parse, Chrome name, or VS Code NLS resolution

| Helper | Import | Apply to |
|--------|--------|----------|
| `emit_item` | `from maccat.catalog.format import emit_item` | All 12 collectors (except raw ones use it too for fallback) |
| `flush_section` | `from maccat.catalog.format import flush_section` | All standard-pipeline collectors (not raw ones) |
| `version_sort_tail` | `from maccat.catalog.format import version_sort_tail` | `chrome.py` only |
| `json_get` | `from maccat.helpers.json_io import json_get` | `gemini.py`, `chrome.py` |
| `chrome_ext_name` | `from maccat.helpers.chrome_name import chrome_ext_name` | `chrome.py` only |
| `resolve_vsc_ext_name` | `from maccat.helpers.vsc_name import resolve_vsc_ext_name` | `vscode.py`, `cursor.py` |

**NEVER reimplement** these helpers in collector modules. Any dotted-path JSON extraction, Chrome `__MSG_` resolution, or VS Code `%nls%` resolution goes through the existing helpers.

---

### Python Module Header (all collector files)
**Source:** `src/maccat/catalog/format.py` lines 1–12, `src/maccat/helpers/json_io.py` lines 1–6
**Apply to:** All `.py` files in `src/maccat/collectors/`

```python
"""One-line description. Byte-parity with update-list.sh:XXXX (function_name)."""
from __future__ import annotations

# stdlib imports first, alphabetical
# then maccat.* imports (catalog.format before collectors.base)
```

---

### Test Fixtures
**Source:** `tests/conftest.py` (full file — 56 lines)
**Apply to:** All `tests/collectors/test_*.py`

The existing `tmp_json`, `git_repo`, and `catalog_repo` fixtures are available to all collector tests automatically (conftest.py is at `tests/` level). No new conftest needed unless collector tests need a shared directory layout fixture — if so, add to `tests/collectors/conftest.py` (new file, mirrors `tests/conftest.py` structure).

---

## Raw-Write vs. flush_section Split

**Critical architectural distinction** — the Phase-16 orchestrator branches on `section.raw`:

| Collector | `section.raw` | Orchestrator action |
|-----------|--------------|---------------------|
| `HomebrewCollector` | `True` | `writer.write_lines(section.items)` — no flush_section |
| `MasCollector` | `True` | `writer.write_lines(section.items)` — no flush_section |
| `SetappCollector` | `True` | `writer.write_lines(section.items)` — no flush_section |
| `WebAppsCollector` | `True` | `writer.write_lines(section.items)` — no flush_section |
| All others | `False` (default) | `writer.write_lines(flush_section(section.items))` |

The four raw collectors must NOT call `flush_section` anywhere — their items list is written verbatim. Brew and mas output order is the source's own order; Setapp/Web are pre-sorted by Python's `sorted()`.

---

## No Analog Found

All collector files have both a zsh analog (the byte-parity spec) and a Python structural analog (from Phase 13/14). No file is without pattern guidance.

---

## Critical Anti-Patterns (do NOT copy these)

| Anti-Pattern | Where It Fails | Correct Pattern |
|---|---|---|
| `flush_section(items)` on Homebrew/mas/Setapp/Web sections | Breaks byte parity — brew output is re-sorted | `section.raw = True`; write items directly |
| `path.is_file()` for Gemini `mcp_config.json` | Succeeds on 0-byte file → `json.JSONDecodeError` | `path.is_file() and path.stat().st_size > 0` |
| `tomllib.loads(toml_text)` for Codex fallback | Parses ALL values including `env`, `command` — CAT-05 leak | Text grep for `^\[mcp_servers\.NAME\]` headers ONLY |
| `json_get(nls_file, "extension.title")` in vscode.py | Dotted-path split fails on flat NLS keys | `nls.get("extension.title")` via `resolve_vsc_ext_name` |
| `cfg.get("command")` inside any MCP loop | CAT-05 secret leakage | Read ONLY `cfg.get("type", "stdio")` |
| `Path.iterdir()` alone for Setapp/Web root dirs | Misses the start-path entry that `find` produces | Prepend `[base.name]` before `iterdir()` results |
| `path.read_text().split("\n")` for Firefox profiles.ini | Leaves `\r` at end of path on CRLF files | `.splitlines()` (handles CRLF automatically) |
| `shell=True` in any subprocess call | Security risk + injection surface | List form, `shell=False` (default) always |
| Reimplementing `chrome_ext_name` or `resolve_vsc_ext_name` | Duplicate logic, divergence risk | Import from `src/maccat/helpers/` |
| `sorted(items, key=str.casefold)` in any collector | Diverges from `LC_ALL=C sort -f -u` | `flush_section(items)` which calls subprocess sort |

---

## Metadata

**Analog search scope:**
- `update-list.sh` (zsh spec, lines 1387–2206 for all collector functions)
- `src/maccat/catalog/format.py` (Phase 13, 108 lines — fully read)
- `src/maccat/catalog/writer.py` (Phase 13, 79 lines — fully read)
- `src/maccat/helpers/json_io.py` (Phase 13, 42 lines — fully read)
- `tests/conftest.py` (Phase 13/14, 56 lines — fully read)
- `tests/test_format.py` (Phase 13, 162 lines — fully read)
- `tests/test_helpers.py` (Phase 13, 80 lines head — structure extracted)
- Phase 13 and 14 SUMMARY files (completion state verified)

**Files scanned:** 8 built source/test files, 2 SUMMARY files, 15-CONTEXT.md + 15-RESEARCH.md
**Pattern extraction date:** 2026-06-14

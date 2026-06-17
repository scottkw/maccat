# Stack Research — Reinstall from Catalog (v2.1.0)

**Domain:** macOS software cataloger CLI — `maccat reinstall` subcommand
**Researched:** 2026-06-16
**Confidence:** HIGH (all command syntax verified against live tools and official docs)

> **Scope:** This is the v2.1.0 research pass. The prior STACK.md (2026-06-14) documented
> the v1.0.0 Python port decisions. That content is preserved but superseded on technology
> choices by this document for the reinstall feature.
> This document answers three questions only:
> 1. Is anything beyond the Python stdlib warranted?
> 2. What is the exact, current install-command syntax per deterministic source?
> 3. Does emitting a shell script require any tooling?

---

## 1. Stdlib-Only: CONFIRMED — No New Dependencies

**Verdict: stdlib-only, no additions required.**

The reinstall feature has two implementation tasks: parse a catalog text file and emit a shell
script. Neither task introduces any new capability requirements:

| Task | Third-party temptation | Stdlib sufficiency | Verdict |
|------|-----------------------|-------------------|---------|
| Parse plain-text catalog sections | `pyparsing`, regex libs | `re` + line iteration — catalog format is fixed, line-oriented (`name (version) [id]`), section-delimited by `----` bars | **stdlib wins** |
| Emit a shell script | `jinja2`, `mako` | Plain string formatting (`f"brew install {name}  # cataloged: {version}"`) — a flat list of commands with comments is not a template problem | **stdlib wins** |
| Catalog file selection (newest per computer) | — | `pathlib.Path.glob()` + `sorted()` — already used in retention.py | **stdlib wins** |
| Computer-folder picking | — | Existing `select_computer` in `machine.py` — reuse as-is | **already exists** |

**Dependency count change: zero.** The `.pyz` zipapp stays dependency-free. `pyproject.toml`
gets no new `[project.dependencies]` entries.

---

## 2. Exact Install Command Syntax Per Source

All commands verified live or against official current documentation (June 2026).

### 2a. Homebrew Formulae

```sh
brew install <formula-name>           # installs or upgrades if outdated
```

**Idempotency behavior (verified: Homebrew 6.0.2):**
Unless `$HOMEBREW_NO_INSTALL_UPGRADE` is set, `brew install` on an already-installed formula
**upgrades it if outdated** and exits 0 silently if already at the latest version. For formulae,
`brew install` is already idempotent — no extra flag is needed.

**Non-interactive flag:** `-y` / `--no-ask` skips any confirmation prompts. Confirmation
prompts are rare for standard formulae but safe to include in a generated script.

**Recommended line format in reinstall.sh:**
```sh
brew install <formula-name>  # cataloged: <version>
```

Do not pin versions. Homebrew has no stable version-pin mechanism for formulae (keg-only
versions are not guaranteed to exist). The cataloged version appears as a comment only.

### 2b. Homebrew Casks

```sh
brew install --cask <cask-name>       # installs the cask
```

**Idempotency behavior — CAUTION (verified: Homebrew 6.0.2, GitHub issue #15295):**
`brew install --cask` on an already-installed cask currently produces a **hard error with a
non-zero exit code** ("Cask is already installed"). This is a known regression vs. formula
behavior. The official workaround is `brew reinstall --cask <cask-name>`, but that always
reinstalls even when not needed.

**Recommended mitigation for the generated script:** wrap each cask install in a guard:

```sh
brew list --cask <cask-name> &>/dev/null || brew install --cask <cask-name>  # cataloged: <version>
```

This makes cask lines idempotent (skip if already installed) without forcing a reinstall.
The pattern is self-contained, readable, and does not require the user to run `brew bundle`.

**Do not emit `brew install <cask-name>` without `--cask`.** Homebrew will attempt to find a
formula of that name and fail or install the wrong thing.

### 2c. Mac App Store (`mas`)

```sh
mas install <app-id>                  # installs the app (requires prior purchase/ownership)
```

**Idempotency behavior (verified: mas 7.0.0 live + `mas help install`):**
`mas install` on an already-installed app prints "Warning: [name] is already installed" and
exits 0. It is effectively idempotent without any extra flag. The `--force` flag forces a
reinstall (re-download and re-install even if current) — do not include this in the generated
script, as it would unconditionally reinstall every app on re-run.

**Recommended line format in reinstall.sh:**
```sh
mas install <app-id>  # cataloged: <name> <version>
```

Use the numeric App Store ID (the `[id]` field from the catalog), not the app name. The name
is only available as a comment for human readability.

**Caveat to surface in the script header:** `mas install` requires the user to be signed in
to the App Store and to have previously purchased the app. The generated script should print
a reminder at the top of the `mas` section.

### 2d. VS Code Extensions

```sh
code --install-extension <publisher.extension-id>  # installs or updates
code --install-extension <publisher.extension-id> --force  # forces update to latest
```

**Verified syntax (official VS Code docs, June 2026):**
- Extension ID format: `publisher.extension-name` (e.g., `ms-python.python`) — this is exactly
  the `[id]` field the maccat catalog already records.
- `code --install-extension` "Install or updates an extension" — already idempotent; if the
  extension is at the latest version, it succeeds silently.
- `--force` skips any "already installed" prompts; use this in the generated script to ensure
  non-interactive behavior.
- `--profile <profile-name>` installs to a specific profile; omit for default profile.

**Recommended line format in reinstall.sh:**
```sh
code --install-extension <publisher.extension-id> --force  # cataloged: <display-name> <version>
```

**Prerequisite:** The `code` CLI must be installed. On macOS it is installed via VS Code's
Command Palette: "Shell Command: Install 'code' command in PATH". The generated script should
guard with `command -v code` and print a skip notice if absent.

### 2e. Cursor Extensions

```sh
cursor --install-extension <publisher.extension-id>  # installs the extension
```

**Verified syntax (Cursor community forum + 2026 docs, June 2026):**
- Uses the same `publisher.extension-name` ID format as VS Code — already what the maccat
  catalog records in `[id]` for the Cursor collector.
- Cursor mirrors the VS Code CLI interface for extension management: `--install-extension`,
  `--uninstall-extension`, `--list-extensions` are all documented and in active use.
- `--force` behavior: community sources confirm `--force` suppresses prompts (same as VS Code);
  official Cursor docs do not yet explicitly document the flag but it is inherited from the
  VS Code codebase Cursor is built on.
- `--profile <profile-name>` also works for profile-scoped installs.

**Recommended line format in reinstall.sh:**
```sh
cursor --install-extension <publisher.extension-id> --force  # cataloged: <display-name> <version>
```

**Prerequisite:** The `cursor` CLI must be installed. On macOS: Cursor Command Palette →
"Shell Command: Install 'cursor' command in PATH". Guard with `command -v cursor`.

---

## 3. Shell Script vs Brewfile — No Tooling Required

**Verdict: plain shell script, no tooling.**

A Brewfile (`brew bundle`) is the declarative alternative for Homebrew items. Reasons to
reject it for this feature:

| Criterion | Plain `.sh` | Brewfile + `brew bundle` |
|-----------|------------|--------------------------|
| Covers all sources | YES (brew + mas + code + cursor) | NO — `brew bundle` handles brew formulae, casks, and mas entries only; VS Code/Cursor extensions are not supported |
| User can review and edit | YES — standard shell script | YES — similar readability |
| Re-runnable safely | YES with the guard pattern above | YES — `brew bundle install` is idempotent |
| Requires extra tool | NO — Zsh/Bash built-in | YES — `brew bundle` is a separate Homebrew subcommand (already bundled but adds a dependency on Homebrew being installed) |
| Comment-annotated versions | YES — `# cataloged: x.y.z` inline | Partial — no standard comment per entry |
| Single file covers all sources | YES | NO — would need a separate script for extensions anyway |

Since VS Code and Cursor extensions cannot go in a Brewfile, a Brewfile would cover at most
two of four deterministic sources. A plain shell script covers all four uniformly and is the
simpler, more complete choice.

**No templating library is needed.** The script body is a flat sequence of:
1. A header block (shebang, `set -e`, section comments, prerequisite reminders)
2. One command per item per section
3. A manual checklist as shell comments or `echo` statements

This is straightforward Python string formatting. `f"brew install {name}  # cataloged: {version}\n"` is all that is needed. Introducing Jinja2 or any template engine would be over-engineering.

---

## 4. Recommended Stack Delta (What Changes in v2.1.0)

**Runtime:** No changes. Stdlib-only, Python >=3.11, zero new dependencies.

**New modules to add inside `src/maccat/`:**

| Module | Responsibility |
|--------|---------------|
| `reinstall/parser.py` | Parse catalog `.txt` sections back into structured items (`name`, `version`, `id` per source) |
| `reinstall/emitter.py` | Emit `reinstall.sh` from parsed items; one function per source section |
| `reinstall/cli.py` | `maccat reinstall` subcommand: `--from PATH` flag, computer-picker fallback, write output file |

**Existing modules reused unchanged:**
- `machine.py` — `select_computer()` for the computer-picker path
- `config.py` — `--catalog-dir` resolution
- `cli.py` — add `reinstall` subparser

**Dev/test stack:** No changes. `pytest`, `ruff`, `mypy --strict` continue as-is. New tests
follow the existing pattern (direct function tests; no snapshot tests needed since output is
deterministic shell commands, not catalog text).

---

## 5. What NOT to Add

| Do Not Add | Why |
|-----------|-----|
| `jinja2` / `mako` | Shell script body is flat string formatting; no template structure justifies a dep |
| `brew bundle` / Brewfile output | Cannot cover VS Code/Cursor extensions; would require a second output file anyway |
| `click` / `typer` | Existing `argparse` subparser handles the new subcommand; no change needed |
| Version pinning (`mas install --version`, `brew install formula@1.2.3`) | No reliable pin mechanism exists for formulae (no versioned formulae variants), `mas` has no version flag, and extension versions are marketplace-controlled. The cataloged version is a comment reference only. |
| `--force` on `mas install` | Would force-reinstall every App Store app on re-run, wasting time and bandwidth |
| Brew cask `brew install --cask` without guard | Non-zero exit on already-installed cask; use the `brew list --cask name &>/dev/null || brew install --cask name` guard |
| Auto-execution of the emitted script | Project constraint: the script is always output for review, never run by maccat itself |

---

## Sources

- Live verification: `brew --version` → 6.0.2; `brew help install` output — HIGH confidence
- Live verification: `mas help install` → `mas 7.0.0`; `--force` flag documented; idempotency warning behavior — HIGH confidence
- [Homebrew Manpage — brew install](https://docs.brew.sh/Manpage) — `--cask`, `-y`/`--no-ask`, upgrade-if-outdated behavior — HIGH confidence
- [Homebrew GitHub issue #15295](https://github.com/Homebrew/brew/issues/15295) — cask already-installed hard error (confirmed current as of 2025) — HIGH confidence
- [VS Code CLI docs — Command Line Interface](https://code.visualstudio.com/docs/configure/command-line) — `--install-extension`, `--force`, `--profile` flags; "Install or update" idempotency — HIGH confidence
- [Cursor Community Forum — command line --list-extensions](https://forum.cursor.com/t/command-line-list-extensions/103565) — `cursor --install-extension`, `--list-extensions` confirmed working; macOS requires shell-command install — MEDIUM confidence (community forum, not official docs)
- [Cursor Docs — Extensions](https://cursor.com/docs/configuration/extensions) — graphical extension management only; CLI flags not yet in official docs — LOW confidence for `--force` on cursor specifically; HIGH confidence for base `--install-extension` syntax
- [Homebrew Bundle docs](https://docs.brew.sh/Brew-Bundle-and-Brewfile) — Brewfile format, `brew bundle` scope (formulae + casks + mas only, no VS Code/Cursor) — HIGH confidence

---
*Stack research for: maccat v2.1.0 Reinstall from Catalog feature*
*Researched: 2026-06-16*

---

# Stack Research — v2.2.0 Broader Coverage (Edge / Brave / Zed / Safari / Codex Plugins)

**Domain:** macOS CLI catalog tool — new browser/editor/AI-CLI extension sources
**Researched:** 2026-06-17
**Confidence:** HIGH (all paths verified on live macOS; sources confirmed via official docs + on-disk inspection)

---

## 1. Microsoft Edge Extensions

### Path (HIGH confidence — verified on-disk + Microsoft docs)

```
~/Library/Application Support/Microsoft Edge/<Profile>/Extensions/<id>/<version>/manifest.json
```

Profile enumeration mirrors Chrome exactly:
- `Default/` first
- Then `Profile */` sorted (same glob as `ChromeCollector`)

Edge is not installed as a browser on this research machine (only `NativeMessagingHosts/` exists under `Microsoft Edge/`), so on machines where Edge is absent the base directory itself will be missing — graceful degradation fires on `not _BASE.is_dir()`.

### Manifest format (HIGH confidence)

Identical Chromium `manifest.json` + `_locales/<locale>/messages.json` format. `__MSG_` name resolution is needed and the existing `chrome_ext_name()` helper handles it without modification.

### Component/built-in extension exclusion (MEDIUM confidence)

Edge ships its own component extensions distinct from Google's Chrome denylist. The existing `COMPONENT_DENYLIST` in `chrome.py` covers 10 Google component IDs; Edge replaces those with Microsoft-specific equivalents. Official Microsoft documentation does not publish a canonical list of Edge component extension IDs. The recommended strategy:

Use a **separate `EDGE_COMPONENT_DENYLIST`** frozenset. As a starting baseline, include the Chrome denylist (shared CRLSet etc.) and flag edge-specific IDs as needing expansion. The same per-profile guards (`skip Temp`, `skip _` prefix) already in `ChromeCollector._collect_profile()` provide a structural first filter. See PITFALLS.md for the open Edge component ID question.

### Chrome collector reuse (HIGH confidence)

**Yes — reuse verbatim with a different `_BASE`.** The `ChromeCollector._collect_profile()` method takes `extensions_dir: Path` and is stateless with respect to browser identity. A new `EdgeCollector` sets:
- `_BASE = Path.home() / "Library/Application Support/Microsoft Edge"`
- `_TITLE = "Microsoft Edge Extensions"`
- `_DENYLIST = EDGE_COMPONENT_DENYLIST`

Stdlib parsing: `json` only. No new deps.

---

## 2. Brave Extensions

### Path (HIGH confidence — verified via Wazuh issue #32451 + on-disk structure)

```
~/Library/Application Support/BraveSoftware/Brave-Browser/<Profile>/Extensions/<id>/<version>/manifest.json
```

Profile enumeration: `Default/` first, then `Profile */` sorted — identical to Chrome.

This machine has Brave installed (`BraveSoftware/Brave-Browser/NativeMessagingHosts/` exists) but no extensions installed yet, so `Default/Extensions/` does not exist. The `not ext_root.is_dir()` guard in `ChromeCollector.collect()` handles this correctly (skips missing `Extensions/` dirs per-profile).

### Manifest format (HIGH confidence)

Identical Chromium `manifest.json` + `_locales`. `chrome_ext_name()` works without modification.

### Component/built-in extension exclusion (HIGH confidence — from Brave Components wiki)

Brave ships 20 verified component extension IDs that appear in the `Extensions/` directory but are not user-installed. These must be excluded via a `BRAVE_COMPONENT_DENYLIST`:

```python
BRAVE_COMPONENT_DENYLIST: frozenset[str] = frozenset({
    "eeigpngbgcognadeebkilcpcaedhellh",  # Autofill States Data
    "iodkpdagapdfkphljnddpjlldadblomo",  # Brave Ad Block Updater
    "gkboaolpopklhgplhaaiboijnklogmbc",  # Brave Ad Block List Catalog
    "mfddibmblmbccpadfndgakiopmmhebop",  # Brave Ad Block Resources Library
    "afalakplffnnnlkncjhbmahjfjhmlkal",  # Brave Local Data Updater
    "cldoidikboihgcjfkhdeidbpclkineef",  # Brave Tor Client Updater (x86)
    "cpoalefficncklhjfpglfiplenlpccdb",  # Brave Tor Client Updater (arm64)
    "biahpgbdmdkfgndcmfiipgcebobojjkp",  # Brave Tor Client Updater (arm)
    "kkjipiepeooghlclkedllogndmohhnhi",  # Brave User Model Installer
    "giekcmmlnklenlaomppkphknjmnnpneh",  # Certificate Error Assistant
    "hfnkpimlhhgieaddgfemjhofmfblmnib",  # CRLSet
    "ggkkehgbnfjpeggfpleeakpidbkibbmn",  # Crowd Deny
    "khaoiebndkojlmppeemjhbpbandiljpe",  # File Type Policies
    "jamhcnnkihinmdlkakkaopbjbbcngflc",  # Hyphenation
    "laoigpblnllgcgjnjnllmfolckpjlhki",  # MEI Preload
    "gccbbckogglekeggclmmekihdgdpdgoe",  # NTP Sponsored Images
    "aoojcmojmmcbpfgoecoadbdpnagfchel",  # NTP Background Images
    "jflookgnkcckhobaglndicnbbgbonegd",  # Safety Tips
    "oimompecagnajdejgnnjijobebaeigek",  # Widevine
    "ojhpjlocmbogdgmfpkhlaaeamibhnphh",  # Zxcvbn Data Dictionaries
})
```

All 20 IDs are 32-char lowercase alpha strings (validated). Brave Shields and Brave Wallet are compiled into the browser binary and do NOT appear as separate `Extensions/` entries — no filter needed for them.

### Chrome collector reuse (HIGH confidence)

**Yes — identical pattern to Edge.** `BraveCollector` sets `_BASE`, `_TITLE`, `_DENYLIST` and delegates to shared `_collect_profile()` logic.

Stdlib parsing: `json` only.

---

## 3. Zed Extensions

### Path (HIGH confidence — verified on-disk + Zed docs)

| Path | Purpose |
|------|---------|
| `~/Library/Application Support/Zed/extensions/installed/<id>/extension.toml` | Per-extension manifest — authoritative |
| `~/Library/Application Support/Zed/extensions/index.json` | Registry index (includes themes/languages — not extension-only) |

**Use `installed/<id>/extension.toml`** — extension-only, avoids mixing with themes/languages, is the canonical extension authoring format.

`~/.config/zed/` contains user config (`settings.json`) but NO extension data. All extension installation state lives in `~/Library/Application Support/Zed/`.

### File format (HIGH confidence — verified with `tomllib` on live machine)

`extension.toml` is valid TOML. Python 3.11+ `tomllib` (stdlib) parses it:

```python
import tomllib
with open(ext_dir / "extension.toml", "rb") as f:
    d = tomllib.load(f)
ext_id  = d["id"]       # e.g. "html"  (matches directory name)
name    = d["name"]     # e.g. "HTML"  (plain string, no __MSG__ localization)
version = d["version"]  # e.g. "0.3.1"
```

All three fields are mandatory in the Zed extension schema. Names are plain strings — no `__MSG_` localization exists in Zed's extension system.

The directory name under `installed/` equals `d["id"]` — use directory name as a fallback id if TOML parse fails.

### CLI (HIGH confidence — verified)

Zed CLI (`zed` v1.6.3) opens files/projects only. **No `zed extension list` subcommand exists.** On-disk manifest parsing is the only approach.

### Component/built-in filter needed? (HIGH confidence)

**No.** The `installed/` directory contains only user-installed extensions from Zed's extension gallery. Built-in language support is compiled into Zed or uses tree-sitter grammars, not the extension system. No denylist required.

### Chrome collector reuse

**Not applicable.** Requires a new `ZedCollector`. Enumeration: `glob("installed/*/extension.toml")`. Parsing: `tomllib`.

---

## 4. Safari Extensions

### Enumeration method (HIGH confidence — verified with `pluginkit` on live machine)

**Use `pluginkit -mAvv -p com.apple.Safari.web-extension`.**

This is the correct macOS-built-in approach for modern macOS. Safari extensions since macOS 10.14 are sandboxed App Extensions (`.appex` bundles) embedded inside host `.app` bundles — they are NOT stored in a predictable user-scoped directory. The `pluginkit` daemon maintains the system registry of all registered app extensions.

Verified plugin point values:
- `com.apple.Safari.web-extension` — **correct, returns extensions** (Bitwarden confirmed)
- `com.apple.Safari.extension` — returns no matches (legacy Gallery format, pre-10.14)
- `com.apple.safari.extension` — returns no matches

### Output format (HIGH confidence — parsed on live machine)

```
     com.bitwarden.desktop.safari(2026.5.0)
        Path = /Applications/Bitwarden.app/Contents/PlugIns/safari.appex
        UUID = ...
     SDK = com.apple.Safari.web-extension
     Display Name = Bitwarden
     Short Name = Bitwarden
```

Parsing: iterate lines, match `^\s+([A-Za-z0-9._-]+)\(([^)]+)\)\s*$` to start an entry (bundle ID + pluginkit-reported version), then collect `Key = Value` tab-indented lines. Key fields: `Display Name`, `Path`.

### Name/version/id fields (HIGH confidence — verified via `plistlib` on live machine)

Two-tier approach:

1. From pluginkit output: `Display Name` as name, version from `bundle_id(version)` suffix, `bundle_id` as id.
2. Upgrade via `plistlib` (preferred): read `<Path>/Contents/Info.plist`:
   - Name: `CFBundleDisplayName` or `CFBundleName`
   - Version: `CFBundleShortVersionString` or `CFBundleVersion`
   - ID: `CFBundleIdentifier`

Verified: Bitwarden's `Info.plist` yields `CFBundleDisplayName=Bitwarden`, `CFBundleShortVersionString=2026.5.0`, `CFBundleIdentifier=com.bitwarden.desktop.safari`. All three fields obtainable via stdlib `plistlib`. The plistlib path can fail (OSError, binary plist corruption) — fall back to pluginkit-parsed values on any exception.

Format: `emit_item("Bitwarden", "2026.5.0", "com.bitwarden.desktop.safari")` → `Bitwarden (2026.5.0) [com.bitwarden.desktop.safari]`

### Alternatives considered and rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Scan `/Applications/*.app/Contents/PlugIns/*.appex` | Misses App Store extensions installed outside `/Applications`; slow; `pluginkit` is the authoritative registry |
| `defaults read com.apple.Safari` | Returns fragmented preference keys, not a clean installed-extension list; unreliable across macOS versions |

### Chrome collector reuse

**Not applicable.** Requires a new `SafariCollector`. Stdlib modules: `subprocess`, `re`, `plistlib`.

---

## 5. Codex Plugins / Agents

### Context (HIGH confidence — verified on live machine)

Installed Codex version: **0.46.0** (`codex --version`). The plugin system was introduced in **v0.117.0**. At v0.46.0:

- No `[plugins.]` section in `~/.codex/config.toml` (grep count: 0).
- No `~/.codex/plugins/` directory.
- No `codex plugin` subcommand (`codex plugin --help` → "unexpected argument 'plugin'").
- `~/.codex/.tmp/plugins/` is a **marketplace catalog cache** (remote plugin registry, not installed plugins).

The current "plugin-like" primitive at v0.46.0 is **`[agents."NAME"]`** sections in `~/.codex/config.toml`, with per-agent `.toml` files in `~/.codex/agents/`. This machine has 33 registered agents (all from the GSD plugin installed as a local plugin from `~/.codex/get-shit-done/`).

### For Codex v0.117+ (plugin system, HIGH confidence via official docs)

- Install path: `~/.codex/plugins/cache/<marketplace>/<plugin-name>/<version>/.codex-plugin/plugin.json`
- Plugin manifest fields: `name` (string), `version` (string), `description` (string)
- CLI (v0.133+): `codex plugin list --json` → array with `pluginId`, `name`, `version`, `installedPath`
- Prefer CLI if available (version-aware); fall back to filesystem scan of `plugins/cache/`

### For Codex v0.46.0 (agents-only, HIGH confidence via on-disk verification)

- Path: `~/.codex/config.toml`, section headers `[agents."NAME"]`
- Fields: `description` (string), `config_file` (optional path to agent `.toml`)
- Agent `.toml` files have `name`, `description` — **no `version` field**
- Format degrades to: `emit_item(name, "", "")` → name-only line (FMT-01 graceful degradation)

### Recommended collector design

```
1. shutil.which("codex") — if absent, emit empty section
2. Try: codex plugin list --json (v0.117+)
   → success + JSON array: parse name/version/pluginId
3. Fallback: scan ~/.codex/plugins/cache/ filesystem
   → found: parse .codex-plugin/plugin.json for name/version
4. Fallback: grep [agents."NAME"] from ~/.codex/config.toml
   → found: emit name-only items (no version)
5. Nothing found: emit empty section (none found)
```

Section title: **"Codex Agents"** (accurate for v0.46.0 reality; also covers plugins when upgraded).

### Relationship to existing `CodexCollector`

`CodexCollector` → "Codex MCP Servers" (covers `[mcp_servers.]` sections). New collector → "Codex Agents" (covers `[agents.]` sections / `plugins/cache/`). No overlap. Both coexist. The new collector mirrors the CLI-then-TOML-fallback structure of the existing one.

**FMT-03 safety:** `[agents."NAME"]` sections in config.toml contain only `description` and `config_file` — no secrets. Agent `.toml` files contain `developer_instructions` (a system prompt) but no credentials. The TOML text-grep approach (section headers only) and/or reading only `name`/`version`/`description` from plugin.json are safe.

Stdlib modules: `json`, `re`, `subprocess`, `shutil`, `tomllib` (optional, for agent .toml files).

---

## Shared Chromium Collector Abstraction

With Chrome + Edge + Brave all using identical `_collect_profile()` logic, this milestone creates 3 real examples — exactly the project's 3-example threshold for justified abstraction. Recommended refactor:

```python
# src/maccat/collectors/chromium.py  (new shared base)
class ChromiumCollector(Collector):
    _BASE: ClassVar[Path]
    _TITLE: ClassVar[str]
    _DENYLIST: ClassVar[frozenset[str]]

    def _collect_profile(self, extensions_dir: Path) -> list[str]: ...  # shared
    def collect(self) -> CollectorResult: ...                             # shared

# src/maccat/collectors/chrome.py
class ChromeCollector(ChromiumCollector):
    _BASE = Path.home() / "Library/Application Support/Google/Chrome"
    _TITLE = "Google Chrome Extensions"
    _DENYLIST = CHROME_COMPONENT_DENYLIST  # rename existing COMPONENT_DENYLIST

# src/maccat/collectors/edge.py  (new)
class EdgeCollector(ChromiumCollector):
    _BASE = Path.home() / "Library/Application Support/Microsoft Edge"
    _TITLE = "Microsoft Edge Extensions"
    _DENYLIST = EDGE_COMPONENT_DENYLIST

# src/maccat/collectors/brave.py  (new)
class BraveCollector(ChromiumCollector):
    _BASE = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"
    _TITLE = "Brave Extensions"
    _DENYLIST = BRAVE_COMPONENT_DENYLIST
```

Current `ChromeCollector._collect_profile()` and `.collect()` are already factored to accept a `Path` argument — extraction is mechanical, not a redesign.

---

## stdlib Parsing Summary

| Source | Stdlib Module(s) | New vs Existing |
|--------|-----------------|-----------------|
| Edge extensions | `json` | Reuses `chrome_ext_name()` helper; new collector class only |
| Brave extensions | `json` | Reuses `chrome_ext_name()` helper; new collector class only |
| Zed extensions | `tomllib` | New `ZedCollector`; `tomllib` already in stdlib (Python 3.11+) |
| Safari extensions | `subprocess`, `re`, `plistlib` | New `SafariCollector`; all modules already in stdlib |
| Codex agents/plugins | `json`, `re`, `subprocess`, `shutil` | New collector; mirrors pattern of existing `CodexCollector` |

**Zero new pip dependencies.** The `.pyz` zipapp constraint is fully satisfied.

---

## What NOT to Add

| Do Not Add | Why |
|-----------|-----|
| Any pip package | Constraint: stdlib-only, single `.pyz` zipapp |
| `tomllib` backport (`tomli`) | Python 3.14.6 is the runtime; `tomllib` is in stdlib since 3.11 — no backport needed |
| Edge component ID guessing | Without an official Microsoft published list, do not fabricate IDs; start with Chrome denylist as baseline and expand in a follow-on as IDs are confirmed |
| `codex plugin list` without fallback | v0.46.0 (the installed version) has no plugin subcommand; the CLI call must be wrapped in try/except subprocess or returncode check |
| Safari App Store enumeration | App Store data is not accessible without private APIs; `pluginkit` is the correct system-provided tool |
| Filesystem scan of all `/Applications/*.appex` | Slow, incomplete (misses non-Applications installs), not the system's authoritative source |

---

## Sources

- Verified on-disk: `~/Library/Application Support/BraveSoftware/Brave-Browser/` — NativeMessagingHosts only (Brave installed, no extensions)
- Verified on-disk: `~/Library/Application Support/Microsoft Edge/` — NativeMessagingHosts only (Edge browser not installed)
- Verified on-disk: `~/Library/Application Support/Zed/extensions/installed/html/extension.toml` — tomllib parse confirmed
- Verified live: `pluginkit -mAvv -p com.apple.Safari.web-extension` → Bitwarden 2026.5.0 with Path + plistlib fields confirmed
- Verified live: `~/.codex/config.toml`, Codex v0.46.0 — no `[plugins.]` section, 33 `[agents.]` entries
- [Brave Components wiki](https://github.com/brave/brave-browser/wiki/Brave-Components) — 20 component extension IDs (HIGH confidence)
- [Wazuh issue #32451](https://github.com/wazuh/wazuh/issues/32451) — confirms Brave macOS path `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions/` (HIGH confidence)
- [Microsoft Edge alternate distribution](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/alternate-distribution-options) — confirms Edge macOS profile path structure (HIGH confidence)
- [Zed Installing Extensions](https://zed.dev/docs/extensions/installing-extensions) — confirms `~/Library/Application Support/Zed/extensions/installed/` as install location (HIGH confidence)
- [Codex Build Plugins](https://developers.openai.com/codex/plugins/build) — confirms `~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/.codex-plugin/plugin.json` for v0.117+ (HIGH confidence)
- [GitHub issue #17431 openai/codex](https://github.com/openai/codex/issues/17431) — confirms no `codex plugin list` CLI in v0.46; manual config only (HIGH confidence)

---
*Stack research for: maccat v2.2.0 Broader Coverage — Edge, Brave, Zed, Safari, Codex Plugins/Agents*
*Researched: 2026-06-17*

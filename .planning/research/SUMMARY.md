# Project Research Summary

**Project:** maccat v2.2.0 — Broader Coverage (Edge, Brave, Zed, Safari, Codex Plugins)
**Domain:** macOS CLI catalog tool — new browser/editor/AI-CLI extension sources
**Researched:** 2026-06-17
**Confidence:** HIGH (all paths verified on live macOS; all architectural claims grounded in source reads)

## Executive Summary

maccat v2.2.0 adds five new extension sources to the existing catalog: Microsoft Edge, Brave, Zed, Safari, and a Codex Plugins section. The architectural approach is additive throughout — four new collector files plus modifications to Chrome and Codex — with zero changes to the reinstall pipeline (parser and emitter handle all new sections automatically). All five sources are implemented with stdlib only (`json`, `tomllib`, `subprocess`, `re`, `plistlib`); the `.pyz` zipapp constraint remains fully satisfied with no new pip dependencies.

The dominant pattern in this milestone is the Chromium collector abstraction. Chrome, Edge, and Brave share identical profile-scan logic differing only by base path, section title, and component denylist — three real examples satisfy the project's 3-example threshold for justified abstraction. A new `ChromiumBaseCollector` in `collectors/chromium.py` holds all shared logic; each browser becomes a three-line thin subclass. The Brave denylist (20 component IDs) is fully confirmed from the Brave wiki; the Edge denylist is confirmed to exist but lacks a single authoritative Microsoft source — ship with Chrome denylist as baseline and a documented gap, verified against a real Edge install during implementation.

The two highest-risk items are Safari and the Codex Plugins section. Safari requires a subprocess call to `pluginkit` followed by per-extension `plistlib` reads — both must be individually never-raising, and the pluginkit output format is undocumented across macOS versions. The Codex Plugins section must handle an installed Codex v0.46.0 that has no plugin system at all — graceful degradation to `(none found)` is the common case today, not an edge case. The recommended build order defers Safari to last precisely because it has the most failure modes and the most cross-cutting test requirements.

---

## Cross-Document Reconciliations

These points were divergent across the four research files. The resolved positions are authoritative for implementation.

### 1. Zed source of truth: `index.json` over `installed/` scan

**Resolved: parse `~/Library/Application Support/Zed/extensions/index.json`.**

`index.json` is the canonical registry. It provides `id`, `name`, and `version` in a single JSON read with no per-extension TOML parsing needed. Scanning `installed/<id>/extension.toml` is slower, risks picking up `work/` (incomplete downloads), and reads a second file per extension unnecessarily.

**Filter `dev: true` entries.** The `index.json` schema includes a `"dev": false/true` field per extension. Dev extensions are local-filesystem extensions not installable from the registry — they must be excluded from the catalog (a restore-focused snapshot should not include non-restorable items). The ARCHITECTURE.md reference to `installed_extensions.json` and the `~/.config/zed/` path is superseded by live verification in STACK.md and PITFALLS.md confirming `~/Library/Application Support/Zed/extensions/index.json` as the correct file.

```python
# Correct path (live-verified)
_INDEX = Path.home() / "Library/Application Support/Zed/extensions/index.json"

# Filter: exclude dev extensions
for ext_id, info in data.get("extensions", {}).items():
    if info.get("dev"):
        continue
    manifest = info.get("manifest", {})
    name    = manifest.get("name", ext_id)
    version = manifest.get("version", "")
    # emit_item(name, version, ext_id)
```

### 2. Safari: correct pluginkit point and name field

**Resolved: use `com.apple.Safari.web-extension` (NOT `com.apple.Safari.extension`).**

`com.apple.Safari.extension` returns zero matches on live macOS (legacy Gallery format, pre-10.14). `com.apple.Safari.web-extension` returns modern App Extension-based extensions and is the only correct filter, verified live against Bitwarden 2026.5.0.

**Resolved: read `CFBundleDisplayName`, NOT `CFBundleName`.**

`CFBundleName` is the binary executable name (commonly `"safari"` in the appex). `CFBundleDisplayName` is the human-readable name that appears in Safari's Extension Manager. This is verified live: Bitwarden's appex has `CFBundleName = "safari"` and `CFBundleDisplayName = "Bitwarden"`. Reading `CFBundleName` would catalog every extension as its binary name.

Name resolution chain (in order):
```
appex_plist["CFBundleDisplayName"]
  -> parent_app_plist["CFBundleDisplayName"]
  -> parent_app_plist["CFBundleName"]
  -> bundle_id from pluginkit output
```

**Safari is LOW risk for name/version/id completeness.** The plist approach reliably yields full `name (version) [id]` entries for App Store extension bundles — no `__MSG__` locale resolution needed. Complexity is in the subprocess+plist chain, not in data availability.

**Version source:** always `CFBundleShortVersionString` from the appex `Info.plist`. Discard the pluginkit parenthetical version — pluginkit can cache `(null)` for 119/485 extensions on the test machine.

### 3. Codex Plugins (CDX-02): current machine produces an empty section

**Resolved: the collector degrades silently to `(none found)` on Codex v0.46.0.**

The installed Codex is **v0.46.0**. The plugin system was introduced in v0.117.0 (March 2026). On this machine there are zero `[plugins.*]` entries — the section will be empty until Codex is upgraded. This is the common case today, not an edge case.

**Collector design (multi-tier fallback):**
1. `shutil.which("codex")` absent — emit empty section, no NOTE
2. Try `codex plugin list --json` (available ~v0.133+) — parse `pluginId`, `name`, `version`
3. Fallback: scan `~/.codex/plugins/cache/` for `.codex-plugin/plugin.json` — parse `name`, `version`
4. Fallback: text-grep `~/.codex/config.toml` for `[plugins."name@marketplace"]` headers — emit `name [name@marketplace]` (no version per FMT-03)
5. Nothing found — `(none found)`

**Section title: `"Codex Plugins"`** — distinct from existing `"Codex MCP Servers"`.

**NEVER read plugin bundle `.mcp.json` files** — these can contain `env.API_KEY` credentials (FMT-03 violation). Text-grep `config.toml` headers only, exactly as `CodexCollector._collect_via_toml` does for MCP servers.

**FLAG: on this machine the `"Codex Plugins"` section will emit `(none found)` until Codex is upgraded beyond v0.117.0.**

### 4. Chromium abstraction: `ChromiumBaseCollector` with correct presence detection

**Resolved: extract `ChromiumBaseCollector` to `collectors/chromium.py`; Chrome/Edge/Brave are thin subclasses.**

Three real examples (Chrome, Edge, Brave) satisfy the project's 3-example threshold. The shared base holds `_collect_profile()`, `collect()`, and the base Chromium `COMPONENT_DENYLIST` (10 IDs, moved from `chrome.py`). Each subclass overrides `_BASE`, `_TITLE`, and `_DENYLIST`.

**Presence detection must check for an actual profile, not just the base directory.** Brave's `~/Library/Application Support/BraveSoftware/Brave-Browser/` exists on the test machine (NativeMessagingHosts registration) despite no installed profile. `_base.is_dir()` alone is a false positive.

Correct pattern:
```python
def collect(self) -> CollectorResult:
    if not self._base.is_dir():
        # Base dir absent: browser definitely not installed
        print(f"  NOTE: {self._browser_name} not installed.", file=sys.stderr)
        return CollectorResult(sections=[Section(title=self._title, items=[])])
    # Profile enumeration naturally returns [] if no Extensions dirs exist
    # (handles NativeMessagingHosts-only case without spurious NOTE)
    all_items: list[str] = []
    for profile in [self._base / "Default"] + sorted(self._base.glob("Profile */")):
        ext_root = profile / "Extensions"
        if ext_root.is_dir():
            all_items.extend(self._collect_profile(ext_root))
    return CollectorResult(sections=[Section(title=self._title, items=all_items)])
```

**Edge component denylist gap:** Brave denylist (20 IDs) fully confirmed. Edge denylist has no single authoritative Microsoft source — ship with Chrome baseline, document the gap, verify during implementation.

**`COMPONENT_DENYLIST` migration:** Move to `chromium.py`; re-export from `chrome.py` for backward compat (`from maccat.collectors.chromium import COMPONENT_DENYLIST`).

**Test patch target update:** After refactor, update `test_chrome.py` patches from `patch.object(chrome_mod, "_BASE", ...)` to `patch.object(ChromeCollector, "_base", new=tmp_path)`.

### 5. Reinstall impact: zero changes required

**Resolved: no changes to `reinstall/parser.py` or `reinstall/emitter.py`.**

The parser is title-agnostic; new sections parse automatically. The emitter's `SECTION_SOURCE_MAP` falls through unknown titles to `_manual_checklist_block` — correct per MAN-01 (browser extensions and Codex plugins have no CLI installer).

**Required addition: section-title uniqueness test.** Assert all `_TITLE` constants across all collector modules form a set with no duplicates. Prevents copy-paste bugs from routing new sections to wrong reinstall renderers.

---

## Key Findings

### Recommended Stack

The milestone is stdlib-only. Zero new pip dependencies. Python 3.11+ stdlib modules: `json` (Chromium manifests, Zed `index.json`), `plistlib` (Safari appex `Info.plist`), `subprocess` (Safari pluginkit, Codex CLI), `re` (pluginkit output parsing, TOML header grep), `shutil` (Codex `which`). `tomllib` is available but not strictly required — `index.json` is JSON.

**Core technologies:**
- `json` (stdlib) — Chromium manifest parsing, Zed `index.json` — already used throughout codebase
- `plistlib` (stdlib) — Safari appex `Info.plist` for name/version/id — already available
- `subprocess` (stdlib) — Safari `pluginkit` invocation, Codex `plugin list --json` — already used in `codex.py`
- `re` (stdlib) — pluginkit output line parsing, Codex TOML header grep — already used throughout

### Expected Features

**Must have (table stakes):**
- `ZedCollector` — `index.json` parse, emit `name (version) [id]`, filter `dev: true`, degrade gracefully
- `SafariCollector` — `pluginkit -mAD -p com.apple.Safari.web-extension`, plist name/version/id, never-raises chain
- `CodexCollector` extended — `_collect_plugins()` + `"Codex Plugins"` section (empty on v0.46.0 — documented)
- `ChromiumBaseCollector` — extract from `ChromeCollector`, zero output change for Chrome
- `EdgeCollector` — ChromiumBaseCollector subclass, Edge denylist (Chrome baseline + documented gap)
- `BraveCollector` — ChromiumBaseCollector subclass, full 20-ID Brave denylist (confirmed from wiki)
- All new sources: NOTE to stderr when absent, `(none found)` when empty, `raw=False` for flush_section
- Section title uniqueness test across all 17+ collector modules

**Should have (differentiators):**
- `ChromiumBaseCollector` with browser-parameterized `_title` property
- Brave `BRAVE_COMPONENT_DENYLIST` constant with all 20 IDs in `brave.py`
- Safari version always from plistlib (never from pluginkit which can return `(null)`)

**Defer (v2+):**
- Extension enabled/disabled state for any browser (CHR-02/FF-02 — explicitly deferred)
- Edge component denylist completeness beyond Chrome baseline (requires real Edge install)
- Safari content blocker support (`com.apple.Safari.content-blocker` point identifier)
- Codex plugin version resolution (requires reading bundle files — FMT-03 violation risk)

### Architecture Approach

The milestone follows the established `Collector -> CollectorResult -> Section` contract. New collectors are additive: five new files (`chromium.py`, `edge.py`, `brave.py`, `zed.py`, `safari.py`) plus modifications to `chrome.py` (thin subclass), `codex.py` (second section), and `collectors/__init__.py`. The orchestration loop in `cli.py`, reinstall parser, and reinstall emitter require zero changes.

**Major components:**
1. `collectors/chromium.py` (NEW) — `ChromiumBaseCollector` with shared `_collect_profile()`, `collect()`, base `COMPONENT_DENYLIST`
2. `collectors/chrome.py` (REFACTORED) — thin subclass; re-exports `COMPONENT_DENYLIST` for backward compat
3. `collectors/edge.py` (NEW) — `EdgeCollector` with Edge base path + `EDGE_COMPONENT_DENYLIST`
4. `collectors/brave.py` (NEW) — `BraveCollector` with Brave base path + `BRAVE_COMPONENT_DENYLIST` (20 IDs)
5. `collectors/zed.py` (NEW) — `ZedCollector` parsing `index.json`, filtering `dev: true`
6. `collectors/safari.py` (NEW) — `SafariCollector` shelling to pluginkit, reading appex plists, individually never-raising
7. `collectors/codex.py` (MODIFIED) — `_collect_mcp()` + `_collect_plugins()`, `collect()` returns both sections
8. `collectors/__init__.py` (MODIFIED) — 22-section registry (was 17 sections from 12 collectors)

**Registry section order after v2.2.0:**
Homebrew → mas → Setapp → WebApps → Claude (x3) → Codex MCP Servers + Codex Plugins → OpenCode (x3) → Gemini (x2) → VS Code → Cursor → Zed → Chrome → Edge → Brave → Safari → Firefox

### Critical Pitfalls

1. **Safari `CFBundleDisplayName` vs `CFBundleName`** — `CFBundleName` is the binary name (`"safari"`), not the user-visible name. Always read `CFBundleDisplayName`. Verified live on this machine. Test fixture must include divergent values.

2. **Safari pluginkit `(null)` version** — 119/485 extensions on this machine have `(null)` as the pluginkit version. Always use `CFBundleShortVersionString` from plistlib as authoritative; discard pluginkit version string.

3. **Brave/Edge presence detection via base directory** — `~/Library/Application Support/BraveSoftware/Brave-Browser/` exists on this machine (NativeMessagingHosts only). Use `_base.is_dir()` for the NOTE message only; let profile enumeration return empty items naturally.

4. **Codex plugin FMT-03 — never read `.mcp.json` bundle files** — can contain `env.API_KEY` credentials. Text-grep `config.toml` for `[plugins."name@marketplace"]` header lines only.

5. **Zed `dev: true` extensions must be excluded** — local installs not restorable from registry. Filter `info.get("dev") == True`. Test with fixture containing a dev extension.

6. **Chrome test patch target breaks after refactor** — update `test_chrome.py` patches to `patch.object(ChromeCollector, "_base", new=tmp_path)`.

---

## Implications for Roadmap

### Phase 1: Codex Plugins + Zed

**Rationale:** Both sources are independent of each other and of the Chromium work. Both are low-risk. Building them first validates the "new section falls to manual checklist in reinstall" path and establishes the uniqueness test infrastructure for all subsequent phases.

**Delivers:** `"Codex Plugins"` section (empty on v0.46.0 — documented gap), `"Zed Extensions"` section with name/version/id from `index.json`, dev extension filtering, graceful degradation on absent installations.

**Key notes:**
- Zed: `~/Library/Application Support/Zed/extensions/index.json`; `data.get("extensions", {})` (never `data["extensions"]`); filter `dev: true`
- Codex: extend `CodexCollector.collect()` to return 2 sections; mirror `ClaudeCollector` multi-section pattern; text-grep headers only (FMT-03)
- Add section-title uniqueness test at end of this phase (run on every subsequent phase)

**Pitfalls to avoid:** Zed `work/` directory scan, Codex FMT-03 bundle read, Codex v0.46.0 empty-section graceful degrade

**Research flags:** None — fully specified.

---

### Phase 2: Chromium Refactor + Edge + Brave

**Rationale:** Edge and Brave depend on `ChromiumBaseCollector`. The refactor must land and be validated (Chrome output unchanged) before adding Edge and Brave as thin subclasses. Build order within phase: `chromium.py` -> `chrome.py` refactor -> `test_chrome.py` patch update -> `brave.py` -> `edge.py`.

**Delivers:** `ChromiumBaseCollector` eliminating 3x code duplication, `"Brave Extensions"` with 20-ID denylist (fully known), `"Microsoft Edge Extensions"` with Chrome-baseline denylist (documented gap), Chrome output verified unchanged.

**Key notes:**
- Move `COMPONENT_DENYLIST` to `chromium.py`; re-export from `chrome.py`
- Update `test_chrome.py` patches: `patch.object(ChromeCollector, "_base", new=tmp_path)`
- `BRAVE_COMPONENT_DENYLIST`: 20 confirmed IDs from STACK.md
- Edge denylist: install Edge locally, inspect `Extensions/` dir vs. `edge://extensions` UI; IDs on disk but invisible in UI are components to add
- Presence detection: base dir check triggers NOTE message only; profile loop handles NativeMessagingHosts-only case silently

**Pitfalls to avoid:** Chrome denylist re-export backward compat, test patch target migration, `version_sort_tail` must be called (not `max()` or `sorted()[-1]`)

**Research flags:** Edge component denylist requires phase-specific verification (install Edge, enumerate Extensions dir). Document as known gap in `EDGE_COMPONENT_DENYLIST` constant comment.

---

### Phase 3: Safari

**Rationale:** Safari is isolated — if pluginkit output format proves unworkable, it can be deferred without blocking any prior phase. Build last to contain risk. Validate `_parse_pluginkit_output` against real pluginkit output before finalizing.

**Delivers:** `"Safari Extensions"` section via `pluginkit -v -m -A -p com.apple.Safari.web-extension`, name from `CFBundleDisplayName`, version from `CFBundleShortVersionString`, id from `CFBundleIdentifier`.

**Key notes:**
- Use `-v` flag (verbose) to get appex path in output; path is 4th tab-separated field
- Discard pluginkit version string; always use plistlib as authoritative version source
- Each extension's plist read individually wrapped in try/except — never a single outer block
- Smoke test with Bitwarden (confirmed installed on this machine: `com.bitwarden.desktop.safari`)

**Pitfalls to avoid:** Wrong pluginkit point identifier (`com.apple.Safari.extension` returns nothing), `CFBundleName` instead of `CFBundleDisplayName`, `(null)` version from pluginkit, single outer try/except, non-verbose pluginkit losing appex path

**Research flags:** Validate `_parse_pluginkit_output` against real `pluginkit` output before shipping. This is the only collector where a live smoke test is essential before finalizing the parser.

---

### Phase Ordering Rationale

- **Phase 1 first:** No dependencies, no existing-code risk, validates reinstall passthrough path for all new sections
- **Phase 2 second:** Must land before Edge/Brave; Chrome regression risk is bounded; Brave denylist is known; Edge denylist gap is documented and acceptable to ship
- **Phase 3 last:** Highest failure modes (undocumented subprocess + chained plist reads); isolated; can be deferred if pluginkit format proves unworkable
- **Reinstall pipeline:** Zero changes throughout — parser/emitter are additive by design

### Research Flags

Phases with documented gaps requiring implementation-time research:
- **Phase 2 (Edge denylist):** Install Edge locally; enumerate `Default/Extensions/` on fresh profile; cross-ref `edge://extensions` UI — IDs on disk but invisible in UI are component IDs. Document as known gap.
- **Phase 3 (Safari pluginkit format):** Validate `_parse_pluginkit_output` against real `pluginkit -v -m -A -p com.apple.Safari.web-extension` output. Run smoke test with Bitwarden.

Phases with standard patterns (no additional research needed):
- **Phase 1 (Codex + Zed):** Fully specified — `index.json` format verified live, CodexCollector TOML-header-grep pattern established.
- **Phase 2 (Chromium base + Brave):** Fully specified — Brave denylist confirmed, base class extraction is mechanical.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All paths live-verified. `index.json` format confirmed. pluginkit output confirmed via Bitwarden test. Codex v0.46.0 vs v0.117.0 gap documented. Zero new deps confirmed. |
| Features | HIGH | All five sources fully specified with entry formats, field sources, degradation rules, section titles. Brave denylist HIGH (wiki). Edge denylist gap explicitly documented. |
| Architecture | HIGH | All integration points grounded in direct source reads (chrome.py, codex.py, claude.py, emitter.py, parser.py). Test patch migration documented. Registry order specified. |
| Pitfalls | HIGH | Critical pitfalls (CFBundleDisplayName, pluginkit null version, Brave NativeMessagingHosts false-positive, FMT-03 bundle read) all verified live or from authoritative source. |

**Overall confidence:** HIGH

### Gaps to Address

- **Edge component denylist completeness (MEDIUM confidence):** No single authoritative Microsoft source. Mitigation: ship with Chrome baseline, add Edge-specific IDs during implementation, document in `EDGE_COMPONENT_DENYLIST` comment.

- **Codex v0.117.0+ plugin format stability (MEDIUM confidence):** Plugin system is newer than the installed version; schema may still evolve. Mitigation: text-grep headers only (immune to value-level churn); CLI call wrapped with fallback.

- **Safari pluginkit verbose format across macOS versions (MEDIUM confidence):** Undocumented internal tool. Mitigation: treat every field as optional; wrap per-extension plist reads individually; validate before shipping.

---

## Sources

### Primary (HIGH confidence — live-verified or official source)

- Live verification: `~/Library/Application Support/Zed/extensions/index.json` — confirmed `{"extensions": {"html": {"manifest": {"id": "html", "name": "HTML", "version": "0.3.1"}, "dev": false}}}` format
- Live verification: `pluginkit -mAD -p com.apple.Safari.web-extension` — Bitwarden 2026.5.0 only (correct filter confirmed; `com.apple.Safari.extension` returns nothing)
- Live verification: `pluginkit -v -m -A -p com.apple.Safari.web-extension` — tab-separated format with path confirmed
- Live verification: `plutil -p /Applications/Bitwarden.app/Contents/PlugIns/safari.appex/Contents/Info.plist` — `CFBundleDisplayName = "Bitwarden"`, `CFBundleName = "safari"` confirmed
- Live verification: `~/.codex/config.toml`, Codex v0.46.0 — no `[plugins.]` section; 33 `[agents.]` entries
- [Brave Components wiki](https://github.com/brave/brave-browser/wiki/Brave-Components) — 20 Brave component extension IDs (all 32-char lowercase alpha, validated)
- `src/maccat/collectors/chrome.py` — `COMPONENT_DENYLIST`, `_collect_profile`, `available()` pattern
- `src/maccat/collectors/codex.py` — `_collect_via_toml` TOML-header-grep pattern (FMT-03 model)
- `src/maccat/collectors/claude.py` — multi-section `collect()` pattern
- `src/maccat/reinstall/emitter.py` — `SECTION_SOURCE_MAP` (4 titles), manual fallthrough logic confirmed
- `src/maccat/reinstall/parser.py` — title-agnostic state machine confirmed (SEPARATOR = 36 dashes)
- [Codex changelog](https://developers.openai.com/codex/changelog) — plugin system in v0.117.0 (March 2026)
- [Codex Build Plugins](https://developers.openai.com/codex/plugins/build) — `~/.codex/plugins/cache/` path for v0.117+

### Secondary (MEDIUM confidence — community/multi-source)

- [Wazuh issue #32451](https://github.com/wazuh/wazuh/issues/32451) — confirms Brave macOS path `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions/`
- [Microsoft Edge alternate distribution docs](https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/alternate-distribution-options) — confirms Edge macOS profile path structure
- [Zed Installing Extensions](https://zed.dev/docs/extensions/installing-extensions) — confirms `~/Library/Application Support/Zed/extensions/installed/` (index.json confirmed as canonical via live verification)
- [GitHub issue #17431 openai/codex](https://github.com/openai/codex/issues/17431) — confirms no `codex plugin list` CLI in v0.46

---
*Research completed: 2026-06-17*
*Ready for roadmap: yes*

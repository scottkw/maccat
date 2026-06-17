# Feature Research

**Domain:** macOS extension cataloging — v2.2.0 Broader Coverage (Edge, Brave, Zed, Safari, Codex Plugins)
**Researched:** 2026-06-17
**Confidence:** HIGH (all sources verified from live filesystem + working macOS tools)

---

## Scope Boundary

This file covers ONLY the five new sources in v2.2.0. Existing sections (Chrome, Firefox, VS Code,
Cursor, Claude, Codex MCP, OpenCode, Gemini, Homebrew, mas, Setapp, web apps) are unchanged.
The reinstall pipeline (v2.1.0) is additive: new browser/editor sections fall into the manual
checklist in `reinstall.sh` identically to how Chrome and Firefox already do.

---

## Source-by-Source Catalog Specification

### 1. Microsoft Edge Extensions

**Section title:** `Microsoft Edge Extensions`

**Entry format:** `name (version) [id]` — full `emit_item` FMT-01 format.
Degradation rules (inherited from `emit_item`):
- name + version + id → `Bitwarden (2026.5.0) [nngceckbapebfimnlniiiahkandclblb]`
- name + id (no version) → `Bitwarden [nngceckbapebfimnlniiiahkandclblb]`
- name only → `Bitwarden`

**Fields:**
- `name`: human-readable display name from `manifest.json` `name` field; `__MSG_` placeholders
  resolved via `chrome_name` helper (same logic as Chrome)
- `version`: `manifest.json` `version` field
- `id`: 32-char lowercase extension ID (the directory name under `Extensions/`)

**Base path:** `~/Library/Application Support/Microsoft Edge`
Profile enumeration order mirrors `ChromeCollector` exactly:
1. `Default/Extensions/`
2. `Profile N/Extensions/` — sorted ascending

**Built-in component exclusion:** Edge ships its own component extensions. The Chrome
`COMPONENT_DENYLIST` (10 Google-specific IDs) does NOT cover Edge components. Edge requires a
separate denylist. Research confirmed Edge component IDs include Edge-specific entries (Wallet,
Shopping Assistant, PDF Viewer, etc.) that are not in the Chrome denylist. Exact IDs are not yet
researched exhaustively — this is a **phase-specific research flag** (see Feature Dependencies).
Safe interim approach: reuse Chrome `COMPONENT_DENYLIST` to exclude known Google components that
may also appear in Edge, plus add a dedicated `EDGE_COMPONENT_DENYLIST` researched during
implementation. Standard Chromium internals guard (skip `Temp`, `_metadata` dirs) applies.

**Profile deduplication:** cross-profile dedup via `flush_section` (raw=False), exactly as Chrome.

**Dependency on existing code:**
- Reuse `ChromeCollector._collect_profile()` — same manifest structure, same `version_sort_tail`,
  same `chrome_ext_name` helper for `__MSG_` resolution
- Only the base path and component denylist differ from Chrome
- Pattern: extract a shared `ChromiumCollector` base class that `ChromeCollector`, `EdgeCollector`,
  and `BraveCollector` all subclass, overriding `_BASE`, `_TITLE`, and `_COMPONENT_DENYLIST`

**Complexity:** LOW — pure path substitution + component denylist research

---

### 2. Brave Extensions

**Section title:** `Brave Extensions`

**Entry format:** `name (version) [id]` — identical to Chrome/Edge.
Same FMT-01 degradation rules.

**Fields:** same as Edge/Chrome (name from manifest `name`, version from manifest `version`, id
from directory name).

**Base path:** `~/Library/Application Support/BraveSoftware/Brave-Browser`
Profile enumeration order mirrors `ChromeCollector`:
1. `Default/Extensions/`
2. `Profile N/Extensions/` — sorted ascending

**Built-in component exclusion:** Brave ships ~20 component extensions for Ad Block, Tor client,
Widevine, NTP images, etc. Confirmed IDs from Brave wiki (HIGH confidence — official source):
```
eeigpngbgcognadeebkilcpcaekhjalm  (Autofill States Data)
iodkpdagapdfkphljnddpjlldadblomo  (Ad Block Updater)
gkboaolpopklhgplhaaiboijnklogmbc  (Ad Block List Catalog)
mfddibmblmbccpadfndgakiopmmhebop  (Ad Block Resources Library)
afalakplffnnnlkncjhbmahjfjhmlkal  (Local Data Updater)
cldoidikboihgcjfkhdeidbpclkineef  (Tor Client Updater)
cpoalefficncklhjfpglfiplenlpccdb  (Tor Client Updater alt)
biahpgbdmdkfgndcmfiipgcebobojjkp  (Tor Client Updater alt)
kkjipiepeooghlclkedllogndmohhnhi  (User Model Installer)
giekcmmlnklenlaomppkphknjmnnpneh  (Certificate Error Assistant)
hfnkpimlhhgieaddgfemjhofmfblmnib  (CRLSet)
ggkkehgbnfjpeggfpleeakpidbkibbmn  (Crowd Deny)
khaoiebndkojlmppeemjhbpbandiljpe  (File Type Policies)
jamhcnnkihinmdlkakkaopbjbbcngflc  (Hyphenation)
laoigpblnllgcgjnjnllmfolckpjlhki  (MEI Preload)
gccbbckogglekeggclmmekihdgdpdgoe  (NTP Sponsored Images)
aoojcmojmmcbpfgoecoadbdpnagfchel  (NTP Background Images)
jflookgnkcckhobaglndicnbbgbonegd  (Safety Tips)
oimompecagnajdejgnnjijobebaeigek  (Widevine)
ojhpjlocmbogdgmfpkhlaaeamibhnphh  (Zxcvbn Data Dictionaries)
```
Apply the Chrome `COMPONENT_DENYLIST` (10 Google IDs) in addition to the Brave-specific list,
because Brave inherits some Chromium components.

**Profile deduplication:** cross-profile dedup via `flush_section` (raw=False), same as Chrome.

**Dependency on existing code:** same shared `ChromiumCollector` base as Edge (above).

**Complexity:** LOW — path substitution + known component denylist (IDs confirmed)

---

### 3. Zed Extensions

**Section title:** `Zed Extensions`

**Entry format:** `name (version) [id]` — full FMT-01 format.
Degradation: name only if version absent (no id-only degradation expected since id is always
present in the index).

**Fields:**
- `name`: `manifest.name` from the `index.json` `extensions` dict
- `version`: `manifest.version` from the same dict
- `id`: the key in the `extensions` dict (e.g., `"html"`)

**Source:** `~/Library/Application Support/Zed/extensions/index.json`
Format (verified on live system):
```json
{
  "extensions": {
    "html": {
      "manifest": {
        "id": "html",
        "name": "HTML",
        "version": "0.3.1",
        ...
      },
      "dev": false
    }
  }
}
```
All three fields (id, name, version) are available in one file — no per-extension manifest parse needed.

**No profile concept:** Zed has a single user config; no cross-profile deduplication required.

**No CLI:** The `zed` CLI binary does not expose an `--list-extensions` subcommand. The `index.json`
file is the canonical installed-extension registry (confirmed by live system inspection).

**Availability check:** `~/Library/Application Support/Zed/extensions/index.json` exists.
If the file is absent (Zed not installed or no extensions installed), emit `  (none found)` via
`flush_section` — consistent with all other collectors' degradation behavior.
Print `  NOTE: Zed not installed.` to stderr when the base app support dir is absent entirely.

**Dev extensions:** The `"dev": false/true` flag in the index entry identifies in-development
extensions loaded from local disk. Include them (they are user-installed); filter is optional
but the most natural behavior is to catalog everything present. Do NOT attempt to resolve a
filesystem path for dev extensions.

**Complexity:** LOW — single JSON parse, no locale resolution needed, no profile loops

---

### 4. Safari Extensions

**Section title:** `Safari Extensions`

**Entry format:** `name (version) [id]` — full FMT-01 format when all three fields obtainable.
Degradation to `name (version)` or `name` when bundle ID or version is unavailable.

**Fields:**
- `name`: `CFBundleDisplayName` (preferred) or `CFBundleName` from the `.appex/Contents/Info.plist`
- `version`: `CFBundleShortVersionString` (preferred) or `CFBundleVersion` from `Info.plist`
- `id`: bundle identifier (`CFBundleIdentifier`) from `Info.plist` (e.g., `com.bitwarden.desktop.safari`)

**Enumeration mechanism:** `pluginkit -v -m -p com.apple.Safari.web-extension`
Output format (verified on live system):
```
     com.bitwarden.desktop.safari(2026.5.0)	UUID	timestamp	/Applications/Bitwarden.app/Contents/PlugIns/safari.appex
```
Parse: `bundle_id(version_from_pluginkit)` in column 1, `appex_path` in last tab-delimited column.
Then read `appex_path/Contents/Info.plist` with `plistlib` for authoritative name, version, and id.
Version from `Info.plist` is preferred over the pluginkit parenthetical (plist is authoritative);
pluginkit version serves as fallback if plist read fails.

**Also query:** `pluginkit -v -m -p com.apple.Safari.extension` for legacy `.safariextz`-based
extensions (rarely seen, may return nothing). Merge results from both queries; dedup by bundle id.

**Apple built-in exclusion:** Filtering by `-p com.apple.Safari.web-extension` already excludes
Apple-internal extensions (e.g., `com.apple.Safari.*`, `com.apple.ScreenTime.*`). These appear
under `pluginkit -m -A` but NOT under the `-p com.apple.Safari.web-extension` extension point —
confirmed on live system. No explicit denylist needed.

**Framing for partial data:** Safari extensions are installed as host-app bundles (`Bitwarden.app`
ships `safari.appex` as a PlugIn). Reading `Info.plist` gives name + version + bundle ID cleanly
in all tested cases. The plist approach is MORE reliable than Chrome manifest parsing because
there are no `__MSG_` locale placeholders in App Store extension bundles. If `plistlib` read fails,
degrade to emitting the bundle ID only (id-as-name promotion via `emit_item`). Do NOT invent a
name from the appex filename — it is typically an unreadable slug.

**Availability check:** If `pluginkit` returns no output for both extension points, emit
`  (none found)`. If `pluginkit` itself is absent (not expected on macOS), print
`  NOTE: pluginkit unavailable — Safari extensions skipped.` and emit empty section.

**No profile concept:** Safari has one extension registry per macOS user account.

**Complexity:** MEDIUM — requires subprocess (`pluginkit`), plist read, regex parse of pluginkit
output. More steps than Chrome/Zed but each step is well-defined.

---

### 5. Codex Plugins (Agents)

**Section title:** `Codex Plugins`

**Entry format:** bare `name` — no version, no id (same as Claude/OpenCode agents sections).
`emit_item(name, "", "")` → bare name.

**Fields:**
- `name`: the key from `[agents."name"]` in `~/.codex/config.toml`
- version: not available (agent registrations have no version field)
- id: not emitted (the section key IS the name; no separate id concept)

**Source:** `~/.codex/config.toml` — text-grep of `[agents."name"]` section headers.
Pattern: `^\[agents\."([^"]+)"\]$` — analogous to existing Codex MCP TOML grep.
Only the section header line is read; `description`, `config_file`, and all other value lines
are NOT read (FMT-03 secret-safety: `config_file` paths are benign but the same header-only
discipline applied to MCP servers should apply here for consistency and future-proofing).

**Context:** Codex 0.46.0 does not expose a `codex agents list` CLI subcommand. The `config.toml`
text-grep is the only available path. The existing `CodexCollector._collect_via_cli()` tries
`codex mcp list --json` for MCP servers — there is no equivalent for agents. TOML grep is
therefore not a fallback but the primary path.

**FMT-03 note:** Agent `config_file` values are filesystem paths to `.toml` files — not secrets.
However, emitting full filesystem paths is unnecessary and potentially privacy-exposing (paths
may reveal usernames or private project names). Emit name only; consistent with how Claude Code
skills/agents are cataloged.

**Availability check:** If `~/.codex/config.toml` is absent, emit `  (none found)`.
If the file exists but has no `[agents.*]` sections, emit `  (none found)`.

**Relationship to existing `CodexCollector`:** Add a new `_collect_agents()` method alongside
`_collect_via_cli()` and `_collect_via_toml()`. Return a second `Section` titled
`"Codex Plugins"` from `collect()` (alongside existing `"Codex MCP Servers"`). The section
title `"Codex Plugins"` matches PROJECT.md v2.2.0 goal naming.

**Complexity:** LOW — extends existing `CodexCollector` by ~15 lines; reuses `_TOML_PATH`

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Edge extensions: enumerate user-installed across all profiles | Edge is Chromium — users expect same coverage as Chrome | LOW | Reuse ChromiumCollector base; only path changes |
| Edge extensions: `__MSG_` name resolution | Same locale-resolution requirement as Chrome | LOW | Reuse `chrome_ext_name` helper directly |
| Edge extensions: exclude built-in component extensions | Chrome does this; users expect same quality | MEDIUM | Chrome denylist IDs don't fully cover Edge; needs Edge-specific research at implementation time |
| Brave extensions: enumerate user-installed across all profiles | Brave is Chromium — same expectations | LOW | Reuse ChromiumCollector base |
| Brave extensions: exclude Brave component extensions | 20 Brave-specific component IDs confirmed | LOW | IDs listed above; HIGH confidence from Brave wiki |
| Zed extensions: enumerate installed with name + version + id | Zed has an extension system; users expect catalog parity with VS Code/Cursor | LOW | Single `index.json` parse; all fields present |
| Safari extensions: enumerate via pluginkit | Safari extensions are user-visible in Safari preferences; users expect them in the catalog | MEDIUM | `pluginkit -p com.apple.Safari.web-extension`; plist read for name |
| Safari extensions: human-readable name (not bundle ID) | Bundle IDs are opaque; catalog must show display name | MEDIUM | `CFBundleDisplayName` / `CFBundleName` from appex Info.plist |
| Safari extensions: version from plist | Version available in Info.plist; expected for restore fidelity | LOW | `CFBundleShortVersionString` preferred |
| Codex Plugins: enumerate registered agents | The `[agents.*]` entries in config.toml are the user's registered "plugins" for Codex | LOW | Extend CodexCollector; TOML header grep |
| All sources: graceful degradation when absent | Consistent with all existing collectors | LOW | Print NOTE to stderr; return empty section → `(none found)` |
| All sources: deterministic stable sort | FMT-04 — diff-empty on repeated runs | LOW | `flush_section` already handles this for all raw=False sections |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Shared `ChromiumCollector` base class | Three Chromium browsers (Chrome, Edge, Brave) share 95% of logic; a base class eliminates duplication and ensures consistent behavior | LOW | Extract from existing `ChromeCollector`; subclasses override `_BASE`, `_TITLE`, `_COMPONENT_DENYLIST` |
| Safari extensions via plist: more reliable than legacy .safariextz parse | plist-based approach gives clean name/version/id with no locale resolution needed | LOW | Simpler than Chrome manifest parsing |

### Anti-Features (Correctly Excluded)

| Feature | Why Excluded | Correct Behavior |
|---------|--------------|-----------------|
| Enabled/disabled state for Edge/Brave extensions | Deferred as CHR-02/FF-02 in existing design; consistently excluded from all browser extension sections | Omit entirely; catalog name + version + id only |
| Enabled/disabled state for Safari extensions | Same CHR-02/FF-02 deferral | Omit entirely |
| Safari extension permissions or entitlements | Not needed for catalog/restore identity | Name + version + bundle_id is sufficient |
| Codex agent `description` or `config_file` values | description is prose, config_file is a filesystem path — neither belongs in the catalog | Name-only per FMT-03 pattern |
| Codex agent `sandbox_mode` or `developer_instructions` | These are configuration values, not identity fields | Name-only |
| Zed dev extension source paths | Dev extensions (flag: `"dev": true`) may have local paths — not stable across machines; name + version + id from index.json is sufficient | Catalog dev extensions by name/version/id same as installed ones; do not include path |
| Multi-account/profile Safari extensions | Safari has one extension registry per macOS user; no profile concept exists | Single-pass enumeration |

---

## Multi-Profile Handling (Edge and Brave)

**Chrome collector behavior (confirmed from source):**
- Enumerates `Default/` first, then sorted `Profile */` directories
- Accumulates all items across profiles into a single flat list
- Deduplication via `flush_section` (`sort -f -u`) — one occurrence of each extension,
  regardless of how many profiles have it installed

**Edge and Brave:** mirror Chrome exactly. Same profile enumeration order (Default first, sorted
Profile N dirs), same cross-profile dedup via `flush_section`. Users with identical extensions
in multiple profiles see each extension once. This is the established maccat convention.

---

## Graceful Degradation Summary

| Source | Not Installed | Name Unavailable | Version Unavailable | ID Unavailable |
|--------|---------------|------------------|---------------------|----------------|
| Edge | NOTE to stderr; `(none found)` | Fall back to ext_id (Chrome pattern) | `name [id]` via emit_item | `name (version)` via emit_item |
| Brave | NOTE to stderr; `(none found)` | Fall back to ext_id (Chrome pattern) | `name [id]` via emit_item | `name (version)` via emit_item |
| Zed | NOTE to stderr; `(none found)` | id promoted as name (emit_item rule) | `name [id]` via emit_item | Unlikely; id == manifest key |
| Safari | NOTE to stderr; `(none found)` | Bundle ID promoted as name (emit_item) | `name [id]` via emit_item | Name-only via emit_item |
| Codex Plugins | `(none found)` (config absent or no agents) | n/a (name IS the section key) | Not applicable (no version) | Not applicable (no id) |

All sources: `flush_section` converts an empty item list to `  (none found)` (two leading spaces,
matching the established pattern from `format.py`).

---

## Feature Dependencies

```
Edge/Brave Extensions
    └──requires──> shared ChromiumCollector base
                       └──requires──> existing chrome_ext_name helper (reuse as-is)
                       └──requires──> existing version_sort_tail helper (reuse as-is)
                       └──requires──> Edge/Brave-specific component denylists
                                          Edge denylist: phase-specific research flag
                                          Brave denylist: confirmed (20 IDs from Brave wiki)

Zed Extensions
    └──requires──> ~/Library/Application Support/Zed/extensions/index.json
                       └──no additional helpers needed

Safari Extensions
    └──requires──> pluginkit CLI (always available on macOS)
    └──requires──> plistlib (Python stdlib, already used in webapps/setapp collectors)
    └──requires──> existing plist_version helper pattern (adapt for appex path)

Codex Plugins section
    └──requires──> existing CodexCollector (extend, do not replace)
    └──requires──> existing _TOML_PATH path constant
```

### Dependency Notes

- **ChromiumCollector base class gates Edge and Brave.** Refactor Chrome first, validate parity,
  then add Edge and Brave as subclasses. This must not change Chrome's output.
- **Safari has no dependency on the Chromium work.** It can be implemented independently.
- **Codex Plugins has no dependency on any browser work.** It is a pure extension of the existing
  `CodexCollector` and can be implemented first.
- **Zed has no dependencies.** Simplest new source; good to implement first for confidence.

---

## MVP Definition

### v2.2.0 Launch With

All five new sources at full table-stakes quality:

- [ ] `ZedCollector`: parse `index.json`, emit `name (version) [id]`, degrade gracefully
- [ ] `SafariCollector`: `pluginkit` enumeration, plist name/version/id extraction, degrade gracefully
- [ ] `CodexCollector` extended: add `_collect_agents()` + `"Codex Plugins"` section
- [ ] `ChromiumCollector` base class extracted from `ChromeCollector` (no output change for Chrome)
- [ ] `EdgeCollector`: ChromiumCollector subclass for `~/Library/Application Support/Microsoft Edge`
- [ ] `BraveCollector`: ChromiumCollector subclass for `~/Library/Application Support/BraveSoftware/Brave-Browser`
- [ ] All new sources: NOTE to stderr when absent, `(none found)` when empty
- [ ] All new sources: deterministic sort via `flush_section` (raw=False)
- [ ] All new sources: additive-only — no changes to existing sections or catalog structure

### Deferred (not v2.2.0)

- Enabled/disabled state for any browser extension (CHR-02/FF-02 — explicitly deferred)
- Edge component denylist completeness (safe to ship with partial denylist + standard guards;
  unrecognized components are rare on personal machines)
- Safari legacy extension support (`.safariextz` format is effectively retired by Apple)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Zed Extensions | HIGH | LOW | P1 |
| Codex Plugins | HIGH | LOW | P1 |
| Brave Extensions (ChromiumCollector base first) | HIGH | LOW | P1 |
| Edge Extensions | HIGH | LOW | P1 |
| Safari Extensions | HIGH | MEDIUM | P1 |
| ChromiumCollector base class refactor | MEDIUM (engineering quality) | LOW | P1 (prerequisite) |
| Edge component denylist (complete) | MEDIUM | MEDIUM | P2 (phase research flag) |

**Priority key:**
- P1: Must have for v2.2.0 launch
- P2: Improve after initial implementation; incomplete denylist ships with known gap documented

---

## Implementation Order Recommendation

1. **Codex Plugins** — extend existing CodexCollector (~15 lines). Zero risk to existing output.
2. **Zed** — new collector, single JSON parse. No locale issues, no profile loops.
3. **ChromiumCollector base** — extract from ChromeCollector, verify Chrome output unchanged.
4. **Brave** — subclass ChromiumCollector; Brave denylist is fully known.
5. **Edge** — subclass ChromiumCollector; Edge denylist needs phase research (document as known gap).
6. **Safari** — most steps; pluginkit + plist. Implement last with most test surface.

---

## Sources

- `src/maccat/collectors/chrome.py` — ChromeCollector implementation (verified, HIGH confidence)
- `src/maccat/helpers/chrome_name.py` — `chrome_ext_name` helper (verified, HIGH confidence)
- `src/maccat/catalog/format.py` — `emit_item` FMT-01 degradation rules (verified, HIGH confidence)
- `src/maccat/collectors/codex.py` — existing CodexCollector / TOML pattern (verified, HIGH confidence)
- `~/Library/Application Support/Zed/extensions/index.json` — live Zed extension index (verified)
- `~/Library/Application Support/Zed/extensions/installed/html/extension.toml` — extension manifest (verified)
- `pluginkit -v -m -p com.apple.Safari.web-extension` — live output on this machine (verified)
- `/Applications/Bitwarden.app/Contents/PlugIns/safari.appex/Contents/Info.plist` — live plist (verified)
- [Brave Components wiki](https://github.com/brave/brave-browser/wiki/Brave-Components) — Brave component IDs (HIGH confidence, official source)
- `.planning/PROJECT.md` — v2.2.0 scope and CDX-02 definition (HIGH confidence)

---
*Feature research for: maccat v2.2.0 Broader Coverage — Edge, Brave, Zed, Safari, Codex Plugins*
*Researched: 2026-06-17*

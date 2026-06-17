# Pitfalls Research

**Domain:** Adding Edge / Brave / Zed / Safari extension collectors and a Codex Plugins section to maccat (v2.2.0)
**Researched:** 2026-06-17
**Confidence:** HIGH for Zed, Chrome-family structure, and reinstall regression; HIGH for Safari pluginkit behavior (verified live on this machine); MEDIUM for Edge/Brave component denylist completeness (IDs researched from source but cannot be exhaustively verified without an Edge install); MEDIUM for Codex plugins format (v0.117.0+ — not yet installed on this machine, v0.46.0 is).

> Scope note: these pitfalls are specific to v2.2.0 — adding new collectors for Edge, Brave, Zed, Safari, and Codex Plugins. They do NOT re-litigate v2.1.0 reinstall pitfalls already documented in the prior version of this file. Every pitfall here is a direct consequence of the new sources' on-disk layouts, tool behaviors, or the integration requirements of the existing collector pattern (FMT-01/03/04, never-raises, graceful degradation, sort stability, and no-regression on existing sections).

---

## HARD CONSTRAINTS (Read Before Scoping)

### HARD CONSTRAINT A: Codex plugins subsystem does not exist in v0.46.0

**Finding:** The installed Codex CLI is v0.46.0. The `[plugins.]` TOML section and the `codex plugin list` command were introduced in Codex v0.117.0 (March 2026). There is no `[plugins.]` section in `~/.codex/config.toml` on machines running v0.46.0. The CLI has no `plugin` subcommand.

**Consequence:** A "Codex Plugins" collector must check whether any `[plugins.]` section exists in config.toml before emitting items. On pre-v0.117.0 installations, the section will simply be absent — the collector must degrade to `(none found)` without error or warning. The degrade-to-empty path is the common case today, not an edge case.

**What changes in the plan:** The Codex Plugins collector must accept both the pre-v0.117.0 (no `[plugins.]` section) and post-v0.117.0 (section present with `[plugins."name@marketplace"]` entries) layouts. The format drift risk is real: the plugin name format `name@marketplace` and the per-plugin override schema may still evolve. The collector must use text-grep on TOML headers (same pattern as `CodexCollector._collect_via_toml`) — never `tomllib.load()` on the full config.

---

### HARD CONSTRAINT B: Safari name resolution requires CFBundleDisplayName, not CFBundleName

**Finding (verified live on this machine):** The `pluginkit -v` output for the Bitwarden Safari extension shows:

```
com.bitwarden.desktop.safari(2026.5.0)    ...    /Applications/Bitwarden.app/Contents/PlugIns/safari.appex
```

The appex `CFBundleName` is `"safari"` (the binary name). `CFBundleDisplayName` is `"Bitwarden"`. If the collector reads `CFBundleName`, every Safari extension on the machine will be emitted as the binary executable name rather than the human-readable extension name.

**Consequence:** The Safari collector must read `CFBundleDisplayName` from the appex `Info.plist`, NOT `CFBundleName`. Since `get_plist_version()` only reads version keys, a separate name-resolution lookup is required.

---

## Critical Pitfalls

### Pitfall 1: Edge and Brave — incomplete component denylist causes built-in extensions to appear in output

**What goes wrong:**
The existing `ChromeCollector.COMPONENT_DENYLIST` contains 10 Chrome-specific component IDs. Edge and Brave ship additional browser-specific components that do NOT appear in this denylist. Without additional denylists, these built-in features appear as user-installed extensions in the catalog:

**Brave-specific components (confirmed from brave-browser wiki):**
- `iodkpdagapdfkphljnddpjlldadblomo` — Brave Ad Block Updater
- `gkboaolpopklhgplhaaiboijnklogmbc` — Brave Ad Block List Catalog
- `mfddibmblmbccpadfndgakiopmmhebop` — Brave Ad Block Resources Library
- `kkjipiepeooghlclkedllogndmohhnhi` — Brave User Model Installer (Ads/Rewards)
- `cldoidikboihgcjfkhdeidbpclkineef`, `cpoalefficncklhjfpglfiplenlpccdb`, `biahpgbdmdkfgndcmfiipgcebobojjkp` — Brave Tor Client Updater (3 platform variants)
- `oimompecagnajdejgnnjijobebaeigek` — Widevine (Brave-bundled)
- `afalakplffnnnlkncjhbmahjfjhmlkal` — Brave Local Data Updater
- `gccbbckogglekeggclmmekihdgdpdgoe` — NTP Sponsored Images
- `aoojcmojmmcbpfgoecoadbdpnagfchel` — NTP Background Images

**Edge-specific components (partially known; exact IDs need phase-specific verification):**
Edge ships components for Shopping Assistant, Wallet/Pay, Sidebar apps, Azure Information Protection, Bing integration, and Edge PDF Viewer. The exact component IDs are not publicly documented in a single authoritative list and were not fully verifiable from available documentation. The community has observed IDs such as `jmjflgjpcpepeafmmgdpfkogkghcpiha` appearing as hidden Edge-specific components.

**Why it happens:**
The Chrome COMPONENT_DENYLIST was built for Chrome's component set. Edge and Brave both inherit Chrome's components AND add their own. A shared Chromium collector that applies only the Chrome denylist will pass through browser-specific components as if they were user-installed extensions.

**How to avoid:**
- Brave: Add a `BRAVE_COMPONENT_DENYLIST` constant with the IDs above. Source: brave-browser wiki, confirmed multiple sources.
- Edge: Create an `EDGE_COMPONENT_DENYLIST` stub with known IDs. Flag this constant for phase-specific research: install Edge locally, run `ls ~/Library/Application\ Support/Microsoft\ Edge/Default/Extensions/` on a fresh profile, and cross-reference with the Edge extension management page (`edge://extensions`). Any IDs present on-disk but NOT visible in the UI are components to denylist.
- The `_collect_profile` method already guards `ext_id.startswith("_")` and `ext_id == "Temp"`. These guards apply to Edge and Brave without change.

**Warning signs:**
- The catalog contains entries named "Microsoft Edge Shopping" or "Brave Ad Block Updater" in the Edge/Brave sections.
- The Brave section emits entries with IDs in the above list.
- No `BRAVE_COMPONENT_DENYLIST` constant exists — Brave is using only Chrome's 10-entry denylist.

**Phase to address:**
Edge/Brave collector phase. Create browser-specific denylist constants in the shared Chromium collector module (or per-browser subclass). For Edge: flag the denylist as requiring verification with a real Edge installation before shipping.

---

### Pitfall 2: Edge and Brave — profile discovery paths differ from Chrome

**What goes wrong:**
The existing `ChromeCollector` hard-codes `_BASE = Path.home() / "Library/Application Support/Google/Chrome"`. Edge and Brave use different base paths:

- Edge: `~/Library/Application Support/Microsoft Edge/`
- Edge Beta: `~/Library/Application Support/Microsoft Edge Beta/`
- Brave: `~/Library/Application Support/BraveSoftware/Brave-Browser/`
- Brave Beta: `~/Library/Application Support/BraveSoftware/Brave-Browser-Beta/`

**Verified on this machine:** `~/Library/Application Support/BraveSoftware/Brave-Browser/` exists but contains only `NativeMessagingHosts/` — no `Default/` profile. This means the presence detection logic must check for the `Default/` profile directory (or any `Profile */` directories), NOT merely for the browser base directory. A check on `_BASE.is_dir()` alone would return True for Brave on this machine even though Brave is not installed and has no extensions.

**Why it happens:**
Browsers create their support directories as part of system-level native messaging registration, independent of whether the browser itself is installed. The base directory existing does not mean a browser profile exists.

**How to avoid:**
The collector's availability check must verify that `_BASE / "Default" / "Extensions"` exists (or at least one `Profile */Extensions/` dir), not just `_BASE.is_dir()`. The `collect()` method already degrades to `items=[]` if no profile has an Extensions dir — but the `NOTE: X not installed` message should only print when the base directory does NOT exist at all.

**Warning signs:**
- `~/Library/Application Support/BraveSoftware/Brave-Browser/` exists on the test machine but Brave is not installed — the collector prints "Brave not installed" despite the directory being present.
- Alternatively: the collector silently produces `(none found)` without the NOTE message on a machine where Brave was previously installed.

**Phase to address:**
Edge/Brave collector phase. Use `_BASE.is_dir()` only for the `NOTE: not installed` message; profile enumeration naturally returns no results if no profiles have Extensions dirs.

---

### Pitfall 3: Chrome `__MSG_` name resolution edge cases for Edge/Brave

**What goes wrong:**
The existing `chrome_ext_name()` helper resolves `__MSG_<key>__` placeholder names by looking up `default_locale` in the manifest and reading `_locales/<locale>/messages.json`. For Edge and Brave, the same mechanism applies — but there are two additional failure modes specific to these browsers:

1. **Edge extensions from the Edge Add-ons store** may use a different `default_locale` (e.g. `en_US` vs `en`) while having `_locales/en_US/` instead of `_locales/en/`. The existing fallback to `ext_id` handles this correctly already (messages file not found → ext_id), but it means some Edge extensions will catalog with their ID rather than a friendly name.

2. **Brave built-in extension manifests** (inside the component extension directories that survive the denylist) use `__MSG_` keys pointing to locale files that ARE present in the extension directory — so name resolution works fine for the ones that pass the denylist. This is not a pitfall but confirms the denylist is the correct control point, not name resolution.

**Why it happens:**
The `chrome_ext_name()` helper is already correct. The risk is in assuming it needs no adjustment for Edge/Brave. It does not — the fallback-to-ext_id path handles locale mismatches gracefully.

**How to avoid:**
Reuse `chrome_ext_name()` unchanged. Do NOT reimplement name resolution for Edge or Brave. The only change needed is passing the correct manifest path, which the shared `_collect_profile` method already handles.

**Warning signs:**
- A new `edge_ext_name()` or `brave_ext_name()` function is created instead of reusing `chrome_ext_name()`.
- The Edge/Brave collector reimplements `__MSG_` resolution inline.

**Phase to address:**
Edge/Brave collector phase. Reuse existing helper; add a test with a synthetic Edge extension whose manifest uses `__MSG_appName__` and verify name resolves correctly.

---

### Pitfall 4: Version directory guard — Edge/Brave need the same `^[0-9]` filter as Chrome

**What goes wrong:**
`version_sort_tail()` in `format.py` already applies a `c[:1].isdigit()` pre-filter to exclude `_metadata`, `_crx_invalidation_map`, and similar non-version directories from the version slot selection. This guard exists because Chrome extension directories contain these internal subdirectories alongside version directories.

Edge and Brave use the identical internal directory structure — the same `_metadata` and similar dirs appear alongside version directories in each extension's folder. Without the digit-first filter, `version_sort_tail` would pick an internal dir as the "latest version" and fail to find a manifest.

**Why it happens:**
The guard is implemented in `version_sort_tail()` which is already shared. The pitfall is NOT in `version_sort_tail` itself — it is in calling it correctly. Any rewrite or reimplementation of version selection for Edge/Brave that bypasses `version_sort_tail()` and uses `sorted()` or `max()` on raw directory names would lose this guard.

**How to avoid:**
Always call `version_sort_tail(candidates)` exactly as `ChromeCollector._collect_profile` does. Do not replace it with `max(candidates)` or `sorted(candidates)[-1]` — those are version-sort-wrong (lexicographic, not `sort -V`) AND lose the digit filter.

**Warning signs:**
- Any `max(candidates)` or `sorted(candidates)[-1]` in the Edge/Brave collector code.
- A new "version selection" helper that does not call `version_sort_tail`.

**Phase to address:**
Edge/Brave collector phase. Code review checklist: confirm `version_sort_tail` is called, not inlined.

---

### Pitfall 5: Zed extensions — index.json is the correct source, not the installed/ subdirectory scan

**What goes wrong:**
`~/Library/Application Support/Zed/extensions/` contains:
- `index.json` — the authoritative registry of installed extensions (verified on this machine)
- `installed/<ext_id>/extension.toml` — per-extension manifest files
- `work/` — in-progress/download scratch space

A scan of `installed/` subdirectories for `extension.toml` files would work but duplicates what `index.json` already tracks. The risk: the `work/` subdirectory contains incomplete in-flight downloads. If the collector scans `installed/` AND `work/`, it will pick up partially-downloaded extensions.

**Why it happens:**
`installed/` looks like the natural place to scan. But `index.json` is the canonical installed list — it tracks `dev: true/false` for each extension. `work/` entries are transient and incomplete.

**How to avoid:**
Parse `index.json`, not a filesystem scan of `installed/`. The JSON structure (verified on this machine):

```json
{
  "extensions": {
    "<id>": {
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

Read `extensions.<id>.manifest.{id, name, version}` and `extensions.<id>.dev`. All three fields (`id`, `name`, `version`) are present and populated in registry-installed extensions.

**Warning signs:**
- The collector uses `Path.glob("installed/*/extension.toml")` instead of parsing `index.json`.
- The collector scans `work/` for extension metadata.
- A partially-downloaded extension appears in test output.

**Phase to address:**
Zed collector phase. Parse `index.json` exclusively. Add a test that has a `work/` entry alongside a valid `installed/` extension and verify only the installed extension appears.

---

### Pitfall 6: Zed dev extensions — must be separated or excluded from the catalog

**What goes wrong:**
Zed supports "dev extensions" — locally-developed extensions installed directly from the filesystem (not from the registry). These appear in `index.json` with `"dev": true`. A dev extension may have:
- A non-registry `id` (e.g. the directory name of the developer's local repo)
- An unstable or stub version (`"0.0.1"` or missing)
- No published `repository` URL

If dev extensions are included in the catalog without filtering, the catalog will contain entries that cannot be reinstalled from any external source. This is misleading in a "restorable snapshot" context.

**Why it happens:**
`index.json` includes both registry and dev extensions without clear visual separation. The `dev` flag is the only distinguisher.

**How to avoid:**
Filter `dev: true` entries OUT of the catalog, OR emit them under a separate section (e.g., "Zed Dev Extensions") with a prominent note that they are local-only and not restorable. The simpler approach (exclude dev extensions) matches the catalog's purpose as a restore-focused snapshot. Document the decision in code comments.

**Warning signs:**
- The Zed collector does not check `info.get("dev")` before emitting an entry.
- A locally-developed extension with an unstable version appears in the catalog output.

**Phase to address:**
Zed collector phase. Decision: exclude `dev: true` entries from the main Zed Extensions section. Add a test fixture with a `dev: true` extension and verify it is excluded.

---

### Pitfall 7: Zed — index.json missing or absent means Zed is not installed, not broken

**What goes wrong:**
`~/Library/Application Support/Zed/extensions/index.json` does not exist on machines that have never installed a Zed extension (or where Zed itself has never been run). The collector must handle this as "Zed has no extensions" (degrade to `(none found)`) rather than as an error condition.

There is also a format drift risk: the `index.json` schema has the `extensions` top-level key wrapping the extension map (verified on this machine). If Zed changes this schema in a future version, parsing `d["extensions"]` directly would raise a `KeyError`. Use `.get("extensions", {})` and degrade gracefully.

**Why it happens:**
A missing `index.json` file looks like a filesystem error but is actually a normal state (fresh install, Zed never run, no extensions installed). Similarly, a schema change to `index.json` is more likely than for Chrome/Firefox manifests, because Zed's extension system is newer and still evolving.

**How to avoid:**
```python
path = Path.home() / "Library/Application Support/Zed/extensions/index.json"
if not path.is_file():
    # Zed has no extensions / not installed; degrade to (none found)
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    return CollectorResult(sections=[Section(title=_TITLE, items=[])])
extensions = data.get("extensions", {})
if not isinstance(extensions, dict):
    extensions = {}
```

**Warning signs:**
- The collector raises `FileNotFoundError` or `KeyError` when `index.json` is absent.
- The collector uses `data["extensions"]` instead of `data.get("extensions", {})`.

**Phase to address:**
Zed collector phase. Test with a missing `index.json` (the common case on most machines).

---

### Pitfall 8: Safari — pluginkit output is undocumented; using wrong flags or not filtering Apple extensions

**What goes wrong:**
`pluginkit -mAD` (without `-p`) returns ALL 485+ installed extensions across all point identifiers on this machine — system daemons, share extensions, Quick Look plugins, Notification Service extensions, etc. Without the `-p com.apple.Safari.web-extension` filter, the collector would emit hundreds of non-Safari entries.

The `-p` filter works correctly and is verified on this machine: `pluginkit -mAD -p com.apple.Safari.web-extension` returns only the Bitwarden extension (the sole Safari web extension installed). However, there are two failure modes:

1. **Not filtering Apple's own Safari extensions:** `pluginkit -mAD` (even with `-p com.apple.Safari.web-extension`) currently returns only user/third-party extensions on this machine. But Apple ships Safari extensions bundled inside Safari itself at `/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app/Contents/Extensions/`. The `-p com.apple.Safari.web-extension` filter is the correct control — Apple's internal Safari extensions (SafariLinkExtension, SafariWidgetExtension) use a different point identifier, not `com.apple.Safari.web-extension`. Verified: they do NOT appear when `-p com.apple.Safari.web-extension` is specified.

2. **Other Safari-adjacent extension types:** Safari content blockers use `com.apple.Safari.content-blocker` (a different point identifier, confirmed empty on this machine). A collector targeting only `com.apple.Safari.web-extension` will miss content blockers. The scope decision (web-extensions only vs. including content blockers) must be explicit.

**Why it happens:**
`pluginkit` is undocumented beyond its man page and is not commonly used in scripts. The tendency is to run `pluginkit -mAD` (all extensions) and then filter in Python — which risks including system extension types.

**How to avoid:**
Always pass `-p com.apple.Safari.web-extension` to `pluginkit`. This is the only documented, verified filter for user-installed Safari web extensions. If content blockers are in scope, add a second pass with `-p com.apple.Safari.content-blocker`.

**Warning signs:**
- `pluginkit -mAD` is called without `-p` and results are filtered in Python.
- The `-p` flag is present but the identifier string has a typo (it must be `com.apple.Safari.web-extension` exactly, not `com.apple.Safari.extension` or `com.apple.Safari-Extension`).

**Phase to address:**
Safari collector phase. Use `pluginkit -mAD -p com.apple.Safari.web-extension`. Run integration test on a machine with at least one Safari extension installed.

---

### Pitfall 9: Safari — CFBundleName is the binary name, not the extension's display name

**What goes wrong (verified on this machine):**
The appex `Info.plist` for Bitwarden's Safari extension has:
- `CFBundleName = "safari"` (the binary executable name — NOT the friendly name)
- `CFBundleDisplayName = "Bitwarden"` (the correct friendly name)

Using `CFBundleName` from the appex would catalog every Safari extension as its binary name (commonly `"safari"` or the developer's internal binary name), not the human-readable extension name that appears in Safari's Extension Manager.

**Why it happens:**
`CFBundleName` is used by macOS to identify the binary; `CFBundleDisplayName` is the user-visible name. The existing `get_plist_version()` helper reads only version keys and does not provide a name-reading function. A new Safari-specific name reader that uses `CFBundleName` (following the pattern of `CFBundleShortVersionString`) would produce wrong output.

**How to avoid:**
Read name from `CFBundleDisplayName` in the appex `Info.plist` as the primary source. If `CFBundleDisplayName` is absent (rare), fall back to the parent app's `CFBundleDisplayName` from `<appex_path>/../../../Contents/Info.plist` (three levels up to the `.app` bundle). Final fallback: the bundle ID from pluginkit output.

Name resolution chain:
```
appex_plist["CFBundleDisplayName"]
  → parent_app_plist["CFBundleDisplayName"]
  → parent_app_plist["CFBundleName"]  
  → bundle_id (from pluginkit line)
```

**Warning signs:**
- The catalog contains entries like `safari (2026.5.0) [com.bitwarden.desktop.safari]` instead of `Bitwarden (2026.5.0) [com.bitwarden.desktop.safari]`.
- The Safari collector reads `CFBundleName` instead of `CFBundleDisplayName`.
- Tests do not include an appex whose `CFBundleName` differs from `CFBundleDisplayName`.

**Phase to address:**
Safari collector phase. Add a fixture with `CFBundleName="safari"` and `CFBundleDisplayName="Bitwarden"`. Assert output uses `CFBundleDisplayName`.

---

### Pitfall 10: Safari — pluginkit requires a subprocess call, and name resolution requires a plistlib read; both must be never-raising

**What goes wrong:**
The Safari collector is more complex than the Chromium-family collectors: it must shell out to `pluginkit` (a subprocess), then for each result read an appex `Info.plist` with plistlib. Both operations can fail independently:

1. `pluginkit` subprocess returns non-zero (unusual but possible during system updates or SIP interference)
2. `pluginkit` output format changes across macOS versions (undocumented)
3. The appex path reported by `pluginkit -v` may no longer exist (race condition during app update/uninstall)
4. The `Info.plist` at the appex path may be binary format, missing, or corrupt

If any of these raise an exception, the entire catalog run fails — violating the never-raises contract.

**Why it happens:**
The collector combines subprocess and filesystem I/O. Most other collectors use one or the other, not both in a chained dependency (where the subprocess output provides the path for the filesystem read). Each failure mode must be individually guarded.

**How to avoid:**
- Wrap `subprocess.run(["pluginkit", ...])` in try/except. On non-zero exit or empty stdout, degrade to `(none found)`.
- Parse each pluginkit output line with a regex that returns `None` on parse failure (never raises).
- Wrap each plist read in try/except (the existing `get_plist_version()` pattern is already correct). Extend it for display name reading with the same never-raises contract.
- Use individual try/except around each extension's name resolution, not a single outer try/except that swallows all extensions if one fails.

**Warning signs:**
- A single `try/except` wraps the entire `pluginkit` call + all plist reads in one block. If one extension's plist is malformed, all subsequent extensions are skipped.
- `pluginkit` non-zero exit raises `subprocess.CalledProcessError` (only happens if `check=True`).
- No test covers a pluginkit output line with an appex path that no longer exists.

**Phase to address:**
Safari collector phase. Each extension's plist read must be individually wrapped. Test with a synthetic pluginkit response that includes one valid entry and one with a missing appex path.

---

### Pitfall 11: Safari — pluginkit output line format and (null) version entries

**What goes wrong:**
The pluginkit output format (verified on this machine) is:
```
     com.bitwarden.desktop.safari(2026.5.0)
```
Note: the version is embedded inside the bundle ID parentheses WITHOUT a space: `id(version)`. Some extensions report `(null)` as the version:
```
     com.apple.parsec.SafariBrowsingAssistantWorker((null))
```

119 of the 485 total extensions on this machine have `(null)` versions. For user-installed Safari web extensions, a `(null)` version means `get_plist_version()` must be used as the authoritative version source (from the appex `Info.plist`), not the pluginkit output. If the implementation uses the pluginkit version string as-is and emits `(null)` as the version, the catalog entry looks like `Bitwarden ((null)) [com.bitwarden.desktop.safari]` — which is user-hostile and technically wrong.

**Why it happens:**
`pluginkit` reports the cached version from its internal database, which may lag behind an installed extension's actual `Info.plist` version. The correct authoritative source is the appex `Info.plist`.

**How to avoid:**
Always use `get_plist_version(appex_path / "Contents/Info.plist")` as the version source. Discard the pluginkit version string entirely (or use it only as a fallback when the plist version is empty). Map `""` (plist version unavailable) to version-degraded `emit_item` call.

**Warning signs:**
- The catalog contains `(null)` as a version string.
- The collector uses `pluginkit_version_string` directly without checking against `(null)`.

**Phase to address:**
Safari collector phase. Version always comes from plistlib; pluginkit version string is discarded.

---

### Pitfall 12: Safari — pluginkit -v (verbose) is required for the appex path; -v may not be needed with a different approach

**What goes wrong:**
To resolve the name from the appex `Info.plist`, the collector needs the path to the appex. `pluginkit -mAD -p com.apple.Safari.web-extension` (non-verbose) returns only `id(version)` — no path. `pluginkit -v -m -A -p com.apple.Safari.web-extension` returns `id(version) \t UUID \t timestamp \t /path/to/appex`.

The verbose output adds a UUID and timestamp that must be parsed alongside the path. If `-v` is not used, name resolution from plistlib is impossible without a separate filesystem search.

**Alternative approach:** Use `pluginkit -mAD -p com.apple.Safari.web-extension` (non-verbose) to get bundle IDs, then use `find /Applications -name "*.appex"` to locate appex files by bundle ID. This is slower (filesystem scan) and fragile (extensions not in `/Applications` would be missed). The `-v` approach is simpler and more reliable.

**Why it happens:**
Developers may use the non-verbose form for a simpler output format, then discover they need paths for plist resolution and switch to `-v`. The verbose output format is undocumented and may change across macOS versions.

**How to avoid:**
Use `-v` from the start. Parse the tab-separated verbose format:
```
   <id>(<version>)\t<UUID>\t<timestamp>\t<path>
```
The path is the 4th tab-separated field. Wrap the parse in a regex with a fallback to skip the line (never-raise).

**Warning signs:**
- Initial implementation uses non-verbose pluginkit then adds a `find /Applications` step to locate appexes.
- The tab-separated verbose format is parsed with `split(" ")` (space split) instead of `split("\t")`.

**Phase to address:**
Safari collector phase. Use `-v` from the start. Parse with tab split.

---

### Pitfall 13: Codex Plugins — reading plugin bundle .mcp.json would violate FMT-03

**What goes wrong:**
The Codex plugin system bundles MCP servers, skills, and app connectors into installable packages. A plugin bundle's `.mcp.json` can contain:
```json
{
  "my-service": {
    "env": {
      "API_KEY": "${MY_SERVICE_API_KEY}"
    }
  }
}
```
If the Codex Plugins collector reads any plugin bundle definition file (not just the `config.toml` registry entry), it may emit environment variable references, API key names, or command-line arguments into the catalog — violating FMT-03 (no secrets ever written to the catalog).

**Why it happens:**
The same mistake was identified for MCP server collection (now guarded by `CodexCollector`'s TOML-header-grep approach). The Codex Plugins collector must follow the same discipline: read only the `config.toml` `[plugins.]` section headers (name + enabled state), never any plugin bundle contents.

**How to avoid:**
The Codex Plugins collector must use text-grep of `config.toml` for `[plugins."name@marketplace"]` header lines only — exactly as `CodexCollector._collect_via_toml` greps `[mcp_servers.NAME]` header lines:

```python
for line in text.splitlines():
    m = re.match(r'^\[plugins\."([^"]+)"\]$', line.strip())
    if m:
        plugin_key = m.group(1)   # e.g. "my-plugin@openai-curated"
        name = plugin_key.split("@")[0]   # e.g. "my-plugin"
        # emit name only — no version, no id beyond the name
        item = emit_item(name, "", plugin_key)
        if item:
            items.append(item)
```

Do NOT: call `tomllib.loads()` on the full `config.toml`. Do NOT: read `~/.codex/plugins/<name>/` bundle directories.

**Warning signs:**
- Any `tomllib.load()` or `toml.load()` call on `config.toml` in the Codex Plugins collector.
- Any `Path.glob("~/.codex/plugins/**/*.json")` or similar bundle-level scan.
- The catalog emits `command`, `env`, `args`, `url`, or `headers` values.

**Phase to address:**
Codex Plugins collector phase. Add a test fixture where `config.toml` has a `[plugins."my-plugin@marketplace"]` section AND a separate nested `[plugins."my-plugin@marketplace".mcp_servers.my-server]` section with an `API_KEY` env reference. Verify only the plugin name appears in the output, not any nested values.

---

### Pitfall 14: Codex Plugins — version unavailable; emit name + marketplace-scoped ID only

**What goes wrong:**
The `[plugins."name@marketplace"]` config.toml entry has no version field — only `enabled = true/false` and MCP server override sub-tables. There is no version in the config registry. Plugin versions (if tracked at all) would live in the plugin bundle definition files — which must NOT be read (FMT-03).

If the collector attempts to resolve a version and falls back to emitting an empty-version entry, it will emit `name [name@marketplace]` (name + id, no version). This is the correct degradation per FMT-01. The `emit_item(name, "", plugin_key)` form produces this output automatically.

**Why it happens:**
Developers may try to find a version because the `name (version) [id]` format is the "full" FMT-01 form. But version is genuinely unavailable for Codex plugins without reading bundle files. Degrade is correct and expected.

**How to avoid:**
Accept the `name [marketplace-scoped-id]` output as correct. The full `name@marketplace` string (e.g. `my-plugin@openai-curated`) is the id. Document this in the collector's docstring. Do not attempt version resolution.

**Warning signs:**
- The collector attempts to read plugin bundle files to find a version field.
- The emitter outputs `name (unknown) [id]` — the literal string "unknown" as a version.

**Phase to address:**
Codex Plugins collector phase. Accept version-absent output as the expected format.

---

### Pitfall 15: Determinism across multiple profiles — duplicate extensions across Edge/Brave profiles

**What goes wrong:**
`ChromeCollector` accumulates items across all profiles and relies on `flush_section()` (which calls `sort -f -u`) for cross-profile deduplication. The same extension installed in both the Default profile and Profile 1 appears only once in the output. This behavior must be replicated identically for Edge and Brave.

If the Edge or Brave collector uses `raw=True` (bypassing `flush_section`) for its section, cross-profile duplicates will appear in the catalog, violating FMT-04 (deterministic, diff-empty on repeated runs).

**Why it happens:**
The `raw=True` flag is used for sources that are already sorted (Homebrew, mas) and must not be re-sorted. Browser extension collectors use `raw=False` (the default) so `flush_section` provides deduplication. A copy-paste of the Homebrew or mas collector pattern with `raw=True` would bypass dedup.

**How to avoid:**
All Chromium-family collectors (Chrome, Edge, Brave) must use `raw=False` (the default). The `flush_section` `sort -f -u` call deduplicates. This is already the pattern in `ChromeCollector`.

**Warning signs:**
- `Section(title=..., items=..., raw=True)` in the Edge or Brave collector.
- The same extension appears twice in Edge output (installed in Default + Profile 1).

**Phase to address:**
Edge/Brave collector phase. The shared Chromium collector base class should default `raw=False`. Add a test with the same extension ID in two profiles and verify it appears once.

---

### Pitfall 16: Reinstall regression — new section titles fall to manual_checklist correctly; no SECTION_SOURCE_MAP update needed

**What goes wrong (non-pitfall, but common concern):**
The reinstall emitter's `SECTION_SOURCE_MAP` maps specific section titles to install-command renderers. New sections (Edge Extensions, Brave Extensions, Zed Extensions, Safari Extensions, Codex Plugins) are NOT in this map. The emitter's fallback behavior sends any unknown section title to `_manual_checklist_block`.

This is the CORRECT behavior. Browser extensions and Codex plugins have no CLI installer keyed on the catalog data (per MAN-01 in v2.1.0). The manual checklist is the right output.

**Verified:** The emitter's `SECTION_SOURCE_MAP.get(section.title)` returns `None` for unknown titles, which routes to `manual_sections.append(section)` → `_manual_checklist_block`. No changes to `SECTION_SOURCE_MAP` or the parser are required.

**The actual risk:** Breaking an existing section title. If a new collector accidentally uses a section title string that EXACTLY matches an existing title (e.g., naming the Edge section "Google Chrome Extensions" by copy-paste), the reinstall emitter would apply the Chrome renderer to Edge data — or the wrong section would appear twice in the catalog.

**How to avoid:**
Each new browser must have a unique, explicit section title string. Proposed titles:
- `"Microsoft Edge Extensions"` (not "Chrome" or "Google")
- `"Brave Extensions"`
- `"Zed Extensions"`
- `"Safari Extensions"`
- `"Codex Plugins"` (not "Codex MCP Servers" which already exists)

Add a test that asserts all `_TITLE` constants across all collector modules are unique (a quick set-length check over imported constants).

**Warning signs:**
- Two collectors define `_TITLE = "Google Chrome Extensions"` (copy-paste residue).
- The new Codex collector uses `_TITLE = "Codex MCP Servers"` instead of `"Codex Plugins"`.

**Phase to address:**
Every new collector phase. Uniqueness test runs on every collector addition.

---

### Pitfall 17: Reinstall regression — parser state machine handles new sections without changes

**What goes wrong (non-pitfall, but needs explicit verification):**
The reinstall `parser.py` uses a state machine that reads any non-blank, non-separator line as a title candidate, followed by a 36-dash separator. New section titles are parsed automatically — no registration or update to the parser is needed.

**The risk:** A new section title that contains the 36-dash separator string (36 hyphens) or a blank line within the title string would corrupt the parser state. Neither is possible with the proposed title strings above — but a future refactor that constructs title strings dynamically (e.g., `f"Extensions: {browser_name}"`) could introduce a user-controlled string into the title.

**How to avoid:**
Section title strings must always be string literals, never dynamic constructions that include user input or external data. Document this constraint in the collector base class.

**Warning signs:**
- A collector uses `_TITLE = f"Extensions: {browser_name}"` where `browser_name` comes from anywhere other than a constant.

**Phase to address:**
All collector phases. Code review: section title must be a module-level string constant.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse Chrome COMPONENT_DENYLIST for Edge/Brave | No new code | Edge/Brave components appear as user extensions | **Never** — create browser-specific denylists |
| Use `_BASE.is_dir()` as "browser installed" check for Brave | Simple | Returns True for Brave even when uninstalled (NativeMessagingHosts dir exists) | **Never** — check for Default/Extensions instead |
| Use `pluginkit -mAD` without `-p` filter for Safari | Single subprocess call | Returns 485+ non-Safari extensions; complex post-filter | **Never** — always use `-p com.apple.Safari.web-extension` |
| Use `CFBundleName` for Safari extension name | Familiar plist key | Returns binary name ("safari") not display name | **Never** — use `CFBundleDisplayName` |
| Scan Codex plugin bundle dirs for version | Complete version info | FMT-03 violation — may read API keys/env vars | **Never** — accept version-absent output |
| `tomllib.load()` on full Codex config.toml | Simple config parsing | FMT-03 violation — reads command/env/args values | **Never** — text-grep headers only |
| Scan Zed `installed/` dirs instead of reading `index.json` | Familiar pattern | Picks up `work/` (incomplete downloads) | Acceptable only if `index.json` is missing AND a dev fallback is needed |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Brave Extensions directory | Assume `BraveSoftware/Brave-Browser/` exists = Brave installed | Check `Default/Extensions/` or any `Profile */Extensions/` |
| Edge component extensions | Apply only Chrome's 10-item denylist | Add Edge-specific component IDs; verify against real Edge install |
| Brave component extensions | Apply only Chrome's 10-item denylist | Add Brave 10+ component IDs from brave-browser wiki |
| Safari pluginkit | Parse all extension types | Always use `-p com.apple.Safari.web-extension` |
| Safari extension name | Read `CFBundleName` | Read `CFBundleDisplayName`; fall back to parent app DisplayName; fall back to bundle ID |
| Safari version | Use pluginkit version string | Use `get_plist_version(appex_info_plist)` — pluginkit can cache `(null)` |
| Codex plugin config | `tomllib.load()` full config.toml | Text-grep `[plugins.".*"]` header lines only |
| Zed extensions | Scan `installed/` filesystem | Parse `index.json`; filter `dev: true` |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Reading Codex plugin bundle .mcp.json | Emits API keys, env var names, command paths to catalog | Text-grep config.toml headers only; never read plugin bundle dirs |
| Reading Codex config.toml with tomllib.load() | Emits full MCP server command/env/args values (same risk as pre-FMT-03) | Mirror `CodexCollector._collect_via_toml` pattern: regex on header lines only |
| Emitting `(null)` from pluginkit as literal version | Confusing but not a security issue | Use plistlib for version; discard pluginkit version string |

## "Looks Done But Isn't" Checklist

- [ ] **Edge component denylist**: verified against a real Edge installation — IDs in Extensions dir that do NOT appear in `edge://extensions` UI are component IDs to add to `EDGE_COMPONENT_DENYLIST`.
- [ ] **Brave component denylist**: 10+ IDs from brave-browser wiki added to `BRAVE_COMPONENT_DENYLIST`; test confirms none appear in Brave catalog output.
- [ ] **Brave presence detection**: `~/Library/Application Support/BraveSoftware/Brave-Browser/` exists on this machine with no Default profile — confirm collector prints NOTE and returns empty, not raises.
- [ ] **Safari display name**: test fixture has `CFBundleName="safari"`, `CFBundleDisplayName="Bitwarden"` — output uses `CFBundleDisplayName`.
- [ ] **Safari (null) version**: pluginkit response with `(null)` version triggers plist read, not `(null)` in output.
- [ ] **Zed dev extensions**: fixture with `"dev": true` entry — verify excluded from catalog.
- [ ] **Codex plugins FMT-03**: fixture where config.toml has both `[plugins."x@y"]` header AND nested `mcp_servers.env.API_KEY` — verify only plugin name appears in output.
- [ ] **Section title uniqueness**: all `_TITLE` constants across all 17+ collector modules are unique (set-length assertion test).
- [ ] **Reinstall no-regression**: run reinstall on a catalog that includes new section titles — Edge/Brave/Zed/Safari/Codex Plugins sections appear in manual checklist, existing Homebrew/mas/VS Code/Cursor blocks are unaffected.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Edge component denylist incomplete (components appear in catalog) | LOW | Add IDs to `EDGE_COMPONENT_DENYLIST`; next run deduplication via `flush_section -u` removes them from new catalogs; old catalogs unaffected |
| Safari `CFBundleName` used (wrong name in catalog) | LOW | Fix to `CFBundleDisplayName`; regenerate catalog; diff shows name corrections only |
| Zed dev extensions included | LOW | Add `dev: true` filter; regenerate; diff removes dev entries |
| Codex FMT-03 violation (env refs in catalog) | HIGH | Remove tomllib.load() immediately; audit emitted catalogs for env var patterns; invalidate affected catalogs |
| Safari pluginkit raises on subprocess failure | MEDIUM | Add try/except around subprocess call; degrade to `(none found)` with WARNING |
| Brave presence false-positive | LOW | Fix is_dir() check; rerun; NOTE message now correct |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Edge/Brave incomplete component denylist | Edge/Brave collector phase | Test with known component IDs; confirm absent from output |
| Edge/Brave presence detection via base dir | Edge/Brave collector phase | Test with NativeMessagingHosts-only Brave dir; confirm graceful degrade |
| Chrome `__MSG_` helper reuse (vs. reimplementation) | Edge/Brave collector phase | Code review: no `edge_ext_name()` function exists |
| `version_sort_tail` called correctly | Edge/Brave collector phase | Code review: no `max(candidates)` or `sorted()[-1]` |
| Zed `index.json` vs. `installed/` scan | Zed collector phase | Test with `work/` entry present; confirm excluded |
| Zed dev extensions excluded | Zed collector phase | Test with `dev: true` fixture; confirm excluded |
| Zed missing `index.json` graceful degrade | Zed collector phase | Test with no Zed config directory |
| Safari `-p` filter usage | Safari collector phase | Verify only `com.apple.Safari.web-extension` entries returned |
| Safari `CFBundleDisplayName` vs `CFBundleName` | Safari collector phase | Test fixture with divergent values; assert DisplayName used |
| Safari never-raises on bad plist | Safari collector phase | Test with missing appex path in pluginkit output |
| Safari `(null)` version discarded | Safari collector phase | Test with `(null)` pluginkit version; assert plist version used |
| Safari `-v` for path extraction | Safari collector phase | Parse tab-separated verbose format; test with synthetic output |
| Codex FMT-03 — header-grep only | Codex Plugins collector phase | Test with config containing nested env ref; assert only name in output |
| Codex version-absent accepted | Codex Plugins collector phase | Fixture with `[plugins."x@y"]` entry; assert `x [x@y]` output (no version) |
| Section title uniqueness | Every new collector phase | Set-length uniqueness test added to test suite |
| Reinstall no-regression | Integration test | Round-trip: generate catalog with new sections → reinstall → new sections in manual checklist only |

## Sources

- `src/maccat/collectors/chrome.py` — `COMPONENT_DENYLIST` (10 IDs, lines 19–30); `_collect_profile` with `ext_id.startswith("_")` and `"Temp"` guards (lines 60–66); `version_sort_tail` call (line 70). Verified: this is the pattern to mirror exactly for Edge/Brave.
- `src/maccat/catalog/format.py` — `version_sort_tail` with `c[:1].isdigit()` pre-filter (line confirmed in source): "Only entries whose first character is an ASCII digit are considered." Mandatory for Edge/Brave.
- `src/maccat/collectors/codex.py` — `_collect_via_toml` (lines 79–99): text-grep of TOML header lines using `re.match(r"^\[mcp_servers\.(.*)\]$")`; value lines never read. This is the FMT-03 pattern to replicate for Codex Plugins.
- `src/maccat/reinstall/emitter.py` — `SECTION_SOURCE_MAP` (lines 230–235): 4 known titles; unknown titles fall to `_manual_checklist_block`. No changes needed for new sections.
- `~/Library/Application Support/Zed/extensions/index.json` — verified format on this machine: `{"extensions": {"html": {"manifest": {"id": "html", "name": "HTML", "version": "0.3.1", ...}, "dev": false}}}`. Single extension installed, `dev: false`.
- `pluginkit -mAD -p com.apple.Safari.web-extension` — verified on this machine: returns only `com.bitwarden.desktop.safari(2026.5.0)`. Apple's own Safari extensions (SafariLinkExtension etc.) do NOT appear with this filter.
- `pluginkit -v -m -A -p com.apple.Safari.web-extension` — returns tab-separated: `id(version)\tUUID\ttimestamp\tpath`. Path: `/Applications/Bitwarden.app/Contents/PlugIns/safari.appex`.
- `plutil -p /Applications/Bitwarden.app/Contents/PlugIns/safari.appex/Contents/Info.plist` — verified: `CFBundleDisplayName = "Bitwarden"`, `CFBundleName = "safari"`. DisplayName is the correct name source.
- brave-browser wiki (Brave Components): confirmed component extension IDs for Ad Block Updater, Tor Client Updater, Widevine, NTP images, User Model Installer, Local Data Updater.
- `developers.openai.com/codex/config-reference` — plugin configuration: `[plugins.<plugin>.mcp_servers.<server>]` schema; no version field; MCP server overrides only. MEDIUM confidence (official source but plugin system post-dates installed v0.46.0).
- `developers.openai.com/codex/changelog` — plugins subsystem first-class in v0.117.0 (March 2026). The installed version (v0.46.0) predates this.
- `.planning/PROJECT.md` — FMT-03 (name+transport only, no secrets), FMT-04 (deterministic sort), graceful degradation constraints. MAN-01 (browser/AI-CLI sources are manual-checklist in reinstall). Source-of-truth for v2.2.0 requirements.

---
*Pitfalls research for: v2.2.0 maccat — Edge/Brave/Zed/Safari collectors and Codex Plugins section*
*Researched: 2026-06-17*

# External Integrations

**Analysis Date:** 2026-08-25

maccat has **no network integrations** — no HTTP client, no SDK, no API keys, no auth provider, no database. Its "integrations" are entirely local: external CLI binaries it shells out to, and on-disk config/manifest files it reads. Every one is optional and gated.

Contract for all of them (`src/maccat/collectors/base.py`):
- `Collector.available()` gates on tool presence or directory existence
- `Collector.collect()` returns a `CollectorResult` of `Section`s and **never raises**
- Missing source → `NOTE:`/`WARNING:` on **stderr** plus an empty or placeholder section; the run always completes
- All `subprocess.run(...)` calls use a list argv with `shell=False`, `capture_output=True`, `text=True`

The ordered collector registry is `get_registry()` in `src/maccat/collectors/__init__.py` — 16 collectors producing 22 sections, in a semantically significant order.

## Package Managers & App Sources

**Homebrew** — `src/maccat/collectors/homebrew.py`
- Availability: `shutil.which("brew")`
- Commands, in this fixed order (a test contract — do not reorder):
  1. `brew list --formula --versions`
  2. `brew leaves`
  3. `brew list --cask --versions`
- `brew leaves` is used purely as a filter over the versioned formula list so only top-level user-installed formulae are cataloged; transitive deps are dropped. Leaf names are compared on the last `/` segment because leaves prints tap formulae fully qualified (`auth0/auth0-cli/auth0`)
- Output lines: `name (version [version2 ...])`, e.g. `python@3.11 (3.11.1 3.11.2)`. Section is `raw=True` — written verbatim, brew's ordering preserved for determinism
- Failure modes: brew absent → `WARNING: brew not found.` + section `"Homebrew is not installed."`; any command non-zero or empty → `[]`; `brew leaves` empty but formulae present → warning and all formulae (including deps) cataloged, on the reasoning that over-reporting is recoverable and a silently empty list is data loss

**Mac App Store (`mas`)** — `src/maccat/collectors/mas.py`
- Availability: `shutil.which("mas")`
- Command: `mas list`
- Parses `<id>  <Multi Word Name> (<version>)` → `emit_item(name, version, id)`. `raw=True`
- Failure modes: absent → `WARNING: mas CLI is not installed. Install with: brew install mas` + a two-line placeholder section; `OSError` on exec → warning + `"Could not retrieve App Store list."`; non-zero exit → same

**Setapp** — `src/maccat/collectors/setapp.py`
- Availability: `/Applications/Setapp` is a directory. No CLI — filesystem scan only
- Version per app from `<App>.app/Contents/Info.plist` via `get_plist_version()`
- Failure mode: not installed → `"Setapp is not installed or detected."`

**Web-installed applications** — `src/maccat/collectors/webapps.py`
- Source: `/Applications` scan. No availability guard (always exists on macOS)
- Excludes `Setapp*` and `*App Store*` directories (covered by their own collectors)
- Versions via `Info.plist`; entries without a readable plist degrade to bare name

## AI Coding CLIs

**Claude Code** — `src/maccat/collectors/claude.py` (3 sections)
- `~/.claude/plugins/installed_plugins.json` → Claude Code Plugins
- `~/.claude.json` key `mcpServers` → Claude Code MCP Servers
- `~/.claude/skills/` (name from `SKILL.md` frontmatter) and `~/.claude/agents/` → Claude Code Skills & Agents
- **Safety invariant (CAT-05):** reads only `cfg["type"]` from each MCP server, defaulted to `stdio` and whitelist-checked. Never reads `.command`, `.env`, `.args`, `.url`, `.headers` — these carry secrets
- Failure modes: missing file, `json.JSONDecodeError`, or `OSError` → empty section, silent (absence is normal). Non-dict server values are skipped per-entry rather than aborting the section

**Codex** — `src/maccat/collectors/codex.py` (2 sections)
- Primary: `codex mcp list --json` and `codex plugin list --json`, gated on `shutil.which("codex")`
- Fallback: text-grep of `[mcp_servers.*]` / `[plugins.*]` **section-header lines only** in `~/.codex/config.toml` — deliberately not `tomllib`, so no value is ever parsed
- Same CAT-05 invariant: only name and type; never command/env/args/url/headers
- Failure modes: `OSError` on exec, non-zero exit, empty stdout, or JSON decode error → `[]` then fall through to the TOML header scan. Codex v0.46.0 has no plugin system, so an empty plugin list is expected, not an error

**OpenCode** — `src/maccat/collectors/opencode.py` (3 sections)
- `~/.config/opencode/opencode.json` → Plugins and MCP Servers
- `~/.config/opencode/agents/*.md` → Agents
- No CLI invoked. Missing/malformed config → empty sections

**Gemini CLI** — `src/maccat/collectors/gemini.py` (2 sections)
- `~/.gemini/extensions/` → Gemini CLI Extensions
- `~/.gemini/config/mcp_config.json` → Gemini CLI MCP Servers (guarded on `is_file()` and non-zero `st_size`)
- No CLI invoked

## Editors

**VS Code / Cursor** — `src/maccat/collectors/vscode.py` (shared helper), `src/maccat/collectors/cursor.py`
- Path A (preferred): `<cli> --list-extensions --show-versions` where `<cli>` is `code` or `cursor`, gated on `shutil.which()`. Display names resolved by joining CLI ids against `extensions.json` `relativeLocation` → `package.json`
- Path B (fallback): parse `~/.vscode/extensions/extensions.json` or `~/.cursor/extensions/extensions.json` directly
- Failure modes: CLI absent and no `extensions.json` → `NOTE: <Cli> not installed or no extensions found.`; CLI present but returns empty → `WARNING: ... CLI returned empty list. Falling back to extensions.json.`; malformed JSON or non-list top level → `[]`

**Zed** — `src/maccat/collectors/zed.py`
- `~/Library/Application Support/Zed/extensions/index.json`. No CLI. Missing/malformed → empty section

## Browsers

**Chromium family** — shared base `src/maccat/collectors/chromium.py`; subclasses set only `_base`, `_title`, `_denylist`, `_browser_name`:
- Chrome — `~/Library/Application Support/Google/Chrome` (`chrome.py`)
- Edge — `~/Library/Application Support/Microsoft Edge` (`edge.py`)
- Brave — `~/Library/Application Support/BraveSoftware/Brave-Browser` (`brave.py`), plus a Brave-specific denylist entry for its Ad Block Resources Library
- Profile enumeration: `Default` first, then sorted `Profile */`; per profile scan `Extensions/<id>/<version>/manifest.json`, picking the version dir by `version_sort_tail()`
- Skips `Temp`, any `_`-prefixed dir, and the 10-ID `COMPONENT_DENYLIST` of Chrome-preinstalled component extensions
- Failure modes: base dir absent → `NOTE: <Browser> not installed.` + empty section; `OSError` while iterating a profile or extension dir (TOCTOU/unreadable) → that entry skipped, others proceed. `raw=False`, so the orchestrator dedupes across profiles

**Firefox** — `src/maccat/collectors/firefox.py`
- `~/Library/Application Support/Firefox/profiles.ini` → `Path=` entries → each profile's `extensions.json`
- `profiles.ini` read with `splitlines()` to tolerate CRLF; filter `location == "app-profile"` so `app-builtin` system add-ons are excluded
- Failure modes: no `profiles.ini` → `NOTE: Firefox not installed.`; malformed `extensions.json` → that profile skipped; non-dict addon entries skipped per-entry (an intentional deviation from the old `jq` behavior, which aborted the whole section)

**Safari** — `src/maccat/collectors/safari.py`
- Availability: `/usr/bin/pluginkit` `is_file()`
- Command: `/usr/bin/pluginkit -mAvv -p <plugin point>`; output parsed for `Path = ....appex` lines, then each `.appex` bundle's plist read for name/version
- Failure modes: pluginkit absent → `NOTE: pluginkit not found.`; `OSError` → `WARNING: could not run pluginkit: ...`; non-zero exit → `WARNING: pluginkit failed (exit N).`; empty stdout → empty section with **no** warning (zero extensions is normal); an unreadable per-extension plist skips just that extension

## Version Control

**git** — `src/maccat/gitops.py`
- Guard: `shutil.which("git")` plus `git rev-parse --git-dir` inside the catalog repo
- Commands: `git pull` (bare — deliberately no `--rebase`), `git add -A -- <computer>/`, `git add -- machine-labels.tsv`, `git diff --cached --quiet` (skip empty commits), `git commit -m <msg>`, `git push`. Rename and convert flows add/stage their own path pairs
- Failure modes: warn-and-continue throughout — the catalog file is always written to disk regardless of git outcome. `--no-commit` skips staging, commit, and push entirely
- The remote is whatever the user's `catalog_dir` repo is configured with; maccat never knows or handles credentials

## Data Storage

- **Databases:** none
- **File storage:** local only — timestamped Markdown catalogs written under `<catalog_dir>/<computer>/`, older files pruned/archived by `src/maccat/retention.py`; writes are atomic (tmp file + rename) per `src/maccat/catalog/writer.py` and `src/maccat/identity.py`
- **Machine registry:** `<catalog_dir>/machine-labels.tsv` — hostname → computer-folder map, hostname obtained via `socket.gethostname()` (`src/maccat/identity.py`)
- **Caching:** none

## Authentication & Identity

- No auth provider, no tokens, no credential handling anywhere in `src/maccat/`
- The only credential surface is transitive: `git push` uses the user's ambient git credentials; `mas install` (in *generated* reinstall scripts) requires the user to be signed into the App Store
- CI uses `secrets.GITHUB_TOKEN` in `.github/workflows/release.yml` for `gh release`; that is a CI concern, not a runtime one
- Explicit anti-integration: MCP collectors are contractually forbidden from reading `command`/`env`/`args`/`url`/`headers`, which is exactly where MCP secrets live. Enforced by tests marked `safety_invariant` in `tests/test_safety_invariants.py`

## Outbound Generated Scripts

`maccat reinstall` (`src/maccat/reinstall/emitter.py`) emits a shell script that *itself* integrates with external tools when the user runs it:
- `brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n> || echo WARN...` — idempotent, non-fatal on failure
- `command -v mas >/dev/null && ! mas list | grep -q <id> && mas install <id> || echo WARN...` — skips when `mas` is absent or the app is already installed
- Everything without an automatable installer is emitted as a manual checklist section
- maccat itself makes no subprocess calls during `reinstall` — it only writes the script text

## Webhooks & Callbacks

**Incoming:** none.
**Outgoing:** none.

---

*Integration audit: 2026-08-25*

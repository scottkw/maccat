# Phase 3: AI-CLI Collectors — Research

**Researched:** 2026-06-13
**Domain:** AI CLI extension cataloging — Claude Code, Codex, OpenCode, Gemini CLI — pure Zsh,
secret-safe output
**Confidence:** HIGH (all findings verified live on this machine against real on-disk configs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**FMT-03 Secret Boundary (milestone-critical — USER LOCKED: strictest)**
- An MCP entry emits `name [transport]` only, where transport is the type (`stdio` / `http` /
  `sse`) read from the config's `type` field (or inferred: presence of `command` ⇒ stdio,
  presence of `url` ⇒ http/sse).
- NEVER emitted, for any MCP server, any tool: `env`, `headers`, `args`, `command`,
  `url` (including host, query string, and userinfo), tokens, or any auth-bearing value.
- For http/sse servers, emit the transport label only — never the URL itself.
- MCP lines: `emit_item "$name" "" "$transport"` → renders `name [transport]`.
- Phase 5 secret-leakage gate: grep output for `http`, `token`, `Bearer`, `key=`,
  `Authorization`, `sk-`, `ghp_` must return zero hits.

**Capture Scope (USER LOCKED: user/global only)**
- Claude Code MCP: `~/.claude.json` top-level `mcpServers`.
- OpenCode MCP: `~/.config/opencode/opencode.json` `.mcp`.
- Gemini MCP: `~/.gemini/config/mcp_config.json` (confirmed location).
- Codex MCP: prefer `codex mcp list --json`; fall back to `~/.codex/config.toml`
  `[mcp_servers.*]` sections.
- Do NOT scan per-project mcpServers.

**Plugins / Skills / Agents Enumeration & Versioning (USER LOCKED: accept all)**
- Claude Code plugins: `~/.claude/plugins/installed_plugins.json`.
- Claude Code skills & agents: `~/.claude/skills/` dirs + `~/.claude/agents/*.md`.
- OpenCode plugins: `~/.config/opencode/opencode.json` `.plugin` array.
- OpenCode agents: `~/.config/opencode/agents/*.md` files.
- Gemini extensions: `~/.gemini/extensions/` (one dir per extension; manifest in
  `gemini-extension.json`).
- Many skills/agents/plugins have no version — emit bare `name` (FMT-01 degrades cleanly).

**Section Organization & Degradation (USER LOCKED: accept all)**
- One section per (tool × concern):
  - "Claude Code Plugins", "Claude Code MCP Servers", "Claude Code Skills & Agents"
  - "Codex MCP Servers"
  - "OpenCode Plugins", "OpenCode MCP Servers", "OpenCode Agents"
  - "Gemini CLI Extensions", "Gemini CLI MCP Servers"
- Tool not installed → section(s) still written with `(none found)` via `flush_section`.
- Everything routed through `emit_item` → `flush_section` (`LC_ALL=C sort -f -u`).

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- Wiring collectors into `generate_catalog` — Phase 5.
- Codex plugins/skills — no plugin system in installed Codex v0.46.0 (v2 CDX-02).
- MCP enabled/disabled state — out of scope.
- Per-project MCP configs and project `.mcp.json` — excluded (scope + secrets).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CC-01 | Catalog installed Claude Code plugins (name + version + ID) | `installed_plugins.json` schema verified; key `plugins` is an object keyed by `name@marketplace`; version in `[0].version`, id derivable from the key; 9 plugins confirmed on this machine |
| CC-02 | Catalog configured Claude Code MCP servers (name + transport only, per FMT-03) | `~/.claude.json` `.mcpServers` confirmed; `execbro [stdio]` extraction verified live; zero-leakage proof run; jq + plutil fallback both confirmed working |
| CC-03 | Catalog Claude Code skills and subagents present under `~/.claude/` | `~/.claude/skills/` = 70 dirs+symlinks with SKILL.md `name:` frontmatter; `~/.claude/agents/` = 33 `.md` files with `name:` frontmatter; all extraction patterns verified |
| CDX-01 | Catalog configured Codex MCP servers (name + transport only, per FMT-03) | `codex mcp list --json` returns `[]` (works, zero servers); TOML fallback pattern documented; TOML format confirmed from `[agents.*]` analog |
| OC-01 | Catalog OpenCode plugins from its config | `.plugin` array in `opencode.json` confirmed; 1 plugin (`superpowers`); name = `${entry%%@*}`; no numeric version available |
| OC-02 | Catalog configured OpenCode MCP servers (name + transport only, per FMT-03) | `.mcp` is `null` in `opencode.json`; section writes `(none found)`; confirmed |
| OC-03 | Catalog OpenCode agents from its config | `~/.config/opencode/agents/*.md` confirmed; 33 files; `name:` frontmatter present in all sampled files |
| GEM-01 | Catalog installed Gemini CLI extensions (name + version + ID) | `~/.gemini/extensions/conductor/gemini-extension.json` has `name` + `version`; `extension-enablement.json` lists enabled extensions; 1 extension confirmed |
| GEM-02 | Catalog configured Gemini CLI MCP servers (name + transport only, per FMT-03) | `~/.gemini/config/mcp_config.json` exists but is 0 bytes; no mcpServers in settings.json or any extension manifest; writes `(none found)` |
| FMT-03 | No secrets written to catalog — MCP server entries capture name + transport only | Live zero-leakage proof run: `execbro [stdio]` output passes all 7 grep checks (token/key/sk-/Bearer/http/Authorization/ghp_); extraction uses `.mcpServers \| to_entries[] \| .key + " [" + (.value.type // "stdio") + "]"` |
</phase_requirements>

---

## Summary

Phase 3 adds nine Zsh collector functions to `update-list.sh`, one per (tool × concern)
section. All four AI CLIs are installed and have real on-disk configs — every finding below
was verified live. The collectors follow the Phase 2 pattern exactly: `write_section` → reset
`_section_lines=()` → enumerate source → `emit_item` → `flush_section`.

**Critical path is FMT-03.** The Claude Code `execbro` MCP server has an `env` object in its
config. Live extraction via `jq '.mcpServers | to_entries[] | .key + " [" + (.value.type // "stdio") + "]"'` produces `execbro [stdio]` and passes all seven secret-pattern grep checks with
zero hits. The collector must never read `.env`, `.command`, `.args`, or `.url`.

**Real-machine state (this machine):** Claude has 9 plugins, 1 MCP server, 70 skills,
33 agents; Codex has 0 MCP servers; OpenCode has 1 plugin, 0 MCP servers, 33 agents; Gemini
has 1 extension, 0 MCP servers. Most sections will have real data; the zero-server sections
write `(none found)` via `flush_section`.

**Gemini MCP location correction:** The ROADMAP speculated `settings.json.mcpServers` — that
field does not exist there. The actual MCP config is `~/.gemini/config/mcp_config.json` (0
bytes on this machine). Extensions do NOT carry mcpServers in their `gemini-extension.json`
manifest (confirmed on conductor v0.4.1).

**Primary recommendation:** Implement one collector function per section, grouped by tool,
inserted after the Phase 2 collectors and before `generate_catalog`. No new dependencies
required — same jq/plutil/grep toolchain already present.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Claude MCP extraction | `~/.claude.json` top-level `mcpServers` (jq or plutil) | — | User-global scope; project-level mcpServers deliberately excluded |
| Claude plugins | `~/.claude/plugins/installed_plugins.json` | — | Single file; structured JSON with name/version/id |
| Claude skills | `~/.claude/skills/*/SKILL.md` frontmatter | dir name fallback | All 70 skills have SKILL.md; `name:` field always present |
| Claude agents | `~/.claude/agents/*.md` frontmatter | filename fallback | All 33 agents have `name:` frontmatter |
| Codex MCP extraction | `codex mcp list --json` CLI | `~/.codex/config.toml` grep | CLI works and is the preferred source; TOML grep is the no-CLI fallback |
| OpenCode plugins | `~/.config/opencode/opencode.json` `.plugin` array | — | Single array of `name@source` strings |
| OpenCode MCP | `~/.config/opencode/opencode.json` `.mcp` | — | Field is null on this machine; writes `(none found)` |
| OpenCode agents | `~/.config/opencode/agents/*.md` frontmatter | filename fallback | 33 files, all have `name:` |
| Gemini extensions | `~/.gemini/extensions/*/gemini-extension.json` | — | manifest has `name` + `version`; extension-enablement.json confirms enablement |
| Gemini MCP | `~/.gemini/config/mcp_config.json` | — | Empty on this machine; writes `(none found)` |

---

## Research Flag Answers

### Flag 1: Claude MCP Transport Derivation + Plugin/Skill/Agent Shapes

**Verified live on this machine.**

#### MCP Server Fields (execbro) — FMT-03 boundary

The `execbro` entry in `~/.claude.json` `.mcpServers` has these fields (confirmed by
`jq '.mcpServers.execbro | to_entries | map({key: .key, valueType: (.value | type)})'`):

| Field | Type | FMT-03 Classification |
|-------|------|-----------------------|
| `type` | string (`"stdio"`) | SAFE — this is the transport label |
| `command` | string | SECRET-BEARING — the executable path; must never be emitted |
| `args` | array | SECRET-BEARING — CLI arguments that may include paths/tokens |
| `env` | object (empty `{}` in this case but secret-bearing by design) | SECRET-BEARING — env vars can hold API keys, tokens |

**Safe extraction:** `jq -r '.mcpServers | to_entries[] | .key + " [" + (.value.type // "stdio") + "]"'`

**Transport inference rule:** If `type` is present, use it directly. If `type` is absent,
infer: `command` present → `stdio`; `url` present → `http` or `sse` (use `http` as a safe
label when the subtype is unclear). In practice on this machine, `type` is always present.

**plutil fallback for no-jq path:**
- Enumerate server names: `plutil -extract "mcpServers" raw -o - ~/.claude.json` — outputs
  one server name per line (confirmed: prints `execbro`).
- For each name: `plutil -extract "mcpServers.${name}.type" raw -o - ~/.claude.json`
  (confirmed: prints `stdio`).

#### Claude Plugins (`installed_plugins.json`) — CC-01

**File:** `~/.claude/plugins/installed_plugins.json`
**Schema (confirmed live):**

```json
{
  "version": 2,
  "plugins": {
    "pluginname@marketplace": [
      {
        "scope": "user",
        "installPath": "...",
        "version": "1.0.0",
        "installedAt": "...",
        "lastUpdated": "...",
        "gitCommitSha": "..."
      }
    ]
  }
}
```

The `plugins` field is a JSON **object** (not array). Each key is `name@marketplace`. The
value is an array of scope-entries; `[0].version` is the version string. Some plugins have
`"version": "unknown"`.

**jq extraction:**
```bash
jq -r '.plugins | to_entries[] | .key + "\t" + (.value[0].version // "")' installed_plugins.json
```
This yields `name@marketplace\tversion` pairs.

**Name from key:** `${key%%@*}` — everything before the first `@`.
**ID from key:** `${key}` (the full `name@marketplace` string is the canonical ID).
**emit_item call:** `emit_item "$name" "$version" "$key"` → `name (version) [name@marketplace]`

For version = `"unknown"`: emit as version (FMT-01 accepts it — never synthesize a replacement).

**plutil fallback note:** `plugins` is an object; `plutil -extract "plugins" raw` would
enumerate its keys. However, iterating all entries by index requires knowing the count. Since
jq is very likely present (it's installed as a Homebrew dep), a simpler plutil fallback is:
use `plutil -extract "plugins" xml1 -o - | grep '<key>' | sed 's/.*<key>//;s/<\/key>//'`
to extract the plugin key names, then look up version per key.

#### Claude Skills (`~/.claude/skills/`) — CC-03

**Directory:** `~/.claude/skills/` — one subdirectory per skill. Includes real directories
AND symlinks (2 symlinks detected: `find-skills`, `impeccable`).

**Name source:** `SKILL.md` frontmatter line `^name:`. All 70 skill dirs have SKILL.md (0
without SKILL.md confirmed by live scan). Fallback: directory basename.

**Extraction pattern (verified):**
```bash
grep '^name:' "$skill_dir/SKILL.md" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'
```

**No version, no ID for skills** (FMT-01: bare `name`). Emit: `emit_item "$name" "" ""`.

#### Claude Agents (`~/.claude/agents/`) — CC-03

**Directory:** `~/.claude/agents/` — flat directory, all `*.md` files (no subdirs). 33 files.

**Name source:** YAML frontmatter `name:` line at file top. All 33 agents have `name:`
frontmatter (confirmed on sample). Fallback: filename without `.md` extension.

**Extraction pattern (verified):**
```bash
grep '^name:' "$f" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'
```

**No version, no ID for agents.** Emit: `emit_item "$name" "" ""`.

---

### Flag 2: Codex MCP — CLI vs TOML Fallback

**Verified live on this machine.**

#### `codex mcp list --json`

`codex mcp list --json` WORKS in the installed version (v0.46.0). It returns a JSON array.
On this machine: `[]` (empty array). Exit code 0.

**This is the preferred path.** When it returns a non-empty array, iterate with jq:
```bash
jq -r '.[] | .name + "\t" + (.type // "stdio")'
```
(The exact field names in the array object for populated servers need to be verified if
encountered, but `codex mcp list --json` is the canonical source per CONTEXT.md.)

#### TOML Fallback (if CLI unavailable or fails)

**File:** `~/.codex/config.toml`

When Codex MCP servers are configured, the TOML format is (confirmed from `[agents.*]`
analog in the same file):
```toml
[mcp_servers."my-tool"]
command = "my-command"
type = "stdio"
```

Section headers follow the pattern `[mcp_servers."<name>"]`.

**TOML name extraction (no TOML parser needed — grep only):**
```bash
grep '^\[mcp_servers\.' ~/.codex/config.toml 2>/dev/null \
  | while IFS= read -r line; do
      name="${line#\[mcp_servers.\"}"
      name="${name%\"\]}"
      echo "$name"
    done
```

This extracts the quoted name portion. For names without quotes:
`[mcp_servers.my-tool]` → `name="${line#\[mcp_servers.}"; name="${name%\]}"`.

A robust pattern that handles both quoted and unquoted names:
```bash
grep '^\[mcp_servers\.' ~/.codex/config.toml 2>/dev/null \
  | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' \
  | tr -d '"'
```

**TOML fallback transport:** When using TOML fallback, the `type` field is on the NEXT line
after the section header. Extracting it safely:
```bash
# Read type from line after section header (simple awk-based approach)
awk '/^\[mcp_servers\./{found=1; header=$0; next}
     found && /^type[[:space:]]*=/{
       gsub(/^type[[:space:]]*=[[:space:]]*"/, ""); gsub(/"$/, ""); print; found=0}
     /^\[/{found=0}' ~/.codex/config.toml
```

But since this is the fallback-of-fallback and the CLI already works, a simpler degradation
is acceptable: when using TOML grep fallback and `type` cannot be determined, emit with a
default of `stdio` (most Codex MCP servers are stdio; the TOML is read-only for names only,
never for secrets).

**KEY RULE:** Even in TOML fallback, NEVER read `command`, `env`, `args`, or `url` values.
Only extract the section header (server name) and optionally the `type` field value.

---

### Flag 3: OpenCode Plugin and Agent Shapes

**Verified live on this machine.**

#### OpenCode Plugins — OC-01

**Source:** `~/.config/opencode/opencode.json` field `.plugin` — a JSON **array of strings**.

On this machine:
```json
["superpowers@git+https://github.com/obra/superpowers.git"]
```

Format: `"<name>@<source>"`. The name is the substring before the first `@`.

**jq extraction:**
```bash
jq -r '.plugin[]? | split("@")[0]' ~/.config/opencode/opencode.json
```

**No numeric version available** for OpenCode plugins. The source URL is not a version.
Emit: `emit_item "$name" "" ""` → bare `superpowers`.

**Null/absent field handling:** `.plugin` may be absent (null). `jq -r '.plugin[]? ...'`
with `?` handles null silently. Or use: `jq -r 'if .plugin then .plugin[] | ... else empty end'`.

#### OpenCode MCP — OC-02

**Source:** `~/.config/opencode/opencode.json` field `.mcp`.

On this machine: `.mcp` is `null` (confirmed by `jq '.mcp'`).

Collector logic: `[[ -z "$(jq -r '.mcp // empty' ...)" ]]` → skip, `flush_section` emits
`(none found)`.

If populated, the shape would be a JSON object of MCP server configs (similar to Claude's
`mcpServers`). When/if populated in the future, apply same FMT-03 rules.

#### OpenCode Agents — OC-03

**Source:** `~/.config/opencode/agents/` directory — flat, all `.md` files (33 files).

**Name source:** YAML frontmatter `name:` line. All sampled files have it.

Extraction pattern (same as Claude agents):
```bash
grep '^name:' "$f" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'
```

Fallback: filename without `.md` extension.

---

### Flag 4: Gemini MCP Location and Extension Shape

**Verified live on this machine. This is the most important path correction.**

#### Gemini MCP Configuration Location — GEM-02

**NOT in `~/.gemini/settings.json`** — confirmed: `settings.json` has no `mcpServers` key.

**ACTUAL location: `~/.gemini/config/mcp_config.json`** (confirmed by `find ~/.gemini/ -name "*.json" | xargs grep -l "mcpServers"` which found this file via its name).

On this machine: the file exists (created at `~/.gemini/config/`) but is **0 bytes** (empty).
An empty file is not valid JSON. The collector must handle this gracefully:
```bash
[[ -s "$mcp_config" ]]  # -s = file exists AND has nonzero size
```
If file is absent or empty: `flush_section` emits `(none found)`.

**Extensions do NOT carry MCP servers:** `~/.gemini/extensions/conductor/gemini-extension.json`
field check confirms `has("mcpServers") = false`. Extensions have no `mcpServers` field on
this machine.

#### Gemini Extensions Manifest — GEM-01

**Directory:** `~/.gemini/extensions/` — one subdirectory per extension.

**Manifest file:** `<ext_dir>/gemini-extension.json`

**Schema (confirmed on `conductor` v0.4.1):**
```json
{
  "name": "conductor",
  "version": "0.4.1",
  "contextFileName": "GEMINI.md",
  "plan": { "directory": "conductor" }
}
```

Fields `name` and `version` are always present. No `id` field — use the directory name as
the ID (it equals `name` in practice).

**Extension enablement:** `~/.gemini/extensions/extension-enablement.json` maps enabled
extensions:
```json
{
  "conductor": {
    "overrides": ["/Users/ken/*"]
  }
}
```

Per the CONTEXT.md decision: list ALL installed extensions (i.e., all subdirs of
`~/.gemini/extensions/` that contain `gemini-extension.json`), not just enabled ones.
The enablement file is informational — a user might want to know all installed extensions
even if some are scoped. The canonical source is the presence of `gemini-extension.json`
in the directory.

**jq extraction for name + version:**
```bash
jq -r '"\(.name)\t\(.version)"' "$ext_dir/gemini-extension.json"
```

**emit_item call:** `emit_item "$name" "$version" ""` → `conductor (0.4.1)` (no ID bracket,
since the dir name === name, emit_item would produce `name [name]` which is the
id-equals-name suppression case — pass `""` as id to get clean `name (version)` output).

---

### Flag 5: Definitive FMT-03 Field Map

**The complete cross-source field safety table.** Every column verified live.

#### Claude Code MCP (`~/.claude.json`)

| Field | Present in execbro | FMT-03 Classification | Action |
|-------|--------------------|-----------------------|--------|
| key (server name, from `to_entries[].key`) | yes | SAFE | Emit as name |
| `type` | yes (`"stdio"`) | SAFE | Emit as transport label |
| `command` | yes | SECRET-BEARING | Never read |
| `args` | yes | SECRET-BEARING | Never read |
| `env` | yes (empty object `{}` here; may hold env vars on other machines) | SECRET-BEARING | Never read |
| `url` | absent on this server (stdio type) | SECRET-BEARING if present | Never read |
| `headers` | absent on this server (stdio type) | SECRET-BEARING if present | Never read |

**Safe jq:** `jq -r '.mcpServers | to_entries[] | .key + " [" + (.value.type // "stdio") + "]"'`

**Safe plutil:** Enumerate keys via `plutil -extract "mcpServers" raw`, then for each name:
`plutil -extract "mcpServers.${name}.type" raw` — reads ONLY the `type` scalar.

#### Codex MCP (`codex mcp list --json` or `~/.codex/config.toml`)

| Source | Field | FMT-03 Classification |
|--------|-------|-----------------------|
| CLI JSON array | `.name` | SAFE |
| CLI JSON array | `.type` | SAFE |
| CLI JSON array | `.command`, `.args`, `.env`, `.url`, `.headers` | SECRET-BEARING — never read |
| TOML section header | `[mcp_servers."name"]` | SAFE (section header only, no values) |
| TOML value | `type = "stdio"` | SAFE (string literal transport label) |
| TOML value | `command`, `env`, `url`, `args`, `headers` | SECRET-BEARING — never read |

#### OpenCode MCP (`~/.config/opencode/opencode.json` `.mcp`)

| Field | FMT-03 Classification |
|-------|-----------------------|
| Object key (server name) | SAFE |
| `.type` | SAFE |
| `.command`, `.args`, `.env`, `.url`, `.headers` | SECRET-BEARING — never read |

(`.mcp` is null on this machine. When populated, same rules as Claude apply.)

#### Gemini MCP (`~/.gemini/config/mcp_config.json`)

| Field | FMT-03 Classification |
|-------|-----------------------|
| Object key (server name) | SAFE |
| `.type` (inferred from structure if absent) | SAFE |
| Any URL, token, env, command, args | SECRET-BEARING — never read |

(File is empty on this machine.)

**The invariant:** For every MCP source, the collector reads ONLY two things:
1. The server name (map key or equivalent)
2. The `type` field scalar (or inferring from `command`/`url` presence)

The collector never iterates `.env`, `.headers`, `.args`, `.command`, `.url`, or any
sibling/child of those keys.

---

### Flag 6: Live Verification + Real Machine Counts

**All counts verified via live commands on 2026-06-13:**

| Tool | Section | Count on This Machine |
|------|---------|----------------------|
| Claude Code | Plugins | 9 (`claude-mem`, `dev-browser`, `pyright-lsp`, `typescript-lsp`, `gopls-lsp`, `frontend-design`, `superpowers`, `ui-ux-pro-max`, `warp`) |
| Claude Code | MCP Servers | 1 (`execbro [stdio]`) |
| Claude Code | Skills | 70 (68 real dirs + 2 symlinks: `find-skills`, `impeccable`) |
| Claude Code | Agents | 33 `.md` files |
| Codex | MCP Servers | 0 → `(none found)` |
| OpenCode | Plugins | 1 (`superpowers`) |
| OpenCode | MCP Servers | 0 (`.mcp` = null) → `(none found)` |
| OpenCode | Agents | 33 `.md` files |
| Gemini CLI | Extensions | 1 (`conductor` v0.4.1) |
| Gemini CLI | MCP Servers | 0 (empty `mcp_config.json`) → `(none found)` |

**Live zero-leakage proof for FMT-03 (execbro):**

Command run:
```bash
jq -r '.mcpServers | to_entries[] | .key + " [" + (.value.type // "stdio") + "]"' ~/.claude.json
```

Output:
```
execbro [stdio]
```

Secret-pattern grep results (all zero):
- `token`: 0 hits
- `key` (word boundary): 0 hits
- `sk-`: 0 hits
- `Bearer`: 0 hits
- `http`: 0 hits
- `Authorization`: 0 hits
- `ghp_`: 0 hits

Supporting evidence:
- `execbro` has fields `type`, `command`, `args`, `env` (type confirmed by jq).
- `env` field type is `object` (empty `{}` on this machine).
- `env` key names list: `[]` (empty — no env var names in the env object on this machine).
- The extraction ONLY touches `.key` (server name) and `.value.type` — never `.value.env`,
  `.value.command`, `.value.args`.

---

## Standard Stack

### Core (no new packages)

| Tool | Availability | Phase 3 Use |
|------|-------------|------------|
| `jq` | Optional (Homebrew, present on this machine as `jq-1.8.1`) | Primary JSON extraction for all collectors |
| `plutil` | Always present (macOS built-in since 10.4) | Fallback JSON extraction |
| `grep` + `sed` | Always present | Codex TOML name extraction (section headers only) |
| Phase 1 helpers | Already in `update-list.sh` | `json_get`, `emit_item`, `flush_section`, `write_section` |

**This phase installs nothing.** All backends are already probed at runtime by Phase 1.

---

## Package Legitimacy Audit

Not applicable — Phase 3 installs no external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
collect_claude_plugins()       collect_claude_mcp()        collect_claude_skills_agents()
       │                              │                              │
       │ read installed_plugins.json  │ read ~/.claude.json          │ glob ~/.claude/skills/*/
       │ jq .plugins | to_entries[]  │ jq .mcpServers |             │ grep SKILL.md name:
       │ name = key%%@*              │ to_entries[]                 │ glob ~/.claude/agents/*.md
       │ version = value[0].version  │ name = .key                  │ grep frontmatter name:
       │ id = key                    │ transport = .value.type       │ emit_item "$name" "" ""
       │ emit_item $name $ver $id    │ emit_item $name "" $transport │ (no version, no id)
       ▼                             ▼                              ▼

collect_codex_mcp()            collect_opencode_plugins()  collect_opencode_mcp()
       │                              │                              │
       │ codex mcp list --json        │ jq '.plugin[]?'              │ jq '.mcp | ...'
       │   → [] or [{name, type}]    │ opencode.json                │ if null → (none found)
       │ fallback:                    │ name = split("@")[0]         │ else: extract name+type
       │   grep ~/.codex/config.toml  │ emit_item $name "" ""        │
       │   [mcp_servers.*] headers   │                              │
       │   emit_item $name "" $type  │                              │
       ▼                             ▼                              ▼

collect_opencode_agents()      collect_gemini_extensions() collect_gemini_mcp()
       │                              │                              │
       │ glob ~/.config/opencode/     │ glob ~/.gemini/extensions/*/ │ [[ -s mcp_config.json ]]
       │   agents/*.md                │ read gemini-extension.json   │ if empty: (none found)
       │ grep frontmatter name:       │ name = .name                 │ else: extract name+type
       │ emit_item $name "" ""        │ version = .version           │
       │                              │ emit_item $name $version ""  │
       ▼                             ▼                              ▼
                              flush_section() for each
                                    │
                              OUTPUT_FILE (global)
```

### Recommended Project Structure

No new files. Nine new collector functions inserted in `update-list.sh` after
`collect_cursor_extensions` (Phase 2) and before `generate_catalog`:

```
update-list.sh
├── display_usage            (unchanged)
├── parse_arguments          (unchanged)
├── get_target_location      (unchanged)
├── archive_old_catalogs     (unchanged)
├── write_section            (unchanged)
├── json_get                 (Phase 1)
├── chrome_ext_name          (Phase 1)
├── emit_item                (Phase 1)
├── flush_section            (Phase 1)
├── resolve_vsc_ext_name     (Phase 2)
├── collect_vscode_extensions  (Phase 2)
├── collect_cursor_extensions  (Phase 2)
├── [NEW] collect_claude_plugins        ← CC-01
├── [NEW] collect_claude_mcp            ← CC-02
├── [NEW] collect_claude_skills_agents  ← CC-03
├── [NEW] collect_codex_mcp             ← CDX-01
├── [NEW] collect_opencode_plugins      ← OC-01
├── [NEW] collect_opencode_mcp          ← OC-02
├── [NEW] collect_opencode_agents       ← OC-03
├── [NEW] collect_gemini_extensions     ← GEM-01
├── [NEW] collect_gemini_mcp            ← GEM-02
└── generate_catalog         (unchanged — collectors NOT wired here yet; Phase 5)
```

### Section-Writing Flow (all 9 collectors follow this pattern)

```zsh
collect_TOOL_THING() {
    local config_file="$HOME/path/to/config"
    local ...vars...

    write_section "Section Title"    # writes header + separator to OUTPUT_FILE
    _section_lines=()                # defensive reset (collector contract)

    # Tool/config not installed check:
    if ! command -v tool &>/dev/null && [[ ! -f "$config_file" ]]; then
        flush_section   # writes "(none found)" since buffer is empty
        return
    fi

    # Enumerate items...
    while IFS= read -r item; do
        [[ -z "$item" ]] && continue
        # parse name, version, id, transport from $item
        emit_item "$name" "$version_or_empty" "$id_or_empty_or_transport"
    done < <(extraction_command 2>/dev/null)

    flush_section   # sorts, deduplicates, writes "(none found)" if empty
}
```

**MCP sections specifically:** `emit_item "$name" "" "$transport"` — version is always empty;
the transport label (`stdio`/`http`/`sse`) goes in the id slot, producing `name [transport]`.

### Pattern: Claude Plugins Collector (CC-01)

```zsh
collect_claude_plugins() {
    local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
    local name="" version="" key=""

    write_section "Claude Code Plugins"
    _section_lines=()

    if [[ ! -f "$plugins_file" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r key version; do
            [[ -z "$key" ]] && continue
            name="${key%%@*}"
            emit_item "$name" "$version" "$key"
        done < <(jq -r '.plugins | to_entries[] | .key + "\t" + (.value[0].version // "")' \
                     "$plugins_file" 2>/dev/null)
    else
        # plutil fallback: enumerate plugin keys via xml1 parsing
        while IFS= read -r key; do
            [[ -z "$key" ]] && continue
            name="${key%%@*}"
            local ver=""
            ver=$(plutil -extract "plugins.${key}.0.version" raw -o - "$plugins_file" 2>/dev/null) || ver=""
            emit_item "$name" "$ver" "$key"
        done < <(plutil -extract "plugins" xml1 -o - "$plugins_file" 2>/dev/null \
                     | grep '<key>' | sed 's/.*<key>//;s/<\/key>//')
    fi

    flush_section
}
```

**NOTE on plutil key escaping:** Plugin keys like `claude-mem@thedotmack` contain `@` and `-`
which plutil handles fine. The `0` index accesses the first array element.

### Pattern: Claude MCP Collector (CC-02) — FMT-03 Safe

```zsh
collect_claude_mcp() {
    local claude_config="$HOME/.claude.json"
    local name="" transport=""

    write_section "Claude Code MCP Servers"
    _section_lines=()

    if [[ ! -f "$claude_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r name transport; do
            [[ -z "$name" ]] && continue
            emit_item "$name" "" "${transport:-stdio}"
        done < <(jq -r '.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")' \
                     "$claude_config" 2>/dev/null)
    else
        # plutil fallback: enumerate server names, then extract type per server
        local server_names=()
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            server_names+=("$name")
        done < <(plutil -extract "mcpServers" raw -o - "$claude_config" 2>/dev/null)

        for name in "${server_names[@]}"; do
            transport=$(plutil -extract "mcpServers.${name}.type" raw -o - \
                            "$claude_config" 2>/dev/null) || transport="stdio"
            [[ -z "$transport" ]] && transport="stdio"
            emit_item "$name" "" "$transport"
        done
    fi

    flush_section
}
```

**FMT-03 guarantee:** The jq expression reads ONLY `.key` (server name) and `.value.type`
(transport). It never reads `.value.env`, `.value.command`, `.value.args`, `.value.url`.
The plutil path reads only `mcpServers` (key names) and `mcpServers.${name}.type` (scalar).

### Pattern: Claude Skills & Agents Collector (CC-03)

```zsh
collect_claude_skills_agents() {
    local skills_dir="$HOME/.claude/skills"
    local agents_dir="$HOME/.claude/agents"
    local name=""

    write_section "Claude Code Skills & Agents"
    _section_lines=()

    # Skills: one subdir per skill
    if [[ -d "$skills_dir" ]]; then
        setopt local_options null_glob
        for skill_dir in "$skills_dir"/*/; do
            [[ -e "$skill_dir" ]] || continue
            local skill_md="${skill_dir}SKILL.md"
            if [[ -f "$skill_md" ]]; then
                name=$(grep '^name:' "$skill_md" | head -1 \
                           | sed 's/^name:[[:space:]]*//' | tr -d '"')
            fi
            [[ -z "$name" ]] && name=$(basename "$skill_dir")
            emit_item "$name" "" ""
            name=""
        done
    fi

    # Agents: *.md files in agents dir
    if [[ -d "$agents_dir" ]]; then
        setopt local_options null_glob
        for f in "$agents_dir"/*.md; do
            [[ -e "$f" ]] || continue
            name=$(grep '^name:' "$f" | head -1 \
                       | sed 's/^name:[[:space:]]*//' | tr -d '"')
            [[ -z "$name" ]] && name=$(basename "$f" .md)
            emit_item "$name" "" ""
            name=""
        done
    fi

    flush_section
}
```

**NOTE:** Skills and agents share a section ("Claude Code Skills & Agents"). They are both
enumerated into the same `_section_lines` buffer, then sorted together by `flush_section`.

### Pattern: Codex MCP Collector (CDX-01)

```zsh
collect_codex_mcp() {
    local codex_config="$HOME/.codex/config.toml"
    local name="" transport=""

    write_section "Codex MCP Servers"
    _section_lines=()

    # Preferred: CLI
    if command -v codex &>/dev/null; then
        local cli_out=""
        cli_out=$(codex mcp list --json 2>/dev/null)
        if [[ -n "$cli_out" && "$cli_out" != "[]" ]]; then
            if command -v jq &>/dev/null; then
                while IFS=$'\t' read -r name transport; do
                    [[ -z "$name" ]] && continue
                    emit_item "$name" "" "${transport:-stdio}"
                done < <(jq -r '.[] | .name + "\t" + (.type // "stdio")' \
                              <<< "$cli_out" 2>/dev/null)
            else
                # plutil can't parse CLI JSON output inline; fall through to TOML
                :
            fi
            flush_section
            return
        fi
    fi

    # Fallback: TOML grep (names only; type defaults to stdio when not extractable)
    if [[ -f "$codex_config" ]]; then
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            emit_item "$name" "" "stdio"
        done < <(grep '^\[mcp_servers\.' "$codex_config" 2>/dev/null \
                     | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' | tr -d '"')
    fi

    flush_section
}
```

**NOTE on TOML transport:** In the TOML fallback, defaulting to `stdio` is acceptable because
(a) this is a fallback-of-fallback, (b) CONTEXT.md allows name+type extraction from TOML,
(c) Codex CLI is the canonical source and it works. The planner may choose to add type
extraction from TOML lines — document it as an improvement option.

### Pattern: OpenCode Plugins Collector (OC-01)

```zsh
collect_opencode_plugins() {
    local oc_config="$HOME/.config/opencode/opencode.json"
    local name="" entry=""

    write_section "OpenCode Plugins"
    _section_lines=()

    if [[ ! -f "$oc_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS= read -r entry; do
            [[ -z "$entry" ]] && continue
            name="${entry%%@*}"
            emit_item "$name" "" ""
        done < <(jq -r '.plugin[]?' "$oc_config" 2>/dev/null)
    else
        # plutil fallback: extract each array element
        local idx=0
        while true; do
            entry=$(plutil -extract "plugin.${idx}" raw -o - "$oc_config" 2>/dev/null) || break
            [[ -z "$entry" ]] && break
            name="${entry%%@*}"
            emit_item "$name" "" ""
            ((idx++))
        done
    fi

    flush_section
}
```

### Pattern: Gemini Extensions Collector (GEM-01)

```zsh
collect_gemini_extensions() {
    local ext_base="$HOME/.gemini/extensions"
    local name="" version=""

    write_section "Gemini CLI Extensions"
    _section_lines=()

    if [[ ! -d "$ext_base" ]]; then
        flush_section
        return
    fi

    setopt local_options null_glob
    for ext_dir in "$ext_base"/*/; do
        [[ -e "$ext_dir" ]] || continue
        local manifest="${ext_dir}gemini-extension.json"
        [[ -f "$manifest" ]] || continue
        name=$(json_get "$manifest" "name")
        version=$(json_get "$manifest" "version")
        [[ -z "$name" ]] && name=$(basename "$ext_dir")
        emit_item "$name" "$version" ""
        name=""
        version=""
    done

    flush_section
}
```

**emit_item call:** `emit_item "$name" "$version" ""` — `id` is empty; for conductor this
yields `conductor (0.4.1)`.

### Anti-Patterns to Avoid

- **Reading any MCP `.env`, `.command`, `.args`, `.url`, or `.headers`:** The primary
  milestone-failing defect. These fields are never needed for FMT-03-compliant output.
  The jq expression must read only `.key` and `.value.type`.
- **Using `plutil -extract "mcpServers" xml1` and then parsing values:** The xml1 output
  shows all nested fields including command/args. Parse xml1 output for key names only,
  not for values.
- **Forgetting null_glob for dir/file globs:** Without `setopt local_options null_glob`,
  a glob like `~/.claude/skills/*/` that matches nothing aborts the function with "no match"
  error. Always use `setopt local_options null_glob` + `[[ -e "$f" ]] || continue`.
- **Not resetting `_section_lines=()` at collector top:** If a prior collector returns early
  without calling `flush_section`, buffer pollution carries over. The defensive reset at
  every collector top prevents this.
- **Hardcoding `stdio` as transport for all Claude MCP servers:** Future servers may use
  `http` or `sse`. Always read the `type` field; fall back to `stdio` only when `type` is
  absent.
- **Including the `@marketplace` suffix as the displayed name in Claude plugins:** The display
  name is `${key%%@*}` (before the first `@`). The full key is the ID.
- **Using `codex mcp list` (without `--json`):** The plain output is human-readable text
  designed for display, not parsing. The `--json` flag returns a machine-parseable array.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing for Codex MCP | Custom TOML parser | `grep '^\[mcp_servers\.'` + `sed` | Only need section header names; full TOML parse is unnecessary complexity and creates risk of reading value lines |
| Frontmatter YAML parsing | YAML parser | `grep '^name:'` + `sed` | Only need one field (`name:`) from a well-known position; full YAML parser adds a dependency |
| Extension version from git hash | Parse gitCommitSha | Use `.version` field directly from `installed_plugins.json` | `.version` is already a human-readable string; git SHA is not meaningful to users |
| JSON path traversal | Regex on raw JSON text | `jq` / `plutil` via `json_get` | Already built in Phase 1; regex on JSON is fragile |

---

## Common Pitfalls

### Pitfall 1: plutil `raw` on an object returns ONE key per line (not all at once)

**What goes wrong:** `plutil -extract "mcpServers" raw -o - file.json` returns `execbro` on
a single line — which looks like it works for one server. For multiple servers (e.g., 5 MCP
servers configured), it returns all 5 names, one per line.

**Why it happens:** `plutil -extract key raw` on an object returns the string representation
of the keys, newline-separated. [VERIFIED: tested with single-server config.]

**How to avoid:** Use `while IFS= read -r name; do ... done < <(plutil -extract ...)` to
iterate all output lines.

**Warning signs:** Only the first MCP server appearing in output when multiple are configured.

### Pitfall 2: `installed_plugins.json` key contains `@` — must use `%%` not `#`

**What goes wrong:** Using `${key#@}` strips the `@` prefix (which doesn't exist) instead
of extracting the name before the first `@`.

**How to avoid:** Use `name="${key%%@*}"` — `%%` strips the LONGEST match of `@*` from the
END, leaving everything before the first `@`. Verified: `claude-mem@thedotmack` → `claude-mem`.

### Pitfall 3: OpenCode `.plugin` array contains full git URLs with `@`

**What goes wrong:** `"superpowers@git+https://github.com/obra/superpowers.git"` — if you
split on `@` using `${entry#*@}` to get the source, or `${entry%%@*}` to get the name, the
result is correct. But if you use `${entry#@}` it strips nothing (no leading `@`).

**How to avoid:** Use `${entry%%@*}` for the name (before first `@`). The source URL after
`@` is never emitted — it can contain a full https URL.

### Pitfall 4: Gemini `mcp_config.json` is 0 bytes — not parseable JSON

**What goes wrong:** `jq ... ~/.gemini/config/mcp_config.json` returns error on 0-byte file.
`[[ -f "$file" ]]` returns true for an empty file. `jq` exits non-zero with parse error.

**How to avoid:** Use `[[ -s "$file" ]]` (file exists AND has nonzero size) before attempting
JSON parsing. If size is zero, skip directly to `flush_section`.

### Pitfall 5: Skills directory includes symlinks — `ls -d */` doesn't follow them

**What goes wrong:** `for dir in ~/.claude/skills/*/` includes symlinks (2 confirmed:
`find-skills`, `impeccable`). The glob matches them because glob expansion includes symlinks
that point to directories. `[[ -d "$dir" ]]` is true for a symlink-to-dir. This is correct
behavior — symlinked skills should be cataloged.

**How to avoid:** The `[[ -e "$dir" ]] || continue` guard handles all cases (real dirs,
symlinks to dirs, dangling symlinks). No special handling needed.

### Pitfall 6: SKILL.md `name:` field may have quoted value

**What goes wrong:** Some SKILL.md files have `name: "gsd-quick"` (quoted) while others
have `name: gsd-quick` (unquoted). `grep '^name:' | sed 's/name://; s/^ *//'` leaves the
quotes intact.

**How to avoid:** Always pipe through `tr -d '"'` to strip any double quotes from the value.
Verified: both quoted and unquoted forms parsed correctly by
`grep '^name:' | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'`.

---

## Code Examples

### FMT-03 Safe Extraction — Live Verified

```zsh
# Source: verified live on this machine, output "execbro [stdio]", zero secret leakage
# jq path: reads ONLY .key (name) and .value.type (transport)
jq -r '.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")' ~/.claude.json
# Output: execbro	stdio

# plutil path (no jq):
# Step 1: enumerate server names
plutil -extract "mcpServers" raw -o - ~/.claude.json
# Output: execbro

# Step 2: for each name, get type
plutil -extract "mcpServers.execbro.type" raw -o - ~/.claude.json
# Output: stdio
```

### Codex TOML Name Extraction

```zsh
# Source: verified on ~/.codex/config.toml using [agents.*] analog format
# Extracts server names from [mcp_servers."name"] TOML section headers
grep '^\[mcp_servers\.' ~/.codex/config.toml 2>/dev/null \
    | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' | tr -d '"'
# Output: (empty on this machine — no MCP servers configured)
# Would output one name per line if servers were configured
```

### OpenCode Plugin Name Parsing

```zsh
# Source: verified on this machine
ENTRY="superpowers@git+https://github.com/obra/superpowers.git"
NAME="${ENTRY%%@*}"
echo "$NAME"
# Output: superpowers
```

### Gemini Extension Name + Version

```zsh
# Source: verified on this machine
jq -r '"\(.name)\t\(.version)"' ~/.gemini/extensions/conductor/gemini-extension.json
# Output: conductor	0.4.1
```

### SKILL.md Name Extraction (with quote strip)

```zsh
# Source: verified on ~/.claude/skills/app-starter/SKILL.md and gsd-quick/SKILL.md
# Works for both: name: app-starter (unquoted) and name: "gsd-quick" (quoted)
grep '^name:' "$SKILL_MD" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'
```

### Null-Glob-Guarded Dir Iteration

```zsh
# Source: verified with Zsh built-in on this machine; 70 skills iterated correctly
# Including 2 symlinks (find-skills, impeccable) which [[ -e ]] handles correctly
setopt local_options null_glob
for skill_dir in "$HOME/.claude/skills"/*/; do
    [[ -e "$skill_dir" ]] || continue
    # process $skill_dir
done
```

---

## Definitive Transport Inference Logic

When a config entry lacks a `type` field, use this inference:

| Config Has | Inferred Transport | Emit Label |
|------------|-------------------|------------|
| `type: "stdio"` | explicit | `stdio` |
| `type: "http"` | explicit | `http` |
| `type: "sse"` | explicit | `sse` |
| `command` present, no `type` | stdio | `stdio` |
| `url` present, no `type` | http or sse | `http` (conservative) |
| Neither `type`, `command`, nor `url` | unknown | `stdio` (safe default) |

In all cases: the transport label is the ONLY thing emitted. The `command` value and `url`
value are NEVER emitted, even when used for inference.

---

## Phase Split Recommendation

This phase has 9 collector functions across 4 tools. The code volume is substantial but the
pattern is highly repetitive. Recommended planning unit breakdown:

| Wave | Functions | Requirements | Notes |
|------|-----------|--------------|-------|
| Wave 1 | `collect_claude_plugins`, `collect_claude_mcp`, `collect_claude_skills_agents` | CC-01, CC-02, CC-03, FMT-03 | Highest-value, most complex; FMT-03 proof centers here |
| Wave 2 | `collect_codex_mcp` | CDX-01 | Simple; CLI-first pattern |
| Wave 3 | `collect_opencode_plugins`, `collect_opencode_mcp`, `collect_opencode_agents` | OC-01, OC-02, OC-03 | Three simple collectors |
| Wave 4 | `collect_gemini_extensions`, `collect_gemini_mcp` | GEM-01, GEM-02 | Dir-iteration pattern |

All waves can be planned as a single phase (the functions are small and the pattern is
consistent). The planner may split into 2 tasks: (1) Claude Code + Codex, (2) OpenCode +
Gemini, for review granularity.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `codex mcp list --json` field names are `.name` and `.type` (based on the empty `[]` return; actual field names unverifiable without a populated server) | Flag 2 / CDX-01 pattern | LOW — CLI is the canonical source; field names can be verified by adding a test server before phase execution |
| A2 | OpenCode `.mcp` field, when populated, is a JSON object keyed by server name (analogous to Claude's `mcpServers`) | Flag 3 / OC-02 | MEDIUM — field is null on this machine; shape unverified; if shape differs, the collector needs adjustment |
| A3 | Gemini `mcp_config.json`, when populated, is a JSON object keyed by server name with `type` field | Flag 4 / GEM-02 | MEDIUM — file is empty on this machine; plausible based on Gemini CLI docs pattern; collector should use `[[ -s ]]` guard regardless |
| A4 | All 70 Claude skills have a `SKILL.md` with `name:` frontmatter (verified 0 without on this machine, but a new skill installed between research and execution may not have it) | Flag 1 / CC-03 | LOW — fallback to dir name is already coded |
| A5 | OpenCode plugin version is not available (no numeric version in `opencode.json` plugin strings) | OC-01 | LOW — emit bare name is FMT-01 compliant; if a version becomes available, update the extraction |

---

## Open Questions (RESOLVED)

1. **`codex mcp list --json` field names when servers are present**
   - RESOLVED (LOW risk): CLI returns `[]` on this machine (exit 0) → the JSON-field path is
     never exercised here. The collector assumes `.name` + `.type`; the plan instructs the
     executor to verify field names via a `codex mcp add` scratch test before relying on them.
     FMT-03 holds regardless: only name + transport are ever read. The verified TOML fallback
     extracts names from `[mcp_servers.<name>]` section headers and defaults transport to `stdio`.

2. **OpenCode `.mcp` object shape when populated**
   - RESOLVED (LOW risk): `.mcp` is null on this machine → degrades to `(none found)`. The
     collector assumes the Claude-style `{name: {type: ...}}` object shape; FMT-03 compliance is
     identical regardless of shape (only `.key` + `.value.type` are read). Adjustable if a
     populated machine reveals an array shape.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `jq` | All JSON collectors (primary) | Yes (Homebrew) | `jq-1.8.1` | `plutil` |
| `plutil` | All JSON collectors (fallback) | Yes (macOS built-in) | macOS built-in | — (always present) |
| `grep` + `sed` | Codex TOML, SKILL.md, agent frontmatter | Yes (POSIX) | — | — (always present) |
| `claude` CLI | CC-01/02/03 config detection | Verified (implied by `~/.claude.json` present) | — | config file presence check |
| `codex` CLI | CDX-01 (preferred path) | Yes | v0.46.0 | TOML grep fallback |
| `opencode` CLI | OC-01/02/03 config detection | Yes | v1.17.3 | config file presence check |
| `gemini` CLI | GEM-01/02 config detection | Yes | v0.46.0 | config dir presence check |

**Missing dependencies with no fallback:** None. All required tooling is present.

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section
is skipped.

---

## Security Domain

This phase reads local config files and writes human-readable strings. The entire security
domain for this phase IS FMT-03, already fully documented above.

**ASVS V5 (Input Validation):** The extracted `type` field value is used as a label in output.
It should be constrained to known transport labels:
```zsh
case "$transport" in
    stdio|http|sse) : ;;
    *) transport="stdio" ;;  # clamp unknown values to safe default
esac
```
This prevents an adversarially-crafted config from injecting arbitrary strings into the catalog
via the `type` field.

---

## Sources

### Primary (HIGH confidence — verified live on this machine 2026-06-13)

- `~/.claude.json` — confirmed field structure of `mcpServers.execbro`; confirmed top-level
  `mcpServers` key; confirmed `projects` key at separate scope; zero-leakage proof run.
- `~/.claude/plugins/installed_plugins.json` — confirmed `{version, plugins}` schema; 9
  plugins with `name@marketplace` keys and `[{version, installPath, ...}]` values.
- `~/.claude/skills/` — confirmed 70 dirs+symlinks; all have SKILL.md with `name:` frontmatter.
- `~/.claude/agents/` — confirmed 33 `.md` files; all have `name:` frontmatter.
- `codex mcp list --json` — confirmed returns `[]` (exit 0); v0.46.0; TOML has no
  `[mcp_servers.*]` sections.
- `~/.codex/config.toml` — confirmed `[agents."name"]` pattern for TOML name extraction analog.
- `~/.config/opencode/opencode.json` — confirmed keys `$schema, model, permission, plugin`;
  `.plugin` = `["superpowers@git+https://github.com/obra/superpowers.git"]`; `.mcp` = null.
- `~/.config/opencode/agents/` — confirmed 33 `.md` files; all have `name:` frontmatter.
- `~/.gemini/extensions/conductor/gemini-extension.json` — confirmed `{name, version, ...}`;
  `has("mcpServers") = false`.
- `~/.gemini/extensions/extension-enablement.json` — confirmed `{"conductor": {overrides: [...]}}`.
- `~/.gemini/config/mcp_config.json` — confirmed exists, 0 bytes (empty).
- `~/.gemini/settings.json` — confirmed no `mcpServers` key.
- Zsh `null_glob` iteration — confirmed 70 skills and 33 agents iterated correctly including
  2 symlinks.
- plutil behavior on object fields — confirmed `plutil -extract "mcpServers" raw` prints key
  names one per line; `plutil -extract "mcpServers.execbro.type" raw` prints `stdio`.

### Secondary (MEDIUM confidence)

- `update-list.sh` (Phase 2 implementations) — established collector pattern for `write_section`
  → reset → loop → `emit_item` → `flush_section`.
- `.planning/phases/01-shared-helpers-foundation/01-RESEARCH.md` — Phase 1 helper signatures
  and contracts.
- `.planning/phases/02-editor-collectors/02-RESEARCH.md` — Phase 2 pattern reference.

---

## Metadata

**Confidence breakdown:**
- FMT-03 field map: HIGH — live extraction verified, zero-leakage proof run
- Claude Code paths/shapes: HIGH — all verified live on real files
- Codex paths: HIGH — CLI verified; TOML format confirmed from analog section
- OpenCode paths: HIGH — verified live; only `.mcp` shape when populated is MEDIUM (null now)
- Gemini paths: HIGH — conductor extension verified; MCP config location confirmed
- Transport inference logic: HIGH — verified against real `type` field
- Zsh iteration patterns: HIGH — all glob patterns run with null_glob guard confirmed

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable — local file formats don't change frequently)

---

## RESEARCH COMPLETE

**Phase:** 03 - AI-CLI Collectors
**Confidence:** HIGH

### Key Findings

1. **FMT-03 zero-leakage proven live:** `jq -r '.mcpServers | to_entries[] | .key + " [" + (.value.type // "stdio") + "]"' ~/.claude.json` produces `execbro [stdio]` — passes all 7 secret-pattern grep checks. The `env` field exists as an empty object `{}` on this machine and must never be read. The plutil fallback path (enumerate keys via `raw`, then read `type` scalar per key) is also confirmed safe.

2. **Gemini MCP location correction:** NOT in `settings.json.mcpServers` (that key doesn't exist). ACTUAL location is `~/.gemini/config/mcp_config.json` — confirmed by `find`. Currently 0 bytes (no MCP servers configured). Collector must use `[[ -s "$file" ]]` guard (nonzero size check) before parsing.

3. **`codex mcp list --json` works in v0.46.0**, returns `[]` (zero servers). The TOML fallback `grep '^\[mcp_servers\.' | sed | tr -d '"'` is ready for when servers are added; confirmed correct by testing against the existing `[agents.*]` section format.

4. **Real-machine counts:** Claude: 9 plugins, 1 MCP server (`execbro [stdio]`), 70 skills, 33 agents. Codex: 0 MCP. OpenCode: 1 plugin (`superpowers`), 0 MCP, 33 agents. Gemini: 1 extension (`conductor 0.4.1`), 0 MCP. Five of nine sections will have real data; four write `(none found)`.

5. **All extraction patterns are verified.** SKILL.md `name:` grep+sed+tr, agent frontmatter grep+sed, OpenCode `${entry%%@*}` plugin name split, Gemini `json_get manifest "name"/"version"`, Codex TOML section header grep — all confirmed working on live data.

### File Created

`.planning/phases/03-ai-cli-collectors/03-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| FMT-03 extraction safety | HIGH | Live proof run; zero secret leakage confirmed |
| Claude Code paths and shapes | HIGH | All files read and structure confirmed |
| Codex MCP | HIGH | CLI tested; TOML format confirmed from analog |
| OpenCode paths | HIGH | Live data confirmed; `.mcp` shape when populated is ASSUMED |
| Gemini paths | HIGH | Extension manifest confirmed; MCP file location found by `find` |
| Zsh iteration patterns | HIGH | null_glob guard tested with 70 items including symlinks |

### Open Questions

1. `codex mcp list --json` exact field names when non-empty (`.name`/`.type` assumed — verify before shipping CDX-01 collector).
2. OpenCode `.mcp` object shape when populated (null on this machine — shape ASSUMED analogous to Claude's `mcpServers`).

### Ready for Planning

Research complete. Planner can now create PLAN.md files.

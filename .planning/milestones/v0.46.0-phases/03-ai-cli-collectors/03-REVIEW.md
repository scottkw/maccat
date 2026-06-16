---
phase: 03-ai-cli-collectors
reviewed: 2026-06-13T18:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: fixed
---

# Phase 3: AI-CLI Collectors — Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 1 (`update-list.sh`, lines 764–1223 — the 9 new collector functions)
**Status:** issues_found

---

## Summary

Nine new Zsh collector functions were added covering Claude Code (plugins, MCP servers,
skills/agents), Codex (MCP), OpenCode (plugins, MCP, agents), and Gemini CLI (extensions,
MCP). The milestone-critical FMT-03 secret-exclusion boundary is correctly enforced across
all four MCP collectors and both code paths (jq and plutil): every jq expression reads only
`.key` and `.value.type`; every plutil path reads only key-name enumeration and the `.type`
scalar; no collector touches `.env`, `.command`, `.args`, `.url`, or `.headers`. Transport
labels are consistently clamped to a `stdio|http|sse` whitelist. The `-s` guard in
`collect_gemini_mcp` is correct and necessary. No Critical findings.

Four Warnings and three Info items were found. The most consequential is a logic bug in
`collect_codex_mcp` that silently swallows Codex MCP server data on any machine that has
Codex installed and populated but does not have jq. A second Warning covers a latent path
in `collect_opencode_plugins` that could emit raw filesystem paths or bare URLs when a
plugin entry lacks an `@` separator. The remaining Warnings are a duplicate plutil call
and a `local` placement convention violation.

---

## Warnings

### WR-01: `collect_codex_mcp` — CLI path with populated output but no jq silently emits `(none found)` and never tries TOML fallback

**File:** `update-list.sh:937-951`

**Issue:** When `codex mcp list --json` returns a non-empty, non-`[]` result, the outer `if`
block is entered (line 937). Inside, the jq sub-block is guarded by `if command -v jq &>/dev/null`.
If jq is absent, that inner block is skipped — but `flush_section; return` at lines 949-950 still
execute unconditionally, writing `(none found)` to the catalog and returning without ever
reaching the TOML fallback. On any machine where Codex is installed with real MCP servers
configured but jq is not installed, the catalog will silently misreport `(none found)` for
"Codex MCP Servers". The comment on the skipped else ("plutil can't parse CLI JSON output
inline; fall through to TOML") documents the intent but the code does the opposite.

```zsh
# CURRENT (buggy): flush_section;return outside the jq guard exits before TOML fallback
if [[ -n "$cli_out" && "$cli_out" != "[]" ]]; then
    if command -v jq &>/dev/null; then
        while ... done < <(jq -r ...)
    fi
    flush_section   # ← runs even when jq was absent, locking out TOML
    return
fi

# FIX: only flush+return when jq was present (data was processed); otherwise fall through
if [[ -n "$cli_out" && "$cli_out" != "[]" ]]; then
    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r name transport; do
            [[ -z "$name" ]] && continue
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "${transport:-stdio}"
        done < <(jq -r '.[] | .name + "\t" + (.type // "stdio")' \
                      <<< "$cli_out" 2>/dev/null)
        flush_section
        return
    fi
    # jq absent: fall through to TOML fallback (comment now matches code)
fi
```

---

### WR-02: `collect_opencode_plugins` — plugin entry without `@` separator emits the entire raw string (could include filesystem paths or bare URLs) as the display name

**File:** `update-list.sh:991-1005`

**Issue:** `name="${entry%%@*}"` strips everything from the first `@` onward. When the
`entry` string contains no `@`, the entire string is used as the name. The research
documents the `name@source` format, but the field is arbitrary user config. A local
plugin specified as `/Users/ken/plugins/myplugin` or a raw URL
`https://example.com/plugin.git` would emit the full path or URL as the plugin name.
Paths expose machine-specific directory structure. This is not a credential but it
diverges from the "name only" intent. A bare `name` guard is needed:

```zsh
while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    name="${entry%%@*}"
    # If the entire entry has no @, we have no name — skip or use the whole string
    # but warn rather than silently emitting a raw path/URL.
    [[ -z "$name" ]] && continue   # entry was "@something" — no usable name
    emit_item "$name" "" ""
done < <(jq -r '.plugin[]?' "$oc_config" 2>/dev/null)
```

The more important fix is to add a warning when the name equals the full entry (i.e., no
`@` was found) so the user knows the plugin string format was unexpected:

```zsh
while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    name="${entry%%@*}"
    if [[ "$name" == "$entry" ]]; then
        echo "  WARNING: OpenCode plugin entry has no '@' separator: ${entry}" >&2
    fi
    [[ -z "$name" ]] && continue
    emit_item "$name" "" ""
done < <(jq -r '.plugin[]?' "$oc_config" 2>/dev/null)
```

---

### WR-03: `collect_opencode_mcp` plutil fallback calls `plutil -extract "mcp" raw` twice, with the first call used only as a null sentinel but actually enumerating keys — wasted call and fragile logic

**File:** `update-list.sh:1055-1066`

**Issue:** Lines 1055-1059 call `plutil -extract "mcp" raw -o - "$oc_config"` to check
whether `.mcp` is non-null. If successful and non-empty, lines 1063-1066 call the exact
same command again to enumerate the server names for the loop. Besides the redundant
process spawning, the sentinel check has a subtle fragility: if `.mcp` is a populated
object, `plutil raw` outputs the key names concatenated (confirmed by research on the
`mcpServers` analog). `mcp_raw` will contain those names, making the null check pass
correctly. But if `.mcp` is a non-null JSON primitive (e.g., `"mcp": "disabled"` —
malformed config but plausible), `plutil raw` returns the string value, `mcp_raw` is
non-empty, the null-check passes, and the second `plutil raw` call at line 1066 outputs
the same string value, which the `while IFS= read -r name` loop interprets as a server
name string. `plutil -extract "mcp.<that-value>.type"` will then exit 1 (miss), set
`transport="stdio"`, and `emit_item` will emit the primitive value as a server name.
Incorrect output, not a secret leak.

Consolidate into one call:

```zsh
# plutil fallback: enumerate server names; empty output = no servers (null or absent .mcp)
local server_names=()
while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    server_names+=("$name")
done < <(plutil -extract "mcp" raw -o - "$oc_config" 2>/dev/null)

if [[ ${#server_names[@]} -eq 0 ]]; then
    flush_section
    return
fi

for name in "${server_names[@]}"; do
    transport=$(plutil -extract "mcp.${name}.type" raw -o - \
                    "$oc_config" 2>/dev/null) || transport="stdio"
    [[ -z "$transport" ]] && transport="stdio"
    case "$transport" in
        stdio|http|sse) : ;;
        *) transport="stdio" ;;
    esac
    emit_item "$name" "" "$transport"
done
```

---

### WR-04: `collect_claude_skills_agents` — `name` is not reset before the SKILL.md `if` block in the skills loop; if SKILL.md exists but `grep` returns empty, the previous iteration's `name` value bleeds into the basename fallback

**File:** `update-list.sh:884-891`

**Issue:** The skills loop structure is:

```zsh
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
```

The `name=""` reset at the end of each iteration prevents cross-iteration bleed for the
common path. However, `name=""` is reached only if `emit_item` is reached. If the loop
is entered but somehow returns early (e.g., a future guard added before `emit_item`), the
reset is skipped. More concretely: if `SKILL.md` exists and `grep '^name:'` returns empty
output (a SKILL.md with no `name:` line), `name` becomes `""`, the basename fallback fires
correctly. This specific case is safe.

The latent bug is that `name` is reset at the END of the iteration rather than the BEGINNING.
The current code works only because every iteration unconditionally reaches `name=""`. The
established convention for the agents loop (and Phase 2 collectors) is to reset at the end,
which is consistent here. However, the `if [[ -f "$skill_md" ]]` conditional — without an
`else name=""` branch — means if `SKILL.md` doesn't exist (unlikely per research, but
possible on a freshly symlinked skill), `name` is not assigned inside the block. The
fallback `[[ -z "$name" ]] && name=$(basename "$skill_dir")` only fires if `name` is
already empty from the previous iteration's `name=""` reset. This is correct for the
current code flow.

Add `name=""` at the START of each skills iteration to be unambiguously safe:

```zsh
for skill_dir in "$skills_dir"/*/; do
    [[ -e "$skill_dir" ]] || continue
    name=""                                   # reset at start, not only at end
    local skill_md="${skill_dir}SKILL.md"
    if [[ -f "$skill_md" ]]; then
        name=$(grep '^name:' "$skill_md" | head -1 \
                   | sed 's/^name:[[:space:]]*//' | tr -d '"')
    fi
    [[ -z "$name" ]] && name=$(basename "$skill_dir")
    emit_item "$name" "" ""
    name=""                                   # keep end reset for symmetry
done
```

---

## Info

### IN-01: `collect_claude_skills_agents` — `setopt local_options null_glob` called twice in the same function; second call is redundant

**File:** `update-list.sh:881, 897`

**Issue:** `setopt local_options null_glob` is set once at line 881 (inside the skills `if`
block) and again at line 897 (inside the agents `if` block). Once set with `local_options`,
`null_glob` is active for the rest of the function's execution — the second call has no
effect. The duplication is harmless but could mislead a reader into thinking there is an
option scoping boundary between the two blocks.

**Fix:** Remove the second `setopt local_options null_glob` at line 897, or hoist a single
call above both loops:

```zsh
collect_claude_skills_agents() {
    local skills_dir="$HOME/.claude/skills"
    local agents_dir="$HOME/.claude/agents"
    local name=""

    write_section "Claude Code Skills & Agents"
    _section_lines=()

    setopt local_options null_glob   # one call covers both loops below

    if [[ -d "$skills_dir" ]]; then
        for skill_dir in "$skills_dir"/*/; do
            ...
        done
    fi

    if [[ -d "$agents_dir" ]]; then
        for f in "$agents_dir"/*.md; do
            ...
        done
    fi

    flush_section
}
```

---

### IN-02: `collect_claude_plugins` plutil fallback — `local ver=""` declared inside a `while` loop body rather than in the function preamble

**File:** `update-list.sh:797`

**Issue:** In the plutil fallback path of `collect_claude_plugins`, `local ver=""` is
declared inside the `while IFS= read -r key; do` loop. In Zsh, `local` inside a loop
creates a function-scoped variable on the first iteration; subsequent iterations just
re-assign it. This is technically correct but violates the project convention (all local
variables declared in the function preamble alongside `local name="" version="" key=""`).
The `ver` variable is also not needed at function scope — it could simply be `ver=""` on
re-assignment.

**Fix:** Move to the function preamble and rename to avoid confusion with the function-level
`version`:

```zsh
collect_claude_plugins() {
    local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
    local name="" version="" key="" ver=""   # add ver="" here
    ...
    # plutil fallback: enumerate plugin keys via xml1 parsing
    while IFS= read -r key; do
        [[ -z "$key" ]] && continue
        name="${key%%@*}"
        ver=""                               # explicit reset (not re-local)
        ver=$(plutil -extract "plugins.${key}.0.version" raw -o - "$plugins_file" 2>/dev/null) || ver=""
        emit_item "$name" "$ver" "$key"
    done < <(plutil -extract "plugins" xml1 -o - "$plugins_file" 2>/dev/null \
                 | grep '<key>' | sed 's/.*<key>//;s/<\/key>//')
```

---

### IN-03: `collect_codex_mcp` TOML fallback — TOML section headers with inline comments (`[mcp_servers.foo] # comment`) would be silently skipped

**File:** `update-list.sh:961-962`

**Issue:** The sed pattern `s/^\[mcp_servers\.\(.*\)\]$/\1/` anchors on `\]$` — the `]`
must be the last character on the line. Valid TOML allows inline comments after the closing
bracket: `[mcp_servers."my-tool"] # description`. Such a line passes the `grep
'^\[mcp_servers\.'` filter but the sed substitution fails because `\]$` does not match
(the line ends with `# description`). The server name is silently dropped.

In practice, TOML editors and automated config writers rarely add comments to section
headers. However, if a user manually annotates their `config.toml` with comments on section
headers, those servers would be invisible to the TOML fallback.

**Fix:** Strip any trailing comment and whitespace before the sed match, or adjust the
pattern to tolerate trailing non-`]` content:

```zsh
done < <(grep '^\[mcp_servers\.' "$codex_config" 2>/dev/null \
             | sed 's/[[:space:]]*#.*$//' \        # strip trailing # comments first
             | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' \
             | tr -d '"')
```

---

## FMT-03 Secret Leakage Verdict

All four MCP collectors (Claude, Codex, OpenCode, Gemini) are clean. Each jq expression
reads only `.key` and `.value.type` (or `.name` and `.type` for the Codex CLI array).
Each plutil path reads only key-name enumeration and the scalar `type` field. No collector
references `.env`, `.command`, `.args`, `.url`, or `.headers` in any code path. The Codex
TOML grep reads only `[mcp_servers.*]` section header lines — no value lines are touched.
Transport labels are clamped to `stdio|http|sse` in both paths of every MCP collector,
preventing attacker-controlled `type` values from injecting arbitrary text. The `-s` guard
in `collect_gemini_mcp` correctly rejects the 0-byte `mcp_config.json`.

**FMT-03 status: PASS. No secret-leakage paths found.**

---

## Severity Summary

| ID | Severity | Function | Description |
|----|----------|----------|-------------|
| WR-01 | WARNING | `collect_codex_mcp` | CLI path with populated JSON but no jq silently discards data, never falls through to TOML fallback |
| WR-02 | WARNING | `collect_opencode_plugins` | Plugin entry without `@` emits entire raw string (path or URL) as name |
| WR-03 | WARNING | `collect_opencode_mcp` | Double plutil call for null sentinel + fragile primitive-value edge case |
| WR-04 | WARNING | `collect_claude_skills_agents` | `name` not reset at loop start; safe today but fragile against future additions |
| IN-01 | INFO | `collect_claude_skills_agents` | Duplicate `setopt local_options null_glob` — second call is a no-op |
| IN-02 | INFO | `collect_claude_plugins` | `local ver=""` inside loop body violates project convention |
| IN-03 | INFO | `collect_codex_mcp` | TOML headers with inline comments (`]  # comment`) silently skipped by sed |

**Critical: 0 | Warning: 4 | Info: 3 | Total: 7**

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

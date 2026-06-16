# Phase 5: Integration & Verification Gates - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase WIRES the 13 collector functions built in Phases 2–4 into `generate_catalog` (in
fixed order) so a single `./update-list.sh` run produces the full software + tooling catalog,
then proves the catalog passes the two non-negotiable gates: **zero secret leakage (FMT-03)**
and **diff-empty determinism (FMT-04)**. It also confirms cross-cutting graceful degradation
(FMT-02). It is the final integration phase — no new collectors, no new catalog features.

The 13 collectors (all already defined and individually verified, NOT yet called):
- AI CLIs: collect_claude_plugins, collect_claude_mcp, collect_claude_skills_agents,
  collect_codex_mcp, collect_opencode_plugins, collect_opencode_mcp, collect_opencode_agents,
  collect_gemini_extensions, collect_gemini_mcp
- Editors: collect_vscode_extensions, collect_cursor_extensions
- Browsers: collect_chrome_extensions, collect_firefox_extensions
</domain>

<decisions>
## Implementation Decisions

### Collector Wiring Order & Placement (USER LOCKED: accept all)
- Append the 13 collector calls inside `generate_catalog` AFTER the existing "Web-installed
  Applications" block (the last existing section).
- Fixed order: **AI CLIs → editors → browsers**, specifically:
  1. collect_claude_plugins → collect_claude_mcp → collect_claude_skills_agents
  2. collect_codex_mcp
  3. collect_opencode_plugins → collect_opencode_mcp → collect_opencode_agents
  4. collect_gemini_extensions → collect_gemini_mcp
  5. collect_vscode_extensions → collect_cursor_extensions
  6. collect_chrome_extensions → collect_firefox_extensions
- The existing sections (Homebrew, App Store, Setapp, Web-installed), the archive flow, and the
  git pull/commit/push flow are UNTOUCHED — the only change is adding 13 function calls.
- Each collector already does its own `write_section` + `flush_section`, so wiring is one call
  per collector (no inline section logic in generate_catalog).

### Secret-Leakage Gate — FMT-03 (USER LOCKED: scoped + refined)
- The gate greps the **NEW tooling sections only** (from the first new section header onward),
  NOT the whole catalog. RATIONALE: legitimate Homebrew formulae (`libmicrohttpd`, `libnghttp2`,
  `libnghttp3`, `llhttp`, and packages like `httpie`) contain the substring `http`, so the
  ROADMAP's literal whole-catalog `grep http` would false-positive on pre-existing, non-secret
  package names. The leakage risk this gate protects against is MCP secrets in the NEW sections.
- Patterns checked (scoped to new sections): `https?://`, `Bearer `, `[?&]key=`, `Authorization`,
  `sk-`, `ghp_`, and bare `token`.
- Pass condition: ZERO matches in the new-sections region. A match FAILS the phase (this is the
  milestone-critical gate).

### Determinism Gate — FMT-04 (USER LOCKED: accept all)
- Mechanism: run the real script twice with `--no-commit` and compare the two output files'
  CONTENT (the timestamp lives only in the filename via `CURRENT_DATE`; file content has no
  internal timestamp). `diff` of the two contents must be empty.
- Scope: full-catalog content should be byte-identical; the NEW sections being byte-identical is
  the FIRM requirement. If a pre-existing source proves inherently volatile (e.g. `mas list`
  ordering), note it rather than failing on legacy behavior — but the new sections must diff-empty.
- Pass condition: `diff` empty (at least across the new sections; ideally the whole file).

### Gate Delivery Form (USER LOCKED: ephemeral, catalog-only)
- The two gates are delivered as this phase's EPHEMERAL verification (run the real
  `update-list.sh` and check its output), matching the prior phases' self-test style. NO new
  permanent `--verify`/self-check subcommand is added — the tool stays "catalog only" (no
  restore/diff feature creep).
- Real-run target: generate into a throwaway location (or `--personal --no-commit` then inspect),
  and DO NOT commit the test catalog files produced by the gate runs.
- FMT-02 check: confirm a full real run completes with all 13 new sections present (each showing
  real entries or `(none found)`) even where a tool/browser is absent, without aborting.
</decisions>

<code_context>
## Existing Code Insights
- `generate_catalog()` at update-list.sh:1399 — existing sections end with "Web-installed
  Applications" (a `find /Applications | sort`). The 13 new calls go right after that, before
  the closing brace.
- Existing sections are already sorted (`brew list` is alphabetical; Setapp/Web-installed use
  `find … | sort`), supporting determinism. `mas list | awk` ordering is the one possible
  volatile pre-existing source to watch.
- The catalog file's only volatile token is the FILENAME timestamp (`CURRENT_DATE` at line 1604,
  `OUTPUT_FILENAME` at 1606); the file CONTENT has no embedded timestamp/date — good for the
  determinism diff.
- All 13 collectors route through `emit_item` → `flush_section` (`LC_ALL=C sort -f -u`), so each
  new section is internally deterministic by construction.
- `--no-commit` flag already exists to run without git push (use it for the gate runs).

### Established Patterns
- `local` vars, `[[ ]]`, `command -v`, double-quoted expansions, graceful degradation, `2>/dev/null`.
</code_context>

<specifics>
## Specific Ideas (verification grounding — THIS machine)
- A full real run on this machine should produce 13 new sections with: 9 Claude plugins, 1 Claude
  MCP (`execbro [stdio]`), ~103 Claude skills+agents, Codex MCP `(none found)`, 1 OpenCode plugin
  (`superpowers`), OpenCode MCP `(none found)`, ~33 OpenCode agents, 1 Gemini extension
  (`conductor`), Gemini MCP `(none found)`, 22 VS Code + 47 Cursor extensions, 7 Chrome + 6
  Firefox extensions.
- Secret-leakage gate must find ZERO hits in those sections (the `execbro` env must not appear).
- Determinism gate: two consecutive `--no-commit` runs → identical content.
- Homebrew false-positive note: `brew list --formula` includes `libnghttp2` etc.; that is WHY the
  leakage gate is scoped to the new sections, not the whole file.
</specifics>

<deferred>
## Deferred Ideas
- Restore/reinstall from catalog — out of scope (future milestone).
- Catalog diffing/change reports — out of scope.
- A permanent `--verify` self-check subcommand — declined (catalog-only scope).
</deferred>

<research_flags>
## Open Questions for Research
1. **Determinism robustness for the existing `mas list` section:** confirm whether
   `mas list | awk` ordering is stable across two back-to-back runs on this machine; if not,
   define the exact determinism-gate comparison (e.g. compare the new-sections region byte-for-byte
   as the firm gate, plus a best-effort full-file diff) so the gate is meaningful and not flaky.
2. **Scoping the leakage grep:** the exact, robust way to extract "the new sections region" from
   the produced catalog (e.g. from the first new section header — "Claude Code Plugins" — to EOF)
   for the grep, in pure shell. Provide the precise awk/sed range and the final grep -E pattern.
3. **Real-run gate harness:** the cleanest way to run the real `update-list.sh` for the gate
   without committing test catalogs (use `--no-commit` and a temp/throwaway target, or generate
   then remove the produced .txt) and capture two runs for the diff.
4. **Wiring verification:** confirm the 13 calls in the exact locked order, placed after the
   Web-installed block, with the existing archive/git flow untouched, and that a full run exits 0.
</research_flags>

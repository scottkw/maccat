# Phase 25: Script Emitter — Research

**Researched:** 2026-06-16
**Domain:** Python string generation, Bash injection safety, `shlex` stdlib, `set -Eeuo pipefail` guard patterns
**Confidence:** HIGH — all critical claims verified by live execution on this machine

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Module:** `src/maccat/reinstall/emitter.py`
- **Public API:** `emit_reinstall_script(catalog: ParsedCatalog, *, source_name: str, generated: str) -> str`
- **Private helpers:** `_brew_block`, `_editor_ext_block`, `_manual_checklist_block`
- **Static map:** `SECTION_SOURCE_MAP` keyed on verbatim `ParsedSection.title`
- **Zero subprocess calls** — emitter is pure text construction
- **File written at 0o644** — by Phase 26, not this phase

**Homebrew guard (GEN-01):**
`brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n>`
- `<n>` is `quote_for_script()`-quoted name
- Append `# cataloged: <version>` when version present; omit when absent
- Multi-version entries (`python@3.11 (3.11.1 3.11.2)`) emit full string: `# cataloged: 3.11.1 3.11.2`
- Degraded sections: skip entirely (no lines, no checklist)
- Section-top comment warning about formula/cask ambiguity

**SECTION_SOURCE_MAP — exactly four auto-install mappings:**
- `"Homebrew Packages"` → `_brew_block`
- `"App Store Applications"` → `_mas_block` (mas install <id>; id-less items → checklist)
- `"VS Code Extensions"` → `_editor_ext_block(editor="code")`
- `"Cursor Extensions"` → `_editor_ext_block(editor="cursor")`

**VS Code/Cursor guard (GEN-03):**
`command -v <editor> >/dev/null && ! <editor> --list-extensions | grep -qi "^<id>$" && <editor> --install-extension <id>`
- Lowercase the marketplace id before quoting
- PATH guard + idempotency check

**Injection safety:** `quote_for_script()` wrapper around `shlex.quote()` is the SOLE path any catalog-derived value reaches shell command position. Strip newlines from values placed in `# cataloged:` comments.

**Script structure:**
`#!/usr/bin/env bash` → `set -Eeuo pipefail` → provenance header → Homebrew block → mas block → VS Code block → Cursor block → manual checklist

**Manual checklist format:** per-source heading `echo` + `echo "  - <name> (<version>)"` per item (version shown only when present). Echo strings quoted via `quote_for_script()`.

**Unknown section titles:** default to manual checklist — never fabricate install commands.

### Claude's Discretion

- Exact bash phrasing within the above guards
- `quote_for_script()` internals
- Emitter function decomposition details
- Header wording
- Test-fixture layout

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.  
Catalog resolution, `reinstall` subcommand, computer-picker, and 0o644 file write are Phase 26.  
RST-03 brew taps and RST-04 AI-CLI auto-restore are v2 per REQUIREMENTS.md.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | Homebrew packages: guarded `brew install` lines, safe to re-run, version comment, formula/cask note | Universal `||`-chain guard verified safe under `set -Eeuo pipefail` (verified: bash tests below) |
| GEN-02 | App Store: `mas install <id>` for id-bearing items; id-less items → checklist (never broken command) | `ParsedItem.id` is `str \| None`; None → checklist route |
| GEN-03 | VS Code/Cursor: `command -v` + `--list-extensions \| grep -qi` guard; ids lowercased | `&&`-chain verified safe under `set -Eeuo pipefail` (verified: bash tests below) |
| GEN-04 | Script: `#!/usr/bin/env bash`, `set -Eeuo pipefail`, provenance header, conventional ordering, `shlex.quote()` for all catalog values | `shlex.quote()` behavior verified; all guard patterns pass `bash -n` |
| MAN-01 | Non-deterministic sources → manual checklist (Setapp, web apps, browsers, AI-CLI tooling); no fabricated installs | All 13 manual-checklist section titles enumerated below |
</phase_requirements>

---

## Summary

Phase 25 builds `src/maccat/reinstall/emitter.py` — a pure Python text-generator that takes a `ParsedCatalog` (from Phase 24) and returns a complete `reinstall.sh` script string. The emitter is the injection-safety and idempotency boundary: every catalog-derived value that enters shell command position must pass through `quote_for_script()` (a thin wrapper around `shlex.quote()`); every value placed in a `# cataloged:` comment must also have embedded newlines stripped. The emitter performs zero subprocess calls.

The dominant technical risk is `set -Eeuo pipefail` interaction with guard expressions. Verified on this machine: `&&`-chains and `||`-chains used in the guard patterns do NOT trigger `errexit` when individual commands in the chain return non-zero, because bash's `set -e` exception rule exempts commands that are part of a conditional context (`&&`/`||`). This means the locked guard patterns are safe as written. The only dangerous interaction — a bare command returning non-zero at statement level — does not occur in any of the emitted guard constructs.

The secondary risk is the `# cataloged:` comment injection vector: `shlex.quote()` wraps values in single-quotes and neutralizes all shell metacharacters in command position, but it does NOT strip embedded newlines. A catalog value containing `\n` will break the comment line and expose the text after `\n` as a live shell command. The fix is a separate `safe_comment_value()` helper that strips `\n` and `\r` before inserting into comment context. Verified: without stripping, `bash -n` passes but `rm -rf /` appears as a live command in the script body. With stripping, both `bash -n` and the injection concern are resolved.

**Primary recommendation:** Implement `quote_for_script = shlex.quote` (or an alias); implement `safe_comment_value(s)` as `s.replace("\n", " ").replace("\r", " ")`; use `&&`-chain for editor guards without trailing `|| true` (safe because the chain resolves non-zero without aborting `set -e`).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Injection safety | emitter.py | — | All catalog values pass through `shlex.quote()` before entering any shell context |
| Idempotency guards | emitter.py | — | Guards are emitted as Bash text; runtime behavior is in the generated script, not the emitter |
| Section routing | emitter.py (`SECTION_SOURCE_MAP`) | — | Static map from title string → renderer function |
| Parsecatalog input contract | parser.py (Phase 24) | — | Emitter consumes `ParsedCatalog`; never reads catalog files directly |
| File I/O + mode 0o644 | Phase 26 (`reinstall/cli.py`) | — | Explicitly out of scope for Phase 25 |
| bash -n validation | test suite | — | Tests run `bash -n` on the emitted string; emitter itself is subprocess-free |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `shlex` | stdlib (Python 3.14.6 on this machine) | Shell quoting / injection safety | Only correct stdlib primitive for shell quoting; no deps |

### No External Packages

This phase is stdlib-only Python. No `pip install` is required.

**Version verification:** `shlex` is a Python standard library module at `/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/Python.framework/Versions/3.14/lib/python3.14/shlex.py`. [VERIFIED: Python stdlib]

---

## Package Legitimacy Audit

No external packages are installed in this phase. Section intentionally omitted.

---

## Architecture Patterns

### System Architecture Diagram

```
ParsedCatalog (from Phase 24 parser.py)
        │
        ▼
emit_reinstall_script(catalog, *, source_name, generated)
        │
        ├─► _header_block(source_name, generated)
        │         └─► shebang + set -Eeuo pipefail + provenance comment
        │
        ├─► for section in catalog.sections:
        │     SECTION_SOURCE_MAP.get(section.title, _manual_checklist_block)
        │         │
        │         ├─ "Homebrew Packages"       → _brew_block(section)
        │         ├─ "App Store Applications"  → _mas_block(section)
        │         ├─ "VS Code Extensions"      → _editor_ext_block(section, "code")
        │         ├─ "Cursor Extensions"       → _editor_ext_block(section, "cursor")
        │         └─ everything else           → _manual_checklist_block(section)
        │
        └─► "\n".join(all_blocks) → complete script string
                │
                ▼ (Phase 26)
          Path.write_text(script, encoding="utf-8")
          Path.chmod(0o644)
```

### Recommended Project Structure

```
src/maccat/reinstall/
├── __init__.py          # (exists, Phase 24)
├── parser.py            # (exists, Phase 24)
└── emitter.py           # NEW this phase

tests/reinstall/
├── test_parser_contract.py   # (exists, Phase 24)
└── test_emitter.py           # NEW this phase
```

### Pattern 1: `quote_for_script` — the sole shell-interpolation gate

**What:** A named wrapper around `shlex.quote()`. The name makes grep/review trivial; any bare f-string in a shell context is an immediate review finding.

**When to use:** Every catalog-derived value in command position.

```python
# Source: verified against Python 3.14 shlex stdlib behavior

from __future__ import annotations
import shlex

def quote_for_script(value: str) -> str:
    """Wrap shlex.quote — the SOLE path catalog values enter shell command position."""
    return shlex.quote(value)

def safe_comment_value(value: str) -> str:
    """Strip embedded newlines before inserting a value into a # comment.

    shlex.quote() neutralizes metacharacters in command position but does NOT
    strip embedded newlines. A newline inside a '...' single-quoted token is
    syntactically valid but BREAKS the comment line: text after the newline
    becomes a live shell command.

    This is the ONLY path a catalog value may reach comment (non-command) context.
    """
    return value.replace("\n", " ").replace("\r", " ")
```

**Critical distinction:** `quote_for_script` is for command arguments; `safe_comment_value` is for `# cataloged:` lines. Both are needed; neither replaces the other.

### Pattern 2: Homebrew universal guard

**What:** Single guard covering both formulae and casks (indistinguishable in catalog).

```bash
brew list GIT_NAME &>/dev/null || brew list --cask GIT_NAME &>/dev/null || brew install GIT_NAME  # cataloged: VERSION
```

**Verified safe under `set -Eeuo pipefail`:** The entire expression is a `||`-chain. When `brew list` returns 1 (package not installed), `set -e` does NOT fire because the command is part of a conditional compound. The script does not abort; execution continues to the next `||` operand. [VERIFIED: bash 3.2.57 on this machine]

**Python generation:**
```python
# Source: verified by bash execution on this machine

def _brew_line(item: ParsedItem) -> str:
    n = quote_for_script(item.name)
    guard = f"brew list {n} &>/dev/null || brew list --cask {n} &>/dev/null || brew install {n}"
    if item.version:
        comment = safe_comment_value(item.version)
        return f"{guard}  # cataloged: {comment}"
    return guard
```

**Multi-version Homebrew entries** (e.g., `python@3.11 (3.11.1 3.11.2)`): the parser produces `version="3.11.1 3.11.2"` (the full space-joined string). Emit verbatim in the comment: `# cataloged: 3.11.1 3.11.2`. [VERIFIED: homebrew.py `_parse_brew_versions_line` confirmed in codebase]

### Pattern 3: `mas install` guard (GEN-02)

**What:** `mas install <id>` — only for items where `ParsedItem.id` is not None.

```python
def _mas_line(item: ParsedItem) -> str | None:
    """Returns None for id-less items — caller routes them to checklist."""
    if item.id is None:
        return None
    qid = quote_for_script(item.id)
    comment = f"  # cataloged: {safe_comment_value(item.version)}" if item.version else ""
    return f"mas install {qid}{comment}"
```

**Note:** `mas install` takes the numeric App Store ID, not the name. The id is preserved in `ParsedItem.id` (Phase 24 MAS-01). Items without an id (pre-MAS-01 catalogs) have `ParsedItem.id = None` and must be routed to the manual checklist. [VERIFIED: parser.py and mas.py confirmed in codebase]

### Pattern 4: VS Code / Cursor extension guard (GEN-03)

**What:** PATH guard + idempotency check — one line per extension.

```bash
command -v code >/dev/null && ! code --list-extensions | grep -qi '^ms-python.python$' && code --install-extension ms-python.python  # cataloged: 2024.1.0
```

**Verified safe under `set -Eeuo pipefail`:** [VERIFIED: bash execution on this machine]

1. `command -v code >/dev/null` returns 1 if `code` is absent. This is in a `&&`-chain (conditional context), so `set -e` does NOT fire. The chain short-circuits to 1 (non-zero) and the next statement is reached normally.
2. `! ... | grep -qi` — `grep` returning 1 (extension not found, so `!` negates to 0). Under `pipefail`, the pipeline exit status is the last non-zero exit; `!` negates it. Result: 0. No abort.
3. `grep` returning 0 (extension found, `!` negates to 1): the `&&` short-circuits, no install runs. No abort.

**Python generation:**
```python
def _ext_line(item: ParsedItem, editor: str) -> str | None:
    """Returns None if item has no id — caller decides fallback."""
    if item.id is None:
        return None
    install_id = quote_for_script(item.id.lower())
    grep_pat = quote_for_script("^" + item.id.lower() + "$")
    line = (
        f"command -v {editor} >/dev/null && "
        f"! {editor} --list-extensions | grep -qi {grep_pat} && "
        f"{editor} --install-extension {install_id}"
    )
    if item.version:
        line += f"  # cataloged: {safe_comment_value(item.version)}"
    return line
```

**Lowercase rule:** Extension marketplace IDs like `MS-Python.Python` must be lowercased to `ms-python.python` before `quote_for_script()` and before constructing the `grep` pattern. [VERIFIED: vscode.py uses `id_.lower()` in the collector's extensions.json path]

### Pattern 5: Manual checklist block (MAN-01)

**What:** Build the display string in Python, then `shlex.quote()` the whole thing for `echo`. This is simpler than quoting name and version separately and avoids awkward shell quoting seams.

```python
def _checklist_line(item: ParsedItem) -> str:
    name = safe_comment_value(item.name)
    if item.version:
        ver = safe_comment_value(item.version)
        display = f"  - {name} ({ver})"
    else:
        display = f"  - {name}"
    return f"echo {shlex.quote(display)}"
```

**Verified:** `bash -n` clean for adversarial names including `$(malicious)`, `it's complex`, embedded newlines. [VERIFIED: bash execution on this machine]

### Pattern 6: Section skip conditions

The emitter must skip sections silently in two cases:

1. **`section.degraded is True`:** The source was absent at catalog time. Skip the entire section — no install lines, no checklist entry. [VERIFIED: parser.py `ParsedSection.degraded` field]
2. **`section.items == [] and not section.degraded`:** Empty but not degraded — this includes the `"Installed Mac Software List"` header section that the parser emits as a leading empty section (WR-05 contract in `parser.py`). Skip silently. [VERIFIED: `test_real_header_layout_yields_leading_empty_header_section` in `test_parser_contract.py`]

```python
def _should_skip(section: ParsedSection) -> bool:
    return section.degraded or len(section.items) == 0
```

### Anti-Patterns to Avoid

- **Bare f-string interpolation in shell context:** `f"brew install {item.name}"` — if `item.name` contains a space or `$()`, this is a shell injection. Every catalog-derived value in command position must pass through `quote_for_script()`.
- **Using `shlex.quote()` for comment context:** `shlex.quote()` preserves embedded newlines (wraps them in single-quotes, which is syntactically valid bash). The quoted value's embedded newline then breaks the comment and exposes the remainder as a live command. Use `safe_comment_value()` instead.
- **Subprocess calls in the emitter:** The emitter must be zero-subprocess. Any `subprocess.run(...)` is a design violation — `bash -n` validation belongs in the test, not the emitter.
- **Omitting the `"Installed Mac Software List"` header skip:** The parser emits this as a leading empty section (WR-05). Without the skip, the emitter would emit an empty section heading block.
- **Not lowercasing extension IDs before quoting:** Extension IDs from the catalog may have mixed case (e.g., `MS-Python.Python`). The `grep -qi` pattern and `--install-extension` argument must both use the lowercased id. Lowercase first, then `quote_for_script()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shell quoting | Custom escape logic (`replace("$", "\\$")`) | `shlex.quote()` | Custom escaping always misses edge cases (single quotes, embedded newlines, `'x'"'"'y'` pattern) |
| Newline safety in comments | Custom regex | `str.replace("\n", " ").replace("\r", " ")` | Two-line function; no regex overhead needed |
| `bash -n` syntax validation | Re-implementing bash parser in Python | `subprocess.run(["bash", "-n", ...])` in the test | bash is always present on macOS; use it |

**Key insight:** `shlex.quote()` is the only stdlib primitive that produces correct POSIX shell quoting for all input including empty strings, single quotes, and all metacharacters. It has been in the Python stdlib since Python 2 and its behavior is frozen.

---

## `shlex.quote()` Semantics — Verified Behavior

**Source:** Python 3.14 stdlib `shlex.py` on this machine. [VERIFIED: stdlib]

| Input | `shlex.quote()` output | Safe in command position? | Notes |
|-------|----------------------|--------------------------|-------|
| `git` | `git` | Yes | Bare safe identifier |
| `My App` | `'My App'` | Yes | Wrapped in single-quotes |
| `$(rm -rf /)` | `'$(rm -rf /)'` | Yes | Single-quotes suppress `$()` expansion |
| `` `id` `` | `` '`id`' `` | Yes | Single-quotes suppress backtick expansion |
| `foo;bar` | `'foo;bar'` | Yes | Semicolon neutralized |
| `it's a test` | `'it'"'"'s a test'` | Yes | POSIX-correct single-quote escape |
| `say "hi"` | `'say "hi"'` | Yes | Double-quotes inside single-quotes are literal |
| `foo\nbar` (with literal newline) | `'foo\nbar'` (with literal newline) | Yes in command position | **DANGEROUS in comment position** — newline breaks the comment line |
| `foo&bar` | `'foo&bar'` | Yes | Ampersand neutralized |
| `3.11.1 3.11.2` | `'3.11.1 3.11.2'` | Yes | Spaces in version string |
| `python@3.11` | `python@3.11` | Yes | No quoting needed |

**Critical observation:** `shlex.quote()` does NOT strip embedded newlines. A single-quoted token containing a literal newline is syntactically valid bash (the shell continues reading the string across lines), but it will break a `# cataloged:` comment by ending the comment early and exposing the remainder as a live command. `safe_comment_value()` (newline strip) is mandatory for comment context.

---

## SECTION_SOURCE_MAP — Complete Title Enumeration

All section titles from the collector files, classified by emitter behavior:

### Auto-Install Sections (4)

| Title constant | Source | Renderer |
|----------------|--------|----------|
| `"Homebrew Packages"` | `homebrew.py:TITLE` | `_brew_block` |
| `"App Store Applications"` | `mas.py:TITLE` | `_mas_block` |
| `"VS Code Extensions"` | `vscode.py:VSCodeCollector.TITLE` | `_editor_ext_block(editor="code")` |
| `"Cursor Extensions"` | `cursor.py:CursorCollector.TITLE` | `_editor_ext_block(editor="cursor")` |

### Manual Checklist Sections (13)

| Title constant | Source | Notes |
|----------------|--------|-------|
| `"Setapp Applications"` | `setapp.py:TITLE` | No CLI installer |
| `"Web-installed Applications"` | `webapps.py:TITLE` | No CLI installer |
| `"Google Chrome Extensions"` | `chrome.py:_TITLE` | Browser extension; no CLI |
| `"Firefox Extensions"` | `firefox.py:_TITLE` | Browser extension; no CLI |
| `"Claude Code Plugins"` | `claude.py:ClaudeCollector._PLUGINS_TITLE` | AI-CLI identity only (FMT-03) |
| `"Claude Code MCP Servers"` | `claude.py:ClaudeCollector._MCP_TITLE` | AI-CLI identity only (FMT-03) |
| `"Claude Code Skills & Agents"` | `claude.py:ClaudeCollector._SKILLS_TITLE` | AI-CLI identity only (FMT-03) |
| `"Codex MCP Servers"` | `codex.py:_TITLE` | AI-CLI identity only (FMT-03) |
| `"Gemini CLI Extensions"` | `gemini.py:_EXT_TITLE` | AI-CLI identity only |
| `"Gemini CLI MCP Servers"` | `gemini.py:_MCP_TITLE` | AI-CLI identity only (FMT-03) |
| `"OpenCode Plugins"` | `opencode.py` (local `title = "OpenCode Plugins"`) | AI-CLI identity only |
| `"OpenCode MCP Servers"` | `opencode.py` (local `title = "OpenCode MCP Servers"`) | AI-CLI identity only (FMT-03) |
| `"OpenCode Agents"` | `opencode.py` (local `title = "OpenCode Agents"`) | AI-CLI identity only |

### Special Sections (skip silently)

| Title | Source | Behavior |
|-------|--------|----------|
| `"Installed Mac Software List"` | `cli.py` header section | Empty items, not degraded — skip (WR-05 contract in parser.py) |

**Total: 17 named section titles** (4 auto-install + 13 manual + 1 header-skip = 18 possible titles, but the header appears as an empty section the parser passes through — it is not a `SECTION_SOURCE_MAP` key; the skip-empty logic handles it before the map lookup.)

**Forward compatibility:** Any future section title not in `SECTION_SOURCE_MAP` routes to manual checklist (default). [VERIFIED: locked in CONTEXT.md]

---

## `set -Eeuo pipefail` Pitfalls — Verified Behavior

All results verified by execution on this machine (bash 3.2.57, macOS 25.5.0). [VERIFIED: bash execution]

### Rule: `&&`/`||` chains are conditional contexts

Under `set -e`, a command that is part of a conditional expression (`&&`, `||`, `if`, `while`) does NOT trigger `errexit` when it returns non-zero. Only a bare non-zero command at statement level triggers `errexit`.

| Pattern | `set -e` fires? | Verified |
|---------|----------------|----------|
| `false` (bare statement) | YES — script aborts | Yes |
| `false && true` | NO — conditional context | Yes |
| `false \|\| true` | NO — conditional context | Yes |
| `false \|\| false \|\| echo "install"` | NO — full `\|\|`-chain is conditional | Yes |
| `true \|\| false \|\| echo "skip"` | NO — first `true` short-circuits | Yes |
| `command -v xyz >/dev/null && echo "install"` | NO (xyz absent, returns 1) | Yes |
| `! { echo "x"; } \| grep -qi "^y$"` (grep returns 1, `!` negates) | NO | Yes |

### Brew guard under `set -e`

```bash
brew list 'git' &>/dev/null || brew list --cask 'git' &>/dev/null || brew install 'git'
```

- `brew list 'git'` returns 1 (not installed): in `||`-chain, no abort. Next operand runs.
- `brew list --cask 'git'` returns 1 (not installed): no abort. Next operand runs.
- `brew install 'git'` runs. If it returns 0: chain resolves to 0. Fine.
- If `brew install` returns non-zero: the chain's exit status is non-zero. This IS a statement-level exit. The script WILL abort. This is the correct behavior (install failure should stop the script).

### VS Code guard under `set -e`

```bash
command -v code >/dev/null && ! code --list-extensions | grep -qi '^ms-python.python$' && code --install-extension ms-python.python
```

- `command -v code` fails (code absent): `&&`-chain returns 1. As a statement this is non-zero — but it IS a `&&`-chain (conditional context), so `set -e` does NOT abort. [VERIFIED]
- `grep -qi` returns 1 (not found): `!` negates to 0. `&&` continues to install. Fine.
- `grep -qi` returns 0 (found): `!` negates to 1. `&&` short-circuits. No install. Non-zero result at statement level — but `&&`-chain is conditional context, no abort. [VERIFIED]
- `code --install-extension` runs successfully: chain resolves to 0. Fine.

**No trailing `|| true` is needed.** The `&&`-chain is already in a conditional context that `set -e` exempts. Adding `|| true` would suppress a real extension install failure, which is undesirable. [VERIFIED: bash tests above]

### Potential trip-wire: bare `false` in an emitted block

The emitter must never emit a bare command at statement level that could return non-zero unexpectedly. All guard patterns use `&&`/`||` chains. The one exception is `mas install <id>` — this runs unconditionally. `mas install` is designed to be idempotent (re-installing an already-installed app is a no-op on macOS), but if it fails (network error, invalid id), the script will abort per `set -e`. This is acceptable behavior (a failure in `mas install` is a real error, not an expected non-zero).

---

## `bash -n` Testability

**Strategy:** In `tests/reinstall/test_emitter.py`, run `subprocess.run(["bash", "-n", ...])` on a temp file containing the emitted string. Skip gracefully if `bash` is not on `PATH` (though on macOS it is always present at `/bin/bash`).

```python
# Source: verified pattern for bash -n testing in stdlib pytest

import shutil
import subprocess
import tempfile
import os
import pytest

def assert_bash_n_clean(script: str) -> None:
    """Assert the script string passes bash -n syntax check. Skip if bash absent."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(["bash", "-n", tmp], capture_output=True, text=True)
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"
    finally:
        os.unlink(tmp)
```

**Emitter constraint:** The emitter itself must make ZERO subprocess calls. Only the test calls `bash -n`. [VERIFIED: confirmed by CONTEXT.md and test separation above]

**Bash version note:** macOS ships bash 3.2.57 (GPL2 license restriction). The guard patterns verified above work on 3.2.57. They are also valid in bash 4.x/5.x. [VERIFIED: `/bin/bash --version` on this machine]

---

## emit_reinstall_script — Recommended Signature

From CONTEXT.md (Phase 26 integration contract):

```python
def emit_reinstall_script(
    catalog: ParsedCatalog,
    *,
    source_name: str,
    generated: str,
) -> str:
    """Render a ParsedCatalog into a complete reinstall.sh script string.

    Args:
        catalog:     Parsed catalog from reinstall.parser.parse_catalog().
        source_name: Human-readable catalog filename for the provenance header.
        generated:   Generation date string for the provenance header (e.g. "2026-06-16").

    Returns:
        Complete script string starting with '#!/usr/bin/env bash'.
        Guaranteed to pass bash -n.
        Every catalog-derived value in command position is shlex.quote()-wrapped.
        No subprocess calls are made.
    """
```

Phase 26 calls this function, writes the result with `path.write_text(script, encoding="utf-8")`, and sets `path.chmod(0o644)`.

---

## Common Pitfalls

### Pitfall 1: `shlex.quote()` does not strip embedded newlines

**What goes wrong:** A catalog item name or version containing `\n` passes through `shlex.quote()` and the newline is preserved inside single-quotes. In command position this is syntactically valid (the shell continues reading the quoted string across lines). But if the same value is placed in a `# cataloged:` comment, the newline ends the comment early and the text after `\n` becomes a live shell command.

**Why it happens:** `shlex.quote()` is designed for command arguments, not comments. Single-quoted strings can span newlines in POSIX shell.

**How to avoid:** Use `safe_comment_value(value)` — which strips `\n` and `\r` — for every value placed in `# cataloged:` context. Use `quote_for_script(value)` — `shlex.quote()` — for command argument position.

**Warning signs:** A test that checks `bash -n` passes (because `brew install evil` on its own line IS valid bash), but the script body contains an unexpected command after a comment-style line. [VERIFIED: demonstrated in research tests above]

### Pitfall 2: Forgetting to skip empty and degraded sections

**What goes wrong:** The parser emits an `"Installed Mac Software List"` section with `items=[]` and `degraded=False` at the head of every real catalog (WR-05 contract). A degraded Homebrew section has `items=[]` and `degraded=True`. If the emitter does not skip these, it will emit empty section blocks or checklist headings with no items.

**Why it happens:** `parse_catalog()` does NOT filter the header section — it explicitly defers this to Phase 25 (documented in `parser.py` docstring and `test_parser_contract.py`).

**How to avoid:** Before routing a section through `SECTION_SOURCE_MAP`, check `_should_skip(section)`. Skip both `degraded=True` and `items == [] and not degraded`.

### Pitfall 3: Uppercase extension IDs in grep pattern

**What goes wrong:** `grep -qi '^MS-Python.Python$'` is case-insensitive (`-i`), so it matches. But `code --install-extension MS-Python.Python` and `code --install-extension ms-python.python` may behave differently depending on the CLI version. More importantly, the catalog stores the original-case id (e.g., `MS-Python.Python` from the collector), but the marketplace canonical id is lowercase.

**How to avoid:** Lowercase the id (`item.id.lower()`) BEFORE calling `quote_for_script()`. Use the lowercased id for both the grep pattern and the `--install-extension` argument.

### Pitfall 4: `brew install` with multi-version version string in command position

**What goes wrong:** Homebrew stores multiple installed versions in the version field: `item.version = "3.11.1 3.11.2"`. If the emitter incorrectly tries to use the version string as a command argument (e.g., `brew install python@3.11 3.11.1 3.11.2`), brew will fail.

**How to avoid:** The version string appears ONLY in the `# cataloged:` comment. The install command is always `brew install <name>` — no version pinning (this is an explicit out-of-scope decision in REQUIREMENTS.md: "Version pinning is unreliable across brew/mas/extensions").

### Pitfall 5: Routing id-less mas items to `mas install`

**What goes wrong:** A catalog generated before MAS-01 (Phase 24) has App Store items with `ParsedItem.id = None`. Emitting `mas install None` or `mas install ` is a broken command that will error at runtime.

**How to avoid:** In `_mas_block`, check `item.id is not None` before emitting a `mas install` line. Route id-less items to the manual checklist under a heading like `"App Store Applications (no ID — install manually)"`.

### Pitfall 6: `SECTION_SOURCE_MAP` key type must be `str`

**What goes wrong:** If `SECTION_SOURCE_MAP` is typed as `dict[str, Callable[..., str]]`, mypy will require explicit typing of the callable type. Using `Callable[[ParsedSection], str]` is correct for most renderers but `_editor_ext_block` takes an additional `editor` argument — it needs a partial or the signature must match.

**How to avoid:** Use `functools.partial` to bind the `editor` argument:
```python
from functools import partial

SECTION_SOURCE_MAP: dict[str, Callable[[ParsedSection], str]] = {
    "Homebrew Packages": _brew_block,
    "App Store Applications": _mas_block,
    "VS Code Extensions": partial(_editor_ext_block, editor="code"),
    "Cursor Extensions": partial(_editor_ext_block, editor="cursor"),
}
```

---

## Code Examples

### Full emitter skeleton

```python
# Source: verified patterns from research above + CONTEXT.md locked decisions

from __future__ import annotations

import shlex
from functools import partial
from typing import Callable

from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection

# ---------------------------------------------------------------------------
# Injection-safety helpers
# ---------------------------------------------------------------------------


def quote_for_script(value: str) -> str:
    """Sole path catalog values enter shell command position."""
    return shlex.quote(value)


def safe_comment_value(value: str) -> str:
    """Strip embedded newlines before inserting a value into a # comment."""
    return value.replace("\n", " ").replace("\r", " ")


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _should_skip(section: ParsedSection) -> bool:
    """Skip degraded sections and legitimately empty sections (including the WR-05 header)."""
    return section.degraded or len(section.items) == 0


def _brew_block(section: ParsedSection) -> str:
    lines: list[str] = [
        'echo "=== Homebrew Packages ==="',
        "# NOTE: if a name is both a formula and a cask, you may need --formula or --cask.",
    ]
    for item in section.items:
        n = quote_for_script(item.name)
        guard = f"brew list {n} &>/dev/null || brew list --cask {n} &>/dev/null || brew install {n}"
        if item.version:
            guard += f"  # cataloged: {safe_comment_value(item.version)}"
        lines.append(guard)
    return "\n".join(lines)


def _mas_block(section: ParsedSection) -> str:
    auto: list[str] = []
    manual: list[ParsedItem] = []
    for item in section.items:
        if item.id is not None:
            qid = quote_for_script(item.id)
            line = f"mas install {qid}"
            if item.version:
                line += f"  # cataloged: {safe_comment_value(item.version)} {item.name}"
            auto.append(line)
        else:
            manual.append(item)
    lines: list[str] = ['echo "=== App Store Applications ==="']
    lines.extend(auto)
    if manual:
        lines.append('echo "App Store Applications (no ID — install manually):"')
        for item in manual:
            lines.append(f"echo {shlex.quote(_checklist_display(item))}")
    return "\n".join(lines)


def _editor_ext_block(section: ParsedSection, *, editor: str) -> str:
    lines = [f'echo "=== {section.title} ==="']
    for item in section.items:
        if item.id is None:
            lines.append(f"echo {shlex.quote(_checklist_display(item))}")
            continue
        low_id = item.id.lower()
        install_id = quote_for_script(low_id)
        grep_pat = quote_for_script(f"^{low_id}$")
        line = (
            f"command -v {editor} >/dev/null && "
            f"! {editor} --list-extensions | grep -qi {grep_pat} && "
            f"{editor} --install-extension {install_id}"
        )
        if item.version:
            line += f"  # cataloged: {safe_comment_value(item.version)}"
        lines.append(line)
    return "\n".join(lines)


def _checklist_display(item: ParsedItem) -> str:
    name = safe_comment_value(item.name)
    if item.version:
        return f"  - {name} ({safe_comment_value(item.version)})"
    return f"  - {name}"


def _manual_checklist_block(section: ParsedSection) -> str:
    lines = [f"echo {shlex.quote(section.title + ':')}"]
    for item in section.items:
        lines.append(f"echo {shlex.quote(_checklist_display(item))}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section routing map
# ---------------------------------------------------------------------------

SECTION_SOURCE_MAP: dict[str, Callable[[ParsedSection], str]] = {
    "Homebrew Packages": _brew_block,
    "App Store Applications": _mas_block,
    "VS Code Extensions": partial(_editor_ext_block, editor="code"),
    "Cursor Extensions": partial(_editor_ext_block, editor="cursor"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_reinstall_script(
    catalog: ParsedCatalog,
    *,
    source_name: str,
    generated: str,
) -> str:
    header = "\n".join([
        "#!/usr/bin/env bash",
        "set -Eeuo pipefail",
        "",
        f"# Generated from: {safe_comment_value(source_name)}",
        f"# Generated on:   {safe_comment_value(generated)}",
        "# Review this script before running. It is NOT auto-executed.",
        "",
    ])
    blocks: list[str] = [header]
    manual_sections: list[ParsedSection] = []
    for section in catalog.sections:
        if _should_skip(section):
            continue
        renderer = SECTION_SOURCE_MAP.get(section.title)
        if renderer is not None:
            blocks.append(renderer(section))
        else:
            manual_sections.append(section)
    if manual_sections:
        blocks.append('echo ""')
        blocks.append('echo "=== Manual Checklist ==="')
        blocks.append('echo "The following items require manual installation:"')
        for section in manual_sections:
            blocks.append("")
            blocks.append(_manual_checklist_block(section))
    return "\n\n".join(blocks) + "\n"
```

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. Section omitted per instructions.

---

## Security Domain

This phase generates shell script text. The primary security concern is injection — a malicious catalog item (crafted name/version) injecting arbitrary shell commands into the generated script.

**Threat model:** The catalog is a local file the user controls. However, hostile data could arrive via a compromised third-party extension name (e.g., a VS Code extension with a specially crafted display name in its `package.json`). The emitter must be safe regardless of catalog content.

**Controls:**
- `quote_for_script()` / `shlex.quote()` neutralizes all shell metacharacters in command position. [VERIFIED]
- `safe_comment_value()` neutralizes newlines in comment context. [VERIFIED]
- No subprocess calls in the emitter — the generated script is never auto-executed.
- The generated script requires a human to review and manually run it (RST-01 design invariant).

**ASVS V5 (Input Validation):** All catalog-derived values are treated as untrusted and sanitized via `shlex.quote()` before shell interpolation. [VERIFIED: consistent with project security stance]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `functools.partial` signature is compatible with `Callable[[ParsedSection], str]` under mypy --strict | Code Examples | Mypy may reject the `partial` type; may need explicit `Protocol` or different approach |
| A2 | `mas install <id>` is idempotent (re-running on an already-installed app is a no-op) | set -Eeuo pitfalls | If mas fails on already-installed app with non-zero exit, the script will abort mid-run |

**All other claims in this research were verified or cited from the actual codebase or by live bash/Python execution on this machine.**

---

## Open Questions

1. **`functools.partial` + mypy --strict compatibility**
   - What we know: `partial(_editor_ext_block, editor="code")` works at runtime.
   - What's unclear: Whether mypy --strict accepts `partial(...)` where a `Callable[[ParsedSection], str]` is expected. mypy may require `cast()` or a `Protocol`.
   - Recommendation: The planner should include a task step to verify mypy --strict passes; if it rejects `partial`, use a `lambda section: _editor_ext_block(section, editor="code")` wrapper instead (mypy-friendly, same behavior).

2. **Manual checklist ordering — sorted or catalog order?**
   - What we know: The `SECTION_SOURCE_MAP` auto-install sections are emitted in catalog order. Manual checklist sections (the remainder) could be emitted in catalog order or sorted.
   - What's unclear: The CONTEXT.md specifies ordering for the auto-install blocks (formulae → casks → mas → code → cursor → manual checklist) but not the ordering within the manual checklist itself.
   - Recommendation: Emit manual sections in catalog order (same order they appear in the catalog). This is deterministic and predictable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x venv | Implementation | Yes | 3.14.6 | — |
| `shlex` (stdlib) | `quote_for_script()` | Yes | stdlib | — |
| `bash` | `bash -n` test | Yes | 3.2.57 | `pytest.skip()` |
| `mypy` | Type checking | Yes | 2.1.0 | — |
| `ruff` | Linting | Yes | 0.15.17 | — |
| `pytest` | Tests | Yes (in venv) | — | — |

**No missing dependencies.**

---

## Sources

### Primary (HIGH confidence)
- `src/maccat/reinstall/parser.py` — `ParsedItem`, `ParsedSection`, `ParsedCatalog` exact dataclass definitions; WR-05 contract documented in docstring
- `tests/reinstall/test_parser_contract.py` — exact shape of parser output; round-trip contract
- `src/maccat/collectors/homebrew.py` — `TITLE = "Homebrew Packages"`, multi-version format `"3.11.1 3.11.2"`
- `src/maccat/collectors/mas.py` — `TITLE = "App Store Applications"`, `ParsedItem.id` holds numeric App Store ID
- `src/maccat/collectors/vscode.py` — `TITLE = "VS Code Extensions"`, id lowercasing in collector
- `src/maccat/collectors/cursor.py` — `TITLE = "Cursor Extensions"`, `cli_name = "cursor"`
- `src/maccat/collectors/chrome.py`, `firefox.py`, `claude.py`, `codex.py`, `gemini.py`, `opencode.py` — all manual-checklist section title strings
- Live bash execution (bash 3.2.57 on this machine) — all `set -Eeuo pipefail` interaction tests
- Live Python execution (Python 3.14.6 on this machine) — all `shlex.quote()` behavior tests

### Secondary (MEDIUM confidence)
- `.planning/phases/25-script-emitter/25-CONTEXT.md` — locked decisions document

### Tertiary (LOW confidence)
- None — all claims in this research are verified against actual code or live execution.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `shlex` is stdlib, verified present
- Guard patterns: HIGH — verified by bash execution on this machine
- `shlex.quote()` semantics: HIGH — verified by Python execution on this machine
- Section title enumeration: HIGH — read directly from collector source files
- Architecture patterns: HIGH — grounded in actual `ParsedCatalog` dataclass shape

**Research date:** 2026-06-16
**Valid until:** Stable — no external dependencies; pure Python stdlib + bash semantics

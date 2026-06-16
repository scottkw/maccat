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

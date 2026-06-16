# Stack Research — Python Port & Distribution (v1.0.0)

**Domain:** macOS software cataloger CLI — Python rewrite of a ~2,500-line Zsh script
**Researched:** 2026-06-14
**Confidence:** HIGH (all version claims verified against official docs and live machine)

> **Scope note:** This is the v1.0.0 research pass. The prior STACK.md (2026-06-12) documented
> discovery methods for the Zsh milestone. That content is preserved in `.planning/codebase/STACK.md`.
> This document answers a single question: **what Python stack should the port use?**

---

## 1. Python Version Floor

### What macOS ships

`/usr/bin/python3` — the system stub installed by Xcode Command Line Tools — is **Python 3.9.6**
(verified live: `Apple clang-2100` build, confirmed by mac.install.guide as of Oct 2024). It has
been 3.9.6 since macOS 12 Monterey; Apple has not updated it. Every developer who has run
`xcode-select --install` has this interpreter, no further action required.

**Critical: Python 3.9 reached EOL on October 31, 2025.** It receives no more security patches
from the upstream CPython team. The Xcode CLT stub is frozen at this version indefinitely (Apple
controls it; they have not updated it in ~4 years).

### Recommended floor: Python 3.11

**Target: `python_requires = ">=3.11"`**

Rationale:

| Factor | Detail |
|--------|--------|
| **EOL safety** | 3.11 is supported through October 2027; 3.12 through Oct 2028; 3.10 through Oct 2026. 3.9 is already EOL. |
| **tomllib** | `tomllib` (stdlib, PEP 680) ships in 3.11+. The config file uses TOML; without 3.11 we need a third-party `tomli` dep, breaking the zero-dep goal for the `.pyz`. |
| **Availability** | Homebrew Python 3.11+ is one `brew install python@3.11` away; pipx automatically uses whatever `python3` is on `PATH`, which is Homebrew's current version (3.14 on this machine). Any developer installing via pipx already has a modern Python. |
| **syrupy** | The chosen snapshot test library (see §5) requires Python >=3.10. 3.11 exceeds this. |
| **Match Homebrew default** | Homebrew ships `python3` → 3.14 on this machine. The realistic user base (macOS devs who use Homebrew) has 3.11+. |

**The Xcode CLT stub at 3.9 is NOT a distribution target.** Users who only have the stub and no
Homebrew Python will need to install one; the README should state `python3.11+` explicitly. This
is the same upgrade step asked of any modern Python tool.

### stdlib features gated by version (relevant to this project)

| Feature | Added in | Used for |
|---------|----------|---------|
| `tomllib` | 3.11 | Parsing the tool's config file (`~/.mac-software-list/config.toml`) |
| `pathlib.Path` | 3.4 | All path operations (available everywhere) |
| `str.removeprefix` / `str.removesuffix` | 3.9 | Cleaner string stripping (available at floor) |
| `zoneinfo` | 3.9 | Not needed — timestamps are local naive datetimes |
| `datetime.fromisoformat` full ISO 8601 | 3.11 | Timestamp parsing if ever needed; floor covers it |
| `ExceptionGroup` / `except*` | 3.11 | Not needed |

**Floor is Python 3.11. Write code at 3.11. Do not use 3.12+ features without a comment.**

---

## 2. Stdlib-Only Feasibility

**Verdict: YES — zero third-party runtime dependencies is achievable.**

Every capability the Zsh script uses maps cleanly to a stdlib module. The only temptation
points where third-party deps look appealing (and why stdlib wins each):

### Capability map

| Zsh capability | Third-party temptation | Stdlib sufficiency | Verdict |
|----------------|------------------------|-------------------|---------|
| Parse JSON manifests (`jq` / `plutil`) | `jq` Python wrapper | `json.loads()` / `json.load()` — handles all JSON the script touches | **stdlib wins** |
| Parse `.plist` files | `biplist`, `plistlib-py3` | `plistlib.load()` — reads XML plist and binary plist; stdlib since 3.4, well-maintained | **stdlib wins** |
| BSD `date -v` arithmetic | `dateutil`, `arrow` | `datetime.datetime` + `datetime.timedelta` — computing cutoff = today − N days is two lines | **stdlib wins** |
| Config file (TOML) | `tomli`, `tomlkit` | `tomllib` (3.11 stdlib) — read-only TOML parse is all we need; we never write TOML config | **stdlib wins (3.11+)** |
| Git operations | `gitpython`, `pygit2` | `subprocess.run(["git", ...])` — script only does `pull`, `add`, `commit`, `push`, `rev-parse`; GitPython adds a runtime dep and known resource-leak issues for this simple use | **subprocess wins** |
| `LC_ALL=C sort -f -u` | `natsort` | `sorted(..., key=str.casefold)` then `dict.fromkeys()` dedup — exact port of the shell sort/dedup behaviour | **stdlib wins** |
| Atomic TSV write (`mv tmp → real`) | — | `pathlib.Path.rename()` is atomic on POSIX (same filesystem); `tempfile.NamedTemporaryFile(dir=target_dir, delete=False)` for cross-filesystem safety | **stdlib wins** |
| Subprocess tool probing (`command -v`) | — | `shutil.which()` — exact equivalent of `command -v` | **stdlib wins** |
| Interactive menu / TTY detection | `blessed`, `click`, `rich` | `sys.stdin.isatty()` + `input()` — the menus are numbered lists, not full TUI; plain `input()` is identical to `read -r` | **stdlib wins** |
| Argument parsing | `click`, `typer` | `argparse` — the flag set is fixed and simple (`--computer`, `--rename`, `--no-commit`, `--archive-days`); argparse handles it with less magic | **stdlib wins** |
| Chrome `__MSG_` name resolution | — | `json` + `pathlib` — the lookup is a two-file read with a case-insensitive key scan; pure stdlib | **stdlib wins** |
| VS Code NLS placeholder resolution | — | Same: `json` read + `.get()` lookup | **stdlib wins** |
| YAML frontmatter parsing (skills/agents) | `pyyaml`, `ruamel.yaml` | `re` — frontmatter is a handful of `key: value` lines between `---` markers; a 5-line regex is all we need. Full YAML parse is over-engineering for this narrow use | **stdlib wins** |

### One genuine complexity: Chrome `__MSG_` without case-insensitive dict access

The `json` module returns a plain `dict` with case-sensitive keys. The Chrome `_locales/messages.json`
key may differ in case from the `__MSG_<key>__` placeholder (e.g., `extName` vs `extname`). Solution:
build a `{k.lower(): v for k, v in messages.items()}` lookup — two lines, zero deps.

### Conclusion

**Zero runtime dependencies.** The `.pyz` zipapp contains only the tool's own package. No
vendoring required. No `pip install` step inside the archive.

---

## 3. Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.11 | Runtime | EOL-safe, unlocks `tomllib`, matches Homebrew default, covers syrupy requirement |
| `argparse` (stdlib) | — | CLI argument parsing | Handles all flags; zero dep; argparse's mutually-exclusive groups model `--personal`/`--office`/`--computer` cleanly |
| `json` (stdlib) | — | JSON manifest parsing | Replaces `jq` + `plutil` for all manifest reads; handles nested paths natively |
| `plistlib` (stdlib) | — | macOS `.plist` parsing | Direct replacement for `plutil -extract`; reads XML and binary plist |
| `subprocess` (stdlib) | — | Git operations + CLI probing | `subprocess.run(["git", ...], check=False)` with warn-and-continue matches the script's existing git behaviour |
| `shutil.which` (stdlib) | — | Tool presence checks | Direct `command -v` equivalent |
| `pathlib` (stdlib) | — | All path operations | Replaces string-based path concatenation throughout |
| `datetime` + `timedelta` (stdlib) | — | Archive date arithmetic | Replaces BSD `date -v-Nd` for cutoff computation |
| `tomllib` (stdlib 3.11+) | — | Config file parsing | Reads `~/.mac-software-list/config.toml` (or XDG equivalent); read-only |
| `configparser` (stdlib) | — | Fallback for simple INI config | Only if we choose INI over TOML; prefer TOML |
| `tempfile` (stdlib) | — | Atomic TSV writes | `NamedTemporaryFile(dir=..., delete=False)` + `Path.rename()` replicates the `> tmp && mv tmp real` pattern |
| `re` (stdlib) | — | YAML frontmatter parsing | Skills/agents frontmatter extraction (narrow use — not full YAML) |

### Supporting Libraries (dev/test only — NOT in runtime `.pyz`)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=8.0 | Test runner | All tests; the standard choice |
| `syrupy` | >=5.0 (current: 5.3.2) | Snapshot / golden-output testing | Byte-parity tests: capture zsh catalog body once, assert Python output matches on every run; requires Python >=3.10 |
| `ruff` | >=0.15 | Linting + formatting | Replaces flake8 + black + isort; single tool; matches repo CLAUDE.md conventions |
| `mypy` | >=1.10 | Type checking | Catches type errors across modules; complements ruff |
| `uv` | >=0.5 | Package/venv management | `uv venv` + `uv pip install -e .[dev]` replaces pip+venv; fast; aligns with CLAUDE.md `uv` preference |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `python -m zipapp` | Build the `.pyz` distribution artifact | stdlib; `python -m zipapp mac_software_list -o mac-software-list.pyz -p "/usr/bin/env python3"` — shebang resolved via `env`, so any Python 3.11+ in PATH works |
| `python -m build` | Build the wheel/sdist for pipx/PyPI | Invokes `hatchling`; produces `.whl` for `pipx install ./dist/*.whl` |
| `hatchling` | Build backend (build-time dep only) | Modern, PEP 517-compliant; zero runtime presence; used by many stdlib-level projects |

---

## 4. Replacements for Shelled-Out Tools

### `plutil` / `jq` → `json` + `plistlib`

**JSON:** `json.loads()` / `json.load()` — exact replacement for `jq -r '...'`. The nested-key
access pattern in `json_get` (dotted key path like `"author.name"`) becomes:

```python
import json, functools, operator

def json_get(path: str, key: str) -> str:
    try:
        with open(path) as f:
            data = json.load(f)
        parts = key.split(".")
        return str(functools.reduce(operator.getitem, parts, data) or "")
    except (KeyError, TypeError, json.JSONDecodeError, OSError):
        return ""
```

**plist:** `plistlib.load(open(path, "rb"))` — handles both XML and binary plist. The Zsh script
only ever called `plutil -extract <key> raw` on JSON files (plutil can parse JSON) and on
`.plist` config files for some sources. Both are covered by `json` + `plistlib`.

### BSD `date -v-Nd` → `datetime.timedelta`

```python
from datetime import date, timedelta
cutoff = date.today() - timedelta(days=archive_age_days)
cutoff_str = cutoff.strftime("%Y%m%d")   # "20260514" — same 8-digit format as the filenames
```

This is an exact replacement for `date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d"`. No third-party dep.

### `git` → `subprocess.run` (NOT GitPython)

**Recommendation: stay with `subprocess.run(["git", ...])`.** Rationale:

- The script only uses five git operations: `rev-parse`, `pull`, `add`, `commit`, `push`. This
  is porcelain-level, not plumbing. GitPython's value is for complex repo introspection.
- GitPython has documented resource-leak issues (destructors not guaranteed in CPython). For
  a short-lived CLI, this creates noise.
- GitPython is a third-party runtime dep, which would appear inside the `.pyz` (it has no
  stdlib fallback). That breaks the zero-dep goal.
- `subprocess.run(["git", "pull"], cwd=repo_dir, capture_output=True)` is 3 lines and trivially
  maps to the existing shell functions.

Pattern for warn-and-continue (matching the Zsh script):

```python
import subprocess, shutil

def git_run(*args: str, cwd: str) -> bool:
    if not shutil.which("git"):
        print("  WARNING: git not found.")
        return False
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARNING: git {args[0]} failed: {result.stderr.strip()}")
        return False
    return True
```

### `LC_ALL=C sort -f -u` → `sorted` + dedup

```python
def flush_section(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for line in sorted(lines, key=str.casefold):
        if line not in seen:
            seen.add(line)
            result.append(line)
    return result
```

`str.casefold` is stronger than `str.lower` for Unicode but produces the same result for the
ASCII-dominant content in these catalogs. The Zsh `sort -f` uses locale-aware case-folding on
ASCII input — `casefold` matches this. `LC_ALL=C` in the Zsh sort guarantees byte-stable order;
Python's sort is also stable and deterministic for ASCII input.

---

## 5. Packaging & Distribution

### Two-artifact strategy

| Artifact | How built | Who uses it | Python required |
|----------|-----------|-------------|-----------------|
| `mac-software-list.pyz` | `python -m zipapp` (stdlib) | Direct download, `curl \| sh` style, cron | Any python3.11+ in PATH |
| PyPI wheel / pipx | `python -m build` + `pipx install mac-software-list` | Developers, ongoing updates via `pipx upgrade` | Managed by pipx |

### `.pyz` zipapp details

`python -m zipapp` (stdlib, PEP 441) is the right tool for a zero-dependency application:

- **Shebang:** `#!/usr/bin/env python3` — resolved at runtime from PATH. On macOS with Homebrew,
  `python3` → 3.14; pipx-managed installs use their own isolated Python. The `env` form avoids
  hardcoding `/usr/bin/python3` (which is the 3.9 stub).
- **Build command:**
  ```bash
  python3 -m zipapp src/mac_software_list \
      -o dist/mac-software-list.pyz \
      -p "/usr/bin/env python3" \
      -m "mac_software_list.__main__:main" \
      -c
  ```
  `-c` enables compression; `-m` names the entry point; the source tree is `src/mac_software_list/`.
- **No vendoring needed** because the tool has zero third-party runtime deps. The archive
  contains only the package source.
- **Executable bit:** `zipapp` sets the bit automatically when given a filename. `chmod +x` not needed.
- **Running on macOS:** `./mac-software-list.pyz --computer Personal` — the kernel reads the
  shebang, finds `python3` via `env`, and Python's ZIP import loads `__main__.py`.

**shiv vs zipapp:** shiv bundles a virtualenv; it exists for apps that _have_ dependencies.
For a zero-dep tool, shiv adds extraction-on-first-run overhead and a `~/.shiv/` cache for
no benefit. **Use stdlib zipapp.**

**pex:** Same story — pex is designed to pack a virtualenv into an executable. Overkill here,
adds a pex build dependency, and the resulting file is larger. Skip.

### pipx distribution (pyproject.toml)

```toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "mac-software-list"
version = "1.0.0"
description = "Catalog every piece of software on your Mac — apps, extensions, plugins, MCP servers."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
# No [project.dependencies] — zero runtime deps

[project.scripts]
mac-software-list = "mac_software_list.__main__:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "syrupy>=5.0",
    "ruff>=0.15",
    "mypy>=1.10",
]

[tool.hatch.build.targets.wheel]
packages = ["src/mac_software_list"]
```

- `pipx install mac-software-list` — installs from PyPI, exposes `mac-software-list` command.
- `pipx install git+https://github.com/user/mac-software-list` — installs direct from GitHub
  (useful before PyPI publish).
- `pipx install ./dist/mac-software-list-1.0.0-py3-none-any.whl` — local wheel install.
- hatchling is the recommended modern build backend from PyPA; it has no runtime presence in
  the installed package.

### Package layout

```
mac-software-list/          ← repo root (contains update-list.sh, machine-labels.tsv, personal/, office/)
├── src/
│   └── mac_software_list/
│       ├── __init__.py
│       ├── __main__.py     ← entry point: main()
│       ├── cli.py          ← argparse + orchestration
│       ├── config.py       ← config file resolution (~/.mac-software-list/config.toml)
│       ├── catalog.py      ← write_section, emit_item, flush_section, output file
│       ├── collectors/
│       │   ├── homebrew.py
│       │   ├── appstore.py
│       │   ├── setapp.py
│       │   ├── webapps.py
│       │   ├── claude.py
│       │   ├── codex.py
│       │   ├── opencode.py
│       │   ├── gemini.py
│       │   ├── vscode.py
│       │   ├── cursor.py
│       │   ├── chrome.py
│       │   └── firefox.py
│       ├── git_ops.py      ← git_pull, git_commit_and_push
│       ├── machine.py      ← select_computer, upsert_machine_label, rename_machine
│       └── retention.py    ← retain_newest_per_host, prune_old_archives
├── tests/
│   ├── conftest.py
│   ├── __snapshots__/      ← syrupy snapshot files
│   └── test_*.py
├── dist/                   ← built artifacts (.pyz, .whl)
├── pyproject.toml
├── update-list.sh          ← untouched Zsh reference implementation
└── machine-labels.tsv
```

The `src/` layout (PEP 517) prevents accidental imports of the uninstalled package during
test runs, a common pitfall with flat layouts.

---

## 6. Dev/Test Stack

### Testing philosophy for this project

The core requirement is **byte-parity with the Zsh output**. That means golden/snapshot tests
are the primary test type, not unit tests. The test strategy:

1. **Golden snapshot tests** (syrupy): capture the catalog body that the Python tool generates
   for a known fixture environment (a temp dir populated with mock manifests), compare against
   either the committed snapshot or a reference run of the Zsh script.
2. **Unit tests** (pytest): test `emit_item`, `flush_section`, `json_get`, `chrome_ext_name`,
   and `resolve_vsc_ext_name` in isolation — these are pure functions with defined input/output.
3. **Integration smoke tests** (pytest + subprocess): run the tool's `__main__` against a
   fixture catalog repo; assert exit code 0 and presence of expected section headers.

### Why syrupy over alternatives

| Tool | Verdict | Reason |
|------|---------|--------|
| **syrupy 5.x** | **Use this** | Pytest-native, zero deps, `assert result == snapshot` syntax, `--snapshot-update` flag to regenerate, `.ambr` files are human-readable diffs in git, Python >=3.10 (covered by our 3.11 floor) |
| `pytest-regtest` | Acceptable alternative | Good for text output; less ergonomic than syrupy for structured data |
| `pytest-golden` | Lower confidence | Smaller community; YAML-based golden files less readable for plain text |
| `approvaltests` | Avoid | Launches external diff tool interactively — breaks CI |
| Plain `.txt` fixtures | Acceptable for pure text | `assert output == (fixtures_dir/"expected.txt").read_text()` works but no `--update` mechanism |

**Recommendation:** syrupy for structured section outputs; plain `.txt` file comparison for
whole-catalog smoke tests where the reference output is directly generated from the Zsh script.

### Dev tooling

| Tool | Version | Config |
|------|---------|--------|
| `ruff` | >=0.15 | `[tool.ruff]` in `pyproject.toml`; enables `E, F, I, UP` rule sets; `ruff format` replaces black |
| `mypy` | >=1.10 | `[tool.mypy]` with `strict = true`; type stubs for stdlib are built-in |
| `uv` | >=0.5 | `uv venv && uv pip install -e ".[dev]"` for local dev; `uv run pytest` for tests |
| `pytest` | >=8.0 | `[tool.pytest.ini_options]` in `pyproject.toml`; `testpaths = ["tests"]` |

---

## 7. Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `stdlib zipapp` | shiv | shiv is for apps with deps; adds extraction overhead and `~/.shiv/` cache for no benefit in a zero-dep tool |
| `stdlib zipapp` | pex | Same issue — designed for virtualenv bundling; significantly more complex build pipeline |
| `subprocess.run(["git", ...])` | `gitpython` | Third-party runtime dep, known resource leaks, adds to `.pyz` size; not worth it for 5 git commands |
| `argparse` | `click` / `typer` | Third-party runtime deps; click/typer's benefits (decorators, type inference) are irrelevant for a fixed CLI; argparse is sufficient and zero-dep |
| `re` for frontmatter | `pyyaml` | Full YAML parse is overkill for `name: value` frontmatter; pyyaml is a runtime dep; the regex is 5 lines and well-tested |
| `tomllib` (3.11) | `tomli` (third-party) | `tomli` is what `tomllib` was back-ported from — use the stdlib version; dropping to 3.9 to avoid the dep is worse than requiring 3.11 |
| `str.casefold` sort | `natsort` | `natsort` adds a dep for no observable benefit on software name strings |
| `hatchling` | `flit_core` | Both are fine; hatchling is more actively maintained and used by PyPA itself; `flit` requires the module docstring to be the description |
| Python 3.11 floor | Python 3.9 | 3.9 is EOL; forces `tomli` dep or a config format switch; syrupy won't install |
| Python 3.11 floor | Python 3.13 | 3.13 is not yet on macOS Xcode CLT; requiring it would block pipx users who rely on `brew install python@3.13` explicitly |

---

## 8. What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `gitpython` | Runtime dep; resource leaks; overkill for 5 git commands | `subprocess.run(["git", ...])` |
| `click` / `typer` | Runtime dep; over-engineered for a fixed flag set | `argparse` (stdlib) |
| `pyyaml` | Runtime dep; overkill for YAML frontmatter with 2 fields | `re` with a 5-line frontmatter extractor |
| `tomli` | Backport of `tomllib`; redundant if Python >=3.11 | `tomllib` (stdlib 3.11+) |
| `shiv` / `pex` | Built for virtualenv bundling; wrong tool for zero-dep apps | `python -m zipapp` (stdlib) |
| `dateutil` / `arrow` | Runtime dep; overkill for `today - N days` | `datetime.timedelta` |
| `PyInstaller` | Creates a frozen binary with its own Python; cross-version incompatibilities; not needed here | `python -m zipapp` |
| `/usr/bin/python3` as the `.pyz` shebang | Points to the EOL 3.9.6 stub | `#!/usr/bin/env python3` (resolves from PATH) |

---

## 9. Installation

```bash
# Dev setup (using uv — preferred per CLAUDE.md)
uv venv
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Build .pyz
python3 -m zipapp src/mac_software_list \
    -o dist/mac-software-list.pyz \
    -p "/usr/bin/env python3" \
    -m "mac_software_list.__main__:main" \
    -c

# Build wheel for pipx
python3 -m build --wheel

# Install via pipx
pipx install ./dist/mac-software-list-1.0.0-py3-none-any.whl
# or
pipx install mac-software-list  # once published to PyPI
```

---

## 10. Version Compatibility

| Package | Requires | Notes |
|---------|----------|-------|
| `syrupy` 5.x | Python >=3.10 | Covered by our 3.11 floor |
| `ruff` 0.15+ | Python >=3.7 runtime, but the tool itself runs on any Python | Installed in dev venv only |
| `mypy` 1.10+ | Python >=3.8 | Installed in dev venv only |
| `hatchling` 1.26+ | Python >=3.8 | Build-time only, not in installed package |
| `pytest` 8.x | Python >=3.8 | Dev only |

The runtime package (what the `.pyz` contains and what `pipx` installs) has **zero dependencies**
beyond CPython 3.11+.

---

## Sources

- Live machine verification — `/usr/bin/python3 --version` → `3.9.6`; Homebrew `python3` → `3.14.6`; `tomllib` available in 3.11, absent in 3.9 (verified)
- [Python 3.9 EOL announcement](https://developers.redhat.com/articles/2025/12/04/python-39-reaches-end-life-what-it-means-rhel-users) — EOL date October 31, 2025
- [Python docs — tomllib](https://docs.python.org/3/library/tomllib.html) — stdlib 3.11+, HIGH confidence
- [Python docs — zipapp](https://docs.python.org/3/library/zipapp.html) — shebang format, `python -m zipapp` CLI, HIGH confidence
- [Python docs — plistlib](https://docs.python.org/3/library/plistlib.html) — reads XML + binary plist, stdlib since 3.0, HIGH confidence
- [syrupy PyPI](https://pypi.org/project/syrupy/) — v5.3.2 (June 2026), requires Python >=3.10, HIGH confidence
- [PyPA — Writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.scripts]` format, hatchling syntax, HIGH confidence
- [PyPA — Creating CLI tools](https://packaging.python.org/en/latest/guides/creating-command-line-tools/) — console_scripts entry point, HIGH confidence
- [ruff FAQ](https://docs.astral.sh/ruff/faq/) — replaces black+isort+flake8, HIGH confidence
- [mac.install.guide — system default](https://mac.install.guide/python/system-default) — Xcode CLT ships Python 3.9.6, MEDIUM confidence (Oct 2024 snapshot; unchanged as of June 2026)
- [shiv docs](https://shiv.readthedocs.io/) — comparison with zipapp, MEDIUM confidence

---
*Stack research for: Python port of mac-software-list Zsh script (v1.0.0)*
*Researched: 2026-06-14*

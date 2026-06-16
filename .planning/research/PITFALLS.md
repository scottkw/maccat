# Pitfalls Research

**Domain:** Generating a reinstall script by parsing a plain-text maccat catalog snapshot
**Researched:** 2026-06-16
**Confidence:** HIGH — all findings are derived from reading the actual collector source
(`mas.py`, `homebrew.py`, `vscode.py`, `cursor.py`, `format.py`, `setapp.py`, `webapps.py`)
and the confirmed test fixtures in `test_homebrew.py`.

> Scope note: these pitfalls are specific to the v2.1.0 `maccat reinstall` feature —
> parsing the emitted plain-text catalog back into structured install commands. They do NOT
> re-litigate v1.0.0 porting pitfalls (sort parity, atomic writes, etc.) already documented
> in the prior version of this file. Every pitfall here is a direct consequence of the
> catalog's text format, specific collector output shapes, or shell-generation safety.

---

## HARD CONSTRAINTS (Must Read Before Scoping)

Two findings from the source code fundamentally reshape the feature scope. They are not
"pitfalls to avoid" — they are facts that determine what is technically possible.

### HARD CONSTRAINT A: The mas App Store ID is NOT in the catalog

**Finding:** `MasCollector._parse_mas_output` (mas.py line 27–45) is an explicit Python
equivalent of `awk '{print $2, $3}'`. Column 1 of `mas list` output is the numeric App Store
ID. The collector **discards it**. The catalog's "App Store Applications" section contains
entries like `Safari (15.0)` — name and version only. No ID.

**Confirmed by test fixture** (`test_homebrew.py` lines 120–129): input
`"1234567890  Safari (15.0)\n"` produces output `["Safari (15.0)"]`. The ID `1234567890` is gone.

**Consequence for reinstall:**
`mas install` requires the numeric App Store ID. You cannot call
`mas install "Safari"` — mas has no name-based lookup. Without the ID, mas apps cannot be
auto-installed. They must move to the manual checklist.

**What changes in the plan:**
The current v2.1.0 milestone spec (`PROJECT.md` line 78) lists `mas install <id>` as an
auto-install target. This is impossible given the current catalog format. The reinstall
feature must either:
1. Move mas apps to the manual checklist entirely (no auto-install), OR
2. Treat this as a prerequisite fix: add a catalog format change that preserves the ID in a
   new `AppName (version) [ID]` format (using `emit_item`'s full three-field path), and
   build the reinstall parser against the new format.

**Option 2 requires a catalog format migration** and must be a scoped prerequisite in Phase 1
of v2.1.0, not an afterthought. If the team assumes the ID is available and discovers it
isn't mid-phase, the auto-install section for mas must be ripped out.

---

### HARD CONSTRAINT B: The formula / cask distinction is NOT in the catalog

**Finding:** `HomebrewCollector.collect` (homebrew.py lines 65–72) runs
`brew list --formula --versions` and `brew list --cask --versions`, then concatenates both
result lists into a single `items` list with no type marker. The catalog's "Homebrew Packages"
section is a flat list: `git (2.44.0)`, `docker (4.30.0)`, `python@3.11 (3.11.1 3.11.2)`.
There is nothing in the line that distinguishes `git` (formula) from `docker` (cask).

**Consequence for reinstall:**
`brew install git` installs a formula. `brew install --cask docker` installs a cask.
Using the wrong flag either silently installs nothing (if the name exists only in the other
type) or — worse — installs the wrong artifact. `brew install docker` without `--cask` will
error or install the Docker Engine formula rather than Docker Desktop.

**What changes in the plan:**
A reinstall script that emits `brew install <name>` for everything from the Homebrew section
will be wrong for every cask. Two options:
1. **Re-query brew at reinstall-script-generation time**: run `brew info --json=v2 <name>` or
   check `brew list --cask` to determine type. This requires brew to be installed on the
   machine generating the script, adds subprocess calls, and changes the "catalog is the
   source of truth" principle.
2. **Preserve the type in the catalog**: change `HomebrewCollector` to emit a type marker
   — for example a separate section "Homebrew Casks" and "Homebrew Formulae" — and build the
   reinstall parser against the new format. This is a catalog format change that must be a
   scoped prerequisite.
3. **Emit both variants and let the user review**: generate both `brew install <name>` and
   `# brew install --cask <name>` with a comment "uncomment the correct line." This is user-
   hostile and defeats the purpose of a reviewable script.

Option 2 (split sections) is the cleanest path. It is a catalog format prerequisite for v2.1.0.
Like HARD CONSTRAINT A, this must be addressed in Phase 1 of v2.1.0, not discovered mid-phase.

---

## Critical Pitfalls

### Pitfall 1: Parsing ambiguity — app names containing `(...)` or `[...]`

**What goes wrong:**
`emit_item` produces lines in these forms:
- `name (version) [id]`
- `name (version)`
- `name [id]`
- `name`
- `id` (id-promoted, no brackets)

A naive parser that splits on the last `(` to find version, or the last `[` to find id, will
mis-parse any name that itself contains parentheses or brackets. Real examples from macOS:
- `Final Cut Pro (10.7.1)` — name is `Final Cut Pro`, but if the name were
  `1Password (7)` (it's not, but a hypothetical), the version `7` would be buried in the name.
- `Microsoft Office 2021 (Home & Student)` — a name containing parens would make the first
  `(` the wrong split point.
- VS Code extension display names: `Prettier - Code formatter (1.0.0) [esbenp.prettier-vscode]`
  — straightforward, but a name like `C/C++ (MS)` would produce `C/C++ (MS) (1.2.3) [ext.id]`
  where the first `(...)` is part of the name.

The Setapp and WebApps collectors emit `AppName.app (version)` — `.app` bundles with spaces in
their names plus a version. `Affinity Designer 2.app (2.4.0)` is unambiguous. But
`Smart Photo Widget (Dark).app (3.1.0)` has two `(...)` groups.

**Why it happens:**
The `emit_item` format was designed for human readability and diff-ability, not for machine
parsing. Round-trip parsing was not a requirement when the format was defined.

**How to avoid:**
Parse with a right-anchored regex that consumes the optional `[id]` suffix first, then the
optional `(version)` suffix, leaving whatever remains as the name. The id and version are
always the rightmost brackets/parens on a line:

```python
import re

_LINE_RE = re.compile(
    r'^(?P<name>.+?)'             # name: everything up to...
    r'(?:\s+\((?P<version>[^)]+)\))?'  # optional (version)
    r'(?:\s+\[(?P<id>[^\]]+)\])?'      # optional [id]
    r'\s*$'
)
```

But this still mis-parses `Smart Photo Widget (Dark).app (3.1.0)` — the regex greedily matches
`Smart Photo Widget` as the name, `Dark` as the version, and `.app (3.1.0)` as trailing noise.

The correct approach is right-anchored greedy matching — parse from the right:
1. If line ends with `]`, extract `[...]` as id suffix.
2. If remainder ends with `)`, extract `(...)` as version suffix.
3. Whatever remains is the name.

This is robust because `emit_item` always appends id last, then version second-to-last.

**Warning signs:**
- Parser splits on the first `(` or `[` in the line.
- Parser uses `line.split("(")` or `str.partition("(")`.
- Test fixtures do not include names with embedded parentheses or brackets.

**Phase to address:**
Phase 1 (catalog parser foundation). Write the parser with a fixture set that includes:
`Smart Photo Widget (Dark).app (3.1.0)`, an extension with `(beta)` in its display name,
a formula named `gnu-tar`, and a degraded name-only entry.

---

### Pitfall 2: Degraded items — name-only and id-promoted entries break version-comment generation

**What goes wrong:**
`emit_item` has three degradation modes that produce no version:
1. **Name-only**: `emit_item("git", "", "")` → `"git"` — version unavailable (VER-05).
2. **Name + id, no version**: `emit_item("My Ext", "", "pub.ext")` → `"My Ext [pub.ext]"`.
3. **Id-promoted (no name)**: `emit_item("", "", "pub.ext")` → `"pub.ext"` — the id string
   appears without brackets.

The reinstall script spec says each install command should carry a `# cataloged: <version>`
comment. For degraded entries, there is no version to comment. If the parser emits
`# cataloged: ` (empty), the script looks broken. If the parser silently omits the comment,
the user loses the "what version was installed" information entirely — which is fine, but
must be an explicit design decision.

More dangerous: the id-promoted form (`"pub.ext"` with no brackets) is syntactically
indistinguishable from a name-only entry `"pub.ext"`. If the parser sees `pub.ext` in the
VS Code Extensions section and treats it as a display name rather than an extension id, the
generated `code --install-extension pub.ext` will be correct by accident (extension ids look
like `publisher.name`). But if the display name happens to look like `publisher.name` (rare
but possible), a name-only entry would generate a plausibly-correct-but-wrong install command.

**Why it happens:**
Degradation was designed for catalog fidelity (always write something rather than nothing),
not for reinstall machine-readability. The round-trip assumption breaks here.

**How to avoid:**
- For the version comment: when version is absent (name-only or name+id entries), emit
  `# cataloged version unknown` rather than `# cataloged: ` or nothing. This is explicit.
- For id-promoted entries in VS Code / Cursor sections: the extension id format
  (`publisher.extensionname`) is reliably dot-separated with no spaces. If the parsed
  "name" in an extension section has no spaces and contains exactly one dot, treat it as
  an id even without brackets. Document this heuristic with a comment.
- For Homebrew name-only entries: `brew install name` without a version comment is correct
  behavior — Homebrew always installs latest. Emit without a version comment.

**Warning signs:**
- The version-comment line is `# cataloged: ` (trailing colon, no value).
- Test fixtures include only fully-decorated `name (version) [id]` lines.
- No test covers what happens when the parser encounters a name-only line.

**Phase to address:**
Phase 1 (catalog parser). Define the degradation-handling contract explicitly in the parser's
return type before building any section emitter.

---

### Pitfall 3: Shell injection from catalog-derived names in the generated script

**What goes wrong:**
The reinstall script (`reinstall.sh`) is generated by writing shell commands. If catalog
item names or versions are interpolated without quoting, a name containing a shell metacharacter
will corrupt the script. Real-world examples that appear in macOS catalogs:
- App name: `AT&T Office@Hand` — `&` is a shell background operator; `@` is safe in `bash`
  but has edge cases.
- Homebrew formula: `gnu-sed` — safe, but `cmake-docs (3.28)` needs quoting in some contexts.
- Extension ID: `ms-vscode.cpptools` — safe, but extension display names can contain `'`, `"`,
  `` ` ``, `$`, `\`, `(`, `)`.
- Version string: `3.11.1 3.11.2` (multi-version brew entry) — spaces in the version string
  would break an unquoted `brew install name --version 3.11.1 3.11.2`.

The generated script runs `brew install <name>`, `mas install <id>`, and
`code --install-extension <id>`. If any catalog value is interpolated directly:

```python
f"brew install {name}"          # WRONG — name may contain spaces, &, etc.
f"code --install-extension {id_}"  # WRONG — publisher.name is safe, but display name is not
```

**Why it happens:**
The tool generates shell scripts, not executes commands directly. Developers think "I just
need to write a string," not "I need to quote shell arguments." The catalog contains user-
controlled data (app names from macOS, extension names from marketplace publishers).

**How to avoid:**
Always `shlex.quote()` every catalog-derived value that goes into a shell command in the
generated script:

```python
import shlex

def brew_install_line(name: str, version_comment: str) -> str:
    return f"brew install {shlex.quote(name)}  {version_comment}"

def mas_install_line(id_: str, name: str, version_comment: str) -> str:
    # mas install takes a numeric id — no quoting needed for digits, but be safe
    return f"mas install {shlex.quote(id_)}  # {shlex.quote(name)} {version_comment}"

def code_install_line(ext_id: str, version_comment: str) -> str:
    return f"code --install-extension {shlex.quote(ext_id)}  {version_comment}"
```

Exception: the version comment is not executed — it is a `# comment`. It still needs escaping
for the comment line to be valid shell (no newlines in the comment value). Strip or replace
any `\n` or `\r` in catalog values before using them in comments.

**Warning signs:**
- Any `f"brew install {name}"` or `f"code --install-extension {id_}"` without `shlex.quote()`.
- Test fixtures do not include a name with `&`, `'`, `"`, `$`, or a space.
- The generated script is tested only with clean ASCII names.

**Phase to address:**
Phase 2 (script emitter). Establish a `quote_for_script(value: str) -> str` wrapper around
`shlex.quote` as the sole path for interpolating catalog values into shell commands. Never
allow direct f-string interpolation of catalog data into generated shell.

---

### Pitfall 4: VS Code / Cursor extension id casing and `code`/`cursor` not on PATH

**What goes wrong — casing:**
The VS Code CLI and extensions.json store extension ids in lowercase
(confirmed in `vscode.py` line 63: `ext_meta[id_.lower()]`). The marketplace treats ids as
case-insensitive. But `code --install-extension` on some VS Code versions is case-sensitive
in its local-cache lookup: installing `ms-python.python` after `MS-Python.Python` has already
been installed may fail silently or install a duplicate entry.

The catalog emits ids in whatever case the CLI reports (Path A) or extensions.json stores
(Path B). Both normalize to lowercase in the metadata lookup, but the id in the emitted
`emit_item` line comes from `id_` (Path A) which is the raw CLI output — which is lowercase
by convention but not guaranteed. If a publisher ever registers an id with uppercase,
`code --install-extension` with the wrong case may behave unexpectedly.

**What goes wrong — PATH:**
The VS Code `code` CLI and Cursor `cursor` CLI are not on PATH by default on macOS. They are
installed via the VS Code/Cursor "Install 'code' command in PATH" menu action (`Shell Command:
Install 'code' command in PATH`). If a user omitted this step, `code --install-extension` will
fail with `command not found`.

The generated `reinstall.sh` will silently skip all extension installs on a machine where the
CLI is not on PATH. `command -v code || echo "ERROR: ..."` is the minimum safeguard.

**Why it happens:**
On macOS, `/usr/local/bin/code` is a symlink placed by the VS Code shell command installer.
It is not present by default. The reinstall script assumes a fully-configured target machine.

**How to avoid — casing:**
Normalize extension ids to lowercase before emitting `code --install-extension <id>`. The
marketplace lookup is case-insensitive; lowercase is canonical. Do this in the script emitter,
not the parser, so the catalog format is not changed.

**How to avoid — PATH:**
Add a guard at the top of the auto-install section of the generated script:

```bash
# Check for required CLIs
command -v brew >/dev/null 2>&1 || { echo "ERROR: brew not found. Install Homebrew first."; exit 1; }
command -v mas  >/dev/null 2>&1 || { echo "ERROR: mas not found. Run: brew install mas"; exit 1; }
command -v code >/dev/null 2>&1 || echo "WARNING: 'code' not on PATH. VS Code extensions will be skipped."
command -v cursor >/dev/null 2>&1 || echo "WARNING: 'cursor' not on PATH. Cursor extensions will be skipped."
```

Use `echo "WARNING:"` (not `exit 1`) for the editor CLIs — a missing editor CLI is expected
on a machine where that editor is not installed.

**Warning signs:**
- Generated script has no `command -v` guards.
- Extension ids in the generated script are not consistently lowercase.
- No test verifies what the script emits when the catalog contains an id-promoted entry
  (where the "name" field IS the extension id).

**Phase to address:**
Phase 2 (script emitter). Add PATH guards as the first generated block. Normalize extension
ids to lowercase in the emitter. Add a test that generates a script from a catalog with a
mixed-case extension id and verify the output is lowercase.

---

### Pitfall 5: Homebrew multi-version entries cannot be passed to `brew install`

**What goes wrong:**
`HomebrewCollector` emits multi-version entries for packages with multiple installed versions:
`python@3.11 (3.11.1 3.11.2)`. The version string inside the parens is **space-separated
multiple versions**, not a single version. `brew install python@3.11 --version "3.11.1 3.11.2"`
is not valid. `brew install python@3.11` (latest only) is the correct command — the catalog's
multi-version string is metadata, not an installable version spec.

A parser that extracts the full parenthesized string as the version and passes it to brew will
generate a broken command. The correct behavior is: strip the version string from the brew
install command (always install latest), and use the full version string in the comment only.

**Why it happens:**
The multi-version format (`3.11.1 3.11.2` inside parens) is correct for catalog fidelity
(shows what was installed) but is invalid syntax for `brew install --version`. Developers who
write the parser before thinking about the emitter will see a version string and pass it through.

**How to avoid:**
The generated script should NEVER include a version pin for Homebrew packages. The spec
(`PROJECT.md` line 247) already says "install latest, record the cataloged version as a
comment." Enforce this in the emitter:

```python
def brew_install_line(name: str, cataloged_version: str) -> str:
    comment = f"  # cataloged: {cataloged_version}" if cataloged_version else ""
    return f"brew install {shlex.quote(name)}{comment}"
```

The `cataloged_version` is the full string (e.g. `3.11.1 3.11.2`) for the comment — that's
fine. Only the `name` is passed to `brew install`.

**Warning signs:**
- Generated script contains `brew install python@3.11 --version "3.11.1 3.11.2"`.
- Parser passes the version string as an argument rather than a comment.
- Test fixtures only include single-version brew entries.

**Phase to address:**
Phase 1 (catalog parser) — ensure the parser returns `version` as metadata-only. Phase 2
(script emitter) — enforce that no version argument is passed to `brew install`.

---

### Pitfall 6: Never auto-executing — the script must not be sourced or piped to `sh`

**What goes wrong:**
The spec is explicit: "never auto-executed." But there are two common mistakes:
1. **Accidental execution during generation**: the Python code that writes `reinstall.sh`
   uses `subprocess.run(["bash", ...])` or `os.system(...)` at any point during the write.
2. **The script itself has a `set -e` that makes partial execution look like success**: if
   the user runs `bash reinstall.sh` and a `brew install` fails mid-run (e.g. network error),
   `set -e` exits immediately, leaving many packages uninstalled. The user may assume the
   script succeeded because it ran without visible error.

Additionally: the script must be safe to re-run. `brew install` is idempotent (skips already-
installed packages). `mas install` is idempotent. `code --install-extension` with a duplicate
may print a warning but succeeds. The script header should document this: "Safe to re-run."

**How to avoid:**
- The Python writer must ONLY open a file and write strings. Zero subprocess calls to execute
  any install command. Validate this in code review.
- Add `set -e` intentionally but with `|| true` on individual install lines that may harmlessly
  fail (e.g. an extension already installed). Or omit `set -e` and document that errors are
  non-fatal (each `brew install` either succeeds or emits a warning). The second approach is
  friendlier for a first-run script on a fresh machine.
- Add a prominent comment at the top of the generated script:
  ```bash
  #!/usr/bin/env bash
  # Generated by maccat reinstall — REVIEW BEFORE RUNNING.
  # Run: bash reinstall.sh
  # Safe to re-run: already-installed packages are skipped.
  # Generated from: <catalog path> on <date>
  ```
- Permissions: write the script as a regular file (mode `0o644`), not executable (`0o755`).
  Requiring `bash reinstall.sh` rather than `./reinstall.sh` adds one step of intentionality.

**Warning signs:**
- Any `subprocess.run`, `os.system`, or `os.execv` call inside the reinstall script writer.
- The generated file is written with `chmod +x` or `0o755` permissions.
- No prominent "REVIEW BEFORE RUNNING" header in the generated script.

**Phase to address:**
Phase 2 (script emitter). Establish a rule at the start of the phase: the emitter is a
pure string builder; it calls no subprocesses.

---

### Pitfall 7: Version comment incorrectly omitted for id-promoted (name-only) items

**What goes wrong:**
When `emit_item` is called with an empty name and only an id, it produces an id-promoted
line: `"pub.ext"` (no brackets). The parser has no way to distinguish `"pub.ext"` (an
id-promoted extension entry) from `"pub.ext"` (an app whose name happens to look like
a publisher.extension string). More critically: there is no version in the line.

If the reinstall emitter generates `code --install-extension pub.ext` with no version comment
and no indication that the name was degraded, the user has no idea what version was cataloged.
That is acceptable — but the script should note it explicitly, not silently omit the comment:

```bash
code --install-extension pub.ext  # cataloged version unavailable (degraded entry)
```

vs. silently:
```bash
code --install-extension pub.ext
```

The silent form is not wrong, but in a "review before running" script, every line should be
as informative as possible.

**Why it happens:**
The emitter checks "is version non-empty?" and emits the comment if yes, skips if no.
The "why" it's empty (degradation vs. id-promoted vs. genuine missing) is lost at parse time.

**How to avoid:**
The parser should return a structured result with a `degraded: bool` flag (or an enum
`EntryKind.FULL | DEGRADED_NO_VERSION | DEGRADED_ID_PROMOTED`). The emitter uses this flag
to choose between `# cataloged: X.Y.Z` and `# cataloged version unavailable (degraded entry)`.

**Warning signs:**
- The parser return type is `tuple[str, str, str]` (name, version, id) with no degradation flag.
- No test verifies the comment emitted for a name-only catalog line.

**Phase to address:**
Phase 1 (catalog parser). Design the parser return type to carry degradation metadata
before implementing any section-specific parsing.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Assume mas ID is available | Simpler reinstall plan | Broken at runtime — ID is not in the catalog | **Never** — fix the catalog format first or use manual checklist |
| Treat all Homebrew entries as formulae | No re-query needed | `brew install docker` installs wrong artifact | **Never** — fix catalog format or re-query brew at generation time |
| Parse lines by splitting on first `(` | Simple split logic | Mis-parses any app name with embedded parens | **Never** — use right-anchored regex |
| Skip `shlex.quote()` for "safe" names | Cleaner-looking generated script | Shell injection on names with `&`, `'`, `$` | **Never** — always quote |
| `set -e` at top of generated script | Abort on first error | Partially-installed machine looks complete | Acceptable if each risky line adds `|| true` |
| Skip PATH guards for `code`/`cursor` | Less boilerplate in script | Silent skips when CLI not installed | **Never** — always guard, warn not error |
| `brew install name@version` | Pins to cataloged version | Brew has no general version-pin flag; `--version` is not supported for most formulae | **Never** — install latest, version is comment only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `mas install` | Pass app name instead of numeric ID | Must have numeric ID; catalog does not have it — use manual checklist or fix catalog format |
| `brew install` | Pass `--cask` for formulae or omit `--cask` for casks | Must know the type; catalog does not distinguish — fix catalog format with separate sections |
| `brew install` multi-version | Pass `"3.11.1 3.11.2"` as version arg | Strip version from install command; keep as comment only |
| `code --install-extension` | Use display name instead of extension id | Use `[id]` field from catalog; fall back to id-promoted bare value for degraded entries |
| `code --install-extension` | Mixed-case extension id | Normalize to lowercase before emitting |
| Shell command generation | Direct string interpolation of catalog values | Always `shlex.quote()` every catalog-derived value inserted into shell command |
| `mas install` | Assume `mas` is installed and signed in | Guard with `command -v mas`; note that App Store sign-in is a manual prerequisite |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unquoted catalog values in generated script | Shell metacharacter injection (`&`, `` ` ``, `$`, `'`, `"`) corrupts script or executes unexpected commands when script is run | `shlex.quote()` on every catalog-derived value in shell position |
| Auto-executing the generated script | High-impact installs without user review | Pure string-writer only; no subprocess calls in the emitter; write as non-executable `0o644` |
| Newlines in catalog values used in comments | Breaks multi-line comment syntax; may inadvertently inject shell commands | Strip/replace `\n`, `\r`, `\t` from any catalog value used in a comment |

## "Looks Done But Isn't" Checklist

- [ ] **mas ID**: verified against `mas.py` source that the catalog does NOT contain the
      App Store numeric ID — mas auto-install is impossible without a catalog format change.
- [ ] **Formula/cask distinction**: verified against `homebrew.py` source that formulae and
      casks land in one "Homebrew Packages" section with no type marker — correct install flag
      requires a catalog format change or a re-query.
- [ ] **Right-anchored parser**: parser tested against `Smart Photo Widget (Dark).app (3.1.0)`
      and an extension with `(beta)` in its display name — correct name/version split.
- [ ] **Degraded entries**: parser handles name-only, name+id, and id-promoted lines; emitter
      generates `# cataloged version unavailable` (not empty comment) for degraded entries.
- [ ] **Shell quoting**: every catalog-derived value in generated shell commands passes through
      `shlex.quote()`; verified with a fixture containing `AT&T Office@Hand`.
- [ ] **Multi-version brew**: `python@3.11 (3.11.1 3.11.2)` generates `brew install python@3.11`
      (no version arg) with `# cataloged: 3.11.1 3.11.2` comment.
- [ ] **PATH guards**: generated script has `command -v brew`, `command -v mas`, `command -v code`,
      `command -v cursor` guards at the top of the auto-install section.
- [ ] **Non-executable permissions**: `reinstall.sh` written as `0o644`, not `0o755`.
- [ ] **No subprocess calls in emitter**: code review confirms the reinstall writer calls
      `open()` and writes strings — zero `subprocess.run` or `os.system` calls.
- [ ] **Re-run safety**: script contains "Safe to re-run" header comment; tested by running
      against a machine where all packages are already installed (no errors, no re-installs).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| mas ID missing (discovered mid-phase) | MEDIUM | Move mas section to manual checklist; update spec; no catalog format change needed if manual checklist is acceptable |
| Formula/cask mislabeled (discovered mid-phase) | MEDIUM | Move all Homebrew to manual checklist OR add re-query; update spec; catalog format change deferred |
| Shell injection in generated script | HIGH (security) | Add `shlex.quote()` globally; regenerate any scripts already emitted; add fuzz test |
| Parser mis-splits names with embedded parens | LOW | Fix regex to right-anchored; regenerate; test with adversarial names |
| Generated script auto-executes | HIGH (data risk) | Remove any subprocess call immediately; write tests that assert emitter produces only strings |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| mas ID missing — hard constraint | Phase 1 (scope definition) | Read `mas.py` before writing any spec; confirm ID is absent in test fixture |
| Formula/cask distinction missing — hard constraint | Phase 1 (scope definition) | Read `homebrew.py` before writing any spec; confirm both land in one section |
| Parsing ambiguity (embedded parens/brackets) | Phase 1 (catalog parser) | Parser test with `Smart Photo Widget (Dark).app (3.1.0)` and `(beta)` extension name |
| Degraded entry handling | Phase 1 (catalog parser) | Parser test with name-only, name+id, id-promoted catalog lines |
| Shell injection | Phase 2 (script emitter) | Fuzz test with metacharacter names; `shlex.quote()` in all emitter paths |
| Extension id casing | Phase 2 (script emitter) | Test with mixed-case extension id in catalog; output is lowercase |
| PATH guards missing | Phase 2 (script emitter) | Generated script inspected for `command -v` guards before first install line |
| Multi-version brew version arg | Phase 1 (parser) + Phase 2 (emitter) | Test with `python@3.11 (3.11.1 3.11.2)` catalog line; generated line has no `--version` |
| Never auto-execute | Phase 2 (script emitter) | Code review: zero subprocess/exec calls in writer; file permissions are `0o644` |
| Version comment for degraded entries | Phase 2 (script emitter) | Test with name-only line; generated comment says `version unavailable`, not empty |

## Sources

- `src/maccat/collectors/mas.py` — `_parse_mas_output` (lines 27–45): explicit awk-column-skip
  confirms App Store ID is discarded. `tests/collectors/test_homebrew.py` (lines 120–129):
  fixture confirms `"1234567890  Safari (15.0)"` produces `["Safari (15.0)"]`.
- `src/maccat/collectors/homebrew.py` — `collect()` (lines 65–72): formula + cask lists
  concatenated without type marker. `_parse_brew_versions_line` (lines 36–51): multi-version
  space-joined in parens.
- `src/maccat/catalog/format.py` — `emit_item` (lines 16–43): full degradation rule set;
  id-as-name promotion (line 31–32) produces brackets-suppressed output that is syntactically
  indistinguishable from a name-only entry.
- `src/maccat/collectors/vscode.py` — `_collect_editor_extensions` (lines 21–117):
  extension ids normalized to lowercase (`id_.lower()`) for metadata lookup; CLI PATH
  dependency (`shutil.which(cli_name)`); two collection paths (CLI preferred, JSON fallback).
- `src/maccat/collectors/setapp.py` — `SetappCollector` (lines 28–54): emits `AppName.app (version)`
  or bare `AppName.app`; no id field; cannot be auto-installed.
- `src/maccat/collectors/webapps.py` — `WebAppsCollector` (lines 31–54): same pattern as
  Setapp; no id field; cannot be auto-installed.
- `.planning/PROJECT.md` — v2.1.0 milestone spec (lines 64–85): auto-install targets;
  Key Decisions (lines 244–248): install-latest, catalog as source of truth, never auto-execute.
- Python `shlex` documentation — `shlex.quote()` for generating safe shell arguments.

---
*Pitfalls research for: v2.1.0 maccat reinstall — parsing a plain-text catalog and generating a reinstall script*
*Researched: 2026-06-16*

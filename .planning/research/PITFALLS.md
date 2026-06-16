# Pitfalls Research

**Domain:** Porting a battle-tested macOS Zsh cataloger (~2,500 LoC) to a modular Python package at byte-identical output parity, then distributing via `.pyz` zipapp and pipx
**Researched:** 2026-06-14
**Confidence:** HIGH — all failure modes derived from the actual zsh source code (cross-referenced line-by-line), the four prior milestones' defect records (v0.46.0–v0.49.0), and the documented UAT findings from live pty-driven testing

> Scope note: these pitfalls are specific to the Python port and distribution phase (v1.0.0).
> Generic Python style (PEP 8, type hints) and generic packaging best practices are not re-litigated
> here. Every pitfall is either (a) specific to achieving byte-identical parity with the zsh reference,
> (b) a re-introduction risk for a destructive-op bug already fixed in prior milestones, or (c) a
> macOS/zipapp/pipx distribution trap specific to this toolchain. Pitfalls are ordered by severity and
> the phase most likely to encounter them.

---

## Critical Pitfalls

### Pitfall 1: Sort-order divergence between Python and `LC_ALL=C sort -f -u`

**What goes wrong:**
The zsh reference produces every catalog section by piping collected lines through
`LC_ALL=C sort -f -u`. Python's `sorted()` uses the process locale by default. On a macOS machine
with `LANG=en_US.UTF-8` (the default), `sorted()` with no key produces Unicode-aware collation that
differs from C/byte-order collation for any name containing an uppercase letter, a digit prefix, a
non-ASCII character, or a punctuation character. The result is a catalog that looks plausible but
will not diff-empty against the zsh reference on any mixed-case list — which is every section.

Specific divergences:
- C locale byte-order: `A < a < B < b` (uppercase sorts before lowercase at each letter). Unicode
  collation: `A < a` and `B < b` are grouped by letter, so `a` and `A` sort together.
- `sort -f` (fold case): effectively makes the sort case-insensitive by comparing
  case-folded copies, but using byte order as the tiebreaker. Python `key=str.lower` is NOT
  equivalent — it uses Unicode case-folding and Unicode ordering for the tiebreaker, producing a
  different result for items whose lowercased forms are identical.
- `sort -u` on the C locale removes byte-identical duplicates. Python's `dict.fromkeys()` or
  `set()` removes Python-equal duplicates, which for strings with different Unicode normalization
  forms (NFD vs NFC) may differ from byte identity.

**Why it happens:**
The naive translation is `sorted(set(lines), key=str.lower)`. This looks right and produces
identical output for simple ASCII-only lists, causing false confidence. Divergence only appears with
mixed-case items (e.g., `1Password`, `Bitwarden`, `zsh`), extension names with non-ASCII characters
(common in browser extensions), or names where two different Unicode representations exist.

**How to avoid:**
Use the `locale` module with an explicit C-locale comparator, or — more robustly — shell out to
`sort -f -u` with `LC_ALL=C` for the sort step. The cleanest approach that keeps Python in control:

```python
import locale, subprocess

def flush_section(lines: list[str]) -> list[str]:
    if not lines:
        return ["  (none found)"]
    result = subprocess.run(
        ["sort", "-f", "-u"],
        input="\n".join(lines) + "\n",
        capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    return result.stdout.rstrip("\n").splitlines()
```

Alternatively implement C-locale byte-order collation directly in Python:
`sorted(set(lines), key=lambda s: s.casefold().encode("utf-8"))` approximates `-f` with C locale
for pure-ASCII names, but still diverges for non-ASCII. The shell-out is safer and guarantees
byte-identical output with zero maintenance risk.

**Warning signs:**
- Parity tests pass on ASCII-only fixture data but fail on real catalogs with mixed-case names.
- `1Password` and `Bitwarden` sort differently in Python output vs. the zsh reference.
- Any browser extension with a non-ASCII name (accented characters, CJK) breaks sort parity.
- `git diff` between a zsh-generated catalog and the Python equivalent shows reordered lines only
  (content identical, order wrong).

**Phase to address:**
Phase establishing the `flush_section` helper (the first output-producing phase). Never let sort
drift accumulate across multiple collectors — fix it at the shared layer before any collector is
written.

---

### Pitfall 2: `version sort` (`sort -V`) semantics not replicated for Chrome extension versions

**What goes wrong:**
The Chrome collector in the zsh reference selects the highest-installed version directory with
`ls -1 "$ext_dir" | grep -E '^[0-9]' | sort -V | tail -1`. `sort -V` is GNU/BSD version sort:
it compares dotted-numeric segments numerically, so `14.0` > `9.0` > `2.10`. Python's `sorted()`
with no key treats version strings as lexicographic strings, so `9.0 > 14.0 > 2.10` —  the
wrong version directory is selected, and the manifest read targets the wrong directory.

**Why it happens:**
Lexicographic comparison "looks right" for version strings that all have the same number of digits
per segment. It only breaks when segment widths vary (e.g. `9.0` vs `14.0`). Developer tests with
extensions that have only one version directory installed never encounter this path.

**How to avoid:**
Use `packaging.version.Version` from the `packaging` library (always present in any Python
environment that has pip, and explicit in requirements), or implement a simple numeric split:
```python
import re
def version_key(s: str) -> tuple:
    return tuple(int(x) for x in re.split(r'[._-]', s) if x.isdigit())
```
Or shell out to `sort -V` exactly as the zsh reference does — one subprocess call per extension
is wasteful, but correctness first.

**Warning signs:**
- Chrome parity tests fail specifically on extensions that have multiple version directories
  installed simultaneously (common: Chrome keeps old + new during update).
- The Python output picks a lower-numbered version dir for an extension where multiple coexist.

**Phase to address:**
Chrome collector phase. Add a dedicated test fixture with a synthetic extension directory
containing two version subdirectories where lexicographic and version sort disagree (e.g.
`9.0.0_0` and `14.0.0_0`).

---

### Pitfall 3: Trailing whitespace and final-newline differences break byte-identical parity

**What goes wrong:**
The zsh `flush_section` function uses `printf "%s\n" "${_section_lines[@]}" | LC_ALL=C sort -f -u`.
This emits exactly one `\n` per line and no trailing newline after the last line of the section
(the next `write_section` call starts a new line with its `echo "\n$title"`). Python's
`print()` adds `\n`, `str.join("\n", ...)` does not add a trailing newline, and
`subprocess.stdout` from `sort` includes a trailing newline. If the Python layer adds or removes
a trailing newline differently from the reference, every section's byte boundary shifts and all
downstream sections will fail parity even if their content is identical.

Separately, the zsh `write_section` function uses `echo "\n$1"` which emits a literal `\n`
followed by the title followed by `\n` (the echo newline). In Python, `print("\n" + title)` is
equivalent, but `f"\n{title}\n"` written with `file.write()` will differ if `print()` was
already adding a trailing newline. Any asymmetry silently shifts all section offsets by one byte.

**Why it happens:**
Python file I/O, `print()`, `subprocess.stdout`, and `str.join()` each have subtly different
trailing-newline behavior. A developer writing "line by line" naturally uses `print()` which always
appends `\n`, but the reference may emit differently at section boundaries.

**How to avoid:**
- Establish a single output writer abstraction early that exactly replicates the zsh section
  format. Write golden byte-comparison tests against the reference output before implementing
  any collector.
- Open the output file in binary mode (`"wb"`) and encode explicitly, or use `"w"` with
  `newline=""` and always write `\n` explicitly — never rely on platform line endings.
- After implementing `write_section` and `flush_section` equivalents with zero collectors, run
  the empty-catalog parity test first: the header section alone should be byte-identical.

**Warning signs:**
- Parity tests fail with identical content but `b'\n'` vs `b'\n\n'` at section boundaries.
- `xxd` diff shows a single extra `0a` byte offset that shifts every subsequent section.
- Tests pass in isolation but fail in integration (individual sections OK, composition wrong).

**Phase to address:**
Output format foundation phase (first phase). This is the load-bearing prerequisite for all
parity tests. Fix before writing any collector.

---

### Pitfall 4: `dict` / `set` iteration order introduced as a source of non-determinism

**What goes wrong:**
Python 3.7+ dicts preserve insertion order, but sets do not. Any collector that builds a `set` of
items and then iterates it will produce non-deterministic output order. The `_section_lines` pattern
in the zsh reference uses an array (ordered insertion) and only deduplicates at the sort step.
If the Python equivalent uses a `set` for deduplication before the sort, the sort will still
produce deterministic output — but if the set is used directly (forgot to sort), the output
varies run-to-run and across Python interpreter restarts (hash randomization).

More subtle: the `dict.keys()` iteration over a JSON object's keys is insertion-order in Python
(json module preserves JSON object key order), but the zsh reference's `jq to_entries[]` emits
keys in JSON document order, which may differ from alphabetical. If the Python collector
uses a different JSON parsing call that returns keys in a different order, the pre-sort input
differs — this does not affect output correctness if `flush_section` sorts, but it means the
sort is the only determinism guarantee and any skip of `flush_section` will be silently wrong.

**Why it happens:**
Developers coming from Python 2 or unfamiliar with CPython hash randomization (`PYTHONHASHSEED`)
assume `set` iteration is stable. It isn't across process restarts.

**How to avoid:**
- Never iterate a `set` directly into output. Always sort first.
- Use a `list` (not `set`) for `_section_lines` equivalent; let `flush_section` deduplicate
  via `sort -u` / sorted+unique.
- Run tests with `PYTHONHASHSEED=random` (the default) and with an explicit seed to confirm
  output is identical regardless.

**Warning signs:**
- Test output differs between two runs of the same test with no code changes.
- Any `for item in some_set:` pattern in a collector that feeds output.

**Phase to address:**
Output format foundation phase; enforce in code review for every collector.

---

### Pitfall 5: The `/usr/bin/python3` Xcode-CLT stub blocks on a GUI dialog

**What goes wrong:**
On a clean macOS machine that has never run Xcode or installed Command Line Tools, `/usr/bin/python3`
is a stub that launches a GUI dialog: "The 'python3' command requires the command line developer
tools." The process does not exit — it blocks waiting for the user to click a button. A `.pyz`
zipapp with a shebang of `#!/usr/bin/python3` will hang silently on such a machine. A pipx install
instruction that says "requires Python 3" with no further guidance will leave the user staring at
a hung terminal.

This was already documented in the v0.46.0 milestone: the zsh `json_get` function explicitly
removed `python3` from its fallback chain for exactly this reason ("on a clean macOS it is an
xcrun stub that opens a GUI dialog and blocks the script"). The Python port is now taking on
Python 3 as its runtime — it must not create the same hang for its users.

**Why it happens:**
Apple ships the stub to intercept `python3` invocations and prompt for CLT installation. The stub
is at `/usr/bin/python3` and satisfies `command -v python3`, so any check that stops at "python3
exists" will falsely conclude Python is available.

**How to avoid — for the `.pyz` zipapp:**
Use `#!/usr/bin/env python3` rather than a hardcoded `/usr/bin/python3` shebang. This resolves via
`PATH`, finding a real Homebrew/pyenv/system Python if one is installed. If the CLT stub is the
only Python on PATH, the stub triggers — but the failure is immediate (the GUI dialog) rather than
a mysterious hang that looks like the tool is doing work. Additionally, add a startup check in the
`__main__.py` entry point that confirms `sys.version_info >= (3, 9)` and emits a clear error
message with CLT install instructions before doing any real work:

```python
import sys
if sys.version_info < (3, 9):
    print("ERROR: mac-catalog requires Python 3.9+. Install via: xcode-select --install")
    sys.exit(1)
```

**How to avoid — for pipx distribution:**
The README and `pyproject.toml` must declare `python_requires = ">=3.9"`. The pipx install
instruction should include: "Requires Python 3.9+. If you don't have it: `xcode-select --install`
or `brew install python`." Do not assume Homebrew is present either — it is optional.

**How to avoid — for CI / test environments:**
Never rely on `/usr/bin/python3` in CI scripts that run on a fresh macOS runner. Explicitly
install Python via `actions/setup-python` or Homebrew.

**Warning signs:**
- Shebang is `#!/usr/bin/python3` (hardcoded, not `env`).
- The tool hangs with no output on a machine without CLT/Homebrew Python.
- A macOS GitHub Actions runner without `actions/setup-python` invokes the CLT stub.
- The README says "requires Python 3" without installation instructions.

**Phase to address:**
Distribution/packaging phase. The `__main__.py` entry point and the shebang are set there; add
the version guard and the startup message at the same time.

---

### Pitfall 6: Archiving the just-written catalog (main-block ordering regression)

**What goes wrong:**
The v0.47.0 milestone documented and fixed a latent main-block ordering bug: the old
`archive_old_catalogs` was called *before* `generate_catalog`, so the just-written catalog could
be immediately swept into the archive on its first run. The fix was to generate first, then sweep.
The Python port's `main()` function must replicate this exact ordering:

```
select_computer → resolve_archive_retention → git_pull →
generate_catalog (writes OUTPUT_FILE) →
retain_newest_per_host →         # now the new file exists, won't be archived
prune_old_archives →
git_commit_and_push
```

If the Python developer naively calls `retain_newest_per_host` before `generate_catalog` — a
natural mistake when reading the function list top-to-bottom — the new catalog does not exist yet
and the previous catalog for this host will be swept to archive. The user gets a run that writes
a new file and immediately archives it.

**Why it happens:**
The ordering dependency is invisible from the function signatures. `retain_newest_per_host(target_dir)`
and `generate_catalog()` are independent-looking functions. Only the comment in the v0.47.0
MILESTONES.md and the main block's ordering encode this dependency.

**How to avoid:**
The Python `main()` must explicitly follow the documented ordering. Write a test that runs `main()`
twice against the same fixture directory and asserts that after the second run, exactly one catalog
exists in the main folder (not zero, which would indicate the new file was swept) and it is the
second run's file.

**Warning signs:**
- After running the Python tool, the target folder is empty and `archive/` contains both the new
  and the previous catalog.
- The `generate_catalog` call appears after `retain_newest_per_host` in `main()`.

**Phase to address:**
Main orchestration / integration phase. Add the ordering test before any other integration tests.

---

### Pitfall 7: Deleting files with unparseable timestamps (prune-on-parse-failure regression)

**What goes wrong:**
The zsh `prune_old_archives` function explicitly skips any file whose timestamp cannot be parsed:
```zsh
if [[ -z "$timestamp" ]]; then
    echo "  WARNING: Could not parse timestamp from: $filename — skipping"
    continue
fi
```
Likewise `retain_newest_per_host` skips unparseable filenames with a warning. The Python port
must replicate this: any file whose name does not match the expected pattern
`mac-software-list-[label]-YYYYMMDDHHMMSS.txt` must be skipped with a warning, never deleted.

A Python implementation that uses a regex and calls `file.unlink()` on the `except` branch — or
that uses `datetime.strptime()` and treats `ValueError` as "file is old" — will delete files it
cannot interpret.

**Why it happens:**
Defensive-by-default instinct: "if I can't parse the date, the file is probably garbage." But
these files could be hand-placed, from a future version of the tool with a different format, or
from another machine's run. The zsh reference was explicit that unparseable = skip, not delete.

**How to avoid:**
```python
import re, datetime

CATALOG_PATTERN = re.compile(
    r'^mac-software-list-\[.+\]-(\d{14})\.txt$'
)

def parse_catalog_ts(filename: str) -> datetime.datetime | None:
    m = CATALOG_PATTERN.match(filename)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    except ValueError:
        return None
```

In both `retain_newest_per_host` and `prune_old_archives`, if `parse_catalog_ts(filename)` returns
`None`, print a warning and `continue` — never delete.

**Warning signs:**
- `prune_old_archives` or `retain_newest_per_host` calls `file.unlink()` inside an `except` block.
- No test exercises the case where a non-catalog file (e.g. `.gitkeep`, `README.md`) exists in
  the archive directory.
- The function deletes files that match `*.txt` rather than the full catalog pattern.

**Phase to address:**
Retention / prune phase. This is a safety-critical function — write the tests before the
implementation, not after.

---

### Pitfall 8: Tied-newest files: both must be kept

**What goes wrong:**
The zsh `retain_newest_per_host` keeps ALL files whose timestamp equals the maximum for their host
(`if [[ "$ts" == "${newest_ts[$host]}" ]]; then continue`). This is data-loss-averse: if two
machines happen to generate catalogs at the same second (unlikely but possible), neither is
archived. A Python implementation that keeps only one file per host (e.g. using `max()` and then
immediately archiving all non-max files) will delete the tied file.

**Why it happens:**
`max()` returns a single value; the natural translation "keep the max, archive the rest" silently
discards tied-newest files.

**How to avoid:**
Two-pass algorithm matching the zsh reference:
1. Pass 1: compute `max_ts_per_host: dict[str, datetime]`
2. Pass 2: for each file, if `ts == max_ts_per_host[host]`, keep; else archive.

The two-pass approach explicitly handles the tie case without special-casing it.

**Warning signs:**
- The retention function uses `max()` and immediately archives all non-max files in one pass.
- No test covers the tied-timestamp case.

**Phase to address:**
Retention / prune phase. Add a test fixture with two same-host files with identical timestamps.

---

### Pitfall 9: Operating on the wrong repository (app repo vs catalog repo)

**What goes wrong:**
The v1.0.0 milestone introduces a critical architectural change: the Python tool's source code
lives in one repository (the app repo) but the catalog files live in a separate, user-configured
catalog repo. The zsh reference always operated from `SCRIPT_DIR` — the directory containing
the script itself — which was always the catalog repo because the script was committed there.

A Python port that continues to use `Path(__file__).parent` or `os.getcwd()` as the catalog root
will operate on the wrong directory. If the user installs via pipx, `__file__` points into the
pipx venv, not the catalog repo. If the user runs the `.pyz` from an arbitrary location, `cwd`
is wherever they launched it from.

**Why it happens:**
The zsh `SCRIPT_DIR="${0:A:h}"` pattern is so natural in shell that it becomes invisible. In
Python, "where is my source?" and "where should I write?" are entirely separate questions, but
developers porting shell scripts often forget to make this split explicit.

**How to avoid:**
Resolve the catalog repo path via a config file (as required by the v1.0.0 spec):
1. Check `--catalog-repo` / `--repo` flag (highest priority).
2. Check `~/.config/mac-catalog/config.toml` (or equivalent) for `catalog_repo = "/path/to/repo"`.
3. If neither is set, fail fast with a clear error: "No catalog repo configured. Run
   `mac-catalog init` or pass `--catalog-repo /path/to/repo`."

Never fall back to `cwd()` or `__file__`-relative paths. The catalog repo is always explicit.

All git operations (`git_pull`, `git_commit_and_push`, `retain_newest_per_host`, `prune_old_archives`)
must receive the catalog repo path as an explicit parameter, not read a global.

**Warning signs:**
- Any use of `Path(__file__).parent` outside the config-loading module.
- Git operations that run from `os.getcwd()`.
- `machine-labels.tsv` being written to the Python package directory.
- The tool writes a catalog file alongside its own source code.

**Phase to address:**
Config-resolution phase (should be the first phase). No other phase should proceed until the
catalog-repo path resolution is correct and tested.

---

### Pitfall 10: Atomic write omission for `machine-labels.tsv`

**What goes wrong:**
The zsh `upsert_machine_label` uses a `.tmp` file + `mv` pattern:
```zsh
: > "$tmp_file"   # truncate without invoking NULLCMD
# ... write to tmp_file ...
mv "$tmp_file" "$map_file"
```
This ensures that a crash or interrupt mid-write leaves either the old complete file or the new
complete file, never a partially-written corrupt file. A Python implementation that opens
`machine-labels.tsv` directly and writes line-by-line will corrupt the file if the process is
interrupted.

The same applies to any other file the Python tool writes: the output catalog itself should be
written to a temp file and atomically renamed. A partial catalog is worse than no catalog because
it looks complete but is truncated.

**Why it happens:**
Python's `open(path, "w")` is concise and feels safe. The interruption risk is low. But the zsh
tool went to explicit effort to use atomic writes — the Python port should not regress this.

**How to avoid:**
Use Python's `tempfile.NamedTemporaryFile` + `os.replace()` for all writes to persistent files:
```python
import tempfile, os

def atomic_write(path: Path, content: str) -> None:
    dir_ = path.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as f:
        f.write(content)
        tmp = f.name
    os.replace(tmp, path)
```
`os.replace()` is atomic on POSIX (single filesystem). Use it for `machine-labels.tsv`,
the catalog output file, and any config file the tool writes.

**Warning signs:**
- `open(map_file, "w")` with incremental writes and no temp file.
- No test verifies that a simulated mid-write interrupt leaves a valid file.

**Phase to address:**
Output writing phase / `machine-labels.tsv` upsert phase. Establish `atomic_write` as a shared
utility before the first write.

---

### Pitfall 11: `--rename` refuse-clobber regression (merging two computer folders)

**What goes wrong:**
The zsh `rename_machine` function has a HARD refuse-clobber guard:
```zsh
if [[ -e "$new_dir" ]]; then
    echo "ERROR: A computer named '${new_name}' already exists. Refusing to merge. Nothing renamed."
    exit 1
fi
```
This prevents renaming "office" to "personal" when "personal" already exists, which would merge two
computers' catalogs into one folder — an irreversible data corruption. A Python port that uses
`shutil.move()` or `Path.rename()` without checking for destination existence first will silently
merge the folders on some OS configurations (or raise `FileExistsError` with a confusing message
on others).

**Why it happens:**
`shutil.move()` docs say it "may" raise on conflicts; behavior varies by OS and filesystem. The
zsh reference made the check explicit and unconditional.

**How to avoid:**
Check `new_dir.exists()` explicitly before any `shutil.move()` or `Path.rename()` call.
Raise a user-visible error (not an exception traceback): "ERROR: Computer '{name}' already exists.
Refusing to merge. Nothing renamed." and exit with code 1.

**Warning signs:**
- `shutil.move(old_dir, new_dir)` without a prior `if new_dir.exists(): ...` check.
- No test covers the rename-to-existing-name case.

**Phase to address:**
Rename command phase.

---

### Pitfall 12: `git add` leading-dash injection in computer folder names

**What goes wrong:**
The v0.49.0 UAT found that `git add` without `--` mis-parses leading-dash pathspecs as options.
The zsh fix was:
```zsh
git add -A -- "${old_name}/" 2>/dev/null || true
git add -A -- "${new_name}/" 2>/dev/null || true
```
A Python port that uses `subprocess.run(["git", "add", "-A", f"{folder}/"])` without `--` will
fail silently (or raise) when the computer folder name begins with `-`. The computer name validator
permits a leading dash (the validator only rejects `/`, `[`, `]`, TAB, newline), so this is a
real user-triggerable failure.

**Why it happens:**
The Python developer knows `subprocess` with a list avoids shell injection, but `--` is still
needed to tell git to stop parsing options. "It works in testing because no test folder starts
with `-`."

**How to avoid:**
Always use `["git", "add", "-A", "--", f"{folder}/"]` in all git subprocess calls that accept
user-provided pathspecs. Apply the same `--` guard to all `git add`, `git rm`, `git diff`, and
`git log` calls that take pathspec arguments derived from user input.

**Warning signs:**
- Any `subprocess.run(["git", "add", ...])` that does not include `"--"` before a user-derived
  path.
- No test uses a computer folder name beginning with `-`.

**Phase to address:**
Git operations phase. Add a test with a folder named `-test-folder`.

---

### Pitfall 13: zipapp `__file__`-relative access and data file embedding

**What goes wrong:**
A `.pyz` zipapp runs from inside a zip archive. `__file__` is set to a path *inside* the zip
(e.g. `/path/to/mac-catalog.pyz/mac_catalog/__init__.py`). Any code that tries to read a file
relative to `__file__` using `Path(__file__).parent / "data/something"` will fail because the
parent is inside a zip, not a real directory, and `open()` cannot read from inside a zip via
a plain path.

This affects:
- Any bundled data file (e.g. the Chrome component extension denylist, if it is a file rather
  than an in-code constant).
- Any test fixture that tries to `import` from the installed package and then reads sibling files.
- `importlib.resources` is the correct API for reading package data from inside a zip, but it has
  a different API shape from `open(Path(__file__).parent / "data/file")`.

Additionally, zipapp cannot include C extensions (`.so` / `.dylib` files). If any dependency
pulls in a C extension at install time (e.g. a version of `packaging` that has a C fast-path),
the `.pyz` build will either fail to include it or silently skip it, causing `ImportError` at
runtime.

**Why it happens:**
`Path(__file__).parent` works fine in a regular install or virtualenv, so developers use it without
thinking about the zip case. The breakage is invisible until the `.pyz` is actually run.

**How to avoid:**
- Keep all data inline as Python constants (e.g. the Chrome component denylist as a `frozenset`
  in a module). This project's data is small enough that no external data files are needed.
- Use `importlib.resources.files(__package__).joinpath("data/file").read_text()` for any
  unavoidable data files — this is zip-safe.
- In the `.pyz` build script, explicitly check that no `.so` / `.dylib` files were included:
  `python -m zipfile -l mac-catalog.pyz | grep -E '\.(so|dylib)$'` should return empty.
- Test the `.pyz` artifact itself (not the development install) as part of the distribution phase.

**Warning signs:**
- `Path(__file__).parent / "..."` used to locate bundled data.
- The build step produces a `.pyz` without verifying it on a clean venv.
- `ImportError` for a package that is definitely in requirements when running the `.pyz`.

**Phase to address:**
Distribution/packaging phase. Validate the `.pyz` artifact specifically, not just the package.

---

### Pitfall 14: Non-TTY hang in interactive menus (cron / pipe regression)

**What goes wrong:**
The zsh `select_computer` has a TTY guard:
```zsh
if [[ ! -t 0 ]]; then
    echo "ERROR: No computer selected and stdin is not a TTY. Pass --computer \"Name\"."
    exit 1
fi
```
Python's `input()` will raise `EOFError` on closed stdin, but it will *block* on open-but-non-TTY
stdin (e.g. a pipe with no data, `echo | mac-catalog`). In a cron job where stdin is `/dev/null`,
`input()` immediately raises `EOFError` — but if stdin is a pipe or a pseudo-terminal with a
connected process that hasn't sent EOF, `input()` blocks indefinitely.

The v0.49.0 UAT found a `NULLCMD` stdin-hang in the zsh tool's `upsert_machine_label` when a bare
`> file` redirect was used instead of `: > file`. The Python port will face the equivalent: any
`input()` or `sys.stdin.read()` call in a non-menu path (e.g. a fallback in a helper) can hang.

**Why it happens:**
`input()` is the natural Python analog of `read -r`. Its blocking behavior on non-TTY non-EOF
stdin is correct per spec but wrong for a tool meant to run non-interactively when given `--computer`.

**How to avoid:**
Gate all `input()` calls with an explicit TTY check:
```python
import sys

def is_tty() -> bool:
    return sys.stdin.isatty()

def prompt(msg: str) -> str:
    if not is_tty():
        raise RuntimeError(f"Interactive prompt required but stdin is not a TTY. Use --computer flag.")
    return input(msg)
```
Call `prompt()` everywhere instead of `input()` directly. The TTY check runs before any blocking
call. For EOF (`Ctrl-D`), catch `EOFError` at the call site and treat it as a clean quit.

**Warning signs:**
- Direct `input()` calls anywhere in the non-flag code paths.
- No test verifies that running with `sys.stdin = io.StringIO("")` (empty non-TTY stdin) fails
  fast rather than hanging.
- `resolve_archive_retention` equivalent does not check `is_tty()` before prompting.

**Phase to address:**
Interactive menu / CLI phase. Add the `is_tty()` utility before any interactive prompt is written,
and test it with a patched `sys.stdin`.

---

### Pitfall 15: EOF / Ctrl-D input loop regression

**What goes wrong:**
The v0.49.0 UAT found an EOF infinite-loop at the rename prompt: the zsh script had `read -r
choice` without `|| ...` to catch EOF, which caused the loop to spin on an empty string forever
when stdin was closed. The fix was `if ! read -r choice; then choice="$quit_idx"; fi`.

Python's `input()` raises `EOFError` on Ctrl-D. If the EOF exception is not caught at the prompt
loop level, it will propagate up and produce a traceback instead of a clean quit. If it is caught
and the loop continues, it creates the same infinite-loop as the zsh bug.

**Why it happens:**
`except EOFError: continue` looks like graceful handling but recreates the infinite loop.
`except EOFError: raise` shows a traceback. The correct behavior — `except EOFError: return QUIT`
— is the non-obvious third option.

**How to avoid:**
```python
while True:
    try:
        choice = prompt("Enter your choice: ")
    except EOFError:
        return QuitSelection()   # clean exit, no traceback, no loop
    # validate choice...
```
Test this with a patched `sys.stdin` that immediately closes (raises `EOFError` on first read).

**Warning signs:**
- `except EOFError: continue` in any input loop.
- No test exercises the EOF path for the computer selection menu and the rename menu.

**Phase to address:**
Interactive menu phase. Test all three interactive menus (computer select, create-new, rename) with
EOF-on-first-read.

---

### Pitfall 16: `--version` drift between `pyproject.toml` and runtime

**What goes wrong:**
The `.pyz` artifact's version as reported by `mac-catalog --version` can drift from the version in
`pyproject.toml` if the version is hardcoded as a string in `__main__.py` or in a `__version__`
variable that is not synchronized with the build metadata. A user who installs `mac-catalog==1.0.0`
but gets `mac-catalog --version` → `0.9.0-dev` has a confusing support experience.

**Why it happens:**
`pyproject.toml` version and `__version__` in code are two separate sources of truth. They drift
when one is updated without the other, or when the `.pyz` is built from a working tree with local
modifications.

**How to avoid:**
Use `importlib.metadata` to read the version at runtime from the installed package metadata:
```python
from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("mac-catalog")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
```
This works in both a regular install and a `.pyz` (which includes `PKG-INFO` / `METADATA`).
Never hardcode the version string in source code.

**Warning signs:**
- `__version__ = "1.0.0"` literal in `__main__.py` or `__init__.py`.
- `mac-catalog --version` output differs from `pip show mac-catalog` output.

**Phase to address:**
Distribution/packaging phase.

---

### Pitfall 17: Committing the `.pyz` binary to git

**What goes wrong:**
A `.pyz` zipapp is a binary artifact. Committing it to the source repo means git stores a full
copy of the binary on every change (git does not delta-compress binaries well). More importantly,
it creates an "install by cloning the repo" pattern that conflicts with the pipx distribution
channel, and it means the binary in git may not match the current source state.

**Why it happens:**
"Just commit the artifact" is a low-friction way to distribute to the first few users without
setting up a proper release pipeline.

**How to avoid:**
- Add `*.pyz` to `.gitignore`.
- Build the `.pyz` as part of a `make dist` / `build.sh` script that is checked in, not the
  artifact itself.
- Distribute via GitHub Releases (attach the `.pyz` as a release asset) or via PyPI + pipx.
- The CI pipeline builds the `.pyz` and attaches it to a tagged release — never commits it.

**Warning signs:**
- `git status` shows a `.pyz` file as tracked.
- The README says "clone this repo and run the `.pyz`."

**Phase to address:**
Distribution/packaging phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `sorted(set(lines), key=str.lower)` instead of `LC_ALL=C sort -f -u` | No subprocess call | Parity failures on mixed-case and non-ASCII names; silently wrong | **Never** — shell out or use C-locale collation |
| `Path(__file__).parent` for config/data reads | Works in dev install | Breaks inside a `.pyz` zipapp | Only in `__main__` entry point (not inside zip) |
| Hardcoded `/usr/bin/python3` shebang | Unambiguous path | Hangs on clean macOS that hits CLT stub | **Never** — use `#!/usr/bin/env python3` |
| Skip atomic writes for catalog output | Simpler code | Partial file on interrupt looks complete but is truncated | **Never** — always write to temp + rename |
| Read catalog repo from `cwd()` | Zero config needed | Wrong directory when installed via pipx | **Never** — always require explicit config |
| `input()` without TTY guard | Natural Python idiom | Hangs in cron/pipe; blocks non-interactive runs | **Never** — always check `isatty()` first |
| Commit the `.pyz` binary to git | Easy first distribution | Binary bloat; version drift; conflicts with release pipeline | Only as a one-time emergency; remove immediately |
| Inline the Chrome denylist as a hardcoded set | Simple | Easy to miss updates | Acceptable — the 10-ID denylist is stable |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `git add` with user-provided folder names | `["git", "add", "-A", folder]` — dash-prefixed names parsed as options | Always include `"--"` before any user-derived pathspec |
| `git` subprocess in pipx-installed tool | `os.chdir(catalog_repo)` then git commands | Pass `-C catalog_repo` to git, or use `cwd=` in `subprocess.run()` — never mutate global cwd |
| `machine-labels.tsv` write | `open(path, "w")` | Atomic: write to `.tmp`, then `os.replace()` |
| `sort -V` for Chrome version selection | Python `sorted()` | Use `packaging.version.Version` or shell out to `sort -V` |
| `LC_ALL=C sort -f -u` | `sorted(set(lines), key=str.lower)` | Shell out with `env={"LC_ALL": "C"}` or use a C-locale-aware comparator |
| `prune_old_archives` timestamp parse | Delete on `ValueError` | Log warning and `continue` — never delete files with unparseable names |
| Rename destination check | `shutil.move()` without existence check | Always `if new_dir.exists(): error` before any move |
| Non-TTY interactive prompts | Direct `input()` | Gate with `sys.stdin.isatty()` check; fail fast with clear message |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Spawning one subprocess per sort call | Hundreds of `sort` processes for large extension lists | Collect all lines for a section, then one `sort` subprocess per `flush_section` call | Large extension installs (100+ VS Code extensions) |
| `subprocess.run(["jq", ...])` for every JSON field | Slow Chrome/Firefox collection | Batch jq calls (one call per file, not one per field) or use Python's `json` module | Large Chrome extension count |
| `git add` one file at a time in commit | Many git subprocess calls | Stage the whole folder with `git add -A -- folder/` | Large archive sweeps |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| MCP secret re-introduction | Credentials committed to git history | Port the FMT-03 guards exactly: name + transport only; never env/headers/args/url |
| Config file containing catalog repo path is world-readable | Other users on the machine can learn the repo path | Config file permissions should be `0o600`; document this |
| Shell injection via `subprocess` with `shell=True` | User-controlled computer names could inject shell commands | Always use `subprocess.run([...list...], shell=False)` — the default |
| `os.system()` with any user-controlled string | Same as above | Never use `os.system()` in this codebase |

## "Looks Done But Isn't" Checklist

- [ ] **Sort parity:** `LC_ALL=C sort -f -u` semantics verified with a mixed-case fixture including
      at least one non-ASCII extension name — Python output matches zsh output byte-for-byte.
- [ ] **Final-newline parity:** Section boundaries (between `write_section` calls) verified at byte
      level, not just line-content level — use `xxd` or `bytes` comparison in tests.
- [ ] **TTY guard:** Running with `echo "" | mac-catalog` (non-TTY stdin, no `--computer` flag) exits
      with a clear error message, does not hang.
- [ ] **EOF handling:** Ctrl-D at the computer selection menu and the rename menu produces a clean
      "No catalog written." exit, not a traceback and not an infinite loop.
- [ ] **Catalog repo path:** Running from an arbitrary working directory (not the catalog repo) with
      no config produces a clear "no repo configured" error, not a silently wrong write.
- [ ] **Atomic writes:** `machine-labels.tsv` written via temp+rename; partial write on interrupt
      leaves the old complete file intact.
- [ ] **Ordering (main block):** After two runs, main folder has exactly one catalog (the newer),
      archive has the older — not zero in main and both in archive.
- [ ] **Unparseable-filename safety:** A non-catalog `.txt` file in the archive is not deleted by
      `prune_old_archives`.
- [ ] **Zipapp data access:** `.pyz` artifact runs correctly from any working directory with no
      `__file__`-relative path errors.
- [ ] **CLT-stub guard:** `--version` flag (which requires no config) prints version and exits on a
      machine where `/usr/bin/python3` is the stub — the startup check fires before any stub hang.
- [ ] **`git add --` guard:** A computer folder named `-test` stages correctly; git does not
      interpret the dash as an option.
- [ ] **Refuse-clobber rename:** Renaming "office" to "personal" when "personal" exists fails with
      a clear error and leaves both folders intact.
- [ ] **Tied-newest retention:** Two same-host catalogs with identical timestamps are both kept in
      the main folder after `retain_newest_per_host`.
- [ ] **MCP secrets (re-check):** The Python collectors replicate the FMT-03 guards; grep the
      generated catalog for `token`, `Bearer`, `sk-`, `ghp_`, `key=`, `Authorization` → zero hits.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Sort divergence found after parity tests pass | MEDIUM | Replace Python sort with LC_ALL=C subprocess; regenerate golden fixtures; re-run parity suite |
| CLT-stub hang shipped in `.pyz` | LOW | Change shebang to `#!/usr/bin/env python3`; add startup version check; rebuild `.pyz` |
| Archiving just-written catalog | LOW | Reorder `main()` calls; add ordering test; re-run |
| Prune deleted unparseable files | HIGH (data loss) | Cannot recover deleted files; add the skip guard immediately; audit git history for lost catalogs |
| Catalog repo written to wrong directory | MEDIUM | Add `--catalog-repo` to config; move misplaced files manually; add the config-resolution test |
| `.pyz` committed to git | LOW | Add `*.pyz` to `.gitignore`; `git rm --cached *.pyz`; move to release artifacts |
| Atomic write regression (partial file) | LOW | Replace `open(path, "w")` with `atomic_write()`; partial files are detectable (truncation) |
| Refuse-clobber regression (merged folders) | HIGH (data loss) | Cannot easily un-merge two folders; add guard immediately; restore from git history |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Sort-order divergence (LC_ALL=C) | Output format foundation (first phase) | Byte-identical parity test with mixed-case + non-ASCII fixture |
| `sort -V` for Chrome versions | Chrome collector phase | Test with two-version-dir fixture where lex != version sort |
| Trailing-newline / section boundary | Output format foundation (first phase) | Binary byte comparison of empty catalog against zsh reference |
| `dict`/`set` non-determinism | Output format foundation; enforce in review | `PYTHONHASHSEED=random` parity test passes consistently |
| `/usr/bin/python3` CLT stub | Distribution/packaging phase | Startup version-check test; shebang uses `env` |
| Main-block ordering regression | Main orchestration / integration phase | Two-run test: main folder has exactly one (newer) catalog |
| Unparseable-timestamp delete | Retention / prune phase | Non-catalog file in archive survives prune run |
| Tied-newest retention | Retention / prune phase | Two same-host same-timestamp files both kept |
| Wrong catalog repo (app vs catalog repo) | Config-resolution phase (first phase) | Running from `/tmp` with config pointing to real repo writes there, not `/tmp` |
| Atomic write omission | Output writing phase | Simulated interrupt test; old file survives |
| Refuse-clobber rename regression | Rename command phase | Rename-to-existing-name test returns error code 1, both folders intact |
| `git add` leading-dash injection | Git operations phase | Test with folder named `-test`; verify `git add -- -test/` stages correctly |
| zipapp `__file__` / data files | Distribution/packaging phase | Run `.pyz` from `/tmp`; no path errors; `zipfile -l` shows no `.so` |
| Non-TTY hang | Interactive menu / CLI phase | `echo "" | mac-catalog` exits fast with clear error |
| EOF infinite loop | Interactive menu / CLI phase | EOF-on-first-read test for all three interactive menus |
| `--version` drift | Distribution/packaging phase | `mac-catalog --version` matches `pyproject.toml` version |
| Committing `.pyz` binary | Distribution/packaging phase | `.gitignore` includes `*.pyz`; CI attaches to release asset |

## Sources

- `update-list.sh` — the authoritative zsh reference, read line-by-line for this analysis:
  `upsert_machine_label` (atomic write, NULLCMD guard), `retain_newest_per_host` (tied-newest,
  unparseable-skip), `prune_old_archives` (skip-on-parse-fail), `rename_machine` (refuse-clobber,
  `git add --` guard), `select_computer` (TTY guard, EOF-as-quit), `resolve_archive_retention`
  (non-TTY default), `flush_section` (`LC_ALL=C sort -f -u`), `json_get` (python3-stub warning).
- `.planning/MILESTONES.md` — v0.47.0: latent main-block ordering bug; v0.49.0: four live UAT
  defects (bare-local echo, NULLCMD hang, git-add dash-injection, EOF infinite loop).
- `.planning/PROJECT.md` — Context section: python3 CLT-stub warning, testing hazard, v0.49.0
  UAT defect list; Key Decisions: Python port rationale, zipapp/pipx distribution target,
  catalog-repo separation, parity tests as safety gate.
- Python zipapp documentation (https://docs.python.org/3/library/zipapp.html) — `__file__` inside
  zip, no C extensions, shebang format.
- macOS developer documentation — `/usr/bin/python3` CLT stub behavior (Apple Developer Forums,
  confirmed in v0.46.0 MILESTONES.md footnote).

---
*Pitfalls research for: Python port of a macOS Zsh cataloger (v1.0.0 — byte-parity rewrite + zipapp/pipx distribution)*
*Researched: 2026-06-14*

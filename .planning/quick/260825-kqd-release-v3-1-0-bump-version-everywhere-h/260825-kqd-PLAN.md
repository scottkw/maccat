---
phase: quick
plan: 260825-kqd
type: execute
wave: 1
depends_on: []
files_modified:
  - src/maccat/__init__.py
  - pyproject.toml
  - README.md
  - src/maccat/reinstall/emitter.py
  - tests/reinstall/test_emitter.py
  - src/maccat/collectors/base.py
  - src/maccat/cli.py
  - tests/test_cli.py
autonomous: true
requirements: [release-v3-1-0-version-bump, emitter-banner-hardening, dead-code-triage]

estimate:
  tokens: 52000
  raw_tokens: 52000
  tasks: 4
  confidence: low

must_haves:
  truths:
    - "`maccat --version` reports `maccat 3.1.0` and the installed distribution metadata reports 3.1.0 — the two authoritative version locations agree"
    - "Catalog frontmatter is stamped `maccat_version: \"3.1.0\"`, and the README's sample output shows the same value"
    - "The release workflow's two `sed` patterns still each match exactly one line, so tag-driven stamping keeps working"
    - "A section title containing `\"`, `$(...)`, a backtick or `\\` cannot inject a command into the generated reinstall.sh banner"
    - "For every metacharacter-free section title the emitted reinstall.sh bytes are unchanged — the full 712-test suite still passes"
    - "`Collector.available()` still exists and still returns True by default; the orchestrator still calls every collector's `collect()` unconditionally"
    - "`Collector.degraded_result` no longer exists on the class"
    - "A warning appended to `CollectorResult.warnings` is printed to stderr by the orchestrator instead of being discarded"
    - "Catalog file bytes are unaffected by the warnings change — warnings go to stderr only"
  artifacts:
    - path: "src/maccat/__init__.py"
      provides: "`__version__ = \"3.1.0\"`"
    - path: "pyproject.toml"
      provides: "`version = \"3.1.0\"` in [project]"
    - path: "src/maccat/reinstall/emitter.py"
      provides: "`safe_banner_value()` helper and its sole use at the editor-extension banner"
    - path: "tests/reinstall/test_emitter.py"
      provides: "Banner byte-stability lock plus adversarial banner-title execution tests"
    - path: "src/maccat/collectors/base.py"
      provides: "Documented `available()` rationale, documented `warnings` contract, `degraded_result` removed"
    - path: "src/maccat/cli.py"
      provides: "Collector loop that drains `result.warnings` to stderr and documents why it does not gate on `available()`"
    - path: "tests/test_cli.py"
      provides: "Stub-collector test proving warnings reach stderr"
  key_links:
    - from: "_editor_ext_block banner"
      to: "safe_banner_value()"
      via: "f-string interpolation of the sanitized title inside the double-quoted echo argument"
      pattern: "safe_banner_value"
    - from: "cli.py collector loop"
      to: "CollectorResult.warnings"
      via: "for-loop printing each warning to sys.stderr"
      pattern: "result.warnings"
    - from: ".github/workflows/release.yml"
      to: "src/maccat/__init__.py and pyproject.toml"
      via: "anchored sed patterns ^__version__ = \".*\" and ^version = \".*\""
      pattern: "sed -i -E"
---

<objective>
Cut the v3.1.0 release in-repo and clear three code-health findings from
`.planning/codebase/CONCERNS.md` (regenerated 2026-08-25).

Four independent changes:

1. **Version bump to 3.1.0** — the two authoritative version locations currently disagree
   (`__init__.py` says 3.0.0, `pyproject.toml` says 2.1.0). Both become 3.1.0, plus the two
   illustrative `maccat_version` lines in the README sample output.
2. **Emitter banner hardening** — close the one unquoted catalog-value interpolation in
   `reinstall/emitter.py` without changing a single emitted byte for normal titles.
3. **Dead-code triage, part 1** — delete `Collector.degraded_result()` (genuinely dead) and
   document why `Collector.available()` is deliberately NOT called by the orchestrator.
4. **Dead-code triage, part 2** — make `CollectorResult.warnings` a live channel by draining it
   to stderr in the orchestrator loop.

Purpose: ship a coherent version number, remove a latent shell-injection class before a routing
change makes it live, and stop three findings from being re-reported as "dead code" next time the
codebase map is regenerated.
Output: a version-consistent tree, one new emitter helper, one deleted method, one wired warning
channel — with the full suite, ruff and mypy --strict all still green.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/maccat/collectors/base.py
@src/maccat/reinstall/emitter.py
@src/maccat/cli.py

## Baseline verified during planning — do not re-derive

Measured on the working tree immediately before this plan was written:

- `./venv/bin/python -m pytest -q` → **712 passed in 3.17s**
- `./venv/bin/ruff check src tests` → All checks passed
- `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` → Success: no issues found in 42 source files

These three are the regression gate. Any drop from 712 is a failure, not a "pre-existing issue".

## Version locations — exhaustive, verified by grep

| Location | Current | Action |
|---|---|---|
| `src/maccat/__init__.py:3` | `__version__ = "3.0.0"` | → `3.1.0` |
| `pyproject.toml:7` | `version = "2.1.0"` | → `3.1.0` |
| `README.md:295` | sample-output frontmatter | → `3.1.0` |
| `README.md:334` | sample-output frontmatter | → `3.1.0` |
| `README.md:7`, `:9`, `:160` | prose `v3.0.0` = the **format-change milestone** | **DO NOT TOUCH** — historical fact |
| `tests/helpers/test_plist_version.py:97,103` | `CFBundleShortVersionString` fixture | **DO NOT TOUCH** — unrelated plist value |
| `scripts/build-pyz.sh` | no version handling at all | nothing to do |

There is no CHANGELOG.md in this repo. `tests/test_pyz.py:137-149` reads `maccat.__version__`
dynamically, so it needs no edit.

**Release workflow compatibility (verified):** `.github/workflows/release.yml` runs
`sed -i -E "s/^__version__ = \".*\"/…/" src/maccat/__init__.py` and
`sed -i -E "s/^version = \".*\"/…/" pyproject.toml`, then asserts `maccat --version` equals
`maccat <tag>`. Each anchored pattern matches **exactly one line** today and still matches exactly
one line after the bump (confirmed: `grep -cE` → 1 for both). The bump is workflow-safe.

**Do NOT create a git tag and do NOT push.** Version bump in files only.

## Emitter banner — why `quote_for_script()` is the WRONG tool here

`emitter.py:185` is the only interpolated banner in the file:

    lines: list[str] = [f'echo "=== {section.title} ==="']

Lines 90, 153 and 292 are hardcoded literals and need no change. Line 220
(`_manual_checklist_block`) already `shlex.quote`s its title correctly.

`quote_for_script()` is `shlex.quote()`. Applied to `=== VS Code Extensions ===` it returns
`'=== VS Code Extensions ==='` — **single** quotes — which changes the emitted bytes for every
normal title and risks the emitter/parser round-trip contract that this milestone's STATE.md calls
"the central invariant". So: do not use it here.

The file already solves the analogous "wrong context for shlex.quote" problem with
`safe_comment_value()` at line 36 (newline-stripping for `#` comment context). Follow that
established pattern: add a third context-specific gate for double-quoted `echo` argument context.

Today the injection is unreachable only because routing is exact-match through
`SECTION_SOURCE_MAP` (line 230-235), so `section.title` is always a dict literal. That safety is an
emergent property of the routing table, not a local property of the function — any future move to
prefix/suffix/regex matching makes it live. Close it now.

## CORRECTION to the brief — verified by grep, affects how Task 4's test is written

The brief states `CollectorResult.warnings` "is populated by `collectors/vscode.py:134` and
`collectors/cursor.py:30`". Those two lines only **pass through** the list. Grepping
`warnings.append` across `src/` and `tests/` returns **zero hits** — `_collect_editor_extensions`
declares `warnings: list[str] = []`, never appends to it, and returns it empty.

The degradation messages the brief is worried about (`NOTE: Cursor not installed…`,
`WARNING: code CLI returned empty list…`) are **already printed directly to stderr** at
`vscode.py:81-84` and `vscode.py:88-91`. Nothing is being silently swallowed today.

**Consequence for the executor:** the channel has zero producers, so a test asserting
`VSCodeCollector` emits warnings would fail. Task 4's test MUST use a stub collector.
The fix is still worth doing — it converts an always-discarded field into a live, documented,
tested channel so a future collector can report degradation without inventing its own print — but
do **not** rewrite vscode.py's existing direct stderr prints into `warnings.append` calls. That
would relocate working, already-tested output and is out of scope for the smallest correct diff.

## Chesterton's Fence — the three findings have three different outcomes

`Collector.available()` — **KEEP. Do not delete. Do not wire into the orchestrator.** Three real
callers self-guard inside their own `collect()` (`setapp.py:37`, `mas.py:58`, `homebrew.py:62`);
`tests/collectors/test_setapp.py:313-314` asserts the base default; `webapps.py:28` carries an
explicit comment about relying on that default. Gating the orchestrator loop on it would suppress
the notice sections that absent-tool collectors must still emit (HomebrewCollector emits a
`"Homebrew is not installed."` section) and would destabilise the 22-section set.

`Collector.degraded_result()` — **DELETE.** Zero call sites in `src/`, zero references in `tests/`
(grep-confirmed: the only hit is the definition itself). The single deletion in this plan.

`CollectorResult.warnings` — **KEEP and wire.** See the correction above.

## Scope guard

Do not restructure `Collector`, do not change any collector's public signature, do not touch
`SECTION_SOURCE_MAP` routing, do not alter catalog output bytes, do not add a dependency, do not
touch `.github/workflows/release.yml`, do not create a tag, do not push, do not update ROADMAP.md.

**Tracer-first is deliberately not used here** (`--no-tracer` rationale): these are four orthogonal
edits to an already-proven architecture with no shared layered path. A synthetic vertical slice
would add no information.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bump the version to 3.1.0 in both authoritative locations and the README samples</name>
  <files>src/maccat/__init__.py, pyproject.toml, README.md</files>
  <action>
    Set `__version__` in `src/maccat/__init__.py` to `3.1.0`, keeping the line's exact existing
    shape (`__version__ = "X"` starting at column 0, no added whitespace) so the release workflow's
    anchored sed pattern still matches.

    Set the `version` key under `[project]` in `pyproject.toml` (line 7) to `3.1.0`, likewise
    keeping the line anchored at column 0 in its current `version = "X"` shape. Do not touch
    `requires-python`, and do not add any other key whose line begins with `version = ` — the
    release workflow's unranged sed would rewrite it too.

    In `README.md`, update the two sample-output frontmatter lines (lines 295 and 334) whose key is
    `maccat_version` so both show 3.1.0. These are illustrative catalog output only.

    Leave the three prose mentions of v3.0.0 in `README.md` (lines 7, 9, 160) exactly as they are —
    they describe the milestone at which the catalog format changed from plain text to Markdown,
    which is a historical fact that this release does not alter. Leave
    `tests/helpers/test_plist_version.py` completely untouched; the value there is a
    `CFBundleShortVersionString` plist fixture with no relation to the package version.

    Make no other edit in this task. Do not create a git tag and do not push.
  </action>
  <verify>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; PYTHONPATH=src ./venv/bin/python -m maccat --version | grep -qx 'maccat 3.1.0' &amp;&amp; echo VERSION_OK</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; test "$(grep -cE '^version = \"3\.1\.0\"$' pyproject.toml)" = 1 &amp;&amp; test "$(grep -cE '^version = \".*\"$' pyproject.toml)" = 1 &amp;&amp; test "$(grep -cE '^__version__ = \".*\"$' src/maccat/__init__.py)" = 1 &amp;&amp; echo SED_PATTERNS_OK</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; test "$(grep -c 'maccat_version:' README.md)" = 2 &amp;&amp; test "$(grep -c 'maccat_version: \"3.1.0\"' README.md)" = 2 &amp;&amp; test "$(grep -c 'v3\.0\.0' README.md)" = 3 &amp;&amp; test "$(grep -c '3\.0\.0' tests/helpers/test_plist_version.py)" = 2 &amp;&amp; echo README_AND_FIXTURE_OK</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest -q 2>&amp;1 | tail -1</automated>
  </verify>
  <done>`maccat --version` prints `maccat 3.1.0`; both authoritative files carry 3.1.0 on a single column-0 line each matching the release workflow's sed patterns; both README sample-frontmatter lines show 3.1.0 while the three historical `v3.0.0` prose mentions and the two plist-fixture values are unchanged; 712 tests still pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Harden the editor-extension banner against title injection without changing emitted bytes</name>
  <files>tests/reinstall/test_emitter.py, src/maccat/reinstall/emitter.py</files>
  <behavior>
    Write these tests FIRST in `tests/reinstall/test_emitter.py` (import `_editor_ext_block`
    alongside the existing emitter imports), confirm the injection ones FAIL against the current
    code, then implement until all pass.

    Add a `TestBannerInjection` class:

    - Test (byte-stability lock — must pass BEFORE and AFTER the change): route a normal section
      through `SECTION_SOURCE_MAP["VS Code Extensions"]` with one ordinary item, and assert the
      first emitted line is exactly `echo "=== VS Code Extensions ==="`. Repeat for
      `SECTION_SOURCE_MAP["Cursor Extensions"]` asserting exactly
      `echo "=== Cursor Extensions ==="`. This is the contract that the fix must not break.

    - Test (RED — command substitution must not execute): build a `ParsedSection` directly with
      `title = 'VS Code $(echo SUBBED) `echo TICKED` Extensions'` and `items=[]`, call
      `_editor_ext_block(section, editor="code")`, execute the resulting one-line block under bash,
      and assert stdout is exactly `=== ` + the raw title + ` ===` and contains neither `SUBBED`
      nor `TICKED`. Today the substitutions run, so the assertion fails.

    - Test (RED — quote break-out must not execute): same shape with
      `title = 'VS Code" ; echo INJECTED ; echo "Extensions'`. Assert stdout is exactly the literal
      banner and does not contain `INJECTED`. Also assert the block passes `assert_bash_n_clean`
      when wrapped in a full script — today the trailing unbalanced quote can break syntax.

    - Test (newline in title): `title = "VS Code\nrm -rf /"` produces a single-line banner (the
      emitted block's first line has no embedded newline) and `assert_bash_n_clean` passes.

    - Unit tests for the new helper directly: a title of only letters, digits, spaces, hyphens and
      periods round-trips **unchanged** (identity); a backslash is doubled; each of `"`, `$` and a
      backtick gains a single leading backslash; `\n` and `\r` become spaces.

    Reuse the module's existing helpers — `_make_section`, `_make_item`, `_make_catalog`,
    `assert_bash_n_clean` — for anything they cover. For the bash-execution assertions, run the
    block with `subprocess.run(["bash", "-c", block], capture_output=True, text=True)` and
    `pytest.skip("bash not available")` when `shutil.which("bash")` is falsy, matching
    `assert_bash_n_clean`'s skip posture. Use only side-effect-free payloads (`echo`) — no test may
    create or delete a file as proof of injection.
  </behavior>
  <action>
    Add a third context-specific gate function to `src/maccat/reinstall/emitter.py`, placed in the
    "Injection-safety helpers" block immediately after `safe_comment_value`, named
    `safe_banner_value`, taking and returning `str`.

    It escapes the four characters that are live inside a bash double-quoted string — backslash,
    dollar, backtick, double-quote — by prefixing each with a backslash, and then replaces carriage
    returns and newlines with a single space (matching `safe_comment_value`'s newline posture, and
    keeping the banner on one line). **Escape the backslash first**, before the other three, or the
    backslashes introduced by the later replacements get double-escaped.

    Its docstring must state: this is the SOLE path a catalog value may reach double-quoted `echo`
    banner context; `quote_for_script()` is deliberately NOT used here because `shlex.quote` wraps a
    space-containing title in single quotes, which would change the emitted bytes of every normal
    banner and disturb the emitter/parser round-trip contract; and that escaping (rather than
    stripping) is chosen so a title carrying one of these characters still renders faithfully.

    Apply it at the one interpolated banner in `_editor_ext_block` (currently line 185), so the
    sanitized title is what lands inside the double quotes. Change nothing else in that function —
    not the item loop, not the guard chain, not the `# cataloged:` handling.

    Update the module docstring's "two-function gate" description to describe all three gates, and
    extend the `emit_reinstall_script` return-value docstring paragraph that currently names the two
    gates so it names the banner gate too.

    Leave the hardcoded literal banners at lines 90, 153 and 292 alone — they contain no
    catalog-derived value. Leave `_manual_checklist_block` alone — it already `shlex.quote`s its
    title, and that is correct for its single-quoted context.

    Confirm the key property by running the full suite: for every metacharacter-free title the
    function is the identity, so no existing emitter assertion may change.
  </action>
  <verify>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest tests/reinstall/ -q 2>&amp;1 | tail -1</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest tests/reinstall/test_emitter.py -k BannerInjection -q 2>&amp;1 | tail -1</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -c "import sys; sys.path.insert(0,'src'); from maccat.reinstall.emitter import SECTION_SOURCE_MAP as M; from maccat.reinstall.parser import ParsedSection, ParsedItem; s=ParsedSection(title='VS Code Extensions', items=[ParsedItem(name='Python', version='1.0', id='ms-python.python', raw_line='')]); assert M['VS Code Extensions'](s).splitlines()[0] == 'echo \"=== VS Code Extensions ===\"', 'banner bytes changed'; print('BYTES_STABLE_OK')"</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest -q 2>&amp;1 | tail -1</automated>
  </verify>
  <done>A section title containing a double-quote, `$(...)`, a backtick, a backslash or a newline cannot execute anything or break bash syntax in the generated script; the banner line for every metacharacter-free title is byte-identical to before; the full suite still reports 712-plus passing with zero failures.</done>
</task>

<task type="auto">
  <name>Task 3: Delete the dead degraded_result method and document why available() stays unwired</name>
  <files>src/maccat/collectors/base.py, src/maccat/cli.py</files>
  <action>
    Remove the `degraded_result` method from `Collector` in `src/maccat/collectors/base.py`
    entirely — signature, docstring and body. It has zero call sites in `src/` and zero references
    in `tests/`; nothing imports it and nothing overrides it. Do not leave a tombstone comment
    naming it, and do not replace it with a deprecation shim.

    Keep `available()` exactly as it is behaviourally — same name, same signature, same
    `return True` default. Only expand its docstring so the next reader (human or codebase mapper)
    can see why it is not called from the orchestrator. The docstring must record: subclasses
    override it to gate on tool presence or directory existence; the three collectors that use it
    call it from **inside** their own `collect()` (`homebrew.py`, `mas.py`, `setapp.py`); and the
    orchestrator deliberately does not gate the registry loop on it, because a collector whose tool
    is absent must still emit its section — HomebrewCollector emits a section whose single item is
    the not-installed notice — so gating centrally would silently drop those sections and
    destabilise the fixed 22-section catalog set. Note that `webapps.py` relies on the True default.

    In `src/maccat/cli.py`, add a short comment at the collector loop (currently lines 352-355,
    `for collector in get_registry():`) stating the same rule in one or two lines: every collector's
    `collect()` runs unconditionally, availability is each collector's own internal concern, and
    this loop must not start skipping unavailable collectors. Add the comment only — do not change
    the loop's behaviour in this task.

    Leave `tests/collectors/test_setapp.py:313-314` untouched; it asserts the base default and must
    keep passing unchanged as proof the method survived.
  </action>
  <verify>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -c "import sys; sys.path.insert(0,'src'); from maccat.collectors.base import Collector; assert not hasattr(Collector, 'degraded_result'), 'method still present'; assert Collector().available() is True, 'available() default changed'; print('TRIAGE_OK')"</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest tests/collectors/ -q 2>&amp;1 | tail -1</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/ruff check src tests</automated>
  </verify>
  <done>`Collector` no longer exposes `degraded_result`; `Collector().available()` still returns True and every collector still runs; `tests/collectors/` passes unmodified; ruff is clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Surface collector warnings on stderr, then run the full regression gate</name>
  <files>tests/test_cli.py, src/maccat/collectors/base.py, src/maccat/cli.py</files>
  <behavior>
    Write these tests FIRST in `tests/test_cli.py` as a new `TestCollectorWarnings` class, confirm
    the first one FAILS against the current code, then implement until they pass.

    Both tests define a **stub** collector locally — the channel has no producers in `src/` today
    (see the correction in this plan's context), so do not build these on `VSCodeCollector` or
    `CursorCollector`; they would return an empty warnings list and the test would be vacuous.

    - Test (RED): a stub `Collector` subclass whose `collect()` returns
      `CollectorResult(sections=[], warnings=["code CLI returned empty list"])`. Patch
      `maccat.collectors.get_registry` with a `MagicMock(return_value=[stub])` via the existing
      `_patch_run_dependencies` helper's return dict (override the `get_registry` mock after
      calling it), set `sys.argv` to `["maccat", "--computer", "MyMac", "--no-commit"]`, call
      `run()`, and assert with `capsys` that the captured **stderr** contains the warning text.
      Today it is discarded, so this fails.

    - Test: a stub collector returning `warnings=[]` and one ordinary section produces no
      `WARNING:` text on stderr — the drain must be silent when there is nothing to report.

    - Test (catalog bytes unaffected): with the warning-emitting stub registered, the written
      `mac-software-list-*.md` file contains none of the warning text — warnings are a stderr-only
      channel and must never reach the catalog.

    Follow the file's existing conventions: `disposable_catalog_repo` fixture,
    `_patch_run_dependencies(monkeypatch, disposable_catalog_repo)`, `monkeypatch.setattr(sys,
    "argv", ...)`, and `from maccat.cli import run` inside the test body.
  </behavior>
  <action>
    In `src/maccat/cli.py`, extend the collector loop (currently lines 352-355) so that after
    extending `all_sections` with `result.sections`, it iterates `result.warnings` and prints each
    one to `sys.stderr`. Format each line in the collectors' established house style — two leading
    spaces and a `WARNING: ` prefix — so orchestrator-drained warnings are visually identical to the
    ones `homebrew.py` and `vscode.py` already print directly. `sys` is already imported at the top
    of the module; add no new import.

    The prefix is added by the orchestrator, not the collector: a collector appends the bare message
    text only. Record that contract as a comment on the `warnings` field of `CollectorResult` in
    `src/maccat/collectors/base.py` — a collector appends a plain degradation message here and the
    orchestrator prints it to stderr with the standard prefix; the field is not written to the
    catalog file.

    Do not touch `vscode.py` or `cursor.py`. Their existing direct `print(..., file=sys.stderr)`
    calls at `vscode.py:81-84` and `vscode.py:88-91` already work and are already covered by
    `tests/collectors/test_vscode.py`; converting them into `warnings.append` calls would relocate
    tested output, risk double-printing, and exceeds the smallest correct diff.

    Do not change anything that reaches `render_markdown_catalog` — the catalog bytes must be
    identical to a run without this change.

    Finally, run the full regression gate and confirm all three commands are green before finishing.
  </action>
  <verify>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest tests/test_cli.py -q 2>&amp;1 | tail -1</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/python -m pytest -q 2>&amp;1 | tail -1</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; ./venv/bin/ruff check src tests</automated>
    <automated>cd /Users/ken/dev/maccat &amp;&amp; PYTHONPATH=src ./venv/bin/mypy --strict src/maccat</automated>
  </verify>
  <done>A warning appended to `CollectorResult.warnings` appears on stderr with the standard two-space `WARNING:` prefix; an empty warnings list produces no output; the catalog file never contains warning text; the full suite passes with no fewer than the 712 baseline tests, ruff is clean, and mypy --strict reports no issues.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| catalog `.md` file → reinstall emitter | Section titles and item fields parsed from a file that may have come from a shared remote cross into generated shell text the user then executes |
| collector → stderr | Degradation messages cross from library code into the operator's terminal |
| git tag → package version | The release workflow rewrites both version files from `GITHUB_REF_NAME` |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-kqd-01 | Elevation of Privilege | `reinstall/emitter.py::_editor_ext_block` banner | high | mitigate | Task 2: the sole interpolated banner routes its catalog-derived title through `safe_banner_value`, escaping backslash, `$`, backtick and `"` and flattening newlines. Locked by execution tests asserting no substitution runs, plus a byte-stability test proving normal titles are untouched. |
| T-kqd-02 | Tampering | emitter/parser round-trip contract | medium | mitigate | The chosen escaping helper is the identity function for every metacharacter-free title, so no existing emitted byte changes. Gated by the full 712-test suite including `tests/reinstall/test_parser_contract.py`. |
| T-kqd-03 | Information Disclosure | `CollectorResult.warnings` → catalog file | low | mitigate | Task 4 routes warnings to stderr only, with an explicit test asserting the written `.md` contains no warning text. |
| T-kqd-04 | Denial of Service (data loss) | `cli.py` collector loop | medium | accept | `available()` is deliberately left unwired: gating the loop on it would drop the notice sections absent-tool collectors emit. Rationale is recorded in the `available()` docstring and at the loop so the decision is not silently reversed. |
| T-kqd-05 | Repudiation | version metadata | low | mitigate | Task 1 makes the two authoritative locations agree, so a catalog's `maccat_version` stamp and the installed distribution metadata give one answer to "what generated this file". Release-workflow sed compatibility is asserted by an anchored `grep -cE` gate. |
| T-kqd-SC | Tampering | package installs | n/a | accept | No pip/npm/cargo dependency is added — stdlib plus existing dev deps only, so no package-legitimacy gate applies. |
</threat_model>

<verification>
Run from `/Users/ken/dev/maccat`:

1. `PYTHONPATH=src ./venv/bin/python -m maccat --version` → `maccat 3.1.0`
2. `grep -cE '^version = ".*"$' pyproject.toml` → `1` and `grep -cE '^__version__ = ".*"$' src/maccat/__init__.py` → `1` (release workflow sed patterns still match exactly one line each)
3. `grep -c 'maccat_version: "3.1.0"' README.md` → `2`; `grep -c 'v3\.0\.0' README.md` → `3` (historical prose preserved)
4. `grep -c '3\.0\.0' tests/helpers/test_plist_version.py` → `2` (plist fixture untouched)
5. `./venv/bin/python -c "import sys; sys.path.insert(0,'src'); from maccat.collectors.base import Collector; assert not hasattr(Collector,'degraded_result'); assert Collector().available() is True"`
6. `./venv/bin/python -m pytest -q` → at least 712 passed, 0 failed
7. `./venv/bin/ruff check src tests` → All checks passed
8. `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` → Success
9. No git tag was created (`git tag --points-at HEAD` is empty) and nothing was pushed
</verification>

<success_criteria>
- Both authoritative version locations read `3.1.0` and `maccat --version` agrees
- The release workflow's two anchored sed patterns each still match exactly one line
- Both README sample-frontmatter lines show 3.1.0; the three historical `v3.0.0` prose mentions and the two plist fixture values are unchanged
- `safe_banner_value` exists, is used at the one interpolated banner, and is the identity for metacharacter-free titles
- A hostile section title neither executes a command nor breaks bash syntax in the generated script
- `Collector.degraded_result` is gone; `Collector.available()` survives with its rationale documented in both `base.py` and at the `cli.py` loop
- Warnings appended to `CollectorResult.warnings` reach stderr and never reach the catalog file
- Full suite green (>= 712 passed), ruff clean, mypy --strict clean
- No git tag created, nothing pushed, ROADMAP.md untouched
</success_criteria>

<output>
Create `.planning/quick/260825-kqd-release-v3-1-0-bump-version-everywhere-h/260825-kqd-SUMMARY.md` when done.
</output>

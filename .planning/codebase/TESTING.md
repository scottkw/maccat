# Testing Patterns

**Analysis Date:** 2026-08-25

**An automated test suite exists and is substantial: 712 tests, all passing, ~4.2s.**
Any documentation claiming otherwise is obsolete.

## Test Framework

**Runner:**
- `pytest >= 9.0` (declared under `[project.optional-dependencies] dev` in `pyproject.toml`)
- Config: `[tool.pytest.ini_options]` in `pyproject.toml` — `testpaths = ["tests"]`

**Assertion Library:**
- Plain `assert` statements (pytest rewriting). No `unittest.TestCase`, no `assertEquals`.

**Mocking:**
- `unittest.mock` (`patch`, `patch.object`, `MagicMock`) from the stdlib
- pytest's `monkeypatch` fixture

**Run Commands:**
```bash
./venv/bin/python -m pytest -q                    # Run all tests (712 passed in ~4.2s)
./venv/bin/python -m pytest -q tests/collectors   # One directory
./venv/bin/python -m pytest -q -m safety_invariant  # Only the destructive-op invariants
./venv/bin/python -m pytest -q -k homebrew        # By name
./venv/bin/ruff check src tests                   # Lint
PYTHONPATH=src ./venv/bin/mypy --strict src/maccat  # Type check
```

There are **no third-party runtime deps**; dev deps are `pytest`, `ruff`, `mypy` only.

## Test File Organization

**Location:** separate `tests/` tree that **mirrors the package layout**:

```
tests/
├── __init__.py
├── conftest.py                     # shared fixtures (tmp_json, git_repo, catalog_repo)
├── test_cli.py                     # ← src/maccat/cli.py
├── test_config.py                  # ← src/maccat/config.py
├── test_convert.py
├── test_format.py                  # ← src/maccat/catalog/format.py
├── test_gitops.py
├── test_helpers.py
├── test_identity.py
├── test_markdown_emitter.py        # ← src/maccat/catalog/markdown.py
├── test_naming.py
├── test_pyz.py                     # zipapp artifact smoke tests
├── test_retention.py
├── test_safety_invariants.py       # cross-cutting invariant suite (TEST-03)
├── test_writer.py                  # ← src/maccat/catalog/writer.py
├── collectors/                     # ← src/maccat/collectors/
│   ├── test_brave.py  test_chrome.py  test_claude.py  test_codex.py
│   ├── test_cursor.py test_edge.py    test_firefox.py test_gemini.py
│   ├── test_homebrew.py test_opencode.py test_safari.py test_setapp.py
│   ├── test_vscode.py test_zed.py
│   └── test_section_titles.py      # cross-collector title uniqueness contract
├── helpers/
│   └── test_plist_version.py       # ← src/maccat/helpers/
└── reinstall/                      # ← src/maccat/reinstall/
    ├── test_emitter.py test_parser_contract.py
    ├── test_picker_and_reinstall_cli.py test_reinstall_cli.py
```

**Naming:** `test_<module>.py`; every test directory has an `__init__.py`.

## Test Structure

**Grouping:** plain `class TestX:` containers (no base class, no `setUp`) for related cases,
and bare module-level `def test_*` for standalone contracts.

```python
"""Tests for src/maccat/gitops.py — git pull, commit/push, and rename operations.

All tests use the disposable git_repo fixture (tmp_path + git init, no remote)
from conftest.py. NEVER reference personal/ or office/ catalog directories.

Behavior spec: update-list.sh:2327-2354 (git_pull), :2374-2431 (git_commit_and_push).
"""
from __future__ import annotations

import pytest
from maccat.gitops import git_pull


class TestGitPull:
    def test_not_a_git_repo_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """git_pull on a plain dir (not git-init'd) prints WARNING, never raises."""
        git_pull(tmp_path)
        assert "WARNING" in capsys.readouterr().out
```

**Required elements of every test file:**
- Module docstring stating what is under test **and the behavioral spec it encodes**
  (usually `update-list.sh:<lines>` or a requirement ID like `VER-01`, `CAT-06`, `PKG-03`)
- `from __future__ import annotations`
- Full type annotations on test signatures (`-> None`, typed fixtures)
- A one-line docstring per test naming the asserted behavior, not the mechanics
- Banner comments (`# ---- ... ----`) separating sections in longer files

**Markers** (declared in `pyproject.toml`, so `--strict-markers` stays viable):
- `safety_invariant` — destructive-op invariants (TEST-03). Applied file-wide via
  `pytestmark = pytest.mark.safety_invariant` in `tests/test_safety_invariants.py`
- `zsh_parity` — declared for live Python-vs-zsh equivalence (CR-02); **currently no test
  uses it**, so it is a reserved slot, not an active suite

`@pytest.mark.parametrize` is used sparingly (9 sites); table-driven data is more often a
module-level list of tuples iterated inside one test — see `ROUND_TRIP_CASES` in
`tests/reinstall/test_parser_contract.py:27`.

## Mocking

### Subprocess-based collectors — the `_brew_mocks` idiom

The canonical pattern: patch `shutil.which` to fake tool presence, and patch
`subprocess.run` with a `side_effect` list of `MagicMock` results in the collector's
**fixed call order**. From `tests/collectors/test_homebrew.py:19-32`:

```python
def _brew_mocks(formulae: str, leaves: str, casks: str, leaves_rc: int = 0) -> list[MagicMock]:
    """Three subprocess.run results in collect()'s fixed call order.

    Order: ``brew list --formula --versions``, ``brew leaves``,
    ``brew list --cask --versions``.
    """
    mocks = []
    for stdout, returncode in ((formulae, 0), (leaves, leaves_rc), (casks, 0)):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = stdout
        mocks.append(mock)
    return mocks


with (
    patch("shutil.which", return_value="/usr/local/bin/brew"),
    patch("subprocess.run", side_effect=_brew_mocks("git 2.44.0\n", "git\n", "docker 4.30.0\n")),
):
    result = HomebrewCollector().collect()
```

**The call order is a contract in both directions.** `side_effect` positionally binds each
mock to a specific `brew` invocation, so reordering calls in the collector silently
rewires every test. The production code carries the matching guard comment:
`# Call order is a test contract — do not reorder.` (`src/maccat/collectors/homebrew.py:76`).
If you add or reorder a subprocess call, update `_brew_mocks` and its docstring in the same commit.

Use `return_value=` (single mock) instead of `side_effect=` when the test does not care
which call is which — e.g. the non-zero-exit and section-title tests.

Absence is tested by `patch("shutil.which", return_value=None)` and asserting the exact
fallback string (`["Homebrew is not installed."]`) plus `section.raw is True`.

### Filesystem-based collectors — `tmp_path` + `patch.object` on the path constant

Collectors that read real user directories expose their paths as module- or class-level
constants precisely so tests can redirect them. From `tests/collectors/test_claude.py`:

```python
def test_plugins_collect(self, tmp_path: Path) -> None:
    plugins_json = tmp_path / "installed_plugins.json"
    plugins_json.write_text(
        json.dumps({"plugins": {"my-plugin@registry": [{"version": "1.2.3"}]}}),
        encoding="utf-8",
    )
    with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
        result = ClaudeCollector().collect()
```

Import the collector module under an alias (`import maccat.collectors.claude as claude_mod`)
so `patch.object(mod, "_CONST", ...)` works. Absence is tested by pointing the constant at a
non-existent `tmp_path` child and asserting `items == []`.

`monkeypatch` handles environment and cwd (82 `setattr`, 24 `setenv`, 17 `chdir`,
11 `delenv` uses) — e.g. `monkeypatch.setattr(sys.stdin, "isatty", lambda: True)` plus
`patch("builtins.input", side_effect=[...])` to drive interactive prompts
(`tests/test_safety_invariants.py:113-115`).

**What to mock:**
- External binaries (`brew`, `mas`, `code`, `git` when not using the real disposable repo)
- Real user paths (`~/.vscode/extensions`, `~/.claude/...`) — via the path constant
- `builtins.input` and `sys.stdin.isatty` for interactive flows
- Time-dependent cutoffs: `patch("maccat.retention.cutoff_yyyymmdd", return_value="20260601")`

**What NOT to mock:**
- `git` itself in `tests/test_gitops.py` — a real disposable repo is created instead
- `pathlib` / filesystem — use `tmp_path`
- The system `sort` binary in `catalog/format.py` — byte parity is the whole point
- Anything inside the module under test (no partial self-mocking)

**Never touch the real `personal/` or `office/` catalog directories.** `tests/conftest.py`
states this as a rule; isolation comes from `tmp_path`.

## Fixtures and Factories

Three shared fixtures in `tests/conftest.py`:

```python
@pytest.fixture()
def tmp_json(tmp_path: Path):
    """Factory fixture: write a dict as JSON to a temp file, return the Path."""

@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Disposable git repo (no remote) for catalog operations."""
    # git init + git config user.email/user.name inside tmp_path

@pytest.fixture()
def catalog_repo(git_repo: Path) -> Path:
    """git_repo pre-populated with personal/ containing one catalog file."""
```

Fixtures compose (`catalog_repo` builds on `git_repo`) and factory fixtures return a
callable rather than data. Local helpers live at the top of the file that needs them:
`_touch_catalog` (`tests/test_safety_invariants.py:28`), `_require_pyz`
(`tests/test_pyz.py:28`), `_brew_mocks`. Promote a helper to `conftest.py` only once a
second file needs it.

Built-in fixtures used pervasively: `tmp_path`, `capsys` (43 sites, typed as
`pytest.CaptureFixture[str]`), `monkeypatch` (typed as `pytest.MonkeyPatch`).

## Coverage

**No coverage tooling is installed or enforced** — `pytest-cov` is not in the dev
extras and no threshold is configured. Coverage is maintained structurally instead: one
test module per source module, plus contract suites that fail when modules drift apart.

CI runs the equivalent gates on `macos-latest` (`.github/workflows/`):
```yaml
- run: ./venv/bin/ruff check src tests
- run: PYTHONPATH=src ./venv/bin/mypy --strict src/maccat
- run: PYTHONPATH=src ./venv/bin/pytest -x -q
```
with a `PYTHONHASHSEED: [0, 42, "random"]` matrix — the suite must be **deterministic under
hash randomization**. Never let a test depend on set/dict iteration order.

## Test Types

**Unit tests:** the bulk. Pure functions (`emit_item`, `parse_catalog_filename`,
`json_get`, `plist_version`) tested directly with table-driven cases.

**Collector tests:** one file per collector, each covering the same four axes —
tool/source present, source absent (fallback message or empty items), malformed input
degrades without raising, and exact section title.

**Contract / invariant tests** (the highest-value suites; treat regressions here as blockers):
- `tests/test_safety_invariants.py` — three destructive-op invariants, marked
  `safety_invariant`: (a) `prune_old_archives` never deletes files with unparseable
  timestamps; (b) `retain_newest_per_host` keeps **all** tied-newest files; (c)
  `rename_machine` hard-refuses to clobber an existing folder. Each docstring names the
  source test it was extracted from and, for (a), explains why the earlier fixture made the
  assertion **vacuous** — the fixture must match the prune glob yet fail
  `parse_catalog_filename`, so the `cf is None` skip branch actually executes.
  Read that reasoning before editing the fixture.
- `tests/reinstall/test_parser_contract.py` — round-trip `parse(emit(x)) == x` over the six
  shapes `emit_item()` can produce; locks `reinstall/parser.py` to `catalog/format.py`.
- `tests/collectors/test_section_titles.py` — all 22 section titles unique; new titles must
  fall through to the manual checklist rather than auto-install blocks.
- `tests/test_writer.py` — byte-exact assertions
  (`b"\nHomebrew Packages\n" + b"-" * 36 + b"\n"`), verified against a real catalog hex dump.

**Artifact smoke tests:** `tests/test_pyz.py` runs `dist/maccat.pyz` as a subprocess from an
unrelated cwd and inspects the zip for `.so`/`.dylib`. It **skips cleanly** when the artifact
is unbuilt via `pytest.skip(...)` in a `_require_pyz()` guard — mirror this for any test with
an optional prerequisite.

**E2E:** none beyond the CLI-level tests in `tests/test_cli.py` and
`tests/reinstall/test_reinstall_cli.py`.

## Common Patterns

**Exit-path testing** (53 `pytest.raises` sites):
```python
with pytest.raises(SystemExit):
    rename_machine(tmp_path)
# then assert the filesystem is UNCHANGED — the invariant, not just the exception
assert old_dir.is_dir(), "old folder untouched after refused rename"
```

**Warning-path testing** — warn-and-continue is asserted as *both* halves: the call must not
raise **and** must emit the prefix.
```python
git_pull(tmp_path)  # must not raise
assert "WARNING" in capsys.readouterr().out
```
Note the stream split: collector warnings land on **stderr**, git/orchestration warnings on
**stdout**. Check `captured.err` vs `captured.out` accordingly.

**Assertion messages carry the reasoning** on any non-obvious check:
```python
assert weird.exists(), "glob-matching but unparseable file must never be deleted (cf is None skip)"
assert file_bytes == expected, f"Byte mismatch!\n  Expected: {expected!r}\n  Got:      {file_bytes!r}"
```

**Async:** not applicable — the codebase is entirely synchronous.

## Workflow: TDD, RED then GREEN

Recent history shows a strict test-first commit sequence, one commit per stage
(`git log --oneline`):

```
c118247 test(quick-260825-k49): add failing tests for brew leaves formula filtering   ← RED
c3606f3 feat(quick-260825-k49): catalog only top-level Homebrew formulae             ← GREEN
b2bb3b4 feat(quick-260825-k49): warn and emit all formulae when brew leaves is unusable
a3e24d5 fix(quick-260825-k49): match tap-qualified brew leaves names to bare formula names
555e0e3 docs(quick-260825-k49): catalog only user-installed Homebrew formulae using brew leaves
```

The same shape appears in phase work (`ec52e38 test(32-02): add full test suite for convert
subcommand` alongside `842126f feat(32-02): wire convert subcommand into cli.py`).

**Follow this:** commit the failing test first, then the implementation, then follow-up
`fix:` commits for edge cases discovered afterwards, then a `docs:` commit. Conventional
Commit prefixes (`test:`, `feat:`, `fix:`, `docs:`, `chore:`) scoped with the phase or quick-task id.

---

*Testing analysis: 2026-08-25*

---
phase: quick
plan: 260825-kqd
subsystem: release + reinstall emitter + collectors
tags: [release, version-bump, shell-injection, dead-code, chesterton-fence]
status: complete
requires: []
provides:
  - "maccat 3.1.0 — both authoritative version locations agree"
  - "safe_banner_value() — third injection-safety gate in reinstall/emitter.py"
  - "Documented rationale for keeping Collector.available() unwired"
affects:
  - src/maccat/__init__.py
  - pyproject.toml
  - README.md
  - src/maccat/reinstall/emitter.py
  - src/maccat/collectors/base.py
  - src/maccat/collectors/vscode.py
  - src/maccat/collectors/cursor.py
  - src/maccat/cli.py
tech-stack:
  added: []
  patterns:
    - "Context-specific escaping gates (one function per shell destination context)"
key-files:
  created: []
  modified:
    - src/maccat/__init__.py
    - pyproject.toml
    - README.md
    - src/maccat/reinstall/emitter.py
    - tests/reinstall/test_emitter.py
    - src/maccat/collectors/base.py
    - src/maccat/collectors/vscode.py
    - src/maccat/collectors/cursor.py
    - src/maccat/cli.py
decisions:
  - "Escape (not shlex.quote) for double-quoted echo banner context — shlex.quote would single-quote every space-containing title and change emitted bytes"
  - "Delete CollectorResult.warnings rather than wire a drain — dead in both directions, redundant with the existing direct stderr prints"
  - "Keep Collector.available() and leave it unwired — gating the cli.py loop would drop absent-tool notice sections"
metrics:
  duration: ~18 min
  completed: 2026-08-25
actuals:
  tokens: 9500
  tasks: 4
  commits: 5
---

# Quick Task 260825-kqd: Release v3.1.0, Emitter Banner Hardening, Dead-Code Triage Summary

Shipped a coherent 3.1.0 version number, closed the one unquoted catalog-value interpolation in
the reinstall emitter without changing a single emitted byte for normal titles, and deleted two
genuinely dead `Collector` members while documenting why a third deliberately stays.

## What Was Built

**Task 1 — version bump (`a72ad75`).** The two authoritative locations disagreed
(`__init__.py` said 3.0.0, `pyproject.toml` said 2.1.0); both now read `3.1.0`, plus the two
illustrative `maccat_version` lines in the README sample output. The three historical `v3.0.0`
prose mentions and the two `CFBundleShortVersionString` plist fixture values were left untouched.
Both release-workflow `sed` anchors still match exactly one line each.

**Task 2 — banner hardening (`6d70a73` RED, `07fe0e1` GREEN).** Added `safe_banner_value()` as a
third context-specific gate alongside `quote_for_script()` and `safe_comment_value()`. It
backslash-escapes the four characters bash still interprets inside double quotes (`\`, `$`,
backtick, `"`) — backslash first, so later replacements are not double-escaped — then flattens
`\n`/`\r` to a space. Applied at the sole interpolated banner in `_editor_ext_block`. Module and
`emit_reinstall_script` docstrings now describe all three gates.

`quote_for_script()` was deliberately not used: `shlex.quote("=== VS Code Extensions ===")`
returns a *single*-quoted string, which would change the emitted bytes of every normal banner and
disturb the emitter/parser round-trip contract STATE.md calls the central invariant.

**Task 3 — `degraded_result` deleted, `available()` documented (`7f4fc97`).** `degraded_result`
had zero call sites in `src/` and zero references in `tests/`; removed with no tombstone.
`available()` was kept behaviourally identical, with its docstring expanded to record its three
in-`collect()` callers (`homebrew.py`, `mas.py`, `setapp.py`), `webapps.py`'s reliance on the
`True` default, and why the orchestrator must not gate on it. The same rule is mirrored as a
comment at the `cli.py` registry loop.

**Task 4 — `CollectorResult.warnings` deleted (`7e371b2`).** Dead in both directions (zero
producers, zero consumers) and redundant with the direct `print(..., file=sys.stderr)` calls the
collectors already use. `CollectorResult` now has `sections` as its only field, the `dataclasses`
import narrowed to `dataclass`, `_collect_editor_extensions` returns a plain `list[str]` from all
five return points, and both call sites use a single-value assignment. Every pre-existing stderr
print is byte-identical.

## Verification Results

| Check | Result |
|---|---|
| `maccat --version` | `maccat 3.1.0` |
| `grep -cE '^version = ".*"$' pyproject.toml` | `1` |
| `grep -cE '^__version__ = ".*"$' src/maccat/__init__.py` | `1` |
| `grep -c 'maccat_version: "3.1.0"' README.md` | `2` |
| `grep -c 'v3\.0\.0' README.md` (historical prose) | `3` — unchanged |
| `grep -c '3\.0\.0' tests/helpers/test_plist_version.py` | `2` — unchanged |
| Banner byte-stability (`echo "=== VS Code Extensions ==="`) | identical before and after |
| Deletions assertion (`degraded_result`, `warnings`, `available()`) | `DELETIONS_OK` |
| **Full suite** | **723 passed, 0 failed** (baseline 712 + 11 new) |
| **ruff** `check src tests` | **All checks passed** |
| **mypy** `--strict src/maccat` | **Success: no issues found in 42 source files** |
| Git tag at HEAD | none created |
| Pushed | no |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stale `dist/maccat.pyz` build artifact failed after the version bump**

- **Found during:** Task 1
- **Issue:** `tests/test_pyz.py::test_pyz_maccat_package_importable_from_pyz` asserts the bundled
  `.pyz` reports the same `__version__` as source. The local `dist/maccat.pyz` was built
  2026-06-18 at 3.0.0, so the bump turned a passing test into `1 failed, 711 passed`.
- **Fix:** Ran `./scripts/build-pyz.sh` to regenerate the artifact from current source. `dist/` is
  gitignored, so no repo content changed and nothing was committed for this.
- **Files modified:** none (untracked build output only)
- **Commit:** n/a — folded into the Task 1 verification

**2. [Rule 1 - Bug] Two self-contradictory assertions in the new banner-injection tests**

- **Found during:** Task 2 (GREEN step)
- **Issue:** The plan's brief asked each injection test to assert both that stdout equals the raw
  title *and* that stdout does not contain `SUBBED` / `TICKED` / `INJECTED`. Those two cannot both
  hold: the payload words appear literally inside the title, so a correctly-escaped banner must
  print them. After the fix landed, the exact-equality assertions passed while the `not in`
  assertions failed — a test defect, not an implementation defect.
- **Fix:** Replaced the `not in` assertions with checks that actually distinguish literal from
  executed output: the substitution *syntax* survives verbatim (`"$(echo SUBBED)" in stdout`,
  `` "`echo TICKED`" in stdout ``), and the quote-breakout banner renders as exactly one line
  (an executed breakout produces three). Exact-equality against the raw title is retained in both.
- **Files modified:** `tests/reinstall/test_emitter.py`
- **Commit:** `07fe0e1`

RED evidence was captured before the fix: the substitution test printed
`=== VS Code SUBBED TICKED Extensions ===` (the command substitutions ran) and the breakout test
produced multi-line output — both fail the retained exact-equality assertion, so the corrected
tests are still genuinely RED against the pre-fix emitter.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern or schema change was introduced.
T-kqd-01 (banner injection) is now mitigated; T-kqd-03 is eliminated by deletion; T-kqd-04
(`available()` unwired) remains an accepted risk with its rationale recorded in two places.

## Commits

| Task | Commit | Message |
|---|---|---|
| 1 | `a72ad75` | chore: bump version to 3.1.0 in both authoritative locations |
| 2 (RED) | `6d70a73` | test: add failing banner-injection tests for section titles |
| 2 (GREEN) | `07fe0e1` | feat: escape section titles in the reinstall banner via safe_banner_value |
| 3 | `7f4fc97` | refactor: delete dead degraded_result, document why available() stays unwired |
| 4 | `7e371b2` | refactor: delete the dead CollectorResult.warnings field and its plumbing |

## Self-Check: PASSED

All five commit hashes verified present in `git log`. All eight modified files verified on disk.
Full suite 723 passed, ruff clean, mypy --strict clean.

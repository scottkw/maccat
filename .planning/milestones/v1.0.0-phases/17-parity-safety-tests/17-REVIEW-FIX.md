---
phase: 17-parity-safety-tests
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/17-parity-safety-tests/17-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/17-parity-safety-tests/17-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (CR-02, the new critical finding from the orchestrator)
- Fixed: 1
- Skipped: 0

Iteration 1 already resolved CR-01 and WR-01 through WR-06 (see git history /
17-REVIEW.md). Iteration 2 addresses the single new blocker, CR-02.

## Fixed Issues

### CR-02: Parity gate was tautological (Python==Python), not Python==zsh

**Files modified:** `tests/golden/generate.py`, `tests/test_golden_parity.py`, `pyproject.toml`
**Commit:** 74b7599
**Applied fix:**

The committed `*.golden.txt` were previously written by the `--update-golden` branch from
**Python collector output**, while the zsh-capture harness (`capture_zsh_section`) was never
wired to produce them. So `test_section_parity` asserted Python==Python — a Python
regression would have been silently absorbed by `--update-golden`. TEST-01 ("Python section
bodies byte-identical to the ZSH reference") was not actually verified.

Fix (all 5 orchestrator requirements satisfied):

1. **Section→zsh-collector mapping + body capture.** `generate.py` now defines
   `ZSH_CAPTURABLE` (13 HOME-driven sections → their `collect_*` zsh function) and
   `NON_ZSH_CAPTURABLE` (the 4 CLI / hardcoded-`/Applications` sections). Added
   `capture_zsh_section_body()`, which captures the full zsh section and strips the leading
   `\n{title}\n{36-dash separator}\n` header (split on the exact `write_section` delimiter,
   `maxsplit=1`) so the result is byte-comparable with the committed body-goldens. It reuses
   the `SEPARATOR_LINE` contract from `normalize.py`.

2. **Authoritative zsh regeneration.** Added `regenerate_zsh_goldens()` and a `main()`
   entrypoint (`python -m tests.golden.generate`). This sources `update-list.sh` in real
   zsh against the fixture and writes the captured **zsh body** as each of the 13 goldens —
   the goldens are now zsh-sourced, NOT Python-sourced. Re-generating produced byte-
   identical goldens (`git diff` on `tests/golden/*.golden.txt` is empty), which is the
   empirical proof that Python==zsh holds for all 13 sections — including the `[id]` fields.
   (Note: firefox and chrome are ALSO HOME-driven and zsh-capturable, so the capturable set
   is 13, not the 11 cited in the finding. Both were verified byte-identical and are
   included — strictly stronger coverage.)

3. **Live zsh-parity assertion in CI.** Added
   `test_golden_parity.py::test_live_zsh_parity` — a `@pytest.mark.zsh_parity` parametrized
   test that, for each of the 13 zsh-capturable sections, captures zsh **live**, normalizes
   both sides (only the 14-digit timestamp is volatile; `[id]` preserved), and asserts the
   Python collector output equals the zsh body. It is `skipif`-guarded on
   `shutil.which("zsh")` so non-macOS dev machines skip cleanly, but it RUNS on this macOS
   machine (verified: `13 passed`) and on macos-latest CI. The `zsh_parity` marker is
   registered in `pyproject.toml`.

4. **Honest non-zsh-capturable documentation.** The 4 `NON_ZSH_CAPTURABLE` sections
   (`homebrew`/`mas`/`setapp`/`webapps`) are explicitly documented in `generate.py` and the
   `test_golden_parity.py` docstring as Python-format goldens that are NOT zsh-captured — no
   zsh-parity claim is made for them. The webapps `[ASSUMED]` caveat was clarified
   accordingly.

5. **Teeth proven.** With a temporary mutation appending `-WRONG` to the VS Code collector's
   emitted `[id]`, `test_live_zsh_parity[vscode-extensions]` FAILED with:
   ```
   - vscomp.test-ext (1.2.3) [vscomp.test-ext]
   + vscomp.test-ext (1.2.3) [vscomp.test-ext-WRONG]
   ```
   The mutation was then reverted (collector restored clean). This confirms a Python ID
   regression now fails the gate rather than being silently absorbed.

**Constraints honored:** `update-list.sh` byte-unmodified
(`git diff --quiet HEAD -- update-list.sh` → clean). All zsh invocations source the script
and call exactly ONE collector; the source-guard at `:2433` prevents the destructive main
flow; `HOME` is set to the synthetic fixture inside the zsh body; the real
`HOME`/`personal`/`office` are never touched. `normalize_catalog_body` (corrected in
iteration 1) does NOT strip `[id]`.

**Verification (all green):**
- `PYTHONHASHSEED=0 PYTHONPATH=src ./venv/bin/pytest -q` → 429 passed, 5 skipped
  (the 5 skips are the unrelated `test_pyz.py` cases requiring a built `dist/maccat.pyz`).
- `PYTHONHASHSEED=random PYTHONPATH=src ./venv/bin/pytest -q` → 429 passed, 5 skipped.
- The 13 `zsh_parity` tests RUN (not skip) on this macOS machine: `13 passed`.
- `./venv/bin/ruff check src tests` → All checks passed.
- `./venv/bin/mypy --strict src/maccat` → Success: no issues found in 29 source files.
- `git diff --quiet HEAD -- update-list.sh` → clean (byte-unmodified).

## Skipped Issues

None.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_

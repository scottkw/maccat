# Codebase Concerns

**Analysis Date:** 2026-08-25

Scope: the Python package at `src/maccat/` (7,749 LOC across 40 modules) and its 712-test
suite in `tests/`. Every item below was derived from the code on disk. The zsh script the
old map described (`update-list.sh`) no longer exists in the repo.

## Tech Debt

**Version metadata is split and out of sync:**
- Issue: `src/maccat/__init__.py:3` declares `__version__ = "3.0.0"`; `pyproject.toml:7`
  declares `version = "2.1.0"`. `.github/workflows/release.yml` rewrites *both* from the git
  tag at release time, so published `maccat.pyz` artifacts are correct — but any local
  `pip install -e .` reports wheel metadata `2.1.0`.
- Files: `src/maccat/__init__.py`, `pyproject.toml`, `.github/workflows/release.yml`
- Impact: `maccat_version` in catalog frontmatter (`catalog/markdown.py:143`, fed by
  `cli.py:362`) comes from `__init__.__version__`, so catalogs are stamped 3.0.0 while the
  installed distribution claims 2.1.0. Two different answers to "what generated this file".
- Fix approach: make one the source of truth — read `pyproject.toml` version via
  `importlib.metadata.version("maccat")` in `__init__.py`, and drop the second `sed` line
  from the release workflow.

**86 stale `update-list.sh:NNNN` cross-references in code comments:**
- Issue: The zsh reference implementation is gone from the repo, but 69 references in `src/`
  and 17 in `tests/` still cite it by line number as the authority for behaviour — e.g.
  `catalog/format.py:3-8` ("Byte-parity contract with update-list.sh functions emit_item
  (line 1243)"), `gitops.py:3-13`, `retention.py:9-12`, `collectors/__init__.py:15`,
  `catalog/writer.py:3-6`.
- Files: `src/maccat/catalog/format.py`, `src/maccat/gitops.py`, `src/maccat/retention.py`,
  `src/maccat/catalog/writer.py`, `src/maccat/collectors/__init__.py`, and ~15 others
- Impact: The stated justification for non-obvious decisions (mandatory `sort` subprocess,
  exactly-36-dash separators, bare `git pull` with no `--rebase`) now points at a file
  nobody can open. A future maintainer cannot verify a "parity" claim before changing it —
  Chesterton's Fence with the fence's blueprint deleted.
- Fix approach: rewrite each comment to state the *reason* rather than the citation, or
  vendor the zsh script into `docs/` as a frozen reference. Already recorded in
  `.planning/STATE.md` Deferred Items ("Code hygiene", 2026-06-16).

**Two parsers and two copies of the item regex coexist:**
- Issue: `reinstall/parser.py` holds both the legacy plain-text `parse_catalog()` (lines
  138-238, used only by `convert.py:90`) and the markdown `parse_markdown_catalog()` (line
  288). Separately, `catalog/markdown.py:48-60` duplicates `ITEM_RE` **verbatim** from
  `reinstall/parser.py:65-77`, and `catalog/markdown.py:35-43` duplicates
  `DEGRADATION_LINES` from `reinstall/parser.py:44-52`. Both duplications are deliberate
  (`catalog/markdown.py:31-33`: "Duplicated ... to avoid coupling to the reinstall module").
- Files: `src/maccat/reinstall/parser.py`, `src/maccat/catalog/markdown.py`
- Impact: The regex is the emitter's column-splitter *and* the parser's line-inverter. A fix
  applied to one copy and not the other silently desynchronizes emit from parse. No test
  asserts the two constants are equal.
- Fix approach: cheapest guard is a one-line test asserting
  `catalog.markdown._ITEM_RE.pattern == reinstall.parser.ITEM_RE.pattern` and likewise for
  the degradation set. Better: move both into a neutral module (e.g. `catalog/format.py`)
  that neither package owns.

**`Collector.available()` is a hook the orchestrator never calls:**
- Issue: `collectors/base.py:29-31` defines `available()`, but `cli.py:353-355` iterates
  `get_registry()` and calls `collect()` unconditionally. Only three collectors call
  `self.available()` from *inside* their own `collect()` (`homebrew.py:62`, `mas.py:58`,
  `setapp.py:37`); the other thirteen do ad-hoc inline checks (`safari.py:129`,
  `chromium.py:82`).
- Files: `src/maccat/collectors/base.py`, `src/maccat/cli.py`, `src/maccat/collectors/*.py`
- Impact: Three different availability idioms for one concept. A new collector that
  overrides `available()` and expects the registry to honour it will run anyway.
- Fix approach: either have `cli.py` skip collectors where `not collector.available()`, or
  delete the base-class method and standardize on the inline check.

## Known Bugs

**`convert` writes the `.md` non-atomically, unlike catalog generation:**
- Symptoms: `convert.py:125` uses `md_path.write_text(content, encoding="utf-8")` directly.
  Catalog generation uses the atomic `CatalogWriter` (tmp + rename, `catalog/writer.py:38-57`)
  precisely so "no partial catalog is ever committed to git".
- Files: `src/maccat/convert.py:125`, `src/maccat/catalog/writer.py`
- Trigger: Interrupt (Ctrl-C, disk full, crash) between `write_text` starting and finishing.
- Result: A truncated `.md` on disk. The `.txt` survives (unlink is at line 133, after), but
  the no-clobber guard at `convert.py:78` then refuses to re-run: "Target already exists".
  The user must manually delete the corrupt file to recover.
- Workaround: delete the partial `.md` and re-run.
- Fix: route the write through `CatalogWriter.write_raw()` like `cli.py:369-370` does.

**Extension IDs are interpolated into `grep` as regexes without escaping:**
- Symptoms: `reinstall/emitter.py:135` builds `f"^{item.id} "` and line 192 builds
  `f"^{low_id}$"`, then shell-quotes them. Shell-quoting is correct; regex-escaping is
  missing. An id containing `.`, `+`, `*`, `[`, or `?` is matched as a pattern.
- Files: `src/maccat/reinstall/emitter.py:135`, `src/maccat/reinstall/emitter.py:192`
- Trigger: any VS Code / Cursor marketplace id or MAS numeric id with a regex metacharacter.
- Impact: idempotency-check false positives/negatives only — a redundant re-install attempt
  or a skipped install. **Not** a shell-injection path (`quote_for_script` still wraps it).
- Fix: `re.escape` is the wrong tool for a shell `grep`; use `grep -F` for the mas case
  (fixed-string) and `grep -Fqix` for the editor case (which currently relies on `^...$`
  purely for whole-line anchoring anyway).

## Security Considerations

### 1. The generated `reinstall.sh` — injection surface (assessed as well-defended)

**Design.** `reinstall/emitter.py` builds a bash script from catalog content that a human
then executes. Two gate functions are the only routes catalog data reaches the script:
`quote_for_script()` (line 27, `shlex.quote`) for command position, and
`safe_comment_value()` (line 36, newline-stripping) for `#` comment position. The
module docstring (lines 7-13) states the invariant, and the reasoning is correct: `shlex.quote`
does *not* strip newlines, and a newline inside a `# cataloged:` comment would terminate the
comment and expose the tail as a live command.

**Verified coverage.** Every catalog-derived value in the four auto-install renderers is
quoted: `_brew_block` (95, 102, 108), `_mas_block` (125, 135, 136, 144-148),
`_editor_ext_block` (191, 192, 199, 206), `_manual_checklist_block` (220, 222),
`_checklist_display` (72, 74), and the provenance header (271, 272).
`tests/reinstall/test_emitter.py` locks this with `TestAdversarialInjection` (lines 621-711,
including parametrized hostile names + `bash -n` syntax checks) and `TestRuntimeExecution`
(lines 714-889, which actually executes the script under `set -Eeuo pipefail`). This is the
strongest-tested area of the codebase and no live injection path was found.

**Residual risk — the one unquoted interpolation:**
- Risk: `reinstall/emitter.py:185` emits `f'echo "=== {section.title} ==="'` — a
  catalog-derived value inside **double** quotes with no `quote_for_script`. A section title
  containing `"` or `$(...)` would inject.
- Current mitigation: unreachable today, because `_editor_ext_block` is only invoked through
  the exact-match dict `SECTION_SOURCE_MAP` (lines 230-235, keys `"VS Code Extensions"` /
  `"Cursor Extensions"`), so `section.title` is always a literal from that dict. `_brew_block`
  (line 90) and `_mas_block` (line 153) hardcode their banners; `_manual_checklist_block`
  (line 220) correctly `shlex.quote`s the title.
- Why it still matters: the safety of line 185 is an emergent property of the routing table,
  not a local property of the function. Any future change to prefix/suffix/regex matching in
  `SECTION_SOURCE_MAP.get()` (`emitter.py:284`) turns it into a live injection. Nothing in
  the code or the tests says so.
- Recommendation: wrap it — `f"echo {quote_for_script('=== ' + section.title + ' ===')}"` —
  matching what `_manual_checklist_block` already does. One line, removes the whole class.

**Residual risk — trust boundary of the catalog file:**
- Risk: `reinstall --from PATH` (`reinstall/picker.py:112-124`) accepts *any* readable `.md`,
  including one pulled from a shared remote or handed over by someone else. The generated
  script's shell syntax is safe, but its *semantics* are not validated: an attacker-supplied
  catalog can list arbitrary package names under `## Homebrew Packages` and the emitted
  `brew install <name>` runs whatever that resolves to (typosquat / malicious tap-qualified
  formula). No name allowlist, no diff-against-current-machine preview.
- Current mitigation: the script is written mode `0o644` (`reinstall/cli.py:80`), is never
  executed by maccat, and carries a `# Review this script before running` banner
  (`emitter.py:273`). That is the right posture.
- Recommendation: keep it. If a `--run` convenience flag is ever proposed, this is the
  reason to refuse.

### 2. Sensitive data reaching a git remote

- Risk: `cli.py:386` calls `gitops.git_commit_and_push()` on every default run — the catalog
  is committed *and pushed* with no preview and no confirmation. The catalog contains: the
  machine hostname (`cli.py:360`), the user's chosen computer label, the full `/Applications`
  listing (`collectors/webapps.py:43`), every browser extension name+id across Chrome, Edge,
  Brave, Firefox and Safari, and — most sensitive — the names of everything under
  `~/.claude/skills`, `~/.claude/agents`, `~/.config/opencode/agents`, `~/.gemini/extensions`,
  plus every MCP server name from `~/.claude.json`, `~/.codex/config.toml`,
  `~/.config/opencode/opencode.json`.
- Files: `src/maccat/collectors/claude.py:21-24`, `src/maccat/collectors/codex.py:27`,
  `src/maccat/collectors/opencode.py:25-26`, `src/maccat/collectors/gemini.py:25-26`,
  `src/maccat/gitops.py:86-166`, `src/maccat/cli.py:385-386`
- Current mitigation (strong, for *secret values*): the CAT-05 invariant is genuinely
  enforced — `claude.py:128-131` reads only `.type` and clamps it to a three-value whitelist;
  `codex.py:96-110` text-greps only `[mcp_servers.NAME]` header lines and deliberately never
  calls `tomllib.loads()`, so `command`, `env`, `args`, `url`, `headers` are never read at
  all. That is the correct design: unread data cannot leak.
- Residual risk (identifiers, not secrets): names still leak. `claude.py:36-49`
  `_read_yaml_name()` copies the entire `name:` frontmatter line from every private agent
  file into the catalog. A skill named after a client, an internal codename, or an unreleased
  project is committed and pushed. `SetappCollector` / `WebAppsCollector` similarly disclose
  the complete installed-app inventory of a machine — useful to an attacker profiling for
  known-vulnerable versions, since versions are included (`webapps.py:36`).
- Recommendations: (a) document loudly in README that the catalog repo must be **private**;
  (b) add a `--dry-run` that renders the markdown to stdout without writing or pushing, so a
  user can inspect what is about to leave the machine; (c) consider a config-level
  section denylist for users who want apps but not AI-tooling identity.

- Risk: `gitops.py:119` runs `git add -A -- "{computer}/"` — it stages **everything** in the
  computer folder, not just the catalog file maccat wrote.
- Impact: any unrelated file a user drops into `~/catalog-repo/MyMac/` (notes, an exported
  keychain, a screenshot) is committed and pushed on the next run without being mentioned.
- Recommendation: stage the specific written path plus the archive moves, as
  `git_commit_convert()` already does correctly (`gitops.py:292-302`).

## Performance Bottlenecks

**One `sort` subprocess per section, plus one per browser extension:**
- Problem: `catalog/format.py:59` spawns `sort -f -u` for every non-raw section, and
  `catalog/format.py:95` spawns `sort -V` **inside** the per-extension loop at
  `collectors/chromium.py:66`.
- Files: `src/maccat/catalog/format.py:46-107`, `src/maccat/collectors/chromium.py:62-66`
- Cause: `format.py:6-8` mandates the subprocess for byte-parity with a zsh script that no
  longer exists. On a machine with 3 Chromium browsers × 2 profiles × 25 extensions, that's
  ~150 process spawns for version-directory selection alone, plus ~18 for section sorting.
- Improvement path: the parity constraint is now unfalsifiable (the reference is deleted).
  `sort -V` in particular is replaceable with a pure-Python tuple key over
  `re.split(r'(\d+)', name)` with zero output change for Chrome's numeric version dirs.
  `sort -f -u` is the harder one (LC_ALL=C case-folded ordering); if it stays, hoist it to
  one batched call rather than one per section.

**No `timeout=` on any of the ~30 `subprocess.run` calls:**
- Problem: verified by grep — zero occurrences of `timeout` in `src/maccat/`.
- Files: `src/maccat/gitops.py` (18 calls), `src/maccat/config.py:145,163`,
  `src/maccat/collectors/homebrew.py`, `mas.py`, `vscode.py`, `codex.py`, `safari.py`,
  `src/maccat/catalog/format.py:59,95`
- Impact: the network calls are the dangerous ones. `git pull` (`gitops.py:71`) and
  `git push` (`gitops.py:153`, `:235`, `:325`) run with `capture_output=True`, so if git
  prompts — SSH key passphrase, HTTPS credential helper, or an editor for a merge commit
  message — the prompt is **swallowed** and maccat hangs forever with no output. A user in
  cron or a non-interactive shell sees a silent stall, not an error.
- Improvement path: pass `timeout=` on all of them, and set
  `env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"}` on the git calls so
  a credential prompt fails fast instead of blocking.

## Fragile Areas

**The emitter↔parser round-trip contract (the project's stated central invariant):**
- Files: `src/maccat/catalog/markdown.py` (render), `src/maccat/reinstall/parser.py`
  (parse), `tests/reinstall/test_parser_contract.py` (lock)
- Why fragile: `.planning/STATE.md` states the contract "must stay lossless ... across all 22
  sections + all `emit_item` line shapes". The actual lock in
  `tests/reinstall/test_parser_contract.py:380-401` uses a **4-section synthetic fixture**
  (`Homebrew Packages`, `App Store Applications`, `Setapp Applications`, `Web Applications`)
  — and note that `"Web Applications"` is not even a real title; the registry's is
  `"Web-installed Applications"` (`collectors/webapps.py:10`). The 18 remaining real
  sections are not exercised through the round trip. Adversarial cell content is covered well
  (pipe at line 464, backslash at 487, version-only at 510, id-only at 528).
- Safe modification: any change to `_escape_cell` / `_render_table` / `_ITEM_RE` in
  `catalog/markdown.py` must be mirrored in `_unescape_cell` / `_parse_markdown_row` /
  `ITEM_RE` in `reinstall/parser.py` in the same commit.
- Test coverage gap: parameterize the round-trip fixture over the real 22-title list already
  assembled in `tests/collectors/test_section_titles.py:85`.

**Section-title strings are load-bearing but only half-checked:**
- Files: `src/maccat/reinstall/emitter.py:230-235`, `tests/collectors/test_section_titles.py`
- Why fragile: `SECTION_SOURCE_MAP` routes on four exact title strings. The test suite
  asserts titles are *unique* (line 33) and that two named new titles fall through to the
  manual checklist (line 92) — but **nothing asserts the four map keys still match live
  collector title constants**. Rename `VSCodeCollector.TITLE` and every VS Code extension
  silently degrades from `code --install-extension` to a printed checklist line. Tests stay
  green; the reinstall script quietly stops installing extensions.
- Fix: assert `set(SECTION_SOURCE_MAP) <= set(<the 22 live title constants>)`.

**`reinstall.sh` is written to the current directory with no clobber guard:**
- Files: `src/maccat/reinstall/cli.py:78-79`
- Why fragile: `Path.cwd() / "reinstall.sh"` then `write_text` — unconditional overwrite. The
  sibling `convert` command has an explicit no-clobber guard marked "USER OVERRIDE -- do NOT
  remove this check" (`convert.py:76-82`). The reinstall path has none, so running
  `maccat reinstall` in a repo that already contains a `reinstall.sh` destroys it silently.
- Fix: mirror the `convert.py:78` guard, or add `--output PATH` / `--force`.

**Any collector exception aborts the whole run before a catalog is written:**
- Files: `src/maccat/cli.py:352-355`
- Why fragile: the loop `for collector in get_registry(): result = collector.collect()` has
  no `try/except`. Individual collectors are careful (`safari.py:179` catches per-plist,
  `chromium.py:50` catches `OSError` per-profile), but `WebAppsCollector.collect()`
  (`webapps.py:43`) calls `self.BASE.iterdir()` unguarded, and `flush_section` raises
  `RuntimeError` on a non-zero `sort` (`format.py:71`). Either produces a traceback and
  **zero output** — violating the project's stated mandatory graceful-degradation constraint,
  which every collector honours individually but the orchestrator does not.
- Safe modification: wrap the per-collector call in `try/except Exception`, print
  `WARNING: <collector> failed`, and continue with an empty section for that source.
- Test coverage: `tests/test_cli.py` has 26 tests including end-to-end `run()` coverage
  (lines 145-208) but none inject a raising collector.

## Scaling Limits

**Catalog repo growth is bounded, but only per-computer:**
- Current behaviour: `retention.py:37` keeps only the newest catalog per host in the computer
  folder; `retention.py:90` prunes archived files older than `archive_days`.
- Limit: pruning is scoped to `catalog_repo / computer / "archive"` (`cli.py:380`) — only the
  folder for *this* run's computer. Folders for machines that have stopped running maccat
  are never swept, and git history retains every catalog ever committed regardless, so the
  clone size grows monotonically forever.
- Scaling path: acceptable for a personal tool (catalogs are a few KB of text). If it ever
  matters, the answer is repo-wide prune plus periodic history squash — not a code change.

## Dependencies at Risk

**None.** `pyproject.toml` declares zero runtime dependencies ("stdlib only"), verified by
inspection of the imports across `src/maccat/`. Dev-only deps are `pytest>=9.0`,
`ruff>=0.15`, `mypy>=1.10`. The real external dependencies are *runtime binaries* the
collectors shell out to (`brew`, `mas`, `code`, `cursor`, `codex`, `pluginkit`, `git`,
`sort`), each of which is presence-checked before use.

## Missing Critical Features

**No dry-run / preview before data leaves the machine:**
- Problem: there is no way to see the catalog before it is committed and pushed. `--no-commit`
  (`cli.py:90-95`) still writes the file into the git repo working tree; it only skips the
  commit.
- Blocks: reviewing what identity data (agent names, app inventory) is about to be published,
  which is the mitigation this tool most needs given the Security section above.

**No bulk convert:**
- Problem: `convert` handles exactly one file (`convert.py:57`, `--from` is `required=True`).
- Blocks: migrating an existing multi-machine catalog repo of legacy `.txt` files without a
  shell loop. Already tracked in `.planning/STATE.md` Deferred Items as `CONV-bulk`.

## Test Coverage Gaps

The 712-test suite is genuinely strong on the highest-risk module (shell emission) and on
destructive-op safety. The gaps below are what it does *not* cover.

**Round-trip across the real 22 sections:**
- What's not tested: 18 of 22 live section titles never go through
  render → parse. See "Fragile Areas" above.
- Files: `tests/reinstall/test_parser_contract.py:380-401`
- Risk: a section-specific escaping bug ships unnoticed.
- Priority: High — this is the contract `.planning/STATE.md` names as central.

**`SECTION_SOURCE_MAP` keys vs. live collector titles:**
- What's not tested: that the four routing keys still correspond to real collectors.
- Files: `src/maccat/reinstall/emitter.py:230-235`, `tests/collectors/test_section_titles.py`
- Risk: silent downgrade of auto-install to manual checklist, green tests.
- Priority: High — one assertion closes it.

**Emitter regex ≡ parser regex:**
- What's not tested: `catalog/markdown.py:_ITEM_RE` and `reinstall/parser.py:ITEM_RE` are
  duplicated source text with no equality assertion; same for the two `DEGRADATION_LINES`
  frozensets.
- Files: `src/maccat/catalog/markdown.py:35-60`, `src/maccat/reinstall/parser.py:44-77`
- Risk: divergence on the next edit to either.
- Priority: High — two assertions close it.

**Orchestrator resilience to a failing collector:**
- What's not tested: no test makes a collector raise inside `cli.run()`'s loop.
- Files: `src/maccat/cli.py:352-355`, `tests/test_cli.py`
- Risk: the graceful-degradation constraint is enforced per-collector but unverified at the
  level where it actually determines whether the user gets a catalog.
- Priority: High.

**Subprocess hang / timeout behaviour:**
- What's not tested: no test simulates a `git pull`/`git push` that blocks on a prompt.
- Files: `src/maccat/gitops.py`, `tests/test_gitops.py`
- Risk: the silent-hang failure mode above ships undetected.
- Priority: Medium.

**Non-`reinstall.sh` clobber and non-atomic convert write:**
- What's not tested: overwriting an existing `reinstall.sh`; interrupted `convert` write.
- Files: `src/maccat/reinstall/cli.py:78`, `src/maccat/convert.py:125`
- Priority: Medium.

**No coverage measurement at all:**
- What's not tested: there is no `pytest-cov` in `pyproject.toml [dev]` and no coverage step
  in `.github/workflows/ci.yml`. "712 tests" is a count, not a coverage figure — the gaps
  above were found by reading, not by a report.
- Files: `pyproject.toml:19-23`, `.github/workflows/ci.yml`
- Risk: unmeasured blind spots beyond the ones enumerated here.
- Priority: Medium.

**Stale test marker:**
- The `zsh_parity` marker is still registered in `pyproject.toml:33` ("sources update-list.sh
  in real zsh") but zero tests use it — the parity suite was removed with the script. Dead
  configuration that implies a safety net that does not exist.
- Priority: Low.

---

*Concerns audit: 2026-08-25*

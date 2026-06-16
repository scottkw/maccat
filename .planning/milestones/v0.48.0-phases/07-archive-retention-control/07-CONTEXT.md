# Phase 7: Archive Retention Control - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the archive-pruning period user-configurable, replacing the
hardcoded `ARCHIVE_AGE_DAYS=30` constant as the sole source of truth. Users can
set the retention window per run via an `--archive-days N` flag or, when the flag
is absent, an interactive prompt. Invalid values are rejected before any archive
files are moved or deleted.

Scope is limited to: argument parsing (`parse_arguments`), a new prompt step, value
validation, and feeding the resolved value into `prune_old_archives`. It does NOT
change the retention sweep (`retain_newest_per_host`), catalog generation, or the
git flow.

</domain>

<decisions>
## Implementation Decisions

### Validation Rules
- Valid values are positive integers ≥ 1 only. Reject `0`, negative numbers,
  decimals, and non-numeric input.
- No upper bound — any positive integer is accepted.
- Invalid flag value prints `ERROR: --archive-days must be a positive integer (got 'X')`
  and exits with status 1.
- Validation runs inside `parse_arguments` the moment the flag is read — fail fast,
  before any files are touched (satisfies SC #3).

### Prompt Behavior
- When `--archive-days` is absent, prompt: `Archive retention period in days [30]:`
  (matches SC #2). Passing the flag suppresses the prompt entirely.
- Non-interactive stdin (cron / piped input, no TTY): fall back to the default 30
  silently — never hang on `read`.
- Empty input (user just presses Enter): use the default 30.
- A value entered at the prompt is validated with the same rules as the flag;
  invalid entry prints the same error and exits.

### Ordering & Interaction
- The prompt appears right after location selection (`get_target_location`) and
  before catalog generation — all interactive prompts are front-loaded.
- The chosen value affects ONLY the `prune_old_archives` cutoff. The retention
  sweep (`retain_newest_per_host`) is unchanged (satisfies SC #4).
- Echo the resolved value (`Archive retention: N days`) for transparency.
- The `ARCHIVE_AGE_DAYS` constant remains as the default value (30); the flag or
  prompt overrides the runtime value used by `prune_old_archives`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_arguments` (line 102) — `while`/`case` flag loop; add an `--archive-days`
  case here. Note flags taking a value need a second `shift`.
- `get_target_location` (line 140) — established `printf` + `read` + `case`
  prompt-and-validate pattern to mirror for the retention prompt.
- `prune_old_archives` (line 272) — consumes `ARCHIVE_AGE_DAYS`; computes cutoff via
  `date -v-${ARCHIVE_AGE_DAYS}d`. This is the single consumer of the value.
- Main block (lines ~1690-1723) — call ordering: location → filename → generate →
  `retain_newest_per_host` → `prune_old_archives`. Insert the retention-period
  resolution after location selection.

### Established Patterns
- Globals set in main, referenced by functions (e.g. `TARGET_LOCATION`, `AUTO_COMMIT`).
  `ARCHIVE_AGE_DAYS` is currently a top-of-file constant (line 45).
- Error convention: `echo "ERROR: ..."` + `exit 1` for fatal arg/choice errors.
- `[[ ]]` conditionals; `command -v` for tool detection; `local` for fn-scoped vars.
- TTY detection idiom for graceful non-interactive fallback: `[[ -t 0 ]]`.

### Integration Points
- New `--archive-days` case in `parse_arguments`.
- New prompt logic (function or inline) invoked from main after `get_target_location`.
- Resolved value flows into the existing `ARCHIVE_AGE_DAYS` global before
  `prune_old_archives` is called.

</code_context>

<specifics>
## Specific Ideas

- Prompt text must read exactly `Archive retention period in days [30]:` per SC #2.
- Error message text: `ERROR: --archive-days must be a positive integer (got 'X')`.
- Integer regex check should reject leading zeros-only / non-digit input; an
  all-digits-and-≥1 test is sufficient (`[[ "$val" =~ ^[0-9]+$ ]] && (( val >= 1 ))`).

</specifics>

<deferred>
## Deferred Ideas

- Persisted config file for retention period — explicitly out of scope; the roadmap
  decision is runtime-only (flag-or-prompt), no config file.

</deferred>

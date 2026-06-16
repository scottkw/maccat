# Deferred Items — Phase 12 (Computer Rename)

Out-of-scope discoveries logged during execution.

| Found in plan | File:Line | Issue | Resolution |
|---------------|-----------|-------|------------|
| 12-02 | update-list.sh:570 (`upsert_machine_label`) | Bare `> "$tmp_file"` truncation runs zsh's `$NULLCMD` (cat) reading from stdin instead of just truncating. REAL hang on interactive runs: the new always-shown menu (Phase 11) leaves stdin on the TTY when `upsert_machine_label` runs, so `cat` blocks. Non-interactive cron/launchd runs read EOF from /dev/null and truncate fine — why it never surfaced before. The 12-02 analog had the same pattern and was fixed in-scope. | **RESOLVED** by the autonomous orchestrator after the executor flagged it. Changed to `: > "$tmp_file"` (commit `fix(12): use ': >' in upsert_machine_label to avoid NULLCMD stdin hang on interactive runs`). `zsh -n` passes; no bare-redirects remain in the file. |

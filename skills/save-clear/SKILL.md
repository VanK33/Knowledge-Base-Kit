---
name: save-clear
description: "Save current conversation to archives then tell the user to /clear. TRIGGER: /save-clear command, or when user requests saving conversation before clearing context."
---

# Save & Clear

Export the current conversation to the daily log file, then instruct the user to run `/clear`.

## Workflow

1. Run the export script:
   ```bash
   python3 ~/.claude/skills/save-clear/scripts/save-conversation.py "$(pwd)"
   ```
2. Report the result to the user (saved message count and file path).
3. **Memory update**: After export, perform memory-hierarchy Phase 3 (context-triggered memory update):
   - Review the current conversation for decisions, lessons, preferences, and project changes
   - Read memory files (projects.md, decisions.md, lessons.md, preferences.md)
   - Write any new entries to the appropriate files (follow /memory-hierarchy formats and dedup rules)
   - Update MEMORY.md index counts
   - Keep this step brief — only write entries that are clearly valuable, skip trivial content
4. Tell the user: "Conversation saved + memory updated. Run `/clear` to clear context."
5. If the export script reports SKIP (already exported or too few messages), still run step 3 (memory update), then inform the user.

## Output format

The script writes to `{vault}/archives/claude-logs/YYYY-MM-DD-Log.md` — only user and AI text messages, no thinking or tool calls. Each export is tagged with `**saved_by:** save-clear (pre-clear export)` to distinguish from SessionEnd exports.

## Deduplication

The script checks `session_id` to prevent double-export. If the SessionEnd hook later fires for the same session, it will skip the duplicate automatically.

# Writing Custom Plugins

## Quick Start

Add a plugin to `~/.claude/skills/inbox-processor/config.json`:

```json
{
  "name": "my-notes",
  "priority": 50,
  "extension": [".md"],
  "content_hints": ["my-project", "sprint review"],
  "move_to": "Projects/MyProject/"
}
```

## Match Logic

Plugins are evaluated in priority order (lower number first). For each file, the first matching plugin wins.

### Evaluation Flow

```
1. filename_contains → any keyword in filename? → MATCH
2. filename_regex → regex matches filename? → MATCH
3. extension → wrong extension? → SKIP this plugin
4. content_hints → read file, any hint found? → MATCH
5. extension matched but no content_hints defined → MATCH
```

**Key rules:**
- Missing fields don't participate (no `extension` = any extension is OK)
- `filename_contains` is the fastest path — no file I/O needed
- `content_hints` triggers file reading (OCR for images, text for md/pdf)

### Content Reading

When `content_hints` is checked, the processor reads content based on file type:
- **Images** (`.png`, `.jpg`, etc.) → OCR via Claude's vision (Read tool)
- **PDF** → Read first pages
- **Markdown** → Read text content
- The read content is cached and passed to handler skills as `content_preview`

## Examples

### Simple file routing

```json
{
  "name": "receipts",
  "priority": 20,
  "extension": [".pdf", ".png", ".jpg"],
  "content_hints": ["receipt", "invoice", "total", "subtotal"],
  "tags": ["finance"],
  "move_to": "Finance/Receipts"
}
```

### Regex matching

```json
{
  "name": "dated-meeting-notes",
  "priority": 10,
  "filename_regex": "\\d{4}-\\d{2}-\\d{2}.*(?:meeting|standup|retro)",
  "extension": [".md"],
  "move_to": "Work/Meetings"
}
```

### Handler skill dispatch

```json
{
  "name": "voice-memos",
  "priority": 15,
  "filename_contains": ["voice", "memo", "transcript"],
  "handler_skill": "voice-memo-processor"
}
```

The handler skill receives:
- `file_path`: absolute path
- `file_name`: filename
- `matched_plugin`: "voice-memos"
- `content_preview`: content if already read, null otherwise

### Multi-action sequence

```json
{
  "name": "research-paper",
  "priority": 25,
  "extension": [".pdf"],
  "content_hints": ["Abstract", "Introduction", "Related Work"],
  "actions": [
    {"type": "handler_skill", "skill": "paper-reader"},
    {"type": "move_to", "path": "Papers/_sources"}
  ]
}
```

## Letting config-learner Do It

Instead of manually editing config.json, you can let the system learn:

1. Drop an unmatched file into Inbox/
2. Run `/inbox-processor`
3. When asked, describe the rule: "Move PDFs with 'invoice' in content to Finance/"
4. config-learner proposes a plugin, you confirm
5. The rule is permanently saved to config.json

This is the recommended way to build your plugin library over time.

## Priority Guidelines

| Range | Use Case |
|-------|----------|
| 1-10 | Exact filename matches (highest specificity) |
| 11-30 | Content-specific with extension filter |
| 31-50 | General extension-based routing |
| 51-70 | Broad content matching |
| 71-99 | Catch-all / fallback plugins |

Lower priority numbers are evaluated first. Avoid conflicts — each plugin should have a unique priority.

## Debugging

If a plugin isn't matching as expected:
1. Check priority — is a higher-priority plugin catching the file first?
2. Check `extension` — does it filter out your file type?
3. Check `content_hints` — are the keywords actually in the file content?
4. Add `tags` for easier identification in the Phase 5 report

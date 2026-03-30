# Config Reference

## User Config (`_shared/user-config.json`)

### paths

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vault_root` | string | `~/ObsidianVault` | Root path to your knowledge base |
| `inbox_folder` | string | `Inbox` | Inbox directory (relative to vault) |
| `unsorted_folder` | string | `Inbox/_unsorted` | Fallback directory for unmatched files |
| `archives_folder` | string | `archives/claude-logs` | Conversation export directory |
| `paper_notes_folder` | string | `Papers` | Paper notes directory |
| `daily_papers_folder` | string | `DailyPapers` | Daily papers output |
| `concepts_folder` | string | `_concepts` | Concept index directory |

### inbox_processor

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_action` | string | `move_to_unsorted` | Action for unmatched files |
| `classify_unknown_images` | bool | `true` | OCR unmatched images and retry matching |
| `ask_when_uncertain` | bool | `true` | Ask user when no plugin matches |
| `semantic_search_fallback` | bool | `true` | Search vault for similar content before asking |

### memory

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `memory_dir` | string | `~/.claude/memory` | Memory files directory |
| `dedup_threshold` | float | `0.7` | Semantic similarity threshold for dedup |

### automation

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_refresh_indexes` | bool | `true` | Auto-rebuild MOC indexes |
| `git_commit` | bool | `false` | Auto-commit changes |
| `git_push` | bool | `false` | Auto-push (requires git_commit) |

## Inbox Plugin Schema

Each plugin in the `plugins` array supports these fields:

### Required

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique plugin identifier |
| `priority` | number | Match order (lower = first). Must be unique across plugins |

### Match Criteria (at least one required)

| Field | Type | Description |
|-------|------|-------------|
| `filename_contains` | string[] | Match if filename contains any keyword |
| `filename_regex` | string | Match if filename matches regex pattern |
| `extension` | string[] | Filter by file extension (e.g., `[".md", ".pdf"]`) |
| `content_hints` | string[] | Match if file content contains any hint |

### Actions (at least one required)

| Field | Type | Description |
|-------|------|-------------|
| `move_to` | string | Target directory (relative to vault root) |
| `handler_skill` | string | Skill name to invoke for processing |
| `actions` | object[] | Multi-action sequence (overrides move_to/handler_skill) |

### Optional

| Field | Type | Description |
|-------|------|-------------|
| `tags` | string[] | Labels for reporting and debugging |

### Actions Array Format

```json
"actions": [
  {"type": "handler_skill", "skill": "my-processor"},
  {"type": "move_to", "path": "Processed/"}
]
```

## Config Resolution Order

1. `_shared/user_config.py` `DEFAULT_CONFIG` (framework defaults)
2. `_shared/user-config.json` (user overrides)
3. `_shared/user-config.local.json` (machine-specific)

Each layer deep-merges into the previous. Nested objects are merged; scalar values are replaced.

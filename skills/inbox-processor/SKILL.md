---
name: inbox-processor
description: "Config-driven file router for Inbox. Reads config.json for plugin-based routing rules. Each plugin defines match criteria (filename, extension, content hints, regex) and actions (handler skill, move_to, or action sequences). Supports runtime learning via config-learner skill. TRIGGER: /inbox-processor command."
---

# Inbox Processor

Process all files in Inbox/, match them against config-driven plugins, dispatch to handlers or move to destinations, then clean the Inbox.

## Workflow

### Phase 1: Scan

1. Read `config.json` from this skill's directory
   - If `config.json` does not exist, copy from `config.example.json` and tell the user: "config.json not found. Copied from config.example.json — please edit paths and plugins before running again." Then stop.
2. List all files in Inbox/ (exclude `.DS_Store` and hidden files)
3. If empty, report "Inbox is empty, nothing to process." and stop

### Parallel Processing Strategy

- **RULE**: When Inbox has >= 3 files, prefer parallel sub-agents for complex tasks to improve throughput.
- **RULE**: Files with dependencies (e.g., `.md` referencing images in the same directory, series of screenshots on the same topic) must be assigned to the same sub-agent to avoid race conditions and context loss.
- **RULE**: Main agent directly handles simple tasks (file moves, small note archiving, renaming). Only delegate complex tasks to sub-agents (OCR matching, handler skill invocations requiring vault search).
- **RULE**: Each sub-agent receives a clear single-responsibility instruction (input file path, expected output format, target directory). Main agent is responsible for final aggregation and conflict detection.

### Phase 2: Match & Dispatch

Sort plugins by `priority` (lower number first). For each file:

#### Plugin Validation (on config load)

Before matching, validate all plugins:
- No duplicate `name` values
- No duplicate `priority` values
- Each plugin has at least one match condition (`filename_contains`, `filename_regex`, `extension`, or `content_hints`)
- Warn about unreachable plugins (shadowed by higher-priority catch-all)

Report warnings in Phase 5.

#### Matching Logic (short-circuit evaluation)

```
a. filename_contains has value AND hits any keyword → MATCH (fast path, no content read)
a2. filename_regex has value AND matches → MATCH (regex match on filename)
b. Else check extension:
   - extension has value AND does not match → SKIP this plugin
   - extension has value AND matches → continue to content_hints
   - extension not defined → continue to content_hints
c. content_hints has value → read content as needed:
   - If plugin has pre_match: ["extract_text"] → run extract_text.py first to get text
   - image (.png/.jpg/.jpeg) → OCR via Read tool
   - PDF → read first pages via Read tool, or extract_text.py
   - .docx/.xlsx/.pptx → extract_text.py (requires pip dependencies)
   - .md/.txt/.csv → direct read
   Hit any hint → MATCH
   Miss all hints → SKIP this plugin
d. extension matches but no content_hints defined → MATCH
* Missing field = does not participate in matching (no extension field means any extension is acceptable)
```

#### Content Extraction for Non-Text Files

When `content_hints` matching needs to read file content, the processor uses this strategy:

| File type | Method |
|-----------|--------|
| `.md`, `.txt`, `.csv`, `.json`, `.yaml` | Direct read |
| `.png`, `.jpg`, `.jpeg` | OCR via Claude Read tool |
| `.pdf` | Claude Read tool (preferred) or `extract_text.py` |
| `.docx` | `python3 <agentkit>/_shared/extract_text.py <path>` |
| `.xlsx` | `python3 <agentkit>/_shared/extract_text.py <path>` |
| `.pptx` | `python3 <agentkit>/_shared/extract_text.py <path>` |

Plugins can explicitly request text extraction via `pre_match`:

```json
{
  "name": "office-docs",
  "extension": [".docx", ".xlsx", ".pptx"],
  "pre_match": ["extract_text"],
  "content_hints": ["quarterly report", "budget", "project plan"],
  "move_to": "Documents/"
}
```

When `pre_match` contains `"extract_text"`, the processor runs `extract_text.py` before checking `content_hints`, regardless of file type. The extracted text is also passed as `content_preview` to handler skills.

#### Dispatch (first matching plugin wins)

A plugin can specify actions in two ways:

**Simple (single action):**
- Plugin has `handler_skill` → invoke that skill with context:
  - `file_path`: absolute path of the file in Inbox
  - `file_name`: filename
  - `matched_plugin`: name of the matched plugin
  - `content_preview`: content already read during matching (OCR/grep result), or null if not read
- Plugin has `move_to` → add to move queue (Phase 3)
- Plugin has neither → apply `default_action` from config

**Sequence (multi-action):**
- Plugin has `actions` array → execute each action in order:
  ```json
  "actions": [
    {"type": "handler_skill", "skill": "paper-reader"},
    {"type": "move_to", "path": "Papers/_sources"}
  ]
  ```

#### No Plugin Matches

- `classify_unknown_images` is `true` AND file is an image → OCR the image, then re-run matching against all plugins using OCR text as content
- **Semantic search fallback** (if configured): search vault for similar content. If results point to a clear classification, use it as a hint.
- `ask_when_uncertain` is `true` → ask the user with a description of the file and suggested actions → invoke config-learner skill to persist the decision to config.json
- Otherwise → apply `default_action` from config

### Phase 3: Execute Moves (with Conflict Detection)

Use `move_files.py` to batch-process all file moves with automatic conflict detection:

1. Build a JSON array of move instructions from Phase 2 results. Each entry:
   ```json
   {"source": "Inbox/filename", "target": "path/to/dest", "skip_move": false}
   ```
   - Set `skip_move: true` for files already handled by a handler skill

2. Execute via stdin:
   ```bash
   echo '<json_array>' | python3 <agentkit>/_shared/move_files.py
   ```

3. Parse the output JSON array. Each result has a `status` field:

   **Auto-resolved (no action needed):**
   - `moved` — file moved successfully
   - `duplicate` — identical content, source deleted
   - `skipped` — skip_move file cleaned up
   - `conflict_md_incoming_superset` — incoming replaced existing (more complete)
   - `conflict_md_existing_superset` — existing kept, source removed

   **Requires LLM intervention:**
   - `conflict_binary` — Ask user: overwrite / rename to keep both / skip
   - `conflict_md_diverged` — Execute smart merge: read both files, keep existing frontmatter/header, append incoming's unique content after `---` with comment `<!-- merged from Inbox (YYYY-MM-DD) -->`. If structure differs too much, ask user instead

4. For `.md` files with image embeds, also move referenced images from `Attachments/` if applicable

### Phase 4: Cleanup Inbox

After ALL files have been successfully processed (matched + moved/dispatched):

1. Verify each file has been moved to its destination (check target exists)
2. Remove any leftover empty files or artifacts in Inbox/
3. Confirm Inbox/ is clean with `ls Inbox/` (should only show `.DS_Store` or be empty)

### Phase 5: Report

Print a summary table:

```
Inbox processing complete (cleaned)

| File | Plugin | Action | Target | Conflict |
|------|--------|--------|--------|----------|
| report.pdf | pdf-report | move | Reports/ | — |
| screenshot.png | screenshot-ocr | move | Screenshots/ | — |
| meeting.md | meeting-notes | move | Meetings/ | — |
| random.md | (no match) | default_action | _unsorted/ | — |
```

If any rules were learned during this run, note: "Updated config.json via config-learner"

If plugin validation found warnings, list them here.

## Plugin Schema

```json
{
  "name": "plugin-name",
  "priority": 10,
  "filename_contains": ["keyword1", "keyword2"],
  "filename_regex": "\\d{4}-\\d{2}-\\d{2}.*meeting",
  "extension": [".md", ".pdf", ".docx", ".xlsx", ".pptx"],
  "pre_match": ["extract_text"],
  "content_hints": ["pattern1", "pattern2"],
  "tags": ["category1", "category2"],
  "handler_skill": "skill-name",
  "move_to": "relative/path/in/vault",
  "actions": [
    {"type": "handler_skill", "skill": "skill-name"},
    {"type": "move_to", "path": "relative/path"}
  ]
}
```

### pre_match Transforms

| Transform | Effect | Requires |
|-----------|--------|----------|
| `extract_text` | Run `_shared/extract_text.py` before content matching | python-docx, openpyxl, python-pptx (optional, per file type) |

When `pre_match` is absent, the processor uses its default content reading strategy (direct read for text, Claude OCR for images, Claude Read for PDFs).

## Critical Rules

- **NEVER guess** when uncertain — always ask the user
- **NEVER delete** source files until confirmed moved to destination
- **NEVER blindly overwrite** existing files — always check for conflicts first
- After asking the user, **ALWAYS invoke config-learner** to persist the decision to config.json
- Preserve original filenames unless the handler skill requests renaming
- **Inbox must be empty** (except `.DS_Store`) when processing is complete
- Conflict resolution results must appear in Phase 5 report with clear status

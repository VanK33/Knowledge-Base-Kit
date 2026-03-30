---
name: memory-hierarchy
description: "Structured memory management system. Scans diary and Inbox for TODOs, maintains decision/preference/lesson/project records, updates MEMORY.md index. TRIGGER: /memory-hierarchy command."
---

# Memory Hierarchy

Manage structured memory files under `~/.claude/memory/`, scan diary and Inbox for TODOs, update index.

## Workflow

### Phase 1: Load Memory

1. Read `~/.claude/memory/projects.md` for current project status and scan watermark
2. Read `~/.claude/memory/decisions.md` for existing decision count
3. Read `~/.claude/memory/preferences.md` for existing preference count
4. Read `~/.claude/memory/lessons.md` for existing lesson count
5. Read `~/.claude/memory/archived-projects.md` for archived project count

### Phase 2: Scan TODOs

#### 2a. Scan Diary

1. Read `<!-- last-diary-scan: YYYY-MM-DD -->` watermark from `projects.md`
2. Glob diary files from the configured vault diary path, extract dates from filenames
3. Filter files after watermark up to today, max 3 weeks lookback
4. For each diary file:
   - Extract `- [ ]` lines (new TODOs, exclude pure tags and pure commands)
   - Extract `- [x]` lines (completed items, sync with projects.md)
5. **Completion sync**: Match diary `- [x]` entries with `- [ ]` TODOs in projects.md, update to `- [x]`

#### 2b. Scan Inbox

1. Glob `*.md` files in the configured Inbox path
2. Read each file, extract `- [ ]` lines
3. Tag source as `source:inbox`

#### 2c. Deduplication

For each newly extracted TODO:

1. **Semantic search** (preferred): search existing memory for similar text
   - Score >= dedup_threshold → duplicate, skip
   - Score between 0.5 and threshold → possible duplicate, ask user
   - Score < 0.5 or no results → not duplicate, continue
2. **Text fallback** (when semantic search unavailable):
   - Normalize: strip `- [ ]` prefix, lowercase, trim whitespace
   - Substring match against existing TODOs in projects.md
3. **Source-date dedup**: same date + same source → don't add duplicate

#### 2d. Check TODO completion

For each open TODO, search vault for related output (concept notes, specs, reports). If highly relevant results found, flag the TODO as potentially completable in the scan report.

#### 2e. Write

1. Append deduplicated new TODOs to `projects.md` under `## TODOs`
2. Format: `- [ ] [YYYY-MM-DD source:diary|inbox] task description`
3. Update watermark: `<!-- last-diary-scan: YYYY-MM-DD -->` to today
4. Include "potentially completable" TODOs from 2d in Phase 5 report

### Phase 3: Update Memory (context-triggered)

During user interaction, proactively update memory files when relevant events occur.

**Dedup before writing**: Search existing memory for similar entries before writing. Skip if duplicate found.

**Trigger rules**:
- **Decision** (chose X over Y, with reason) → append to `~/.claude/memory/decisions.md`
  - Format: `- [YYYY-MM-DD] Chose X over Y: reason`
- **Lesson learned** → append to `~/.claude/memory/lessons.md`
  - Format: `- [YYYY-MM-DD] Problem: X → Solution: Y → Reason: Z`
- **Project status change** → update `~/.claude/memory/projects.md`
  - New project: add under `## Project Status`
  - Completed/abandoned: move to `~/.claude/memory/archived-projects.md`
- **New preference observed** → silently append to `~/.claude/memory/preferences.md`

### Phase 4: Update Index

1. Count entries in each memory file
2. Update `MEMORY.md` index with current counts

### Phase 5: Report

Output brief summary:

```
Memory Hierarchy update complete

Scan:
- Diary: X files (YYYY-MM-DD ~ YYYY-MM-DD)
- Inbox: X files
- New TODOs: X (after dedup)
- Completion sync: X items

Memory state:
| File | Entries |
|------|---------|
| decisions.md | X |
| preferences.md | X |
| projects.md TODOs | X |
| lessons.md | X |
| archived-projects.md | X |

Index updated.
```

## Writing Principles

- Only record **conclusions and decisions**, not conversation process
- Each entry is atomic: one decision/lesson/preference per line
- Strict format adherence
- When unsure whether to record, ask the user
- Never overwrite existing entries, only append or archive

## Critical Rules

- **Never overwrite**: existing entries can only be appended to or archived, not modified or deleted
- **Dedup first**: always check for similar entries before writing
- **Strict format**: each file uses its specified format
- **Ask when unsure**: if uncertain whether to record something, ask the user
- **Index < 200 lines**: MEMORY.md must stay under 200 lines
- **Atomic entries**: one decision/lesson/preference per line, no merging

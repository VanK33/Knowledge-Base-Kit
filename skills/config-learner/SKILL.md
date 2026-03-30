---
name: config-learner
description: "Runtime learning for config-driven skills. Receives a user's classification decision and persists it as a new plugin entry in the calling skill's config.json. Use when: another skill encounters an unknown input and the user provides a handling decision, or user says 'learn this rule'/'add rule'."
---

# config-learner

## Workflow

### Step 1: Receive input

Receive the following parameters from the calling skill:

- `skill_name`: which skill's config to update (e.g. "inbox-processor")
- `file_example`: the file that triggered learning
- `user_decision`: how the user wants to handle it (e.g. "move screenshots like this to Screenshots/")

### Step 2: Parse user decision

Infer match rules from the user's decision:

- Extract keywords from filename → `filename_contains`
- Record file extension → `extension`
- If content was already read/OCR'd, extract distinguishing phrases → `content_hints`
- Determine action: if user specified a skill → `handler_skill`; if user specified a path → `move_to`

### Step 3: Propose plugin draft

Show the inferred rule to the user via AskUserQuestion:

- Display inferred match rules
- Display handler_skill or move_to
- Suggest priority (default 50, user can adjust)
- Ask: "Is this rule accurate? Need adjustments?"
- Options: "Confirm" / "Adjust match rules" / "Adjust priority" / "Cancel"

### Step 4: Read config

Load `~/.claude/skills/{skill_name}/config.json`

- If file doesn't exist → error: "skill {skill_name} has no config.json"

### Step 5: Validate

Check new plugin against existing plugins:

- No duplicate `name`
- No duplicate `priority` (if conflict, suggest next available number)
- No identical `match` rules (warn if very similar)

### Step 6: Write

Append new plugin to the `plugins` array, write back to config.json

### Step 7: Verify

Re-read config.json, verify valid JSON, report: "Plugin '{name}' added to {skill_name}/config.json, priority {n}"

## What it does NOT do

- Does not create handler skills (only registers routing rules, handlers must be installed separately)
- Does not modify SKILL.md files (only operates on config.json)
- Does not delete or modify existing plugin entries (only appends new ones)

## Interaction Rules

- Follow user's language (Chinese → Chinese, English → English)
- One question at a time
- If user cancels at step 3, stop gracefully: "Cancelled, no changes made."

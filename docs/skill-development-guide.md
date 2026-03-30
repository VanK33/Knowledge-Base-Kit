# Skill Development Guide

## What is a Skill?

A Claude Code skill is a directory containing a `SKILL.md` file — a structured prompt that gives Claude specialized capabilities. Skills are invoked via slash commands (e.g., `/inbox-processor`) or by other skills.

## Skill Structure

```
skills/my-skill/
├── SKILL.md              # Required: the skill prompt
├── config.json           # Optional: runtime config (gitignored)
├── config.example.json   # Optional: config template (committed)
├── scripts/              # Optional: Python/bash utilities
│   └── process.py
└── references/           # Optional: domain rules, templates
    └── rules.md
```

## Writing SKILL.md

### Frontmatter

```yaml
---
name: my-skill
description: "One-line description. Include trigger conditions so Claude knows when to activate."
---
```

### Body Structure

A good SKILL.md follows this pattern:

```markdown
# Skill Name

Brief description of what the skill does.

## Workflow

### Phase 1: Input
What the skill receives and how it validates input.

### Phase 2: Processing
Step-by-step logic. Be explicit — Claude follows these instructions literally.

### Phase 3: Output
What the skill produces and where it goes.

## Critical Rules
Non-negotiable constraints (never delete, always ask, etc.)
```

### Writing Tips

1. **Be explicit.** Claude follows SKILL.md literally. If you want it to check for conflicts before moving, say so.
2. **Use phases.** Breaking the workflow into phases helps Claude maintain context in long operations.
3. **Include error handling.** What happens when a file doesn't exist? When config is missing?
4. **Define the contract.** What inputs does the skill expect? What does it output?

## Config-Driven Skills

For skills that need user-customizable behavior:

1. Create `config.example.json` with documented defaults
2. SKILL.md Phase 1 reads `config.json` (or copies from example)
3. Use `_shared/user_config.py` for vault paths:
   ```python
   from user_config import vault_root_path, resolve_vault_path
   ```

## Handler Skills

Handler skills are invoked by inbox-processor. They receive a standard context:

```
file_path: /absolute/path/to/Inbox/file.md
file_name: file.md
matched_plugin: plugin-name
content_preview: (text content if already read, null otherwise)
```

Your SKILL.md should document that it expects this context.

## Skill Communication Patterns

### Orchestrator → Sub-skills

```markdown
## Workflow

1. Invoke `/step-1-skill` with parameters
2. Invoke `/step-2-skill` with output from step 1
3. Aggregate results
```

### Utility Skills

Called by other skills with custom parameters:

```markdown
## Workflow

### Step 1: Receive input
Parameters from calling skill:
- `param1`: description
- `param2`: description
```

## Agent Templates

Agent templates (in `agents/`) define specialized sub-agents:

```yaml
---
name: my-agent
description: What this agent does
tools: Read, Glob, Grep, Bash    # Available tools
model: sonnet                      # Model to use
maxTurns: 15                       # Turn limit
---
```

Agents are invoked via the Agent tool in Claude Code. They run in isolation and return a result.

## Testing Your Skill

1. Create test input files in Inbox/
2. Run your skill: `/my-skill`
3. Verify output matches expectations
4. Test edge cases: empty input, missing config, conflicts

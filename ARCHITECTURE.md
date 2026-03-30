# Architecture

AgentKit is built on five core design patterns that work together to create an intelligent knowledge management system.

## 1. Config-Driven Routing

The inbox-processor uses a **priority-ordered plugin system** where each plugin declares match criteria and actions in JSON:

```
File arrives in Inbox/
  → Sort plugins by priority (lower = higher priority)
  → For each plugin:
      1. filename_contains → keyword match (fast path, no file read)
      2. filename_regex → regex match
      3. extension → type filter
      4. content_hints → read content (OCR for images, text for md/pdf)
      → First match wins → dispatch action
  → No match → fallback chain (OCR retry → semantic search → ask user)
```

**Why this design:**
- Short-circuit evaluation minimizes I/O (most files match on filename alone)
- Priority system allows precise ordering without plugin interdependency
- Missing fields don't participate in matching (progressive specificity)
- JSON config is editable by both humans and LLMs (config-learner)

## 2. Self-Learning Rules

When inbox-processor encounters an unknown file:

```
Unknown file
  → OCR/read content
  → Semantic search vault for similar files (optional)
  → Ask user: "How should I handle this?"
  → User decides → config-learner activates:
      1. Infer match rules from the file + user's decision
      2. Propose plugin draft → user confirms/adjusts
      3. Validate against existing plugins (no conflicts)
      4. Append to config.json
  → Next time: auto-matched by the new rule
```

**Key property:** The system gets smarter with use. Every user interaction that resolves an unknown file permanently teaches the system. After a few weeks, most files route automatically.

## 3. Conflict-Aware File Operations

`move_files.py` handles the complexity of moving files to destinations that may already have content:

```
Move file to target
  → Target doesn't exist → move (simple case)
  → Target exists:
      Binary: md5 match → duplicate (delete source)
              md5 differ → conflict_binary (ask user)
      Markdown: exact match → duplicate
                incoming ⊃ existing → replace (incoming is more complete)
                existing ⊃ incoming → keep existing (delete source)
                both have unique content → conflict_md_diverged (LLM merges)
```

**Design decisions:**
- Superset detection prevents data loss when the same note is edited in multiple places
- Binary conflicts always require human decision (no safe auto-resolution)
- Diverged markdown can be smart-merged by the LLM (append unique content with merge comment)
- All operations are stdin/stdout JSON — pure function, no side effects beyond file I/O

## 4. Structured Memory

memory-hierarchy maintains four atomic memory files:

| File | Format | Trigger |
|------|--------|---------|
| `decisions.md` | `- [YYYY-MM-DD] Chose X over Y: reason` | User makes an explicit choice |
| `lessons.md` | `- [YYYY-MM-DD] Problem → Solution → Reason` | Problem solved with reusable insight |
| `preferences.md` | `[Topic] Conclusion \| Files \| #tags` | Behavioral pattern observed |
| `projects.md` | `- [ ] [date source] description` | TODO extracted from diary/inbox |

**Deduplication** before every write:
1. Semantic search existing entries (threshold-based)
2. Fallback to text substring matching
3. Source-date dedup (same date + source = skip)

**Why atomic entries:** Each line is self-contained. No merge conflicts. Append-only means nothing is ever lost. The MEMORY.md index stays under 200 lines for fast loading.

## 5. Session Lifecycle

Hooks run at session boundaries:

**SessionStart** — `session-start-dispatcher.py`:
- Runs all registered scripts in parallel via ThreadPoolExecutor
- Each script has an independent timeout
- Global timeout prevents runaway startup
- Individual failures don't block other scripts

**SessionEnd** — export conversation to vault:
- Only text messages (no tool calls or thinking)
- Session ID dedup prevents double-export
- save-clear provides manual trigger with memory extraction

## Skill Interface Contract

Every skill follows these conventions (documented, not enforced by code):

```
skills/{name}/
├── SKILL.md              # Required: prompt with YAML frontmatter
├── config.json           # Optional: runtime-configurable behavior
├── config.example.json   # Optional: template for config.json
├── scripts/              # Optional: Python/bash utilities
└── references/           # Optional: domain-specific rules
```

**Communication patterns:**
- **Orchestrator → sub-skills**: chains skills in sequence (e.g., daily-papers → fetch → review → notes)
- **Handler skills**: called by inbox-processor with standard context `{file_path, file_name, matched_plugin, content_preview}`
- **Utility skills**: called by other skills with custom parameters (e.g., config-learner)

## Configuration Architecture

```
DEFAULT_CONFIG (user_config.py)     ← Framework defaults (committed)
  ↓ deep merge
user-config.json                    ← User overrides (gitignored)
  ↓ deep merge
user-config.local.json              ← Machine-specific (gitignored)
  = final config
```

Skills access config via `user_config.py` helpers:
- `vault_root_path()` → resolved Path
- `resolve_vault_path("relative/path")` → full Path
- `skill_config("skill-name")` → skill's config.json as dict
- `automation_config()` → git/index automation flags

This three-layer system means:
- Framework updates don't overwrite user config
- Machine-specific paths (vault location) stay local
- All paths resolve through one module (no hardcoding in skills)

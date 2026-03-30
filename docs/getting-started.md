# Getting Started

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed (CLI, desktop app, or IDE extension)
- Python 3.10+
- A knowledge base directory (e.g., Obsidian vault or any directory you want to organize)

## Installation

```bash
git clone https://github.com/youruser/agentkit.git
cd agentkit
chmod +x setup.sh
./setup.sh
```

The setup script will ask you:
1. **Vault path** — where your knowledge base lives (e.g., `~/MyVault`)
2. **What to install** — core skills only, or everything including agents and hooks

It creates symlinks from the repo to `~/.claude/skills/`, so `git pull` updates everything.

## First Run

1. Create a test file in your vault's Inbox:
   ```bash
   echo "# Meeting Notes 2024-01-15\n\n- Discussed project timeline\n- Action items for next week" > ~/MyVault/Inbox/test-meeting.md
   ```

2. In Claude Code, run:
   ```
   /inbox-processor
   ```

3. The processor will:
   - Scan Inbox/
   - Match `test-meeting.md` against plugins
   - If `meeting-notes` plugin exists → move to `Meetings/`
   - If no match → ask you how to handle it → learn the rule

## Customizing Plugins

Edit `~/.claude/skills/inbox-processor/config.json` to add your own plugins:

```json
{
  "name": "my-plugin",
  "priority": 25,
  "filename_contains": ["keyword"],
  "extension": [".md"],
  "move_to": "MyFolder/"
}
```

Or let the system learn — drop an unmatched file, tell Claude where it should go, and config-learner will create the rule automatically.

## Example Configs

Pre-built plugin sets for common workflows:

- `examples/inbox-plugins/academic-researcher.json` — Papers, reading notes, lecture slides
- `examples/inbox-plugins/knowledge-worker.json` — Meeting notes, voice memos, project docs
- `examples/inbox-plugins/software-engineer.json` — Bug reports, design docs, config files

Copy one to get started:
```bash
cp examples/inbox-plugins/knowledge-worker.json ~/.claude/skills/inbox-processor/config.json
```

Then edit the `paths` section to point to your vault.

## Next Steps

- [Config Reference](config-reference.md) — all configuration options
- [Writing Custom Plugins](writing-custom-plugins.md) — plugin schema and matching logic
- [Skill Development Guide](skill-development-guide.md) — creating your own skills

#!/bin/bash
set -euo pipefail

# AgentKit Setup Script
# Interactive bootstrap for installing skills, agents, and hooks

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"
AGENTS_DIR="$CLAUDE_DIR/agents"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AgentKit Setup${NC}"
echo "=============="
echo ""

# --- Prerequisites ---

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Python: ${GREEN}$PYTHON_VERSION${NC}"

if [ ! -d "$CLAUDE_DIR" ]; then
    echo "Error: ~/.claude/ not found. Is Claude Code installed?"
    exit 1
fi
echo -e "Claude Code: ${GREEN}found${NC}"
echo ""

# --- Vault Path ---

read -p "Knowledge base path [~/MyKnowledgeBase]: " VAULT_PATH
VAULT_PATH="${VAULT_PATH:-~/MyKnowledgeBase}"
VAULT_PATH_EXPANDED="${VAULT_PATH/#\~/$HOME}"

if [ ! -d "$VAULT_PATH_EXPANDED" ]; then
    echo -e "${YELLOW}Warning: $VAULT_PATH does not exist. Creating it...${NC}"
    mkdir -p "$VAULT_PATH_EXPANDED"
fi
echo ""

# --- Skill Selection ---

echo "Which skill sets do you want to install?"
echo ""
echo "  [1] Core (inbox-processor, config-learner, memory-hierarchy, save-clear)"
echo "  [2] Core + Shared infrastructure (_shared utilities)"
echo "  [3] Everything (Core + _shared + agents + hooks)"
echo ""
read -p "Choice [3]: " CHOICE
CHOICE="${CHOICE:-3}"

# --- Install _shared ---

install_shared() {
    echo -e "\n${BLUE}Installing shared infrastructure...${NC}"
    mkdir -p "$SKILLS_DIR/_shared"

    # Symlink shared files
    for f in user_config.py moc_builder.py move_files.py; do
        if [ -L "$SKILLS_DIR/_shared/$f" ]; then
            rm "$SKILLS_DIR/_shared/$f"
        fi
        if [ -f "$SKILLS_DIR/_shared/$f" ] && [ ! -L "$SKILLS_DIR/_shared/$f" ]; then
            echo -e "  ${YELLOW}Backing up existing $f → $f.bak${NC}"
            mv "$SKILLS_DIR/_shared/$f" "$SKILLS_DIR/_shared/$f.bak"
        fi
        ln -sf "$SCRIPT_DIR/_shared/$f" "$SKILLS_DIR/_shared/$f"
        echo "  Linked _shared/$f"
    done

    # Create user-config.json from example if it doesn't exist
    if [ ! -f "$SKILLS_DIR/_shared/user-config.json" ]; then
        sed "s|~/YourVault|$VAULT_PATH|g" "$SCRIPT_DIR/_shared/user-config.example.json" > "$SKILLS_DIR/_shared/user-config.json"
        echo -e "  ${GREEN}Created user-config.json with vault path: $VAULT_PATH${NC}"
    else
        echo "  user-config.json already exists, skipping"
    fi
}

# --- Install Skills ---

install_skill() {
    local skill_name="$1"
    echo -e "  Installing skill: ${GREEN}$skill_name${NC}"
    mkdir -p "$SKILLS_DIR/$skill_name"

    # Symlink SKILL.md
    if [ -L "$SKILLS_DIR/$skill_name/SKILL.md" ]; then
        rm "$SKILLS_DIR/$skill_name/SKILL.md"
    fi
    if [ -f "$SKILLS_DIR/$skill_name/SKILL.md" ] && [ ! -L "$SKILLS_DIR/$skill_name/SKILL.md" ]; then
        mv "$SKILLS_DIR/$skill_name/SKILL.md" "$SKILLS_DIR/$skill_name/SKILL.md.bak"
    fi
    ln -sf "$SCRIPT_DIR/skills/$skill_name/SKILL.md" "$SKILLS_DIR/$skill_name/SKILL.md"

    # Copy config.example.json and create config.json if needed
    if [ -f "$SCRIPT_DIR/skills/$skill_name/config.example.json" ]; then
        cp "$SCRIPT_DIR/skills/$skill_name/config.example.json" "$SKILLS_DIR/$skill_name/config.example.json"
        if [ ! -f "$SKILLS_DIR/$skill_name/config.json" ]; then
            sed "s|~/YourVault|$VAULT_PATH|g" "$SCRIPT_DIR/skills/$skill_name/config.example.json" > "$SKILLS_DIR/$skill_name/config.json"
            echo "    Created config.json from example"
        fi
    fi

    # Symlink scripts/ if exists
    if [ -d "$SCRIPT_DIR/skills/$skill_name/scripts" ]; then
        mkdir -p "$SKILLS_DIR/$skill_name/scripts"
        for script in "$SCRIPT_DIR/skills/$skill_name/scripts"/*; do
            [ -f "$script" ] || continue
            local basename=$(basename "$script")
            ln -sf "$script" "$SKILLS_DIR/$skill_name/scripts/$basename"
        done
    fi
}

install_core_skills() {
    echo -e "\n${BLUE}Installing core skills...${NC}"
    for skill in inbox-processor config-learner memory-hierarchy save-clear; do
        install_skill "$skill"
    done
}

# --- Install Agents ---

install_agents() {
    echo -e "\n${BLUE}Installing agent templates...${NC}"
    mkdir -p "$AGENTS_DIR"

    for agent in researcher.md coder.md checker.md; do
        if [ -f "$AGENTS_DIR/$agent" ] && [ ! -L "$AGENTS_DIR/$agent" ]; then
            mv "$AGENTS_DIR/$agent" "$AGENTS_DIR/$agent.bak"
        fi
        ln -sf "$SCRIPT_DIR/agents/$agent" "$AGENTS_DIR/$agent"
        echo "  Linked agents/$agent"
    done
}

# --- Install Hooks ---

install_hooks() {
    echo -e "\n${BLUE}Installing hooks...${NC}"
    echo "  Hooks template available at: $SCRIPT_DIR/hooks/hooks.example.json"
    echo -e "  ${YELLOW}To activate, add the hook config to your ~/.claude/settings.json${NC}"
    echo "  See hooks/hooks.example.json for the format."
}

# --- Execute ---

case "$CHOICE" in
    1)
        install_shared
        install_core_skills
        ;;
    2)
        install_shared
        install_core_skills
        ;;
    3)
        install_shared
        install_core_skills
        install_agents
        install_hooks
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# --- Create Inbox directory ---

INBOX_DIR="$VAULT_PATH_EXPANDED/Inbox"
if [ ! -d "$INBOX_DIR" ]; then
    mkdir -p "$INBOX_DIR"
    echo -e "\n${GREEN}Created Inbox directory: $INBOX_DIR${NC}"
fi

# --- Done ---

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit ~/.claude/skills/_shared/user-config.json to customize paths"
echo "  2. Edit ~/.claude/skills/inbox-processor/config.json to add your plugins"
echo "  3. Run /inbox-processor in Claude Code to test"
echo ""
echo "Example plugin configs available in: $SCRIPT_DIR/examples/inbox-plugins/"

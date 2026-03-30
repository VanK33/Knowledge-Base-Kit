#!/usr/bin/env python3
"""
Configuration loader for AgentKit skills.

Three-layer config resolution:
  1. DEFAULT_CONFIG (framework defaults, committed)
  2. user-config.json (user overrides, gitignored)
  3. user-config.local.json (machine-specific overrides, gitignored)

Usage:
  from user_config import load_user_config, vault_root_path, resolve_vault_path
"""

import copy
import json
from functools import lru_cache
from pathlib import Path


DEFAULT_CONFIG = {
    "paths": {
        "vault_root": "~/KnowledgeBase",
        "inbox_folder": "Inbox",
        "unsorted_folder": "Inbox/_unsorted",
        "archives_folder": "archives/claude-logs",
        "paper_notes_folder": "Papers",
        "daily_papers_folder": "DailyPapers",
        "concepts_folder": "_concepts",
    },
    "inbox_processor": {
        "default_action": "move_to_unsorted",
        "classify_unknown_images": True,
        "ask_when_uncertain": True,
        "semantic_search_fallback": True,
    },
    "memory": {
        "memory_dir": "~/.claude/memory",
        "dedup_threshold": 0.7,
    },
    "automation": {
        "auto_refresh_indexes": True,
        "git_commit": False,
        "git_push": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def load_user_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_dir = Path(__file__).resolve().parent

    for filename in ("user-config.json", "user-config.local.json"):
        config_path = config_dir / filename
        if not config_path.exists():
            continue
        with config_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            _deep_merge(config, loaded)

    return config


def _expand(path_value: str) -> Path:
    return Path(path_value).expanduser()


def paths_config() -> dict:
    return load_user_config()["paths"]


def automation_config() -> dict:
    config = load_user_config()["automation"]
    if config.get("git_push") and not config.get("git_commit"):
        config = copy.deepcopy(config)
        config["git_push"] = False
    return config


def vault_root_path() -> Path:
    """Return the knowledge base root path."""
    paths = paths_config()
    # Support both "vault_root" and legacy "obsidian_vault" key
    root = paths.get("vault_root") or paths.get("obsidian_vault", "~/KnowledgeBase")
    return _expand(root)


# Backward-compatible alias
obsidian_vault_path = vault_root_path


def resolve_vault_path(relative: str) -> Path:
    """Resolve a path relative to the knowledge base root."""
    return vault_root_path() / relative


def inbox_path() -> Path:
    return resolve_vault_path(paths_config()["inbox_folder"])


def unsorted_path() -> Path:
    return resolve_vault_path(paths_config()["unsorted_folder"])


def archives_path() -> Path:
    return resolve_vault_path(paths_config()["archives_folder"])


def paper_notes_dir() -> Path:
    return resolve_vault_path(paths_config()["paper_notes_folder"])


def daily_papers_dir() -> Path:
    return resolve_vault_path(paths_config()["daily_papers_folder"])


def concepts_dir() -> Path:
    return paper_notes_dir() / paths_config()["concepts_folder"]


def skill_config(skill_name: str) -> dict:
    """Load a specific skill's config.json, merged with framework defaults."""
    skills_dir = Path(__file__).resolve().parent.parent / "skills" / skill_name
    config_path = skills_dir / "config.json"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def auto_refresh_indexes_enabled() -> bool:
    return bool(automation_config()["auto_refresh_indexes"])


def git_commit_enabled() -> bool:
    return bool(automation_config()["git_commit"])


def git_push_enabled() -> bool:
    return bool(automation_config()["git_push"])

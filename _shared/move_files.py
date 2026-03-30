#!/usr/bin/env python3
"""
Conflict-aware file mover for config-driven file routing.

Input (stdin): JSON array of move instructions:
  [{"source": "/path/to/file.md", "target": "/path/to/dest.md", "skip_move": false}, ...]

Output (stdout): JSON array of results:
  [{"source": "...", "target": "...", "status": "moved|duplicate|skipped|conflict_binary|conflict_md_incoming_superset|conflict_md_existing_superset|conflict_md_diverged", "detail": "..."}, ...]

Auto-resolved statuses (no intervention needed):
  - moved: file moved successfully
  - duplicate: identical content, source deleted
  - skipped: skip_move=true and target exists, source deleted
  - conflict_md_incoming_superset: incoming replaces existing, source deleted
  - conflict_md_existing_superset: existing kept, source deleted

Statuses requiring intervention:
  - conflict_binary: binary files differ (md5 mismatch)
  - conflict_md_diverged: both files have unique content
"""

import hashlib
import json
import os
import shutil
import sys


BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif",
    ".pdf", ".zip", ".tar", ".gz", ".mp3", ".mp4", ".mov", ".wav",
}


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_binary(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in BINARY_EXTENSIONS


def normalize_lines(text: str) -> set[str]:
    """Return set of non-empty stripped lines for superset comparison."""
    return {line.strip() for line in text.splitlines() if line.strip()}


def compare_markdown(source: str, target: str) -> str:
    """Compare two markdown files and return conflict type.

    Returns one of:
      duplicate, conflict_md_incoming_superset,
      conflict_md_existing_superset, conflict_md_diverged
    """
    with open(source, "r", encoding="utf-8", errors="replace") as f:
        incoming_text = f.read()
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        existing_text = f.read()

    if incoming_text == existing_text:
        return "duplicate"

    incoming_lines = normalize_lines(incoming_text)
    existing_lines = normalize_lines(existing_text)

    if incoming_lines == existing_lines:
        return "duplicate"

    incoming_only = incoming_lines - existing_lines
    existing_only = existing_lines - incoming_lines

    if not incoming_only and existing_only:
        return "conflict_md_existing_superset"
    elif incoming_only and not existing_only:
        return "conflict_md_incoming_superset"
    else:
        return "conflict_md_diverged"


def process_move(instruction: dict) -> dict:
    source = instruction["source"]
    target = instruction["target"]
    skip_move = instruction.get("skip_move", False)

    result = {"source": source, "target": target}

    if not os.path.exists(source):
        result["status"] = "error"
        result["detail"] = f"source not found: {source}"
        return result

    target_dir = os.path.dirname(target)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    if skip_move:
        if os.path.exists(target):
            os.remove(source)
            result["status"] = "skipped"
            result["detail"] = "skip_move: target exists, source removed"
        else:
            result["status"] = "error"
            result["detail"] = "skip_move=true but target does not exist"
        return result

    if not os.path.exists(target):
        shutil.move(source, target)
        if os.path.exists(target):
            result["status"] = "moved"
        else:
            result["status"] = "error"
            result["detail"] = "move succeeded but target not found after move"
        return result

    # Conflict: target exists
    if is_binary(source):
        src_md5 = md5_file(source)
        tgt_md5 = md5_file(target)
        if src_md5 == tgt_md5:
            os.remove(source)
            result["status"] = "duplicate"
            result["detail"] = f"md5 match: {src_md5}"
        else:
            result["status"] = "conflict_binary"
            result["detail"] = f"md5 differ: src={src_md5} tgt={tgt_md5}"
    else:
        conflict_type = compare_markdown(source, target)
        if conflict_type == "duplicate":
            os.remove(source)
            result["status"] = "duplicate"
            result["detail"] = "content identical"
        elif conflict_type == "conflict_md_incoming_superset":
            shutil.move(source, target)
            result["status"] = "conflict_md_incoming_superset"
            result["detail"] = "incoming is superset, replaced existing"
        elif conflict_type == "conflict_md_existing_superset":
            os.remove(source)
            result["status"] = "conflict_md_existing_superset"
            result["detail"] = "existing is superset, source removed"
        else:
            result["status"] = "conflict_md_diverged"
            result["detail"] = "both files have unique content"

    return result


def main():
    try:
        raw = sys.stdin.read()
        instructions = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps([{"status": "error", "detail": f"invalid JSON input: {e}"}]))
        sys.exit(1)

    if not isinstance(instructions, list):
        print(json.dumps([{"status": "error", "detail": "input must be a JSON array"}]))
        sys.exit(1)

    results = []
    for instr in instructions:
        if not isinstance(instr, dict) or "source" not in instr or "target" not in instr:
            results.append({
                "source": instr.get("source", "?"),
                "target": instr.get("target", "?"),
                "status": "error",
                "detail": "missing required fields: source, target",
            })
            continue
        results.append(process_move(instr))

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

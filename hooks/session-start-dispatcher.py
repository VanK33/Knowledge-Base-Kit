#!/usr/bin/env python3
"""
SessionStart Dispatcher — run all startup scripts in parallel.

Register this single hook in settings.json. Internal scripts are managed in the
SCRIPTS list below. Each script runs in parallel; individual failures don't affect others.

Usage:
  Direct:    python3 hooks/session-start-dispatcher.py
  Hook:      Auto-invoked by Claude Code SessionStart
"""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# === Configuration ===

SCRIPTS_DIR = Path(__file__).parent
LOG_FILE = SCRIPTS_DIR / "session-start-dispatcher.log"

# Global timeout (seconds) — all scripts must finish within this time
GLOBAL_TIMEOUT = 30

# ============================================================
# Register SessionStart scripts here
# ============================================================
# Format: { "name": display_name, "command": command, "timeout": per-script_timeout_seconds }
#
# Variables available in command:
#   {scripts_dir} → directory containing this dispatcher
#
# To add a new script, append an entry to this list.
# To disable a script, add "disabled": True.
# ============================================================

SCRIPTS = [
    # Example scripts — uncomment and customize for your setup:
    #
    # {
    #     "name": "scan-todos",
    #     "command": "python3 {scripts_dir}/scan-todos.py",
    #     "timeout": 15,
    # },
    # {
    #     "name": "check-skills-updates",
    #     "command": "python3 {scripts_dir}/check-skills-updates.py",
    #     "timeout": 10,
    # },
    # {
    #     "name": "summarize-projects",
    #     "command": "python3 {scripts_dir}/summarize-projects.py",
    #     "timeout": 5,
    # },
]


# === Logging ===

def log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


# === Runner ===

def run_script(entry: dict) -> dict:
    """Run a single script and return result dict."""
    name = entry["name"]
    cmd = entry["command"].replace("{scripts_dir}", str(SCRIPTS_DIR))
    timeout = entry.get("timeout", 15)

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        elapsed = time.monotonic() - start
        return {
            "name": name,
            "ok": result.returncode == 0,
            "elapsed": elapsed,
            "returncode": result.returncode,
            "stderr": result.stderr.strip()[-200:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return {
            "name": name,
            "ok": False,
            "elapsed": elapsed,
            "returncode": -1,
            "stderr": f"TIMEOUT after {timeout}s",
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "name": name,
            "ok": False,
            "elapsed": elapsed,
            "returncode": -1,
            "stderr": str(e)[:200],
        }


def main():
    active_scripts = [s for s in SCRIPTS if not s.get("disabled")]

    if not active_scripts:
        log("no active scripts, exiting")
        sys.exit(0)

    names = ", ".join(s["name"] for s in active_scripts)
    log(f"=== dispatcher start ({len(active_scripts)} scripts: {names}) ===")

    total_start = time.monotonic()

    with ThreadPoolExecutor(max_workers=len(active_scripts)) as pool:
        futures = {pool.submit(run_script, s): s["name"] for s in active_scripts}
        results = []

        for future in as_completed(futures, timeout=GLOBAL_TIMEOUT):
            results.append(future.result())

    total_elapsed = time.monotonic() - total_start

    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        err = f' — {r["stderr"]}' if r["stderr"] else ""
        log(f"  {status} {r['name']}: {r['elapsed']:.2f}s (exit {r['returncode']}){err}")

    ok_count = sum(1 for r in results if r["ok"])
    log(f"=== dispatcher done: {ok_count}/{len(results)} ok, total {total_elapsed:.2f}s ===")


if __name__ == "__main__":
    main()

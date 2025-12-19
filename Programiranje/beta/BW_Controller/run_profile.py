"""Run a saved Camoufox profile (created by `create_profile`).

Loads `profile.json` and starts Camoufox using the saved `options` via
`Camoufox(from_options=opts, persistent_context=True)`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from camoufox import Camoufox


def run_profile_process(profile_json_path: str) -> None:
    p = Path(profile_json_path)
    if not p.exists():
        raise FileNotFoundError(profile_json_path)

    # Accept either a profile.json path (top-level) or a namespace.json path.
    if p.name == "profile.json":
        with p.open("r", encoding="utf-8") as f:
            profile = json.load(f)
        namespaces = profile.get("namespaces", {})
        if not namespaces:
            raise RuntimeError("Profile has no namespaces")
        # Prefer a 'default' namespace if present, otherwise pick the first one
        if "default" in namespaces:
            ns_path = Path(namespaces["default"])
        else:
            ns_path = Path(list(namespaces.values())[0])
        if not ns_path.exists():
            raise FileNotFoundError(ns_path)
        with ns_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

    opts = data.get("options", {})

    print(f"Starting Camoufox for profile/namespace {data.get('name') or data.get('profile_id')}")

    with Camoufox(from_options=opts, persistent_context=True) as browser:
        # Avoid creating a second window: if a page already exists, re-use it.
        pages = list(browser.pages)
        if pages:
            page = pages[0]
        else:
            page = browser.new_page()
        page.goto("about:blank")
        print("Camoufox is running. Close the browser window to stop it.")

        # Waiting strategy:
        # - If stdin is available (running from a terminal), allow user to press ENTER.
        # - Otherwise (spawned GUI process without a TTY), poll until the page is closed.
        import sys
        import time

        try:
            if sys.stdin and sys.stdin.isatty():
                input()
            else:
                while True:
                    try:
                        if page.is_closed():
                            break
                    except Exception:
                        # If querying the page fails, assume the browser closed
                        break
                    time.sleep(0.5)
        except (KeyboardInterrupt, EOFError):
            pass


if __name__ == "__main__":  # pragma: no cover - manual run
    import sys

    if len(sys.argv) < 2:
        print("Usage: python BW_Controller/run_profile.py path/to/profile.json")
        raise SystemExit(1)

    run_profile_process(sys.argv[1])

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

        # Apply saved geolocation if present
        geo = data.get("geolocation")
        if geo:
            try:
                # Browser is a BrowserContext when persistent_context=True
                # set_geolocation expects dict with latitude & longitude
                loc = {"latitude": float(geo["latitude"]), "longitude": float(geo["longitude"])}
                if hasattr(browser, "set_geolocation"):
                    try:
                        browser.set_geolocation(loc)
                    except Exception:
                        # some environments require page.context.set_geolocation; try both
                        try:
                            page.context.set_geolocation(loc)
                        except Exception:
                            pass
            except Exception:
                pass

        # Apply timezone override if present in geolocation metadata
        tz = data.get("geolocation", {}).get("timezone")
        if tz:
            try:
                # Use a small init script to override Intl timezone resolution
                script = (
                    "(() => { const tz = '" + str(tz) + "'; try { const orig = Intl.DateTimeFormat.prototype.resolvedOptions; Intl.DateTimeFormat.prototype.resolvedOptions = function() { return Object.assign({}, orig.call(this), { timeZone: tz }); }; } catch(e) {} })();"
                )
                try:
                    page.add_init_script(script)
                except Exception:
                    try:
                        # Older API
                        page.context.add_init_script(script)
                    except Exception:
                        pass
            except Exception:
                pass

        # Enforce viewport/window size to 1920x1080 to match fingerprint
        try:
            page.set_viewport_size({"width": 1920, "height": 1080})
        except Exception:
            try:
                # older API
                page.set_viewport_size(1920, 1080)
            except Exception:
                pass

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

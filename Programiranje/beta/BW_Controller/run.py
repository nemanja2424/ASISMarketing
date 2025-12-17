# BW_Controller/run.py

import json
import os
import time
from camoufox import Camoufox


def _load_profile(profile_path: str):
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If this is a meta file, resolve fingerprint/storage files relative to meta dir
    if "fingerprint_file" in data or "storage_state_file" in data:
        base = os.path.dirname(profile_path)
        fingerprint = None
        storage_state = None

        if data.get("fingerprint_file"):
            fp_path = os.path.join(base, data["fingerprint_file"])
            with open(fp_path, "r", encoding="utf-8") as ff:
                fingerprint = json.load(ff)
        if data.get("storage_state_file"):
            ss_path = os.path.join(base, data["storage_state_file"])
            with open(ss_path, "r", encoding="utf-8") as sf:
                storage_state = json.load(sf)

        return data, fingerprint, storage_state

    # Legacy single-file profile
    return data, data.get("fingerprint"), None


def run_profile_process(profile_path: str):
    """
    OVA FUNKCIJA SE POKREĆE U POSEBNOM PROCESS-U
    """
    profile, fingerprint, storage_state = _load_profile(profile_path)

    profile_dir = os.path.dirname(profile_path)
    lock_path = os.path.join(profile_dir, ".lock")
    if os.path.exists(lock_path):
        print(f"⚠️ Profile is already in use: {profile_path}")
        return

    # Acquire lock
    open(lock_path, "w").close()

    try:
        # Ensure Camoufox targets Windows when restoring a Windows profile
        with Camoufox(os='windows') as browser:
            # Create context using fingerprint hints
            ctx_args = {}
            if fingerprint:
                ctx_args.update({
                    "user_agent": fingerprint.get("userAgent"),
                    "locale": ",".join(fingerprint.get("languages", [])),
                    "timezone_id": fingerprint.get("timezone"),
                })

                # viewport options
                if fingerprint.get("screen"):
                    screen = fingerprint["screen"]
                    ctx_args["viewport"] = {
                        "width": screen.get("width"),
                        "height": screen.get("height"),
                    }
                    if screen.get("dpr"):
                        ctx_args["device_scale_factor"] = screen.get("dpr")

            context = browser.new_context(**ctx_args)
            page = context.new_page()

            # Restore cookies
            if storage_state and storage_state.get("cookies"):
                try:
                    context.add_cookies(storage_state.get("cookies"))
                except Exception:
                    # best-effort: ignore if API differs
                    pass

            # Restore localStorage for origins
            if storage_state and storage_state.get("origins"):
                for origin in storage_state.get("origins", []):
                    origin_url = origin.get("origin")
                    try:
                        page.goto(origin_url)
                        items = origin.get("localStorage", [])
                        for it in items:
                            name = it.get("name")
                            value = it.get("value")
                            page.evaluate("(k,v)=>localStorage.setItem(k,v)", name, value)
                    except Exception:
                        # ignore errors per-origin
                        pass

            page.goto("https://browserleaks.com")

            print(f"[RUNNING] {profile.get('profile_id')}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("[STOP] Browser zatvoren")
    finally:
        try:
            os.remove(lock_path)
        except Exception:
            pass
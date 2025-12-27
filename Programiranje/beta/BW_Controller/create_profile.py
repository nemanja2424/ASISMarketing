"""Create a persistent Camoufox profile and save its launch options.

This module is executed in a separate process from the GUI. When run it:

- Creates a new folder under `profiles/` (e.g. `profiles/profile_ab12cd34`).
- Creates a `user_data` directory inside it and calls `launch_options(user_data_dir=...)`.
- Saves a `profile.json` file containing `profile_id`, `metadata` and the serialized `options`.
- Launches Camoufox with `from_options=opts, persistent_context=True` so the user can interact
  with the browser before finalizing the profile.

Usage:
	python BW_Controller/create_profile.py
	or from your GUI with multiprocessing.Process(target=create_profile)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from camoufox import Camoufox, launch_options
from browserforge.fingerprints import Screen

# For optional public IP geolocation lookup
try:
    import requests
except Exception:
    requests = None


PROFILES_DIR = Path("profiles")


def _make_serializable(obj: Any) -> Any:
	"""Recursively convert object to JSON-serializable types."""
	if obj is None or isinstance(obj, (str, int, float, bool)):
		return obj
	if isinstance(obj, Path):
		return str(obj)
	if isinstance(obj, dict):
		return {k: _make_serializable(v) for k, v in obj.items()}
	if isinstance(obj, (list, tuple)):
		return [_make_serializable(v) for v in obj]
	# Fallback to string representation for unknown types
	return str(obj)


def create_profile(display_name: str | None = None, *, namespace: str = "default", category: str | None = None, headless: bool = False, no_launch: bool = False, profile_path: str | None = None, use_geoip: bool = True, proxy_template: str | None = None) -> tuple[str, str]:
    """Create a profile (or namespace) and save its launch options.

    If `profile_path` points to an existing `profile.json`, add the namespace under
    that profile. Otherwise create a new profile. Returns (profile_id, namespace).
    
    Args:
        proxy_template: Optional proxy URL template (e.g. http://user:pass@host:port with {id profila koji se pokrece} placeholder)
    """
    PROFILES_DIR.mkdir(exist_ok=True)

    # If profile_path is given, load it and reuse that profile
    if profile_path:
        p = Path(profile_path)
        if not p.exists():
            raise FileNotFoundError(profile_path)
        with p.open("r", encoding="utf-8") as f:
            profile_meta = json.load(f)
        profile_id = profile_meta.get("profile_id")
        profile_dir = p.parent
    else:
        # Create new profile
        profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        profile_dir = PROFILES_DIR / profile_id
        profile_dir.mkdir(exist_ok=True)
        profile_meta = {
            "profile_id": profile_id,
            "metadata": {
                "display_name": display_name or profile_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "category": category,
            },
            "namespaces": {},
        }

    # Write profile.json if missing
    profile_path = profile_dir / "profile.json"
    with profile_path.open("w", encoding="utf-8") as f:
        json.dump(profile_meta, f, indent=2, ensure_ascii=False)

    # Create namespace directory
    ns_dir = profile_dir / "namespaces" / namespace
    ns_dir.mkdir(parents=True, exist_ok=True)

    user_data_dir = ns_dir / "user_data"
    user_data_dir.mkdir(exist_ok=True)

    user_data_dir_abs = str(user_data_dir.resolve())

    print(f"Generating launch options for namespace '{namespace}' at: {user_data_dir_abs}")

    # Generate the launch options (force 1920x1080 screen; optionally use geoip)
    # Use exact 1920x1080 to ensure consistent fingerprints
    screen = Screen(min_width=1920, max_width=1920, min_height=1080, max_height=1080)
    try:
        opts = launch_options(user_data_dir=user_data_dir_abs, headless=headless, screen=screen, geoip=use_geoip)
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        msg = str(exc)
        # If camoufox requires the geoip extra, fall back to generating options without it
        if "Please install the geoip extra" in msg or "NotInstalledGeoIPExtra" in msg:
            print("GeoIP extra not installed for camoufox; generating launch options without geoip and will perform external lookup if requested.")
            opts = launch_options(user_data_dir=user_data_dir_abs, headless=headless, screen=screen, geoip=False)
        else:
            print(f"Error while generating launch options: {exc}")
            raise

    # Convert launch options into a JSON serializable form
    opts_serial = _make_serializable(opts)

    # Normalize and fix obvious anomalies in CAMOU_CONFIG_1 (screen properties etc.)
    try:
        env = opts_serial.get("env", {})
        camo_raw = env.get("CAMOU_CONFIG_1")
        if isinstance(camo_raw, str):
            try:
                camo_json = json.loads(camo_raw)
            except Exception:
                camo_json = None

            if isinstance(camo_json, dict):
                # Ensure core screen values are consistent
                width = int(camo_json.get("screen.width", camo_json.get("screen.availWidth", 1920)))
                height = int(camo_json.get("screen.height", camo_json.get("screen.availHeight", 1080)))
                avail_w = int(camo_json.get("screen.availWidth", width))
                avail_h = int(camo_json.get("screen.availHeight", max(0, height - 48)))
                avail_left = int(camo_json.get("screen.availLeft", 0))

                # Fix obvious anomalies
                if avail_left >= width or avail_left < 0:
                    camo_json["screen.availLeft"] = 0
                if avail_w != width:
                    camo_json["screen.availWidth"] = width
                if avail_h <= 0 or avail_h > height:
                    camo_json["screen.availHeight"] = max(0, height - 48)

                # Window offsets sanity
                if camo_json.get("window.screenX", 0) >= width:
                    camo_json["window.screenX"] = 0
                if camo_json.get("window.screenY", 0) >= height:
                    camo_json["window.screenY"] = 0

                # Write back modified CAMOU_CONFIG_1
                env["CAMOU_CONFIG_1"] = json.dumps(camo_json)
                opts_serial["env"] = env
    except Exception as _exc:  # pragma: no cover - best-effort normalization
        print("Could not normalize CAMOU_CONFIG_1:", _exc)

    ns_meta = {
        "name": namespace,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "options": opts_serial,
        "user_data_dir": user_data_dir_abs,
        "category": category,
    }

    # Ensure per-namespace consistency options default to desirable values
    ns_meta.setdefault("consistency_options", {})
    ns_meta.setdefault("consistency_options", {})["ignore_geo_country"] = ns_meta.get("consistency_options", {}).get("ignore_geo_country", True)

    # Read proxy_template from parameter, environment variable, or profile meta
    if not proxy_template:
        proxy_template = os.environ.get("CAMOUFOX_PROXY") or profile_meta.get("proxy_template")
    
    if proxy_template:
        ns_meta["proxy_template"] = proxy_template
        print(f"Using proxy_template: {proxy_template[:80]}...")  # Show first 80 chars to avoid exposing full credentials

    # If we asked to use geoip and requests is available, resolve public IP geolocation now
    if use_geoip and requests is not None:
        try:
            # ip-api is simple and doesn't require a token for light usage
            r = requests.get("http://ip-api.com/json", timeout=5)
            if r.status_code == 200:
                j = r.json()
                ns_meta["geolocation"] = {
                    "latitude": j.get("lat"),
                    "longitude": j.get("lon"),
                    "city": j.get("city"),
                    "region": j.get("regionName"),
                    "country": j.get("country"),
                    "timezone": j.get("timezone"),
                    "ip": j.get("query"),
                }

                # Attempt reverse geocoding to confirm country matches coordinates
                try:
                    rev = requests.get(
                        f"https://nominatim.openstreetmap.org/reverse?format=json&lat={j.get('lat')}&lon={j.get('lon')}",
                        headers={"User-Agent": "ASISMarketing/1.0 (contact@example.com)"},
                        timeout=5,
                    )
                    if rev.status_code == 200:
                        rj = rev.json()
                        addr = rj.get("address", {})
                        country_res = addr.get("country") or addr.get("country_code")
                        if country_res:
                            ns_meta.setdefault("geolocation", {})["country_resolved"] = country_res
                            # If country_res differs notably from ip-api's country, prefer the coordinate-derived country
                            if str(country_res).lower() not in str(j.get("country", "")).lower():
                                ns_meta["geolocation"]["country_source"] = "reverse_geocode"
                                ns_meta["geolocation"]["country"] = country_res
                            else:
                                ns_meta["geolocation"]["country_source"] = "ip-api"
                except Exception:
                    pass

        except Exception as exc:  # pragma: no cover - network dependent
            print("Could not fetch public IP geolocation:", exc)

    # Write namespace metadata to disk and register in profile.json
    ns_path = ns_dir / "namespace.json"
    with ns_path.open("w", encoding="utf-8") as f:
        json.dump(ns_meta, f, indent=2, ensure_ascii=False)

    # If we got geolocation, also store it into options so that run-time JS geolocation matches IP
    try:
        if "geolocation" in ns_meta:
            lat = ns_meta["geolocation"].get("latitude")
            lon = ns_meta["geolocation"].get("longitude")
            if lat and lon:
                # Store a simple geolocation_js field for deterministic checks and for clarity
                ns_meta["geolocation_js"] = {"latitude": lat, "longitude": lon}
                # Also update the namespace file with the added field
                with ns_path.open("w", encoding="utf-8") as f:
                    json.dump(ns_meta, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Normalize namespace immediately so hardware/canvas/webgl/accept-language and defaults are applied
    try:
        from BW_Controller.consistency import normalize_namespace
        normalize_namespace(ns_path)
    except Exception as _exc:
        print("Could not normalize namespace during creation:", _exc)

    # Register namespace in profile meta and write profile.json
    profile_meta.setdefault("namespaces", {})[namespace] = str(ns_path)
    with profile_path.open("w", encoding="utf-8") as f:
        json.dump(profile_meta, f, indent=2, ensure_ascii=False)

    print(f"Namespace saved to {ns_path}")

    # Start asynchronous consistency check (runs in background)
    try:
        from BW_Controller.consistency import run_consistency_and_save
        import multiprocessing as _mp

        # run_consistency_and_save will read namespace file and apply defaults (ignore_geo_country default is True)
        p = _mp.Process(target=run_consistency_and_save, args=(ns_path,), daemon=True)
        p.start()
    except Exception as _exc:  # pragma: no cover - non-fatal
        print("Could not start consistency background task:", _exc)

    if no_launch:
        print("Skipping launching Camoufox (no_launch=True). Namespace generation finished.")
        return profile_id, namespace

    # Launch Camoufox so the user can interact and finalize anything stored in user_data
    try:
        with Camoufox(from_options=opts, persistent_context=True) as browser:
            # Use an existing page if present to avoid opening an extra window/tab
            pages = list(browser.pages)
            if pages:
                page = pages[0]
            else:
                page = browser.new_page()
            page.goto("about:blank")
            print("Camoufox is running for namespace. Interact with the browser to populate the namespace.")
            print("Close the browser window to finalize the namespace, or press ENTER if running from a TTY")
            import sys, time
            try:
                if sys.stdin and sys.stdin.isatty():
                    input()
                else:
                    while True:
                        try:
                            if page.is_closed():
                                break
                        except Exception:
                            break
                        time.sleep(0.5)
            except (KeyboardInterrupt, EOFError):
                pass

    except Exception as exc:  # pragma: no cover - depends on runtime
        print(f"Error while launching Camoufox: {exc}")
        raise

    print(f"Profile {profile_id} namespace '{namespace}' creation finished.")
    return profile_id, namespace

if __name__ == "__main__":  # pragma: no cover - manual run
	create_profile()

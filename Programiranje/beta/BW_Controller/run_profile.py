"""Run a saved Camoufox profile (created by `create_profile`).

Loads `profile.json` and starts Camoufox using the saved `options` via
`Camoufox(from_options=opts, persistent_context=True)`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from camoufox import Camoufox
import os
import re
from urllib.parse import urlparse


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

    # Determine profile id for placeholder substitution
    profile_id = None
    try:
        if p.name == "profile.json":
            with p.open("r", encoding="utf-8") as f:
                profile = json.load(f)
            profile_id = profile.get("profile_id")
        else:
            # namespace.json -> profile dir should be three levels up (profiles/<profile_id>/namespaces/<ns>/namespace.json)
            try:
                profile_id = p.parents[2].name
            except Exception:
                profile_id = None
    except Exception:
        profile_id = None

    print(f"Starting Camoufox for profile/namespace {data.get('name') or profile_id}")

    # Build proxy URL/template from env or namespace/profile fields
    proxy_template = os.environ.get("CAMOUFOX_PROXY") or data.get("proxy_template") or None
    if not proxy_template:
        # try profile-level proxy_template if available
        try:
            profile_json = p.parents[2] / "profile.json"
            if profile_json.exists():
                pj = json.loads(profile_json.read_text(encoding="utf-8"))
                proxy_template = pj.get("proxy_template") or pj.get("proxy")
        except Exception:
            proxy_template = proxy_template

    proxy_url = None
    if proxy_template:
        # replace placeholder tokens that mention profile/id/profil
        def _repl_token(m):
            tok = m.group(0)[1:-1]
            lower = tok.lower()
            if "profile" in lower or "id" in lower or "profil" in lower:
                # Extract only the UUID part (remove "profile_" prefix if present)
                uuid_only = profile_id.replace("profile_", "") if profile_id else ""
                return uuid_only
            # allow simple {id} too
            if tok == "id":
                uuid_only = profile_id.replace("profile_", "") if profile_id else ""
                return uuid_only
            # unknown token -> keep as-is
            return m.group(0)

        proxy_url = re.sub(r"\{[^}]+\}", _repl_token, proxy_template)
        print(f"[DEBUG] Proxy template: {proxy_template}")
        print(f"[DEBUG] Proxy URL after substitution: {proxy_url}")

    proxy_info = None
    if proxy_url:
        try:
            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port
            scheme = parsed.scheme or "http"
            username = parsed.username
            password = parsed.password
            if host and port:
                server = f"{scheme}://{host}:{port}"
            elif host:
                server = f"{scheme}://{host}"
            else:
                server = proxy_url

            proxy_info = {"server": server}
            if username:
                proxy_info["username"] = username
            if password:
                proxy_info["password"] = password

            # Ensure args include --proxy-server (Chromium style) only when launching Chromium.
            # For non-Chromium browsers (e.g., Firefox), set HTTP(S)_PROXY env vars so the native
            # network stack can use the proxy instead.
            try:
                args = opts.get("args") or []
                product = (opts.get("product") or "").lower()
                # If the caller explicitly set product to 'chromium', add the Chromium CLI arg.
                if product == "chromium":
                    proxy_arg = f"--proxy-server={host}:{port}" if host and port else None
                    if proxy_arg and proxy_arg not in args:
                        args = list(args) + [proxy_arg]
                        opts["args"] = args
                else:
                    # For Firefox/non-Chromium: Playwright proxy format is: http://host:port or socks5://host:port
                    # For authentication, Playwright expects username/password as separate fields when using proxy
                    print(f"[DEBUG] Configuring proxy for Firefox via Playwright")
                    print(f"[DEBUG] Host: {host}, Port: {port}, Auth: {bool(username)}")
                    
                    # Reset proxy_info to use the format Playwright expects
                    proxy_info = {"server": f"http://{host}:{port}"}
                    if username:
                        proxy_info["username"] = username
                    if password:
                        proxy_info["password"] = password
                    
                    # Configure Firefox prefs for proxy and WebRTC leak prevention
                    if "firefox_user_prefs" not in opts:
                        opts["firefox_user_prefs"] = {}
                    
                    # Proxy settings
                    opts["firefox_user_prefs"]["network.proxy.type"] = 1  # Manual proxy config
                    opts["firefox_user_prefs"]["network.proxy.http"] = host or "localhost"
                    opts["firefox_user_prefs"]["network.proxy.http_port"] = port or 8080
                    opts["firefox_user_prefs"]["network.proxy.ssl"] = host or "localhost"
                    opts["firefox_user_prefs"]["network.proxy.ssl_port"] = port or 8080
                    opts["firefox_user_prefs"]["network.proxy.share_proxy_settings"] = True
                    opts["firefox_user_prefs"]["network.proxy.no_proxies_on"] = ""
                    
                    # CRITICAL: Disable WebRTC to prevent IPv4/IPv6 leak
                    opts["firefox_user_prefs"]["media.peerconnection.enabled"] = False
                    opts["firefox_user_prefs"]["media.peerconnection.ice.default_address_only"] = True
                    opts["firefox_user_prefs"]["media.peerconnection.use_document_iceservers"] = False
                    opts["firefox_user_prefs"]["media.peerconnection.identity.timeout"] = 12000
                    
                    print(f"[DEBUG] Proxy info for Playwright: {proxy_info}")
                    print(f"[DEBUG] WebRTC disabled for leak prevention")
            except Exception:
                pass

            # Persist proxy info to namespace for future runs
            try:
                data.setdefault("proxy", {})
                data["proxy"]["server"] = proxy_info.get("server")
                if username:
                    data["proxy"]["username"] = username
                if password:
                    data["proxy"]["password"] = "***REDACTED***"
                # write back namespace file without exposing password
                with p.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            method = "chromium-arg" if (opts.get("product") or "").lower() == "chromium" else "env"
            print(f"Using proxy server: {proxy_info.get('server')} (auth={'yes' if username or password else 'no'}, method={method})")

        except Exception as exc:
            print("Failed to parse proxy URL:", exc)

    # If proxy_info exists, attempt to pass it in options under 'proxy' (Camoufox/Playwright style)
    if proxy_info:
        try:
            opts = dict(opts)  # copy to avoid mutating shared structures
            opts["proxy"] = proxy_info
            print(f"[DEBUG] Set opts['proxy']: {proxy_info}")
        except Exception:
            pass


    with Camoufox(from_options=opts, persistent_context=True) as browser:
        # Avoid creating a second window: if a page already exists, re-use it.
        pages = list(browser.pages)
        if pages:
            page = pages[0]
        else:
            page = browser.new_page()

        # If we set proxy credentials in opts, attempt to set HTTP credentials on the context
        try:
            proxy = opts.get("proxy") or (data.get("proxy") if isinstance(data.get("proxy"), dict) else None)
            if proxy and proxy.get("username") and proxy.get("password"):
                try:
                    # Try Playwright-style API (context-level HTTP credentials)
                    if hasattr(page.context, "set_http_credentials"):
                        page.context.set_http_credentials({"username": proxy.get("username"), "password": proxy.get("password")})
                    elif hasattr(page.context, "_impl") and hasattr(page.context._impl, "set_http_credentials"):
                        page.context._impl.set_http_credentials({"username": proxy.get("username"), "password": proxy.get("password")})
                except Exception:
                    # Best-effort; if it fails, the proxy may still work if authless or browser prompts
                    pass
        except Exception:
            pass

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

        # Disable WebRTC leak by setting appropriate prefs
        # (Already set during proxy configuration, but enforce it here too as a safeguard)
        try:
            if "firefox_user_prefs" not in opts or opts["firefox_user_prefs"] is None:
                opts["firefox_user_prefs"] = {}
            # Ensure WebRTC is fully disabled
            opts["firefox_user_prefs"]["media.peerconnection.enabled"] = False
            opts["firefox_user_prefs"]["media.peerconnection.ice.default_address_only"] = True
            opts["firefox_user_prefs"]["media.peerconnection.use_document_iceservers"] = False
        except Exception:
            pass

        # Navigate to test page with timeout
        try:
            page.goto("https://browserleaks.com/ip", timeout=15000)  # 15 second timeout
        except Exception as e:
            print(f"Warning: Could not navigate to browserleaks.com: {e}")
            # Continue anyway - user can navigate manually
        
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

"""Base campaign class for multi-profile browser automation.

All campaigns inherit from BaseCampaign and define:
- profiles: list of profile IDs to launch
- url: URL to navigate to
- run(): main campaign logic
"""
from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

from camoufox import Camoufox
import os
import re
from urllib.parse import urlparse


class BaseCampaign:
    """Base class for campaigns that run multiple profiles."""
    
    def __init__(self, profile_ids: List[str], url: str = None, concurrent: bool = False):
        """
        Args:
            profile_ids: List of profile IDs to run (e.g., ["profile_abc", "profile_def"])
            url: URL to navigate to (e.g., "https://instagram.com")
            concurrent: If True, launch all profiles at once; if False, sequential
        """
        self.profile_ids = profile_ids
        self.url = url
        self.concurrent = concurrent
        self.profiles_dir = Path("profiles")
    
    def run(self):
        """Main campaign entry point. Override in subclasses."""
        if self.concurrent:
            self.run_concurrent()
        else:
            self.run_sequential()
    
    def run_sequential(self):
        """Run profiles one after another."""
        for profile_id in self.profile_ids:
            print(f"\n[Campaign] Starting {profile_id}...")
            self._launch_profile(profile_id)
            time.sleep(1)  # Small delay between launches
    
    def run_concurrent(self):
        """Launch all profiles at the same time using multiprocessing."""
        processes = []
        for profile_id in self.profile_ids:
            p = multiprocessing.Process(target=self._launch_profile, args=(profile_id,))
            p.start()
            processes.append(p)
        
        # Wait for all to finish (or Ctrl+C to stop)
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            print("\n[Campaign] Stopping all profiles...")
            for p in processes:
                p.terminate()
            for p in processes:
                p.join()
    
    def _launch_profile(self, profile_id: str):
        """Launch a single profile and execute campaign logic."""
        try:
            # Load profile.json
            profile_dir = self.profiles_dir / profile_id
            profile_json = profile_dir / "profile.json"
            
            if not profile_json.exists():
                print(f"[{profile_id}] ERROR: {profile_json} not found")
                return
            
            with profile_json.open("r", encoding="utf-8") as f:
                profile_data = json.load(f)
            
            # Get first namespace
            namespaces = profile_data.get("namespaces", {})
            if not namespaces:
                print(f"[{profile_id}] ERROR: No namespaces found")
                return
            
            ns_name = "default" if "default" in namespaces else list(namespaces.keys())[0]
            ns_path = Path(namespaces[ns_name])
            
            if not ns_path.exists():
                print(f"[{profile_id}] ERROR: {ns_path} not found")
                return
            
            with ns_path.open("r", encoding="utf-8") as f:
                ns_data = json.load(f)
            
            # Setup options with proxy
            opts = ns_data.get("options", {})
            self._setup_proxy(opts, profile_id, profile_data, ns_path)
            
            # Launch browser
            print(f"[{profile_id}] Launching Camoufox...")
            with Camoufox(from_options=opts, persistent_context=True) as browser:
                pages = list(browser.pages)
                page = pages[0] if pages else browser.new_page()
                
                # Apply geolocation
                geo = ns_data.get("geolocation")
                if geo:
                    try:
                        loc = {"latitude": float(geo["latitude"]), "longitude": float(geo["longitude"])}
                        if hasattr(browser, "set_geolocation"):
                            browser.set_geolocation(loc)
                        elif hasattr(page.context, "set_geolocation"):
                            page.context.set_geolocation(loc)
                    except Exception as e:
                        print(f"[{profile_id}] Geolocation setup failed: {e}")
                
                # Apply timezone
                tz = ns_data.get("geolocation", {}).get("timezone")
                if tz:
                    try:
                        script = f"(() => {{ const tz = '{tz}'; try {{ const orig = Intl.DateTimeFormat.prototype.resolvedOptions; Intl.DateTimeFormat.prototype.resolvedOptions = function() {{ return Object.assign({{}}, orig.call(this), {{ timeZone: tz }}); }}; }} catch(e) {{}} }})();"
                        page.add_init_script(script)
                    except Exception:
                        pass
                
                # Navigate to URL if specified
                if self.url:
                    print(f"[{profile_id}] Navigating to {self.url}...")
                    try:
                        # Try with different wait strategies
                        try:
                            page.goto(self.url, timeout=20000, wait_until="domcontentloaded")
                        except Exception as e:
                            # Retry with just load
                            if "REDIRECT_LOOP" in str(e) or "timeout" in str(e).lower():
                                print(f"[{profile_id}] First attempt failed, retrying...")
                                page.goto(self.url, timeout=20000, wait_until="load")
                            else:
                                raise
                        print(f"[{profile_id}] ✓ Page loaded")
                    except Exception as e:
                        print(f"[{profile_id}] Navigation failed: {e}")
                        print(f"[{profile_id}] Continuing anyway (page may still be usable)...")
                        # Try to get current URL to see if we're at least somewhere
                        try:
                            current_url = page.url
                            print(f"[{profile_id}] Current URL: {current_url}")
                        except:
                            pass
                
                # Run campaign-specific logic
                self.execute(page, profile_id, ns_data)
                
                print(f"[{profile_id}] Campaign completed, browser will stay open (press Ctrl+C to stop)")
                # Keep browser open - user can interact with it
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        
        except Exception as e:
            print(f"[{profile_id}] ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_proxy(self, opts: Dict[str, Any], profile_id: str, profile_data: Dict, ns_path: Path):
        """Setup proxy with authentication from config.json or env."""
        # Load proxy template from profiles/config.json
        config_path = self.profiles_dir / "config.json"
        proxy_template = None
        
        if config_path.exists():
            try:
                with config_path.open("r") as f:
                    config = json.load(f)
                proxy_template = config.get("proxy_template")
            except:
                pass
        
        if not proxy_template:
            proxy_template = os.environ.get("CAMOUFOX_PROXY")
        
        if not proxy_template:
            print(f"[{profile_id}] No proxy template found")
            return
        
        # Replace {id} with profile UUID (without "profile_" prefix)
        uuid_only = profile_id.replace("profile_", "")
        proxy_url = proxy_template.replace("{id profila koji se pokrece}", uuid_only)
        proxy_url = proxy_url.replace("{id}", uuid_only)
        
        print(f"[{profile_id}] Proxy: {proxy_url[:50]}... (auth hidden)")
        
        # Parse proxy
        try:
            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port
            username = parsed.username
            password = parsed.password
            
            proxy_info = {"server": f"http://{host}:{port}"}
            if username:
                proxy_info["username"] = username
            if password:
                proxy_info["password"] = password
            
            # Configure Firefox
            if "firefox_user_prefs" not in opts:
                opts["firefox_user_prefs"] = {}
            
            opts["firefox_user_prefs"]["network.proxy.type"] = 1
            opts["firefox_user_prefs"]["network.proxy.http"] = host
            opts["firefox_user_prefs"]["network.proxy.http_port"] = port
            opts["firefox_user_prefs"]["network.proxy.ssl"] = host
            opts["firefox_user_prefs"]["network.proxy.ssl_port"] = port
            opts["firefox_user_prefs"]["network.proxy.share_proxy_settings"] = True
            opts["firefox_user_prefs"]["network.proxy.no_proxies_on"] = ""
            
            # WebRTC leak prevention
            opts["firefox_user_prefs"]["media.peerconnection.enabled"] = False
            opts["firefox_user_prefs"]["media.peerconnection.ice.default_address_only"] = True
            opts["firefox_user_prefs"]["media.peerconnection.use_document_iceservers"] = False
            opts["firefox_user_prefs"]["media.peerconnection.identity.timeout"] = 12000
            
            opts["proxy"] = proxy_info
            
        except Exception as e:
            print(f"[{profile_id}] Proxy setup failed: {e}")
    
    def execute(self, page, profile_id: str, ns_data: Dict[str, Any]):
        """Override this in subclasses to add campaign-specific logic.
        
        Args:
            page: Playwright page object
            profile_id: Current profile ID
            ns_data: Namespace data (geolocation, hardware, etc)
        """
        # Default: just keep page open
        pass

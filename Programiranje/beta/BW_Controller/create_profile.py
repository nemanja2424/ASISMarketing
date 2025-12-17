import json
import os
import uuid
from datetime import datetime
from time import sleep

from camoufox import Camoufox
from BW_Controller.fingerprint_validator import is_valid_windows_fingerprint

PROFILES_DIR = "profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

MAX_ATTEMPTS = 10  # maksimalno pokušaja za validan fingerprint

def create_profile():
    profile_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    attempt = 0
    fingerprint = None

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"Attempt {attempt} to generate valid Windows fingerprint...")

        with Camoufox() as browser:
            context = browser.new_context()
            page = context.new_page()

            # Otvaramo praznu stranicu – fingerprint se automatski generiše
            page.goto("about:blank")

            # Uzimamo realne vrednosti iz browsera
            fingerprint = page.evaluate(
                """
                () => {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    const debugInfo = gl ? gl.getExtension('WEBGL_debug_renderer_info') : null;

                    return {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        languages: navigator.languages,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        screen: {
                            width: screen.width,
                            height: screen.height,
                            dpr: window.devicePixelRatio
                        },
                        hardwareConcurrency: navigator.hardwareConcurrency,
                        deviceMemory: navigator.deviceMemory || null,
                        webgl: gl ? {
                            vendor: debugInfo
                                ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
                                : gl.getParameter(gl.VENDOR),
                            renderer: debugInfo
                                ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                                : gl.getParameter(gl.RENDERER)
                        } : null
                    };
                }
                """
            )

        # VALIDACIJA
        valid, reason = is_valid_windows_fingerprint(fingerprint)
        if valid:
            print("Valid Windows fingerprint generated.")
            break
        else:
            print(f"Invalid fingerprint: {reason}")
            fingerprint = None
            sleep(0.5)  # mali delay pre ponovnog pokušaja

    if not fingerprint:
        raise RuntimeError(f"Failed to generate valid Windows fingerprint in {MAX_ATTEMPTS} attempts")

    # Spremamo profil u JSON
    profile_data = {
        "profile_id": profile_id,
        "created_at": created_at,
        "fingerprint": fingerprint
    }

    profile_path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=4)

    return profile_path

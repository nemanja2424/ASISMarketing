# BW_Controller/create_profile.py

import json
import os
import uuid
from datetime import datetime
from time import sleep

from camoufox import Camoufox

PROFILES_DIR = "profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

MAX_ATTEMPTS = 10


def extract_fingerprint(page):
    """
    Izvlači kompletan fingerprint iz browser stranice.
    Vraća dict sa svim potrebnim podacima.
    """
    fingerprint = page.evaluate(
        """
        () => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            const debugInfo = gl ? gl.getExtension('WEBGL_debug_renderer_info') : null;

            // Canvas fingerprint
            let canvasFingerprint = null;
            try {
                canvas.width = 200;
                canvas.height = 50;
                const canvasCtx = canvas.getContext('2d');
                if (canvasCtx) {
                    canvasCtx.textBaseline = 'top';
                    canvasCtx.font = '14px Arial';
                    canvasCtx.fillStyle = '#f60';
                    canvasCtx.fillRect(125, 1, 62, 20);
                    canvasCtx.fillStyle = '#069';
                    canvasCtx.fillText('Canvas fingerprint', 2, 15);
                    canvasFingerprint = canvas.toDataURL();
                } else {
                    canvasFingerprint = null;
                }
            } catch (e) {
                canvasFingerprint = null;
            }

            // Audio context fingerprint
            let audioFingerprint = null;
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                audioFingerprint = {
                    sampleRate: audioContext.sampleRate,
                    state: audioContext.state,
                    maxChannelCount: audioContext.destination.maxChannelCount
                };
                audioContext.close();
            } catch (e) {
                audioFingerprint = null;
            }

            // WebGL fingerprint
            let webglFingerprint = null;
            if (gl) {
                webglFingerprint = {
                    vendor: debugInfo 
                        ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
                        : gl.getParameter(gl.VENDOR),
                    renderer: debugInfo 
                        ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                        : gl.getParameter(gl.RENDERER),
                    version: gl.getParameter(gl.VERSION),
                    shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                    maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                    maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS)
                };
            }

            // Fonts detection
            const baseFonts = ['monospace', 'sans-serif', 'serif'];
            const testFonts = [
                'Arial', 'Verdana', 'Times New Roman', 'Courier New',
                'Georgia', 'Palatino', 'Garamond', 'Comic Sans MS',
                'Trebuchet MS', 'Arial Black', 'Impact'
            ];
            const detectedFonts = [];
            
            const testString = 'mmmmmmmmmmlli';
            const testSize = '72px';
            const h = document.getElementsByTagName('body')[0] || document.documentElement;
            const s = document.createElement('span');
            s.style.fontSize = testSize;
            s.innerHTML = testString;
            const defaultWidth = {};
            const defaultHeight = {};
            
            for (const baseFont of baseFonts) {
                s.style.fontFamily = baseFont;
                h.appendChild(s);
                defaultWidth[baseFont] = s.offsetWidth;
                defaultHeight[baseFont] = s.offsetHeight;
                h.removeChild(s);
            }
            
            for (const font of testFonts) {
                let detected = false;
                for (const baseFont of baseFonts) {
                    s.style.fontFamily = font + ',' + baseFont;
                    h.appendChild(s);
                    const matched = (s.offsetWidth !== defaultWidth[baseFont] || 
                                   s.offsetHeight !== defaultHeight[baseFont]);
                    h.removeChild(s);
                    if (matched) {
                        detected = true;
                        break;
                    }
                }
                if (detected) {
                    detectedFonts.push(font);
                }
            }

            return {
                // Browser basics
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                languages: navigator.languages,
                language: navigator.language,
                
                // Screen & Display
                screen: {
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                    dpr: window.devicePixelRatio
                },
                
                // Hardware
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory || null,
                
                // Timezone & Locale
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                timezoneOffset: new Date().getTimezoneOffset(),
                
                // WebGL
                webgl: webglFingerprint,
                
                // Canvas
                canvas: canvasFingerprint,
                
                // Audio
                audio: audioFingerprint,
                
                // Fonts
                fonts: detectedFonts,
                
                // Additional properties
                doNotTrack: navigator.doNotTrack,
                cookieEnabled: navigator.cookieEnabled,
                plugins: Array.from(navigator.plugins || []).map(p => ({
                    name: p.name,
                    description: p.description,
                    filename: p.filename
                })),
                
                // Media devices
                mediaDevices: navigator.mediaDevices ? true : false,
                
                // Permissions
                permissions: navigator.permissions ? true : false
            };
        }
        """
    )
    
    return fingerprint


def create_profile():
    """
    Kreira novi browser profil i čuva:
      - profiles/<id>/fingerprint.json
      - profiles/<id>/storage_state.json
      - profiles/<id>/meta.json
      - profiles/<id>/user_data/  (prazan folder za buduću upotrebu)

    Vraća putanju do `meta.json` koji run.py kasnije koristi za pokretanje.
    """
    profile_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    profile_dir = os.path.join(PROFILES_DIR, profile_id)
    os.makedirs(profile_dir, exist_ok=True)
    user_data_dir = os.path.join(profile_dir, "user_data")
    os.makedirs(user_data_dir, exist_ok=True)

    attempt = 0
    fingerprint = None
    storage_state = None

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"🔄 Pokušaj {attempt}/{MAX_ATTEMPTS} generisanja validnog Windows fingerprinta...")

        try:
            # Target Windows OS to generate Windows-like fingerprints
            with Camoufox(headless=False, os='windows') as browser:
                context = browser.new_context()
                page = context.new_page()

                page.goto("about:blank")
                page.wait_for_timeout(1000)

                fingerprint = extract_fingerprint(page)

                viewport = page.viewport_size
                if viewport:
                    fingerprint['viewport'] = {
                        'width': viewport['width'],
                        'height': viewport['height']
                    }

                # Pokušamo da sačuvamo storage_state ako je dostupan
                try:
                    if hasattr(context, "storage_state"):
                        # Ako metoda vraća dict kada se pozove bez path
                        storage_state = context.storage_state()
                    else:
                        cookies = []
                        try:
                            cookies = context.cookies()
                        except Exception:
                            cookies = []

                        local_storage = page.evaluate(
                            """() => { const s = {}; for (let i=0;i<localStorage.length;i++){ const k = localStorage.key(i); s[k]=localStorage.getItem(k);} return s;}"""
                        )

                        origins = []
                        if local_storage:
                            origin_entry = {
                                "origin": page.url,
                                "localStorage": [{"name": k, "value": v} for k, v in local_storage.items()]
                            }
                            origins.append(origin_entry)

                        storage_state = {"cookies": cookies, "origins": origins}
                except Exception as e:
                    print(f"⚠️ Ne mogu da očuvam storage_state: {e}")
                    storage_state = {"cookies": [], "origins": []}

            # No validation: accept the first successfully generated fingerprint
            print("✅ Fingerprint generisan (bez validacije).")
            break

        except Exception as e:
            print(f"⚠️  Greška pri generisanju fingerprinta: {e}")
            fingerprint = None
            storage_state = None
            sleep(0.5)

    if not fingerprint:
        raise RuntimeError(
            f"❌ Nije uspelo generisanje validnog Windows fingerprinta u {MAX_ATTEMPTS} pokušaja"
        )

    # Sačuvaj fingerprint i storage state
    fingerprint_path = os.path.join(profile_dir, "fingerprint.json")
    storage_path = os.path.join(profile_dir, "storage_state.json")
    meta_path = os.path.join(profile_dir, "meta.json")

    with open(fingerprint_path, "w", encoding="utf-8") as f:
        json.dump(fingerprint, f, indent=4, ensure_ascii=False)

    with open(storage_path, "w", encoding="utf-8") as f:
        json.dump(storage_state or {"cookies": [], "origins": []}, f, indent=4, ensure_ascii=False)

    meta = {
        "profile_id": profile_id,
        "created_at": created_at,
        "user_data_dir": os.path.relpath(user_data_dir, start=os.getcwd()),
        "fingerprint_file": os.path.relpath(fingerprint_path, start=profile_dir),
        "storage_state_file": os.path.relpath(storage_path, start=profile_dir),
        "metadata": {
            "last_used": None,
            "usage_count": 0,
            "notes": "",
        },
        "version": 1
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)

    print(f"💾 Profil sačuvan: {meta_path}")
    return meta_path
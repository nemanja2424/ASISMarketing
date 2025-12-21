"""Fingerprint consistency checks and LM Studio integration.

Provides deterministic checks and an LLM-based assessor that calls a local
LM Studio instance (OpenAI-compatible endpoint). The main entry point is
`run_consistency_and_save(namespace_path: Path)` which updates the
namespace.json file with a `consistency` field.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib

import requests

LM_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
TIMEOUT = 30


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def deterministic_checks(ns: Dict[str, Any], ignore_geo_country: bool = False) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    # Screen resolution check (CAMOU_CONFIG_1 env blob often contains screen values)
    try:
        cfg = ns.get("options", {}).get("env", {}).get("CAMOU_CONFIG_1", "")
        # Prefer parsing CAMOU_CONFIG_1 as JSON to check numeric values
        parsed_camo = None
        try:
            if isinstance(cfg, str) and cfg.strip().startswith("{"):
                parsed_camo = json.loads(cfg)
        except Exception:
            parsed_camo = None

        if parsed_camo:
            checks["screen_ok"] = int(parsed_camo.get("screen.width", 0)) == 1920 and int(parsed_camo.get("screen.height", 0)) == 1080
        else:
            checks["screen_ok"] = '"screen.width":1920' in cfg and '"screen.height":1080' in cfg

        # detect anomalies: availLeft equal to width, availHeight > height, large gaps
        checks["screen_anomalies"] = []
        camo = parsed_camo
        if not camo and isinstance(cfg, str):
            try:
                camo = json.loads(cfg.replace('\"', '"'))
            except Exception:
                camo = None

        if camo and isinstance(camo, dict):
            w = camo.get("screen.width")
            h = camo.get("screen.height")
            aw = camo.get("screen.availWidth")
            ah = camo.get("screen.availHeight")
            aleft = camo.get("screen.availLeft")
            try:
                if w and aleft is not None and int(aleft) >= int(w):
                    checks["screen_anomalies"].append("availLeft>=width")
                if ah and h and int(ah) > int(h):
                    checks["screen_anomalies"].append("availHeight>height")
                if ah and h and abs(int(h) - int(ah)) > 200:
                    checks["screen_anomalies"].append("availHeight_diff_large")
            except Exception:
                pass
        if not checks["screen_anomalies"]:
            checks["screen_anomalies"] = None
    except Exception:
        checks["screen_ok"] = False
        checks["screen_anomalies"] = None

    # Geo distance (IP-based geo from earlier lookup vs JS geo if present)
    ipgeo = ns.get("geolocation")
    # Some setups may include js geo under options or a dedicated key; we try a couple of slots
    jsgeo = None
    try:
        # If page JS geolocation stored explicitly (non-standard; optional)
        jsgeo = ns.get("options", {}).get("geolocation_js") or ns.get("geolocation_js")
        if not jsgeo:
            # fallback: attempt to parse CAMOU_CONFIG_1 for lat/lon strings (rare)
            cfg = ns.get("options", {}).get("env", {}).get("CAMOU_CONFIG_1", "")
            mlat = re.search(r'"latitude":\s*([0-9\.\-]+)', cfg)
            mlon = re.search(r'"longitude":\s*([0-9\.\-]+)', cfg)
            if mlat and mlon:
                jsgeo = {"latitude": float(mlat.group(1)), "longitude": float(mlon.group(1))}
    except Exception:
        jsgeo = None

    if ipgeo and jsgeo:
        try:
            d = haversine_km(float(ipgeo["latitude"]), float(ipgeo["longitude"]), float(jsgeo["latitude"]), float(jsgeo["longitude"]))
            checks["geo_distance_km"] = d
            checks["geo_ok"] = d < 200.0
        except Exception:
            checks["geo_distance_km"] = None
            checks["geo_ok"] = False
    else:
        checks["geo_distance_km"] = None
        checks["geo_ok"] = None

    # Timezone check: compare ip timezone vs any stored timezone using offsets when possible
    try:
        ip_tz = (ipgeo or {}).get("timezone")
        opt_tz = ns.get("options", {}).get("timezone") or ns.get("timezone")
        if ip_tz and opt_tz:
            try:
                dt = datetime.utcnow()
                off1 = ZoneInfo(ip_tz).utcoffset(dt)
                off2 = ZoneInfo(opt_tz).utcoffset(dt)
                checks["timezone_match"] = (off1 == off2)
            except ZoneInfoNotFoundError:
                checks["timezone_match"] = ip_tz == opt_tz
            except Exception:
                checks["timezone_match"] = None
        else:
            checks["timezone_match"] = None
    except Exception:
        checks["timezone_match"] = None
    # Country mismatch: compare ip country vs reverse-geocoded country when available
    try:
        check_country = None
        geo = ns.get("geolocation")
        if geo and geo.get("country") and geo.get("country_resolved"):
            check_country = str(geo.get("country")).strip().lower() != str(geo.get("country_resolved")).strip().lower()
            if ignore_geo_country:
                check_country = None
        checks["country_mismatch"] = check_country
    except Exception:
        checks["country_mismatch"] = None
    # UA/platform heuristic check
    try:
        cfg = ns.get("options", {}).get("env", {}).get("CAMOU_CONFIG_1", "")
        ua = re.search(r'"navigator.userAgent":\s*"([^"]+)"', cfg)
        platform = re.search(r'"navigator.platform":\s*"([^"]+)"', cfg) or re.search(r'"navigator.oscpu":\s*"([^"]+)"', cfg)
        checks["ua_present"] = bool(ua)
        checks["platform_present"] = bool(platform)
    except Exception:
        checks["ua_present"] = None
        checks["platform_present"] = None

    # Hardware & fingerprint signals (prefer explicit ns['hardware'] values when present)
    try:
        hw = ns.get("hardware", {}) or {}
        camo = parsed_camo or {}

        # fonts
        fonts = hw.get("fonts") or (camo.get("fonts") if isinstance(camo, dict) else None)
        checks["fonts_count"] = len(fonts) if isinstance(fonts, list) else None
        checks["fonts_enough"] = checks["fonts_count"] is not None and checks["fonts_count"] >= 20

        # device memory (GB)
        dm = hw.get("device_memory_gb") if hw.get("device_memory_gb") is not None else (camo.get("navigator.deviceMemory") or camo.get("deviceMemory"))
        try:
            checks["device_memory_gb"] = float(dm) if dm is not None else None
        except Exception:
            checks["device_memory_gb"] = None

        # hardware concurrency
        hc = hw.get("hardware_concurrency") if hw.get("hardware_concurrency") is not None else (camo.get("navigator.hardwareConcurrency") or camo.get("hardwareConcurrency"))
        try:
            checks["hardware_concurrency"] = int(hc) if hc is not None else None
        except Exception:
            checks["hardware_concurrency"] = None

        # webgl / GPU
        webgl_vendor = hw.get("webgl_vendor") or camo.get("webgl.vendor") or camo.get("webgl_unmasked_vendor") or camo.get("gpu.vendor")
        webgl_renderer = hw.get("webgl_renderer") or camo.get("webgl.renderer") or camo.get("webgl_unmasked_renderer") or camo.get("gpu.renderer")
        webgl_present = hw.get("webgl_present") if hw.get("webgl_present") is not None else bool(webgl_vendor or webgl_renderer)
        checks["webgl_present"] = webgl_present
        checks["webgl_vendor"] = webgl_vendor
        checks["webgl_renderer"] = webgl_renderer

        # Canvas fingerprint hash (if provided or derivable)
        canvas_hash = hw.get("canvas_hash") or camo.get("canvas.hash") or camo.get("canvas_fingerprint") or camo.get("canvas")
        if isinstance(canvas_hash, dict) or isinstance(canvas_hash, list):
            canvas_serial = json.dumps(canvas_hash, sort_keys=True)
            canvas_hash_val = hashlib.md5(canvas_serial.encode("utf-8")).hexdigest()
        elif isinstance(canvas_hash, str) and canvas_hash:
            # If it's already a hash-looking string, keep it; otherwise hash its content
            if re.fullmatch(r"[0-9a-fA-F]{16,128}", canvas_hash):
                canvas_hash_val = canvas_hash
            else:
                canvas_hash_val = hashlib.md5(canvas_hash.encode("utf-8")).hexdigest()
        else:
            canvas_hash_val = None
        checks["canvas_present"] = canvas_hash_val is not None
        checks["canvas_hash"] = canvas_hash_val

        # webgl hash: prefer explicit hash, otherwise hash vendor+renderer
        webgl_hash = hw.get("webgl_hash") or camo.get("webgl.hash")
        if not webgl_hash and (webgl_vendor or webgl_renderer):
            try:
                webgl_hash = hashlib.md5((str(webgl_vendor or "") + "|" + str(webgl_renderer or "")).encode("utf-8")).hexdigest()
            except Exception:
                webgl_hash = None
        checks["webgl_hash"] = webgl_hash

        # media device enumeration (audio/video)
        mdevs = None
        if hw.get("media_device_count") is not None:
            checks["media_device_count"] = int(hw.get("media_device_count"))
        else:
            mdevs = camo.get("media_devices") or camo.get("enumerateDevices")
            checks["media_device_count"] = len(mdevs) if isinstance(mdevs, list) else None

        # Accept-Language header / navigator.languages
        al = hw.get("accept_language") or camo.get("navigator.languages") or camo.get("acceptLanguage") or ns.get("accept_language")
        if isinstance(al, list):
            al_str = ",".join(al)
        else:
            al_str = al if al else None
        checks["accept_language"] = al_str

        # timezone offset minutes (if timezone present)
        tz = ns.get("options", {}).get("timezone") or ns.get("timezone") or (ns.get("geolocation") or {}).get("timezone")
        tz_offset = None
        if tz:
            try:
                dt = datetime.utcnow()
                off = ZoneInfo(tz).utcoffset(dt)
                if off is not None:
                    tz_offset = int(off.total_seconds() // 60)
            except Exception:
                tz_offset = None
        checks["tz_offset_minutes"] = tz_offset
    except Exception:
        checks.setdefault("fonts_count", None)
        checks.setdefault("fonts_enough", None)
        checks.setdefault("device_memory_gb", None)
        checks.setdefault("hardware_concurrency", None)
        checks.setdefault("webgl_present", None)
        checks.setdefault("webgl_vendor", None)
        checks.setdefault("webgl_renderer", None)
        checks.setdefault("media_device_count", None)

    return checks


def _extract_json(text: str) -> str:
    """Attempt to extract JSON substring from text by finding the first '{' and last '}'."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return text[start : end + 1]


def _compact_fingerprint(fingerprint: Dict[str, Any], max_chars: int = 4000) -> Dict[str, Any]:
    """Produce a compact representation of the fingerprint suitable for short prompts.

    Truncates long string fields and retains only essential keys.
    """
    compact: Dict[str, Any] = {}
    for k in ("name", "created_at", "user_data_dir"):
        if k in fingerprint:
            compact[k] = fingerprint[k]

    # geolocation summary
    geo = fingerprint.get("geolocation")
    if geo:
        compact["geolocation"] = {"latitude": geo.get("latitude"), "longitude": geo.get("longitude"), "country": geo.get("country")}

    # options summary: keep env.CAMOU_CONFIG_1 but truncated
    try:
        env = fingerprint.get("options", {}).get("env", {})
        camo = env.get("CAMOU_CONFIG_1")
        if camo:
            if len(camo) > max_chars:
                compact["CAMOU_CONFIG_1_truncated"] = camo[: max_chars] + "..."
            else:
                compact["CAMOU_CONFIG_1"] = camo
        # also copy headless and user_data_dir
        if "headless" in fingerprint.get("options", {}):
            compact["headless"] = fingerprint["options"]["headless"]
    except Exception:
        pass

    # include deterministic hints (if present elsewhere)
    if "geolocation_js" in fingerprint:
        compact["geolocation_js"] = fingerprint["geolocation_js"]

    # include hardware summary, canvas/webgl hashes, accept-language and tz offset
    hw = fingerprint.get("hardware", {}) or {}
    for key in ("device_memory_gb", "hardware_concurrency", "fonts", "fonts_count", "webgl_present", "webgl_vendor", "webgl_renderer", "webgl_hash", "canvas_hash", "media_device_count", "accept_language", "tz_offset_minutes"):
        if key in hw:
            compact[key] = hw[key]

    return compact


def call_lm_assess(fingerprint: Dict[str, Any], checks: Dict[str, Any], consistency_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    system = {"role": "system", "content": "You are a strict JSON-only auditor for fingerprint consistency."}

    def build_user_msg(fp: Dict[str, Any], ck: Dict[str, Any], note: Optional[str] = None) -> Dict[str, str]:
        content = "Fingerprint:\n" + json.dumps(fp, indent=2) + "\nDeterministic checks:\n" + json.dumps(ck, indent=2)
        if note:
            content += "\nNote: " + note
        content += "\nTask: Return EXACTLY one JSON: {score:int(0-100), verdict:str, issues:list, hints:list, confidence:float(0-1)}."
        return {"role": "user", "content": content}

    # Allow caller to pass per-namespace consistency options which modify the prompt
    note: Optional[str] = None
    if consistency_options and consistency_options.get("ignore_geo_country"):
        note = "Ignore any mismatch between IP-based country and reverse-geocoded country; do not score this as an issue."

    # Pre-emptively compact if the raw JSON looks very large (heuristic)
    raw_len = len(json.dumps(fingerprint)) + len(json.dumps(checks))
    if raw_len > 20000:
        user = build_user_msg(_compact_fingerprint(fingerprint, max_chars=3000), checks, note=(note or "Input was too large; using compact fingerprint summary."))
    else:
        user = build_user_msg(fingerprint, checks, note=note)

    payload = {"model": MODEL, "messages": [system, user], "max_tokens": 512, "temperature": 0.0}

    try:
        r = requests.post(LM_URL, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        # Attempt a compact retry if the server complains about context/token limits
        msg = str(http_err)
        try:
            resp_text = http_err.response.text if getattr(http_err, "response", None) is not None else ""
        except Exception:
            resp_text = ""
        if any(sub in msg.lower() for sub in ("context", "overflow", "token")) or any(sub in resp_text.lower() for sub in ("context", "overflow", "token", "Trying to keep")):
            # Retry with compact fingerprint
            compact_fp = _compact_fingerprint(fingerprint, max_chars=2000)
            user2 = build_user_msg(compact_fp, checks, note="Retry with compact fingerprint due to server context limits.")
            payload2 = {"model": MODEL, "messages": [system, user2], "max_tokens": 512, "temperature": 0.0}
            r2 = requests.post(LM_URL, json=payload2, timeout=TIMEOUT)
            r2.raise_for_status()
            jr2 = r2.json()
            text2 = jr2["choices"][0]["message"]["content"]
            try:
                return json.loads(text2)
            except Exception:
                js = _extract_json(text2)
                return json.loads(js)
        # If not a context issue, re-raise
        raise

    jr = r.json()
    # Extract assistant message and any extra fields (some backends include `reasoning`)
    msg = jr["choices"][0]["message"]
    text = msg.get("content", "")

    # Prepare a container for LLm result that preserves raw output and metadata
    llm_result: Dict[str, Any] = {"raw": text, "reasoning": msg.get("reasoning"), "tool_calls": msg.get("tool_calls", [])}

    # Try to parse JSON that the assistant was asked to return
    parsed = None
    try:
        parsed = json.loads(text)
        llm_result.update(parsed)
        return llm_result
    except Exception:
        # Try to extract JSON substring
        try:
            js = _extract_json(text)
            parsed = json.loads(js)
            llm_result.update(parsed)
            return llm_result
        except Exception:
            # Attempt to recover important fields via regex (best-effort)
            try:
                score_m = re.search(r'"score"\s*:\s*(\d+)', text)
                verdict_m = re.search(r'"verdict"\s*:\s*"([^"]+)"', text)
                issues_m = re.search(r'"issues"\s*:\s*\[(.*?)\]', text, re.DOTALL)
                if score_m:
                    llm_result["score"] = int(score_m.group(1))
                if verdict_m:
                    llm_result["verdict"] = verdict_m.group(1)
                if issues_m:
                    # crude split of simple string items
                    items = [i.strip().strip('"') for i in re.split(r',(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', issues_m.group(1)) if i.strip()]
                    llm_result["issues"] = items
            except Exception:
                pass

            # If nothing useful found, attach a parse error marker
            llm_result.setdefault("parse_error", "Could not parse assistant JSON; raw output preserved in 'raw'")
            return llm_result


def run_consistency_and_save(namespace_path: Path, consistency_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run deterministic checks and the LLM assessor and save results to `namespace.json`.

    Returns the consistency dict for convenience.
    """
    ns_path = Path(namespace_path)
    if not ns_path.exists():
        raise FileNotFoundError(ns_path)

    ns = json.loads(ns_path.read_text(encoding="utf-8"))
    # Merge options: explicit arg overrides namespace-stored preferences
    opts = {}
    try:
        opts = ns.get("consistency_options", {}) or {}
    except Exception:
        opts = {}
    if consistency_options:
        opts.update(consistency_options)

    # Default to ignoring IP-country mismatches unless explicitly disabled
    opts.setdefault("ignore_geo_country", True)

    checks = deterministic_checks(ns, ignore_geo_country=bool(opts.get("ignore_geo_country")))

    try:
        llm_result = call_lm_assess(ns, checks, consistency_options=opts)
    except Exception as exc:
        llm_result = {"score": 0, "verdict": "ERROR", "issues": [str(exc)], "hints": [], "confidence": 0.0}

    consistency = {
        "score": int(llm_result.get("score") or 0),
        "verdict": llm_result.get("verdict") or ("OK" if int(llm_result.get("score") or 0) >= 85 else "SUSPICIOUS"),
        "details": {"deterministic": checks, "llm": llm_result},
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "model": MODEL,
    }

    ns["consistency"] = consistency
    ns_path.write_text(json.dumps(ns, indent=2, ensure_ascii=False), encoding="utf-8")
    return consistency


def normalize_namespace(ns_path: Path) -> Dict[str, Any]:
    """Normalize CAMOU_CONFIG_1 screen fields and reconcile geolocation if present.

    Returns a dict describing changes made.
    """
    p = Path(ns_path)
    if not p.exists():
        raise FileNotFoundError(p)
    ns = json.loads(p.read_text(encoding="utf-8"))
    changes = {}

    # Normalize CAMOU_CONFIG_1 if present
    try:
        env = ns.get("options", {}).get("env", {})
        camo_raw = env.get("CAMOU_CONFIG_1")
        if isinstance(camo_raw, str):
            try:
                camo_json = json.loads(camo_raw)
            except Exception:
                camo_json = None

            if isinstance(camo_json, dict):
                original = camo_json.copy()
                width = int(camo_json.get("screen.width", camo_json.get("screen.availWidth", 1920)))
                height = int(camo_json.get("screen.height", camo_json.get("screen.availHeight", 1080)))
                avail_w = int(camo_json.get("screen.availWidth", width))
                avail_h = int(camo_json.get("screen.availHeight", max(0, height - 48)))
                avail_left = int(camo_json.get("screen.availLeft", 0))

                if avail_left >= width or avail_left < 0:
                    camo_json["screen.availLeft"] = 0
                if avail_w != width:
                    camo_json["screen.availWidth"] = width
                if avail_h <= 0 or avail_h > height:
                    camo_json["screen.availHeight"] = max(0, height - 48)
                if camo_json.get("window.screenX", 0) >= width:
                    camo_json["window.screenX"] = 0
                if camo_json.get("window.screenY", 0) >= height:
                    camo_json["window.screenY"] = 0

                if camo_json != original:
                    env["CAMOU_CONFIG_1"] = json.dumps(camo_json)
                    ns.setdefault("options", {})["env"] = env
                    changes["CAMOU_CONFIG_1_normalized"] = True
    except Exception as exc:
        changes["CAMOU_CONFIG_1_error"] = str(exc)

    # Reconcile geolocation if present: attempt reverse geocode and set country_source
    try:
        geo = ns.get("geolocation")
        if geo and "latitude" in geo and "longitude" in geo and requests is not None:
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            try:
                rev = requests.get(
                    f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}",
                    headers={"User-Agent": "ASISMarketing/1.0 (contact@example.com)"},
                    timeout=5,
                )
                if rev.status_code == 200:
                    rj = rev.json()
                    addr = rj.get("address", {})
                    country_res = addr.get("country") or addr.get("country_code")
                    if country_res:
                        ns.setdefault("geolocation", {})["country_resolved"] = country_res
                        if str(country_res).lower() not in str(geo.get("country", "")).lower():
                            ns["geolocation"]["country_source"] = "reverse_geocode"
                            ns["geolocation"]["country"] = country_res
                            changes["geolocation_country_overridden"] = True
                        else:
                            ns["geolocation"]["country_source"] = "ip-api"

                # Ensure a JS geolocation is present so deterministic checks can compute distance
                if "latitude" in geo and "longitude" in geo:
                    ns["geolocation_js"] = {"latitude": geo.get("latitude"), "longitude": geo.get("longitude")}
                    changes["geolocation_js_set"] = True

                # If timezone present, copy into options top-level for runtime use
                tz = geo.get("timezone")
                if tz:
                    ns.setdefault("options", {})["timezone"] = tz
                    changes["timezone_in_options"] = tz

            except Exception as exc:
                changes["reverse_geocode_error"] = str(exc)
    except Exception as exc:
        changes["geolocation_error"] = str(exc)

    # Extract canvas/webgl/accept-language/tz offset into hardware if present in CAMOU_CONFIG_1
    try:
        camo = None
        try:
            camo = json.loads(ns.get("options", {}).get("env", {}).get("CAMOU_CONFIG_1", "") or "")
        except Exception:
            camo = None

        if camo:
            hw = ns.setdefault("hardware", {})
            # canvas
            c = camo.get("canvas.hash") or camo.get("canvas_fingerprint") or camo.get("canvas")
            if c:
                if isinstance(c, (dict, list)):
                    hw["canvas_hash"] = hashlib.md5(json.dumps(c, sort_keys=True).encode("utf-8")).hexdigest()
                else:
                    hw["canvas_hash"] = c if re.fullmatch(r"[0-9a-fA-F]{16,128}", str(c)) else hashlib.md5(str(c).encode("utf-8")).hexdigest()

            # webgl
            wv = camo.get("webgl.vendor") or camo.get("webgl_unmasked_vendor") or camo.get("gpu.vendor")
            wr = camo.get("webgl.renderer") or camo.get("webgl_unmasked_renderer") or camo.get("gpu.renderer")
            if wv or wr:
                hw.setdefault("webgl_present", True)
                if wv:
                    hw["webgl_vendor"] = wv
                if wr:
                    hw["webgl_renderer"] = wr
                hw["webgl_hash"] = hashlib.md5((str(wv or "") + "|" + str(wr or "")).encode("utf-8")).hexdigest()

            # accept-language / navigator.languages
            al = camo.get("navigator.languages") or camo.get("acceptLanguage")
            if al:
                hw["accept_language"] = ",".join(al) if isinstance(al, list) else str(al)

            # timezone offset
            tz = ns.get("options", {}).get("timezone") or ns.get("timezone") or (ns.get("geolocation") or {}).get("timezone")
            if tz:
                try:
                    dt = datetime.utcnow()
                    off = ZoneInfo(tz).utcoffset(dt)
                    if off is not None:
                        hw["tz_offset_minutes"] = int(off.total_seconds() // 60)
                except Exception:
                    pass
    except Exception as exc:
        changes["hardware_extract_error"] = str(exc)

    # Heuristic: if options.headless is True but the CAMOU_CONFIG_1 shows desktop-like fingerprint, mark headless->False for fingerprint consistency
    try:
        opts = ns.get("options", {})
        env = opts.get("env", {})
        camo_raw = env.get("CAMOU_CONFIG_1")
        camo_parsed = None
        if isinstance(camo_raw, str):
            try:
                camo_parsed = json.loads(camo_raw)
            except Exception:
                camo_parsed = None
        if opts.get("headless") and camo_parsed:
            fonts = camo_parsed.get("fonts", [])
            oscpu = camo_parsed.get("navigator.oscpu", "")
            if (isinstance(fonts, list) and len(fonts) > 20) or ("Windows" in str(oscpu)):
                opts["headless"] = False
                ns.setdefault("options", {})["headless"] = False
                changes["headless_for_fingerprint"] = True
    except Exception:
        pass

    # Hardware defaults & extraction: derive WebGL/device/media info from CAMOU_CONFIG_1 or apply safe defaults
    try:
        camo = camo_parsed or {}
        hw_changes = []

        webgl_vendor = camo.get("webgl.vendor") or camo.get("webgl_unmasked_vendor") or camo.get("gpu.vendor")
        webgl_renderer = camo.get("webgl.renderer") or camo.get("webgl_unmasked_renderer") or camo.get("gpu.renderer")
        if webgl_vendor or webgl_renderer:
            ns.setdefault("hardware", {})["webgl_present"] = True
            if webgl_vendor:
                ns["hardware"]["webgl_vendor"] = webgl_vendor
            if webgl_renderer:
                ns["hardware"]["webgl_renderer"] = webgl_renderer
            hw_changes.append("webgl_from_camo")
        else:
            ns.setdefault("hardware", {}).setdefault("webgl_present", False)

        dm = camo.get("navigator.deviceMemory") or camo.get("deviceMemory") or ns.get("hardware", {}).get("device_memory_gb")
        if dm is None:
            ns.setdefault("hardware", {})["device_memory_gb"] = 8
            hw_changes.append("device_memory_default_8GB")
        else:
            try:
                ns.setdefault("hardware", {})["device_memory_gb"] = float(dm)
            except Exception:
                ns.setdefault("hardware", {})["device_memory_gb"] = None

        hc = camo.get("navigator.hardwareConcurrency") or camo.get("hardwareConcurrency")
        if hc is not None:
            try:
                ns.setdefault("hardware", {})["hardware_concurrency"] = int(hc)
            except Exception:
                pass

        mdevs = camo.get("media_devices") or camo.get("enumerateDevices") or ns.get("hardware", {}).get("media_device_count")
        if mdevs is None:
            ns.setdefault("hardware", {})["media_device_count"] = 0
            hw_changes.append("media_device_count_default_0")
        else:
            if isinstance(mdevs, list):
                ns.setdefault("hardware", {})["media_device_count"] = len(mdevs)
            else:
                try:
                    ns.setdefault("hardware", {})["media_device_count"] = int(mdevs)
                except Exception:
                    ns.setdefault("hardware", {})["media_device_count"] = None

        if hw_changes:
            changes["hardware_defaults_applied"] = hw_changes
    except Exception as exc:
        changes["hardware_defaults_error"] = str(exc)

    # Write back changes if any
    if changes:
        p.write_text(json.dumps(ns, indent=2, ensure_ascii=False), encoding="utf-8")
    return changes


__all__ = ["deterministic_checks", "call_lm_assess", "run_consistency_and_save", "normalize_namespace"]

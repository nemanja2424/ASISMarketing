# BW_Controller/fingerprint_validator.py

WINDOWS_PLATFORM_VALUES = {"Win32", "Win64"}

WINDOWS_UA_KEYWORDS = [
    "Windows NT 10.0",
    "Windows NT 11.0"
]

FORBIDDEN_KEYWORDS = [
    "Apple",
    "Mac OS",
    "Macintosh",
    "M1",
    "M2",
    "M3",
    "Metal",
    "ARM",
    "ANGLE Metal"
]

ALLOWED_GPU_VENDORS = [
    "Intel",
    "NVIDIA",
    "AMD"
]


def is_valid_windows_fingerprint(fp: dict) -> tuple[bool, str]:
    """
    Validira da li fingerprint predstavlja REALISTIČNU Windows mašinu.
    Vraća (True, "OK") ili (False, razlog)
    """

    # ========= PLATFORM =========
    platform = fp.get("platform")
    if platform not in WINDOWS_PLATFORM_VALUES:
        return False, f"Invalid platform: {platform}"

    # ========= USER AGENT =========
    ua = fp.get("userAgent", "")
    if not any(k in ua for k in WINDOWS_UA_KEYWORDS):
        return False, f"Invalid User-Agent: {ua}"

    # ========= WEBGL =========
    webgl = fp.get("webgl")
    if not webgl:
        return False, "Missing WebGL info"

    vendor = (webgl.get("vendor") or "").lower()
    renderer = (webgl.get("renderer") or "").lower()

    for bad in FORBIDDEN_KEYWORDS:
        bad_l = bad.lower()
        if bad_l in vendor or bad_l in renderer:
            return False, f"Forbidden WebGL keyword detected: {bad}"

    if not any(v.lower() in vendor for v in ALLOWED_GPU_VENDORS):
        return False, f"Non-Windows GPU vendor: {vendor}"

    # ========= SCREEN =========
    screen = fp.get("screen", {})
    width = screen.get("width")
    height = screen.get("height")
    dpr = screen.get("dpr")

    if not width or not height:
        return False, "Invalid screen size"

    if width < 1024 or height < 720:
        return False, "Screen resolution too small for desktop Windows"

    if dpr not in {1, 1.25, 1.5, 2}:
        return False, f"Suspicious DPR: {dpr}"

    # ========= HARDWARE =========
    cores = fp.get("hardwareConcurrency")
    if not cores or cores < 2 or cores > 32:
        return False, f"Unrealistic CPU cores: {cores}"

    memory = fp.get("deviceMemory")
    if memory is not None and memory not in {4, 8, 16, 32}:
        return False, f"Suspicious deviceMemory: {memory}"

    # ========= TIMEZONE =========
    tz = fp.get("timezone", "")
    if not tz:
        return False, "Missing timezone"

    # ========= LANGUAGES =========
    languages = fp.get("languages", [])
    if not isinstance(languages, list) or not languages:
        return False, "Invalid languages"

    # Ako je sve prošlo
    return True, "OK"

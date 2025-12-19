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


def create_profile(display_name: str | None = None, *, namespace: str = "default", headless: bool = False, no_launch: bool = False, profile_path: str | None = None) -> tuple[str, str]:
	"""Create a profile (or namespace) and save its launch options.

	If `profile_path` points to an existing `profile.json`, add the namespace under
	that profile. Otherwise create a new profile. Returns (profile_id, namespace).
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

	# Generate the launch options
	try:
		opts = launch_options(user_data_dir=user_data_dir_abs, headless=headless)
	except Exception as exc:  # pragma: no cover - runtime environment dependent
		print(f"Error while generating launch options: {exc}")
		raise

	# Convert launch options into a JSON serializable form
	opts_serial = _make_serializable(opts)

	ns_meta = {
		"name": namespace,
		"created_at": datetime.utcnow().isoformat() + "Z",
		"options": opts_serial,
		"user_data_dir": user_data_dir_abs,
	}

	# Save namespace metadata
	ns_path = ns_dir / "namespace.json"
	with ns_path.open("w", encoding="utf-8") as f:
		json.dump(ns_meta, f, indent=2, ensure_ascii=False)

	# Update the top-level profile metadata
	profile_meta.setdefault("namespaces", {})[namespace] = str(ns_path)
	with profile_path.open("w", encoding="utf-8") as f:
		json.dump(profile_meta, f, indent=2, ensure_ascii=False)

	print(f"Namespace saved to {ns_path}")

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

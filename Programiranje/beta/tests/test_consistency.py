import json
from pathlib import Path

import pytest

from BW_Controller.consistency import deterministic_checks, run_consistency_and_save, call_lm_assess


def test_deterministic_checks_basic():
    ns = {
        "options": {
            "env": {
                "CAMOU_CONFIG_1": '{"screen.width":1920,"screen.height":1080,"navigator.userAgent":"UA"}'
            }
        },
        "geolocation": {"latitude": 48.0, "longitude": 8.0},
        "geolocation_js": {"latitude": 48.1, "longitude": 8.1},
        "timezone": "Europe/Paris",
    }
    checks = deterministic_checks(ns)
    assert checks["screen_ok"] is True
    assert checks["geo_distance_km"] is not None


class DummyResp:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._content


def test_call_lm_assess_parsing(monkeypatch):
    # Simulate LM Studio returning a JSON object in content
    fake = {
        "choices": [
            {"message": {"content": '{"score":90,"verdict":"OK","issues":[],"hints":[],"confidence":0.9}'}}
        ]
    }

    def fake_post(url, json=None, timeout=None):
        return DummyResp(fake)

    monkeypatch.setattr("BW_Controller.consistency.requests.post", fake_post)

    res = call_lm_assess({"dummy": True}, {"check": 1})
    assert res["score"] == 90
    assert res["verdict"] == "OK"


def test_run_consistency_and_save(tmp_path, monkeypatch):
    # Prepare namespace file
    ns = {
        "name": "testns",
        "options": {"env": {"CAMOU_CONFIG_1": '{"screen.width":1920,"screen.height":1080}'}}
    }
    ns_path = tmp_path / "namespace.json"
    ns_path.write_text(json.dumps(ns), encoding="utf-8")

    # Mock LM call to return predictable JSON
    fake = {
        "choices": [
            {"message": {"content": '{"score":75,"verdict":"WARN","issues":["geo"],"hints":[],"confidence":0.6}'}}
        ]
    }

    def fake_post(url, json=None, timeout=None):
        return DummyResp(fake)

    monkeypatch.setattr("BW_Controller.consistency.requests.post", fake_post)

    consistency = run_consistency_and_save(ns_path)
    assert consistency["score"] == 75
    written = json.loads(ns_path.read_text(encoding="utf-8"))
    assert "consistency" in written
    assert written["consistency"]["verdict"] == "WARN"

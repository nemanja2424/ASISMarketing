import json
from pathlib import Path

import pytest

from BW_Controller.consistency import call_lm_assess


class DummyResp:
    def __init__(self, content, status_code=200, text=None):
        self._content = content
        self.status_code = status_code
        self._text = text or json.dumps(content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"{self.status_code} Client Error: {self._text}")

    def json(self):
        return self._content


# Simulate first call raising context error, second returns good JSON

def test_retry_on_context_overflow(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # Simulate HTTPError with context message
            resp = DummyResp({"error": "context overflow"}, status_code=400, text="Trying to keep the first 7000 tokens when context overflows")
            class E(Exception):
                def __init__(self, response):
                    self.response = response
                def __str__(self):
                    return "400 Client Error"
            raise E(resp)
        else:
            return DummyResp({"choices": [{"message": {"content": '{"score":85,"verdict":"OK","issues":[],"hints":[],"confidence":0.85}'}}]})

    monkeypatch.setattr("BW_Controller.consistency.requests.post", fake_post)

    # Large dummy fingerprint to trigger compacting path
    fingerprint = {"big": "x" * 50000}
    checks = {"geo_ok": True}

    res = call_lm_assess(fingerprint, checks)
    assert res["score"] == 85
    assert res["verdict"] == "OK"
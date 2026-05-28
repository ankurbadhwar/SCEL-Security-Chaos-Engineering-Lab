"""
Integration tests for Orchestrator ↔ Metrics Dashboard bidirectional API.
Requires: Target (5000), Engine API (5002), Metrics (5001) running.
"""
import time
import requests
import pytest

ENGINE = "http://127.0.0.1:5002"
METRICS = "http://127.0.0.1:5001"
TARGET = "http://127.0.0.1:5000"
API_KEY = "scel-engine-key-2024"
HEADERS = {"X-API-Key": API_KEY}


# ─── Engine API Tests ───────────────────────────────────────────────────────

class TestEngineHealth:
    def test_health(self):
        r = requests.get(f"{ENGINE}/api/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "scel-engine-api"
        assert data["status"] == "ok"

    def test_status_idle(self):
        r = requests.get(f"{ENGINE}/api/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("idle", "completed")


class TestEngineAuth:
    def test_execute_no_key_401(self):
        r = requests.post(f"{ENGINE}/api/execute", json={}, timeout=5)
        assert r.status_code == 401

    def test_execute_bad_key_401(self):
        r = requests.post(f"{ENGINE}/api/execute", json={},
                          headers={"X-API-Key": "wrong"}, timeout=5)
        assert r.status_code == 401

    def test_stop_no_key_401(self):
        r = requests.post(f"{ENGINE}/api/stop", json={}, timeout=5)
        assert r.status_code == 401

    def test_controls_no_key_401(self):
        r = requests.post(f"{ENGINE}/api/controls", json={}, timeout=5)
        assert r.status_code == 401


class TestEngineValidation:
    def test_invalid_phase(self):
        r = requests.post(f"{ENGINE}/api/execute",
                          json={"phase": "invalid"},
                          headers=HEADERS, timeout=5)
        assert r.status_code == 400

    def test_invalid_attack(self):
        r = requests.post(f"{ENGINE}/api/execute",
                          json={"attacks": ["nonexistent"]},
                          headers=HEADERS, timeout=5)
        assert r.status_code == 400

    def test_invalid_control(self):
        r = requests.post(f"{ENGINE}/api/controls",
                          json={"control": "FAKE_CONTROL", "value": True},
                          headers=HEADERS, timeout=5)
        assert r.status_code == 400


class TestEngineControls:
    def test_toggle_single(self):
        r = requests.post(f"{ENGINE}/api/controls",
                          json={"control": "RATE_LIMIT_ENABLED", "value": True},
                          headers=HEADERS, timeout=5)
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_toggle_batch(self):
        r = requests.post(f"{ENGINE}/api/controls",
                          json={"controls": {
                              "RATE_LIMIT_ENABLED": True,
                              "RBAC_ENABLED": True,
                          }},
                          headers=HEADERS, timeout=5)
        assert r.status_code == 200
        results = r.json()["results"]
        assert results["RATE_LIMIT_ENABLED"]["success"] is True

    def test_controls_status(self):
        r = requests.get(f"{ENGINE}/api/controls/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "RATE_LIMIT_ENABLED" in data


class TestEngineAttacksList:
    def test_list_attacks(self):
        r = requests.get(f"{ENGINE}/api/attacks", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "brute_force" in data
        assert "idor" in data
        assert "csrf" in data


class TestEngineResults:
    def test_results_endpoint(self):
        r = requests.get(f"{ENGINE}/api/results", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_history_endpoint(self):
        r = requests.get(f"{ENGINE}/api/history", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ─── Metrics Dashboard Tests ───────────────────────────────────────────────

class TestMetricsDashboard:
    def test_index_page(self):
        r = requests.get(f"{METRICS}/", timeout=5)
        assert r.status_code == 200
        assert "Tactical Chaos Metrics" in r.text

    def test_api_metrics(self):
        r = requests.get(f"{METRICS}/api/metrics", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_api_submit(self):
        r = requests.post(f"{METRICS}/api/submit", json={
            "phase": "before_chaos",
            "attack_type": "Test Attack",
            "enabled_controls": 3,
            "total_controls": 3,
            "tte": 5.0,
            "success": False,
        }, timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    def test_api_submit_invalid_phase(self):
        r = requests.post(f"{METRICS}/api/submit", json={
            "phase": "invalid_phase",
        }, timeout=5)
        assert r.status_code == 400


class TestMetricsProxy:
    def test_orchestrator_status(self):
        r = requests.get(f"{METRICS}/api/orchestrator/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data

    def test_attacks_list(self):
        r = requests.get(f"{METRICS}/api/attacks", timeout=5)
        assert r.status_code == 200

    def test_controls_status(self):
        r = requests.get(f"{METRICS}/api/controls/status", timeout=5)
        assert r.status_code == 200

    def test_results_proxy(self):
        r = requests.get(f"{METRICS}/api/results", timeout=5)
        assert r.status_code == 200

    def test_history_proxy(self):
        r = requests.get(f"{METRICS}/api/history", timeout=5)
        assert r.status_code == 200


class TestMetricsProfiles:
    def test_create_profile(self):
        r = requests.post(f"{METRICS}/api/profiles", json={
            "name": "test_profile",
            "controls": {"RATE_LIMIT_ENABLED": True, "RBAC_ENABLED": False},
        }, timeout=5)
        assert r.status_code == 201

    def test_list_profiles(self):
        r = requests.get(f"{METRICS}/api/profiles", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_profile_no_name(self):
        r = requests.post(f"{METRICS}/api/profiles", json={
            "controls": {},
        }, timeout=5)
        assert r.status_code == 400


# ─── End-to-End: Execute via Dashboard → Engine ─────────────────────────────

class TestE2EExecution:
    def test_execute_single_attack_via_dashboard(self):
        """Dashboard proxies execute to engine, engine runs attack."""
        r = requests.post(f"{METRICS}/api/execute", json={
            "phase": "before",
            "attacks": ["brute_force"],
        }, timeout=10)
        assert r.status_code == 202
        data = r.json()
        assert "run_id" in data

        # Poll status until done (max 60s)
        for _ in range(20):
            time.sleep(3)
            sr = requests.get(f"{METRICS}/api/orchestrator/status", timeout=5)
            status = sr.json().get("status", "")
            if status in ("completed", "failed", "idle"):
                break

        assert status in ("completed", "idle"), f"Unexpected status: {status}"

    def test_concurrent_execute_409(self):
        """Second execute while running returns 409."""
        # Start a run
        r1 = requests.post(f"{ENGINE}/api/execute",
                           json={"phase": "before", "attacks": ["brute_force"]},
                           headers=HEADERS, timeout=10)
        # Could be 202 or 429 (rate limited from previous test)
        if r1.status_code == 202:
            time.sleep(0.5)
            r2 = requests.post(f"{ENGINE}/api/execute",
                               json={"phase": "before"},
                               headers=HEADERS, timeout=10)
            assert r2.status_code in (409, 429)
            # Wait for completion
            for _ in range(20):
                time.sleep(3)
                sr = requests.get(f"{ENGINE}/api/status", timeout=5)
                if sr.json().get("status") in ("completed", "failed", "idle"):
                    break


# ─── Target Webapp Sanity ───────────────────────────────────────────────────

class TestTargetWebapp:
    def test_login_page(self):
        r = requests.get(f"{TARGET}/", timeout=5)
        assert r.status_code == 200

    def test_status_endpoint(self):
        r = requests.get(f"{TARGET}/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "RATE_LIMIT_ENABLED" in data

    def test_toggle_control(self):
        r = requests.post(f"{TARGET}/toggle", json={
            "control": "RATE_LIMIT_ENABLED",
            "value": True,
        }, timeout=5)
        assert r.status_code == 200

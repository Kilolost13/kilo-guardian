import requests
import os

def test_metrics_direct_requires_token():
    url = os.environ.get('AI_BRAIN_URL', 'http://localhost:9004')
    # Without token should fail (401 or 403)
    r = requests.get(f"{url}/metrics")
    assert r.status_code in (401, 403)

    # With token (use LIBRARY_ADMIN_KEY or METRICS_TOKEN env var) should succeed
    token = os.environ.get('METRICS_TOKEN') or os.environ.get('LIBRARY_ADMIN_KEY')
    assert token is not None, "Set METRICS_TOKEN or LIBRARY_ADMIN_KEY for this test"
    r2 = requests.get(f"{url}/metrics", headers={"X-Admin-Token": token})
    assert r2.status_code == 200
    assert 'ai_brain_requests_total' in r2.text


def test_metrics_via_gateway_with_admin():
    gw = os.environ.get('GATEWAY_URL', 'http://localhost:8000')
    # Create admin token (first token allowed without auth)
    resp = requests.post(f"{gw}/admin/tokens")
    assert resp.status_code == 200
    token = resp.json().get('token')
    assert token

    # Now fetch metrics via gateway admin proxy
    r = requests.get(f"{gw}/admin/ai_brain/metrics", headers={"X-Admin-Token": token})
    assert r.status_code == 200
    assert 'ai_brain_requests_total' in r.text


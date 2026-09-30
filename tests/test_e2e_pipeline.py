import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.db.session import init_db


@pytest.mark.asyncio
async def test_full_e2e_pr_pipeline():
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # 2. Trigger End-to-End Analysis Run
        sample_diff = (
            "diff --git a/app.py b/app.py\n"
            "+def calculate_total(price, tax):\n"
            "+    # TODO: add discount handling\n"
            "+    return price + tax\n"
        )
        trigger_payload = {
            "repository_id": "org/payment-service",
            "pr_number": 42,
            "base_sha": "a1b2c3d4e5f60000000000000000000000000000",
            "head_sha": "f6e5d4c3b2a11111111111111111111111111111",
            "priority": "P0",
            "sample_diff": sample_diff,
            "changed_files": ["app.py"],
        }

        resp = await client.post("/api/v1/trigger", json=trigger_payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "COMPLETED"
        assert data["published"] is True
        assert "analysis_id" in data
        analysis_id = data["analysis_id"]

        # 3. Fetch detailed run report
        run_resp = await client.get(f"/api/v1/runs/{analysis_id}")
        assert run_resp.status_code == 200
        run_data = run_resp.json()

        assert run_data["repository_id"] == "org/payment-service"
        assert run_data["priority"] == "P0"
        assert run_data["status"] == "COMPLETED"
        assert run_data["is_fresh"] is True
        assert len(run_data["test_evidence"]) > 0
        assert run_data["test_evidence"][0]["passed"] is True

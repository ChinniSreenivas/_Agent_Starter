"""
Integration tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "GTM" in data["app"]


@pytest.mark.asyncio
async def test_dashboard_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "GTM 4-Agent" in response.text


@pytest.mark.asyncio
async def test_run_pipeline_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/gtm/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "demand" in data
        assert "manager" in data


@pytest.mark.asyncio
async def test_signal_ingest_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "signals": ["Increasing demand for AI-driven revenue intelligence in mid-market."],
            "source": "techcrunch_rss"
        }
        response = await client.post("/api/v1/signals/ingest", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "demand_signals" in data["result"]


@pytest.mark.asyncio
async def test_lead_ingest_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "customers": [
                {
                    "company": "API Tester SaaS",
                    "industry": "B2B SaaS",
                    "employees": 350,
                    "sales_team_size": 25,
                    "pain_points": ["manual lead research"]
                }
            ],
            "source": "salesforce_webhook"
        }
        response = await client.post("/api/v1/customers/ingest", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["total_evaluated"] == 1


@pytest.mark.asyncio
async def test_step_wise_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1
        r1 = await client.post("/api/v1/gtm/step/demand")
        assert r1.status_code == 200
        assert r1.json()["step"] == 1

        # Step 2
        r2 = await client.post("/api/v1/gtm/step/customer")
        assert r2.status_code == 200
        assert r2.json()["step"] == 2

        # Step 3
        r3 = await client.post("/api/v1/gtm/step/outbound")
        assert r3.status_code == 200
        assert r3.json()["step"] == 3

        # Step 4
        r4 = await client.post("/api/v1/gtm/step/manager")
        assert r4.status_code == 200
        assert r4.json()["step"] == 4

        # Reset
        r_reset = await client.post("/api/v1/gtm/reset")
        assert r_reset.status_code == 200
        assert r_reset.json()["status"] == "success"


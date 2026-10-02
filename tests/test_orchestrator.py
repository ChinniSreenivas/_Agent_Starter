"""
Tests for GTM Orchestrator and real-time event mechanisms.
"""

import pytest
import asyncio
from app.orchestrator import GTMOrchestrator
from schemas.models import PipelineStatus, RawCustomerData, CampaignStatus


@pytest.mark.asyncio
async def test_orchestrator_pipeline_run():
    orch = GTMOrchestrator()
    result = await orch.run_pipeline()

    assert result.status == PipelineStatus.COMPLETED
    assert result.demand is not None
    assert result.customer is not None
    assert result.outbound is not None
    assert result.manager is not None
    assert result.execution_time_seconds is not None
    assert len(orch.history) >= 8  # Start, 4 agents (processing + completed), and pipeline completed


@pytest.mark.asyncio
async def test_orchestrator_hitl_approval():
    orch = GTMOrchestrator()
    result = await orch.run_pipeline()

    campaign_id = result.outbound.campaign_id
    assert result.outbound.status == CampaignStatus.PENDING_APPROVAL

    # Approve campaign
    approved_campaign = await orch.review_campaign(campaign_id, approved=True, notes="Looks sharp, approved!")
    assert approved_campaign.status == CampaignStatus.APPROVED

    # Check invalid campaign
    with pytest.raises(KeyError):
        await orch.review_campaign("non_existent_id", approved=True)


@pytest.mark.asyncio
async def test_realtime_lead_ingestion():
    orch = GTMOrchestrator()
    new_leads = [
        RawCustomerData(
            company="RealTime Corp",
            industry="B2B SaaS",
            employees=600,
            sales_team_size=50,
            pain_points=["manual qualification"]
        )
    ]
    output = await orch.ingest_customer_leads(new_leads, source="test_webhook")
    assert output.total_evaluated == 1
    assert output.segments[0].company == "RealTime Corp"
    assert output.segments[0].fit_score >= 80.0

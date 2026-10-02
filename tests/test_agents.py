"""
Unit tests for the 4 GTM agents.
"""

import pytest
from pathlib import Path
import json

from agents.demand_sensing import run_async as run_demand
from agents.customer_profiling import run_async as run_customer
from agents.outbound import run_async as run_outbound
from agents.manager import run_async as run_manager
from schemas.models import (
    GTMContext,
    DemandSensingOutput,
    CustomerProfilingOutput,
    OutboundCampaignOutput,
    GTMStrategyOutput
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def gtm_context():
    with open(ROOT / "data" / "gtm_context.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return GTMContext.model_validate(data)


@pytest.mark.asyncio
async def test_demand_sensing_agent(gtm_context):
    output = await run_demand(gtm_context)
    assert isinstance(output, DemandSensingOutput)
    assert "Demand" in output.agent
    assert len(output.demand_signals) > 0
    assert len(output.opportunities) > 0
    assert len(output.risks) > 0


@pytest.mark.asyncio
async def test_customer_profiling_agent(gtm_context):
    demand_out = await run_demand(gtm_context)
    output = await run_customer(gtm_context, demand_output=demand_out)
    assert isinstance(output, CustomerProfilingOutput)
    assert any(term in output.agent for term in ["Customer", "Profiling", "Revenue", "Specialist"])
    assert len(output.segments) >= 1
    assert output.total_evaluated >= 1
    assert output.priority_segment != ""


@pytest.mark.asyncio
async def test_outbound_agent(gtm_context):
    demand_out = await run_demand(gtm_context)
    customer_out = await run_customer(gtm_context, demand_output=demand_out)
    output = await run_outbound(gtm_context, demand_output=demand_out, customer_output=customer_out)

    assert isinstance(output, OutboundCampaignOutput)
    assert any(term in output.agent for term in ["Outbound", "Campaign", "Copywriter", "Strategist"])
    assert output.value_proposition != ""
    assert len(output.channels) > 0
    assert output.compliance_passed is True


@pytest.mark.asyncio
async def test_manager_agent(gtm_context):
    demand_out = await run_demand(gtm_context)
    customer_out = await run_customer(gtm_context, demand_output=demand_out)
    outbound_out = await run_outbound(gtm_context, demand_output=demand_out, customer_output=customer_out)
    output = await run_manager(gtm_context, demand_out, customer_out, outbound_out)

    assert isinstance(output, GTMStrategyOutput)
    assert any(term in output.agent for term in ["Manager", "Strategy", "Officer", "Director"])
    assert len(output.key_risks) > 0
    assert len(output.assumptions_to_validate) > 0
    assert len(output.next_actions) > 0
    assert 0.0 <= output.confidence_score <= 1.0

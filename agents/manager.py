"""
Manager Agent (Production Ready)
Strategic Orchestrator and GTM Executive. Synthesizes inputs from Demand Sensing, Customer Profiling,
and Outbound Campaigns to formulate, evaluate, and dynamically adapt the master GTM strategy.
Tracks key hypotheses, risk mitigation protocols, and operational roadmaps.
"""

from typing import Any, Dict, List, Optional, Union
import json
import asyncio

from core.llm_client import llm_client
from core.logger import get_logger
from schemas.models import (
    GTMStrategyOutput,
    StrategicRisk,
    ValidationHypothesis,
    ActionItem,
    DemandSensingOutput,
    CustomerProfilingOutput,
    OutboundCampaignOutput,
    GTMContext
)

logger = get_logger("agents.manager")

SYSTEM_INSTRUCTION = """
You are the Chief Strategy Officer / VP of Go-To-Market Manager Agent.
Your mandate:
1. Synthesize market intelligence, account qualifications, and outbound campaign proposals into a unified, actionable GTM Strategy.
2. Evaluate strategic coherence: do the channels and messaging accurately hit the priority segment's specific pain points and market tailwinds?
3. Formulate rigorous hypotheses to validate with clear success metrics (e.g. reply rates, qualification conversion).
4. Identify execution risks and assign concrete mitigation measures.
5. Prescribe prioritized immediate next action items (P0/P1/P2) with designated owners.
6. Return strictly structured JSON conforming to the GTMStrategyOutput schema.
"""


def _generate_fallback(
    priority_segment: str,
    positioning: str,
    opportunities: List[str],
    risks: List[str],
    channels: List[str]
) -> GTMStrategyOutput:
    """Executive GTM synthesis fallback engine."""
    structured_risks = [
        StrategicRisk(
            risk=r if isinstance(r, str) else "Risk of market saturation",
            severity="high" if i == 0 else "medium",
            mitigation="Implement strict quality gates and account-specific personalization before outbound dispatch."
        )
        for i, r in enumerate(risks[:3])
    ] or [
        StrategicRisk(
            risk="Deliverability degradation due to cold outreach volume",
            severity="medium",
            mitigation="Warm up secondary sending domains and cap daily sends per inbox to 30 emails."
        )
    ]

    hypotheses = [
        ValidationHypothesis(
            assumption="Mid-market B2B SaaS sales leaders have sufficient lead volume to justify automated qualification.",
            test_method="Conduct 10 discovery calls with VPs of Sales in the target segment.",
            success_metric="70%+ of respondents confirm spending >10 hours/week on manual research."
        ),
        ValidationHypothesis(
            assumption="Personalized, pain-specific outreach outperforms standard industry templates.",
            test_method="Run an A/B test of 200 prospects split evenly between pain-specific copy and generic pitch.",
            success_metric="Achieve >= 6.5% positive reply rate on personalized variant vs < 2% on control."
        )
    ]

    action_items = [
        ActionItem(action="Finalize approval of outbound sequence variants and load into sales engagement platform.", owner="RevOps Lead", priority="P0"),
        ActionItem(action="Enrich list of top 100 Tier-1 accounts matching priority segment with verified contact info.", owner="SDR Lead", priority="P0"),
        ActionItem(action="Launch A/B outbound pilot campaign across Email and LinkedIn channels.", owner="Growth Marketing", priority="P1"),
        ActionItem(action="Establish weekly review cadence to feed conversion data back into Manager Agent.", owner="Head of GTM", priority="P1")
    ]

    return GTMStrategyOutput(
        agent="Manager Agent",
        gtm_strategy=(
            f"Execute an account-based growth sprint targeting {priority_segment}. "
            "Pair real-time lead research automation with hyper-relevant multi-channel messaging "
            "to capture pipeline before competitors capitalize on macro market demand."
        ),
        priority_segment=priority_segment,
        market_reason=opportunities or ["Increasing enterprise demand for automated sales qualification"],
        positioning=positioning,
        recommended_channels=channels or ["Email", "LinkedIn"],
        key_risks=structured_risks,
        assumptions_to_validate=hypotheses,
        next_actions=action_items,
        confidence_score=0.91
    )


def run(
    context: Union[Dict[str, Any], GTMContext],
    demand_output: Optional[Union[Dict[str, Any], DemandSensingOutput]] = None,
    customer_output: Optional[Union[Dict[str, Any], CustomerProfilingOutput]] = None,
    outbound_output: Optional[Union[Dict[str, Any], OutboundCampaignOutput]] = None,
) -> GTMStrategyOutput:
    """Synchronous execution entrypoint."""
    return asyncio.run(run_async(context, demand_output, customer_output, outbound_output))


async def run_async(
    context: Union[Dict[str, Any], GTMContext],
    demand_output: Optional[Union[Dict[str, Any], DemandSensingOutput]] = None,
    customer_output: Optional[Union[Dict[str, Any], CustomerProfilingOutput]] = None,
    outbound_output: Optional[Union[Dict[str, Any], OutboundCampaignOutput]] = None,
) -> GTMStrategyOutput:
    """
    Asynchronously synthesizes all agent reports into an executive GTM strategy.
    """
    ctx_dict = context.model_dump() if isinstance(context, GTMContext) else context

    # Extract upstream data
    demand_data = demand_output.model_dump() if isinstance(demand_output, DemandSensingOutput) else (demand_output or {})
    customer_data = customer_output.model_dump() if isinstance(customer_output, CustomerProfilingOutput) else (customer_output or {})
    outbound_data = outbound_output.model_dump() if isinstance(outbound_output, OutboundCampaignOutput) else (outbound_output or {})

    priority_segment = customer_data.get("priority_segment", "Mid-market B2B SaaS")
    positioning = outbound_data.get("value_proposition", "Automated lead qualification and research")
    opportunities = demand_data.get("opportunities", [])
    risks = demand_data.get("risks", [])
    channels = outbound_data.get("channels", ["Email", "LinkedIn"])

    logger.info("Manager Agent synthesizing master GTM strategy.")

    prompt = f"""
Formulate the master Go-To-Market (GTM) Strategy based on inputs from all specialized agents.

COMPANY & OFFERING:
{json.dumps(ctx_dict.get('company', {}))}
{json.dumps(ctx_dict.get('product', {}))}

AGENT 1 (Demand Sensing) READOUT:
Signals: {json.dumps(demand_data.get('demand_signals', []))}
Opportunities: {json.dumps(opportunities)}
Risks: {json.dumps(risks)}

AGENT 2 (Customer Profiling) READOUT:
Priority Segment: {priority_segment}
Evaluated Segments: {json.dumps(customer_data.get('segments', [])[:3])}

AGENT 3 (Outbound Campaign) READOUT:
Positioning / Value Prop: {positioning}
Channels: {json.dumps(channels)}
Message Preview: {outbound_data.get('message', '')}
CTA: {outbound_data.get('cta', '')}

REQUIREMENTS:
1. Synthesize an authoritative GTM strategy narrative.
2. Link the market reasoning directly to the identified demand signals.
3. Define key risks with actionable mitigations.
4. Establish 2-3 measurable hypotheses with validation methods and target metrics.
5. Create prioritized immediate next action items (P0/P1/P2) with owners.
6. Provide an overall confidence score (0.0 to 1.0).
"""

    return await asyncio.to_thread(
        llm_client.generate_structured,
        prompt=prompt,
        response_model=GTMStrategyOutput,
        system_instruction=SYSTEM_INSTRUCTION,
        fallback_fn=lambda: _generate_fallback(priority_segment, positioning, opportunities, risks, channels),
    )

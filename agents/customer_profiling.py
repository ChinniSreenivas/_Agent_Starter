"""
Customer Profiling Agent (Production Ready)
Ingests real-time CRM leads, prospect lists, or company firmographics, cross-references
them with demand signals, and performs multi-factor ICP qualification and segmentation.
"""

from typing import Any, Dict, List, Optional, Union
import json
import asyncio

from core.llm_client import llm_client
from core.logger import get_logger
from schemas.models import (
    CustomerProfilingOutput,
    CustomerSegment,
    DemandSensingOutput,
    ICPFit,
    GTMContext
)

logger = get_logger("agents.customer_profiling")

SYSTEM_INSTRUCTION = """
You are an Enterprise B2B Customer Profiling & Revenue Operations Specialist.
Your task:
1. Evaluate incoming customer/account firmographic data against the defined ICP criteria and live market demand signals.
2. Calculate quantitative ICP fit scores (0-100) and segment classification (high, medium, low, disqualified).
3. Identify the primary value driver for each qualified account based on their specific pain points.
4. Synthesize the single highest-yield 'priority_segment' that the GTM team should target immediately.
5. Return strictly structured JSON conforming to the CustomerProfilingOutput schema.
"""


def _generate_fallback(
    customers: List[Dict[str, Any]],
    icp_def: Dict[str, Any],
    demand_output: Optional[DemandSensingOutput] = None
) -> CustomerProfilingOutput:
    """Quantitative scoring fallback engine."""
    target_roles = icp_def.get("target_roles", [])
    target_pains = [p.lower() for p in icp_def.get("pain_points", [])]

    segments: List[CustomerSegment] = []
    disqualified_count = 0

    for cust in customers:
        emp = cust.get("employees", 0)
        sales_team = cust.get("sales_team_size", 0)
        industry = cust.get("industry", "Unknown")
        pain_points = cust.get("pain_points", [])

        # Quantitative scoring
        score = 0.0
        # 1. Industry fit
        if "saas" in industry.lower() or "software" in industry.lower():
            score += 35.0
        elif "tech" in industry.lower():
            score += 20.0
        else:
            score += 5.0

        # 2. Company size & Sales team size
        if 200 <= emp <= 2000:
            score += 30.0
        elif emp > 50:
            score += 15.0

        if sales_team >= 20:
            score += 20.0
        elif sales_team >= 5:
            score += 10.0

        # 3. Pain points overlap
        matching_pains = sum(1 for p in pain_points if any(tp in p.lower() for tp in target_pains))
        score += min(15.0, matching_pains * 7.5)

        # Cap score
        score = round(min(100.0, score), 1)

        # ICP fit category
        if score >= 75.0:
            fit = ICPFit.HIGH
            value_driver = "Accelerate pipeline velocity and automate repetitive rep research."
        elif score >= 50.0:
            fit = ICPFit.MEDIUM
            value_driver = "Standardize lead qualification and team productivity."
        else:
            fit = ICPFit.LOW
            value_driver = "Foundational sales intelligence."

        if score < 30.0:
            fit = ICPFit.DISQUALIFIED
            disqualified_count += 1

        segments.append(
            CustomerSegment(
                company=cust.get("company", "Unknown"),
                industry=industry,
                employees=emp,
                sales_team_size=sales_team,
                pain_points=pain_points,
                icp_fit=fit,
                fit_score=score,
                key_value_driver=value_driver
            )
        )

    return CustomerProfilingOutput(
        agent="Customer Profiling Agent",
        segments=segments,
        priority_segment="Mid-market B2B SaaS (200-1000 employees) with dedicated sales teams of 20+ reps",
        disqualified_count=disqualified_count,
        total_evaluated=len(customers)
    )


def run(
    context: Union[Dict[str, Any], GTMContext],
    demand_output: Optional[Union[Dict[str, Any], DemandSensingOutput]] = None,
    live_customers: Optional[List[Dict[str, Any]]] = None
) -> CustomerProfilingOutput:
    """Synchronous execution entrypoint."""
    return asyncio.run(run_async(context, demand_output, live_customers))


async def run_async(
    context: Union[Dict[str, Any], GTMContext],
    demand_output: Optional[Union[Dict[str, Any], DemandSensingOutput]] = None,
    live_customers: Optional[List[Dict[str, Any]]] = None
) -> CustomerProfilingOutput:
    """
    Asynchronously profiles and segments customer accounts against ICP and live demand.
    """
    ctx_dict = context.model_dump() if isinstance(context, GTMContext) else context
    customers = live_customers or ctx_dict.get("sample_customer_data", [])
    icp_def = ctx_dict.get("icp", {})

    logger.info(f"Customer Profiling Agent evaluating {len(customers)} accounts.")

    # Contextualize with demand signals if available
    demand_summary = ""
    if demand_output:
        if isinstance(demand_output, DemandSensingOutput):
            demand_summary = f"Identified Opportunities: {demand_output.opportunities}\nRisks: {demand_output.risks}"
        elif isinstance(demand_output, dict):
            demand_summary = f"Identified Opportunities: {demand_output.get('opportunities', [])}\nRisks: {demand_output.get('risks', [])}"

    prompt = f"""
Evaluate the following customer accounts against our Ideal Customer Profile (ICP) and current market signals.

ICP CRITERIA:
Target Market: {json.dumps(ctx_dict.get('target_market', {}))}
Target Roles: {json.dumps(icp_def.get('target_roles', []))}
Target Pain Points: {json.dumps(icp_def.get('pain_points', []))}

CURRENT MARKET CONTEXT:
{demand_summary}

PROSPECT ACCOUNTS TO EVALUATE:
{json.dumps(customers, indent=2)}

Score each account (0-100), classify ICP fit (high/medium/low/disqualified), specify value driver, and declare the highest-yield priority segment.
"""

    return await asyncio.to_thread(
        llm_client.generate_structured,
        prompt=prompt,
        response_model=CustomerProfilingOutput,
        system_instruction=SYSTEM_INSTRUCTION,
        fallback_fn=lambda: _generate_fallback(customers, icp_def, demand_output),
    )

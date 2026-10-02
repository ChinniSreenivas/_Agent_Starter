"""
Tests for Pydantic V2 schemas and data validation.
"""

import pytest
from pydantic import ValidationError

from schemas.models import (
    DemandSensingOutput,
    DemandSignal,
    SignalStrength,
    SignalTrend,
    CustomerSegment,
    CustomerProfilingOutput,
    ICPFit,
    OutboundCampaignOutput,
    EmailVariant,
    LinkedInVariant,
    PersonalizedCampaign,
    CampaignStatus,
    GTMStrategyOutput,
    StrategicRisk,
    ValidationHypothesis,
    ActionItem,
    GTMContext
)


def test_demand_signal_validation():
    sig = DemandSignal(
        signal="Increasing budget for sales automation",
        strength=SignalStrength.HIGH,
        trend=SignalTrend.INCREASING,
        confidence=0.95
    )
    assert sig.strength == SignalStrength.HIGH
    assert sig.trend == SignalTrend.INCREASING
    assert sig.confidence == 0.95

    # Test confidence bounds
    with pytest.raises(ValidationError):
        DemandSignal(signal="Invalid", confidence=1.5)


def test_customer_segment_validation():
    seg = CustomerSegment(
        company="Test Corp",
        industry="B2B SaaS",
        employees=500,
        sales_team_size=40,
        pain_points=["manual research"],
        icp_fit=ICPFit.HIGH,
        fit_score=90.0
    )
    assert seg.company == "Test Corp"
    assert seg.icp_fit == ICPFit.HIGH
    assert seg.fit_score == 90.0

    with pytest.raises(ValidationError):
        CustomerSegment(
            company="Test Corp",
            industry="B2B SaaS",
            employees=500,
            sales_team_size=40,
            pain_points=[],
            icp_fit="INVALID_FIT",
            fit_score=50.0
        )


def test_outbound_campaign_validation():
    campaign = OutboundCampaignOutput(
        target_segment="Enterprise FinTech",
        value_proposition="Automate research",
        channels=["Email", "LinkedIn"],
        message="Test message",
        cta="Book a demo",
        variants=[
            PersonalizedCampaign(
                target_persona="VP Sales",
                email=EmailVariant(subject="Subject", body="Body", hook="Hook"),
                linkedin=LinkedInVariant(connection_note="Note < 300", inmail_message="InMail")
            )
        ]
    )
    assert campaign.status == CampaignStatus.PENDING_APPROVAL
    assert len(campaign.variants) == 1
    assert campaign.variants[0].target_persona == "VP Sales"


def test_manager_strategy_validation():
    strat = GTMStrategyOutput(
        gtm_strategy="Focus on mid-market SaaS",
        priority_segment="B2B SaaS",
        market_reason=["High demand"],
        positioning="AI sales intelligence",
        recommended_channels=["Email"],
        key_risks=[StrategicRisk(risk="Spam fatigue", severity="high", mitigation="Personalize")],
        assumptions_to_validate=[
            ValidationHypothesis(assumption="Reps need this", test_method="Interviews", success_metric="80% confirm")
        ],
        next_actions=[ActionItem(action="Run pilot", owner="SDR Lead", priority="P0")],
        confidence_score=0.88
    )
    assert strat.agent == "Manager Agent"
    assert strat.confidence_score == 0.88

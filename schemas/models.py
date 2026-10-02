"""
Pydantic V2 Data Models and Contracts for the 4-Agent GTM Strategy System.
Enforces strict typing, JSON schema validation, and structured outputs for Gemini.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class SignalStrength(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignalTrend(str, Enum):
    EMERGING = "emerging"
    INCREASING = "increasing"
    PERSISTENT = "persistent"
    DECLINING = "declining"


class ICPFit(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DISQUALIFIED = "disqualified"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPATCHED = "dispatched"


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Input Context Models
# ============================================================================

class CompanyInfo(BaseModel):
    name: str = Field(..., description="Name of the company offering the solution")
    description: str = Field(..., description="Brief summary of company offerings")


class ProductInfo(BaseModel):
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product overview")
    features: List[str] = Field(default_factory=list, description="Core feature set")


class TargetMarket(BaseModel):
    industry: str = Field(..., description="Target industry")
    company_size: str = Field(..., description="Target company size range")
    geography: str = Field(default="Global", description="Target geographical focus")


class ICPDefinition(BaseModel):
    target_roles: List[str] = Field(default_factory=list, description="Target buyer/influencer titles")
    pain_points: List[str] = Field(default_factory=list, description="Target core operational pain points")


class RawCustomerData(BaseModel):
    company: str
    industry: str
    employees: int = 0
    pain_points: List[str] = Field(default_factory=list)
    sales_team_size: int = 0
    budget: Optional[str] = None
    country: Optional[str] = "Global"


class GTMContext(BaseModel):
    company: CompanyInfo
    product: ProductInfo
    target_market: TargetMarket
    icp: ICPDefinition
    sample_market_signals: List[str] = Field(default_factory=list)
    sample_customer_data: List[RawCustomerData] = Field(default_factory=list)


# ============================================================================
# 1. Demand Sensing Agent Schemas
# ============================================================================

class DemandSignal(BaseModel):
    signal: str = Field(..., description="Synthesized market signal or headline")
    strength: SignalStrength = Field(SignalStrength.HIGH, description="Signal market impact / urgency")
    trend: SignalTrend = Field(SignalTrend.INCREASING, description="Observed trend direction")
    category: Optional[str] = Field("Industry Shift", description="Signal category, e.g. Technology, Competitor, Budget")
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Confidence score of this signal")


class DemandSensingOutput(BaseModel):
    agent: str = Field("Demand Sensing Agent", description="Agent name identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    demand_signals: List[DemandSignal] = Field(..., description="Identified and prioritized demand signals")
    opportunities: List[str] = Field(..., description="Actionable GTM opportunities identified from signals")
    risks: List[str] = Field(..., description="Market or competitive risks to navigate")
    executive_summary: Optional[str] = Field(None, description="One-paragraph macro market readout")


# ============================================================================
# 2. Customer Profiling Agent Schemas
# ============================================================================

class CustomerSegment(BaseModel):
    company: str
    industry: str
    employees: int
    sales_team_size: int
    pain_points: List[str]
    icp_fit: ICPFit
    fit_score: float = Field(0.0, ge=0.0, le=100.0, description="Quantitative ICP fit score 0-100")
    key_value_driver: Optional[str] = Field(None, description="Primary value proposition driver for this account")


class CustomerProfilingOutput(BaseModel):
    agent: str = Field("Customer Profiling Agent", description="Agent name identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    segments: List[CustomerSegment] = Field(..., description="Classified customer accounts and segments")
    priority_segment: str = Field(..., description="High-priority segment to target immediately")
    disqualified_count: int = Field(0, description="Number of disqualified leads")
    total_evaluated: int = Field(0, description="Total number of evaluated prospects")


# ============================================================================
# 3. Outbound Agent Schemas
# ============================================================================

class EmailVariant(BaseModel):
    subject: str = Field(..., description="High-open-rate subject line")
    body: str = Field(..., description="Concise, personalized email body")
    hook: str = Field(..., description="The context hook connecting market signal to pain point")


class LinkedInVariant(BaseModel):
    connection_note: str = Field(..., max_length=300, description="300-char LinkedIn connection request note")
    inmail_message: str = Field(..., description="Direct message or InMail message pitch")


class ObjectionRebuttal(BaseModel):
    objection: str = Field(..., description="Common prospect objection")
    rebuttal: str = Field(..., description="Tactical counter response")


class ColdCallScript(BaseModel):
    opener: str = Field(..., description="10-second pattern interrupt opener")
    elevator_pitch: str = Field(..., description="Problem-focused elevator pitch")
    objection_handling: List[ObjectionRebuttal] = Field(default_factory=list, description="Rebuttals for top 2 objections")


class PersonalizedCampaign(BaseModel):
    target_persona: str = Field(..., description="e.g. VP Sales, Head of RevOps")
    email: EmailVariant
    linkedin: LinkedInVariant
    cold_call: Optional[ColdCallScript] = None


class OutboundCampaignOutput(BaseModel):
    agent: str = Field("Outbound Agent", description="Agent name identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    campaign_id: str = Field(default_factory=lambda: f"cmp_{int(datetime.now(timezone.utc).timestamp())}")
    target_segment: str = Field(..., description="Target segment this outbound campaign addresses")
    value_proposition: str = Field(..., description="Core value proposition")
    channels: List[str] = Field(default_factory=lambda: ["Email", "LinkedIn"], description="Execution channels")
    message: str = Field(..., description="Executive summary preview of outbound messaging")
    cta: str = Field(..., description="Primary Call to Action")
    variants: List[PersonalizedCampaign] = Field(default_factory=list, description="Personalized messaging variants")
    compliance_passed: bool = Field(True, description="Passed CAN-SPAM and brand voice checks")
    status: CampaignStatus = Field(CampaignStatus.PENDING_APPROVAL, description="Campaign workflow status")


# ============================================================================
# 4. Manager Agent Schemas
# ============================================================================

class StrategicRisk(BaseModel):
    risk: str
    severity: str = "medium"
    mitigation: str


class ValidationHypothesis(BaseModel):
    assumption: str
    test_method: str
    success_metric: str


class ActionItem(BaseModel):
    action: str
    owner: str = "GTM Team"
    priority: str = "P1"


class GTMStrategyOutput(BaseModel):
    agent: str = Field("Manager Agent", description="Agent name identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    strategy_id: str = Field(default_factory=lambda: f"gtm_{int(datetime.now(timezone.utc).timestamp())}")
    gtm_strategy: str = Field(..., description="Synthesized executive GTM strategy summary")
    priority_segment: str = Field(..., description="Primary ICP segment to penetrate")
    market_reason: List[str] = Field(..., description="Market demand catalysts backing this strategy")
    positioning: str = Field(..., description="Core product positioning")
    recommended_channels: List[str] = Field(..., description="Channels recommended for distribution")
    key_risks: List[StrategicRisk] = Field(default_factory=list, description="Identified execution and market risks")
    assumptions_to_validate: List[ValidationHypothesis] = Field(default_factory=list, description="Core hypotheses to test")
    next_actions: List[ActionItem] = Field(default_factory=list, description="Immediate execution roadmap items")
    confidence_score: float = Field(0.85, ge=0.0, le=1.0, description="Overall GTM viability score")



# ============================================================================
# Orchestration & Real-Time Event Schemas
# ============================================================================

class AgentEvent(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: str
    agent: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class PipelineExecutionResult(BaseModel):
    pipeline_id: str
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    demand: Optional[DemandSensingOutput] = None
    customer: Optional[CustomerProfilingOutput] = None
    outbound: Optional[OutboundCampaignOutput] = None
    manager: Optional[GTMStrategyOutput] = None
    execution_time_seconds: Optional[float] = None
    error: Optional[str] = None


class SignalIngestRequest(BaseModel):
    signals: List[str] = Field(..., min_length=1, description="List of raw market signals or news items")
    source: str = Field("manual_webhook", description="Data source identifier (e.g. google_trends, rss, crunchbase)")


class LeadIngestRequest(BaseModel):
    customers: List[RawCustomerData] = Field(..., min_length=1, description="List of new customer accounts to evaluate")
    source: str = Field("crm_webhook", description="Source CRM (e.g. hubspot, salesforce)")


class CampaignApprovalRequest(BaseModel):
    campaign_id: str
    approved: bool
    reviewer_notes: Optional[str] = None

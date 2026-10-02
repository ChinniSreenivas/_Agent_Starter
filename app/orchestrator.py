"""
Real-Time Event-Driven Orchestrator for the 4-Agent GTM System.
Manages pipeline lifecycles, event queues, SSE streaming, CRM webhooks, and HITL approvals.
"""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from agents.demand_sensing import run_async as run_demand
from agents.customer_profiling import run_async as run_customer
from agents.outbound import run_async as run_outbound
from agents.manager import run_async as run_manager
from core.logger import get_logger
from schemas.models import (
    AgentEvent,
    CampaignStatus,
    CustomerProfilingOutput,
    DemandSensingOutput,
    GTMContext,
    GTMStrategyOutput,
    OutboundCampaignOutput,
    PipelineExecutionResult,
    PipelineStatus,
    RawCustomerData
)

logger = get_logger("app.orchestrator")


class GTMOrchestrator:
    """
    Central coordinator orchestrating asynchronous agent execution,
    broadcasting real-time events to subscribers, and managing HITL workflows.
    """

    def __init__(self, context_path: Optional[Path] = None):
        self.root_path = Path(__file__).resolve().parents[1]
        self.context_path = context_path or (self.root_path / "data" / "gtm_context.json")
        self._load_context()

        # State storage
        self.latest_result: Optional[PipelineExecutionResult] = None
        self.campaigns: Dict[str, OutboundCampaignOutput] = {}
        self.event_subscribers: List[asyncio.Queue] = []
        self.history: List[AgentEvent] = []
        self.is_running: bool = False

    def _load_context(self):
        with open(self.context_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.context = GTMContext.model_validate(raw)
        logger.info(f"Loaded context for company: '{self.context.company.name}'")

    async def subscribe(self) -> AsyncGenerator[AgentEvent, None]:
        """Subscribes an async generator to the real-time event bus (for SSE / WebSockets)."""
        queue = asyncio.Queue()
        self.event_subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self.event_subscribers.remove(queue)

    async def _emit(self, step: str, agent: str, status: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Emits an event to all active real-time subscribers and audit history."""
        event = AgentEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            step=step,
            agent=agent,
            status=status,
            message=message,
            data=data
        )
        self.history.append(event)
        logger.info(f"[{step}] {agent} - {status}: {message}")

        # Broadcast to all connected clients
        for queue in list(self.event_subscribers):
            await queue.put(event)

    async def run_pipeline(
        self,
        live_signals: Optional[List[str]] = None,
        live_customers: Optional[List[Dict[str, Any]]] = None
    ) -> PipelineExecutionResult:
        """
        Runs the complete 4-agent GTM pipeline asynchronously with real-time event telemetry.
        """
        pipeline_id = f"pipe_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now(timezone.utc)
        self.is_running = True

        result = PipelineExecutionResult(
            pipeline_id=pipeline_id,
            status=PipelineStatus.RUNNING,
            started_at=start_time
        )
        self.latest_result = result

        try:
            await self._emit(
                step="pipeline",
                agent="System",
                status="started",
                message=f"Starting GTM Strategy pipeline [{pipeline_id}]"
            )

            # Step 1: Demand Sensing Agent
            await self._emit(
                step="demand_sensing",
                agent="Demand Sensing Agent",
                status="processing",
                message="Scanning market signals and emerging opportunities..."
            )
            demand_output = await run_demand(self.context, live_signals=live_signals)
            result.demand = demand_output
            await self._emit(
                step="demand_sensing",
                agent="Demand Sensing Agent",
                status="completed",
                message=f"Detected {len(demand_output.demand_signals)} signals and {len(demand_output.opportunities)} opportunities.",
                data=demand_output.model_dump(mode="json")
            )

            # Step 2: Customer Profiling Agent
            await self._emit(
                step="customer_profiling",
                agent="Customer Profiling Agent",
                status="processing",
                message="Evaluating accounts against ICP and market demand..."
            )
            customer_output = await run_customer(self.context, demand_output=demand_output, live_customers=live_customers)
            result.customer = customer_output
            await self._emit(
                step="customer_profiling",
                agent="Customer Profiling Agent",
                status="completed",
                message=f"Profiled {customer_output.total_evaluated} accounts. Priority: '{customer_output.priority_segment}'",
                data=customer_output.model_dump(mode="json")
            )

            # Step 3: Outbound Agent
            await self._emit(
                step="outbound",
                agent="Outbound Agent",
                status="processing",
                message="Crafting personalized multi-channel campaigns..."
            )
            outbound_output = await run_outbound(self.context, demand_output=demand_output, customer_output=customer_output)
            result.outbound = outbound_output
            self.campaigns[outbound_output.campaign_id] = outbound_output
            await self._emit(
                step="outbound",
                agent="Outbound Agent",
                status="completed",
                message=f"Generated campaign [{outbound_output.campaign_id}] across channels: {', '.join(outbound_output.channels)}. Status: {outbound_output.status.value}",
                data=outbound_output.model_dump(mode="json")
            )

            # Step 4: Manager Agent
            await self._emit(
                step="manager",
                agent="Manager Agent",
                status="processing",
                message="Synthesizing master strategy, risk mitigations, and validation hypotheses..."
            )
            manager_output = await run_manager(
                self.context,
                demand_output=demand_output,
                customer_output=customer_output,
                outbound_output=outbound_output
            )
            result.manager = manager_output
            await self._emit(
                step="manager",
                agent="Manager Agent",
                status="completed",
                message=f"Master GTM Strategy formulated with confidence score {manager_output.confidence_score}.",
                data=manager_output.model_dump(mode="json")
            )

            # Finalize
            completion_time = datetime.now(timezone.utc)
            duration = (completion_time - start_time).total_seconds()
            result.completed_at = completion_time
            result.execution_time_seconds = round(duration, 2)
            result.status = PipelineStatus.COMPLETED

            # Persist to disk for backward compatibility
            self._save_strategy(result)

            await self._emit(
                step="pipeline",
                agent="System",
                status="completed",
                message=f"Pipeline completed successfully in {result.execution_time_seconds}s. Output saved to final_gtm_strategy.json",
                data={"pipeline_id": pipeline_id, "duration": result.execution_time_seconds}
            )

            return result

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            await self._emit(
                step="pipeline",
                agent="System",
                status="failed",
                message=f"Pipeline error: {str(e)}"
            )
            raise e
        finally:
            self.is_running = False

    def _save_strategy(self, result: PipelineExecutionResult):
        output_file = self.root_path / "final_gtm_strategy.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "pipeline_id": result.pipeline_id,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "execution_time_seconds": result.execution_time_seconds,
                "demand": result.demand.model_dump(mode="json") if result.demand else None,
                "customer": result.customer.model_dump(mode="json") if result.customer else None,
                "outbound": result.outbound.model_dump(mode="json") if result.outbound else None,
                "manager": result.manager.model_dump(mode="json") if result.manager else None
            }, f, indent=2)

    # ------------------------------------------------------------------------
    # Real-Time Ingestion Handlers
    # ------------------------------------------------------------------------

    async def ingest_market_signals(self, signals: List[str], source: str = "webhook") -> DemandSensingOutput:
        """Real-time webhook ingestion for market signals."""
        await self._emit(
            step="demand_sensing",
            agent="Demand Sensing Agent",
            status="ingesting",
            message=f"Ingested {len(signals)} real-time signals from source: {source}"
        )
        demand_output = await run_demand(self.context, live_signals=signals)
        await self._emit(
            step="demand_sensing",
            agent="Demand Sensing Agent",
            status="completed",
            message=f"Real-time signal analysis completed.",
            data=demand_output.model_dump(mode="json")
        )
        return demand_output

    async def ingest_customer_leads(self, leads: List[RawCustomerData], source: str = "crm_webhook") -> CustomerProfilingOutput:
        """Real-time CRM webhook ingestion for new accounts/leads."""
        await self._emit(
            step="customer_profiling",
            agent="Customer Profiling Agent",
            status="ingesting",
            message=f"Ingested {len(leads)} leads from source: {source}"
        )
        leads_dict = [l.model_dump() for l in leads]
        customer_output = await run_customer(self.context, live_customers=leads_dict)
        await self._emit(
            step="customer_profiling",
            agent="Customer Profiling Agent",
            status="completed",
            message=f"Real-time lead qualification completed.",
            data=customer_output.model_dump(mode="json")
        )
        return customer_output

    # ------------------------------------------------------------------------
    # Human-In-The-Loop Approval Gateway
    # ------------------------------------------------------------------------

    async def review_campaign(self, campaign_id: str, approved: bool, notes: Optional[str] = None) -> OutboundCampaignOutput:
        """Review and approve/reject an outbound campaign before dispatch."""
        if campaign_id not in self.campaigns:
            raise KeyError(f"Campaign with ID '{campaign_id}' not found.")

        campaign = self.campaigns[campaign_id]
        if approved:
            campaign.status = CampaignStatus.APPROVED
            msg = f"Campaign '{campaign_id}' APPROVED by reviewer. Ready for dispatch."
        else:
            campaign.status = CampaignStatus.REJECTED
            msg = f"Campaign '{campaign_id}' REJECTED by reviewer. Notes: {notes or 'No notes'}"

        await self._emit(
            step="hitl_gateway",
            agent="Outbound Reviewer",
            status="approved" if approved else "rejected",
            message=msg,
            data={"campaign_id": campaign_id, "status": campaign.status.value, "notes": notes}
        )

        return campaign

    # ------------------------------------------------------------------------
    # Step-Wise Execution Handlers
    # ------------------------------------------------------------------------

    def _ensure_active_result(self) -> PipelineExecutionResult:
        if not self.latest_result or self.latest_result.status == PipelineStatus.COMPLETED:
            self.latest_result = PipelineExecutionResult(
                pipeline_id=f"pipe_{uuid.uuid4().hex[:8]}",
                status=PipelineStatus.RUNNING,
                started_at=datetime.now(timezone.utc)
            )
        return self.latest_result

    async def run_step_demand(self, live_signals: Optional[List[str]] = None) -> DemandSensingOutput:
        """Step 1: Run Demand Sensing independently."""
        result = self._ensure_active_result()
        await self._emit(
            step="demand_sensing",
            agent="Demand Sensing Agent",
            status="processing",
            message="Scanning market signals and emerging opportunities..."
        )
        demand_output = await run_demand(self.context, live_signals=live_signals)
        result.demand = demand_output
        await self._emit(
            step="demand_sensing",
            agent="Demand Sensing Agent",
            status="completed",
            message=f"Detected {len(demand_output.demand_signals)} signals and {len(demand_output.opportunities)} opportunities.",
            data=demand_output.model_dump(mode="json")
        )
        return demand_output

    async def run_step_customer(self, live_customers: Optional[List[Dict[str, Any]]] = None) -> CustomerProfilingOutput:
        """Step 2: Run Customer Profiling independently."""
        result = self._ensure_active_result()
        await self._emit(
            step="customer_profiling",
            agent="Customer Profiling Agent",
            status="processing",
            message="Evaluating accounts against ICP and market demand..."
        )
        customer_output = await run_customer(self.context, demand_output=result.demand, live_customers=live_customers)
        result.customer = customer_output
        await self._emit(
            step="customer_profiling",
            agent="Customer Profiling Agent",
            status="completed",
            message=f"Profiled {customer_output.total_evaluated} accounts. Priority: '{customer_output.priority_segment}'",
            data=customer_output.model_dump(mode="json")
        )
        return customer_output

    async def run_step_outbound(self) -> OutboundCampaignOutput:
        """Step 3: Run Outbound Agent independently."""
        result = self._ensure_active_result()
        await self._emit(
            step="outbound",
            agent="Outbound Agent",
            status="processing",
            message="Crafting personalized multi-channel campaigns..."
        )
        outbound_output = await run_outbound(self.context, demand_output=result.demand, customer_output=result.customer)
        result.outbound = outbound_output
        self.campaigns[outbound_output.campaign_id] = outbound_output
        await self._emit(
            step="outbound",
            agent="Outbound Agent",
            status="completed",
            message=f"Generated campaign [{outbound_output.campaign_id}] across channels: {', '.join(outbound_output.channels)}.",
            data=outbound_output.model_dump(mode="json")
        )
        return outbound_output

    async def run_step_manager(self) -> GTMStrategyOutput:
        """Step 4: Run Manager Agent independently."""
        result = self._ensure_active_result()
        await self._emit(
            step="manager",
            agent="Manager Agent",
            status="processing",
            message="Synthesizing master strategy, risk mitigations, and validation hypotheses..."
        )
        manager_output = await run_manager(
            self.context,
            demand_output=result.demand,
            customer_output=result.customer,
            outbound_output=result.outbound
        )
        result.manager = manager_output
        result.completed_at = datetime.now(timezone.utc)
        result.status = PipelineStatus.COMPLETED
        if result.started_at:
            result.execution_time_seconds = round((result.completed_at - result.started_at).total_seconds(), 2)
        self._save_strategy(result)

        await self._emit(
            step="manager",
            agent="Manager Agent",
            status="completed",
            message=f"Master GTM Strategy formulated with confidence score {manager_output.confidence_score}.",
            data=manager_output.model_dump(mode="json")
        )
        return manager_output

    async def reset_pipeline(self):
        """Resets the active pipeline state."""
        self.latest_result = None
        self.campaigns.clear()
        await self._emit(
            step="system",
            agent="System",
            status="reset",
            message="Pipeline state reset. Ready for new run."
        )


# Shared singleton instance
orchestrator = GTMOrchestrator()

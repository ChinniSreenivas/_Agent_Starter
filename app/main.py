"""
Main Entrypoint for the 4-Agent GTM Strategy System.
Dual-mode:
  1. CLI Runner: python app/main.py
  2. Real-Time Production Web Server: python app/main.py --server  (or uvicorn app.main:app)
"""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Optional

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


from app.orchestrator import orchestrator
from core.config import settings
from core.logger import get_logger
from schemas.models import (
    CampaignApprovalRequest,
    LeadIngestRequest,
    PipelineExecutionResult,
    SignalIngestRequest
)

logger = get_logger("app.main")

# ============================================================================
# FastAPI Server Application
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Event-Driven 4-Agent Go-To-Market Platform",
)

# Enable CORS for external frontend or webhook consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the real-time interactive operations dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>GTM 4-Agent Platform</h1><p>UI file not found. Visit <a href='/docs'>/docs</a> for API.</p>")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/healthz")
async def health_check():
    """Production readiness & liveness probe."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": settings.is_gemini_configured,
        "model": settings.GEMINI_MODEL,
        "environment": settings.ENVIRONMENT
    }


@app.post("/api/v1/gtm/run", response_model=PipelineExecutionResult)
async def run_pipeline():
    """Triggers an end-to-end run across all 4 agents."""
    try:
        result = await orchestrator.run_pipeline()
        return result
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gtm/stream")
async def stream_events():
    """
    Server-Sent Events (SSE) endpoint broadcasting real-time agent thoughts,
    status updates, and output milestones to connected clients.
    """
    async def event_generator():
        try:
            async for event in orchestrator.subscribe():
                yield f"data: {event.model_dump_json()}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/v1/signals/ingest")
async def ingest_signals(request: SignalIngestRequest):
    """Real-time webhook endpoint for external market signals / news."""
    try:
        output = await orchestrator.ingest_market_signals(request.signals, source=request.source)
        return {"status": "success", "result": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/customers/ingest")
async def ingest_leads(request: LeadIngestRequest):
    """Real-time CRM webhook endpoint for new prospect accounts."""
    try:
        output = await orchestrator.ingest_customer_leads(request.customers, source=request.source)
        return {"status": "success", "result": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: str, request: CampaignApprovalRequest):
    """Human-In-The-Loop (HITL) approval endpoint before outbound dispatch."""
    try:
        updated = await orchestrator.review_campaign(campaign_id, approved=request.approved, notes=request.reviewer_notes)
        return {"status": "success", "campaign": updated}
    except KeyError:
        raise HTTPException(status_code=404, detail="Campaign ID not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/gtm/step/demand")
async def step_demand(request: Optional[SignalIngestRequest] = None):
    """Step 1: Execute Demand Sensing independently."""
    signals = request.signals if request else None
    output = await orchestrator.run_step_demand(live_signals=signals)
    return {"status": "success", "step": 1, "output": output}


@app.post("/api/v1/gtm/step/customer")
async def step_customer(request: Optional[LeadIngestRequest] = None):
    """Step 2: Execute Customer Profiling independently."""
    leads = [l.model_dump() for l in request.customers] if request else None
    output = await orchestrator.run_step_customer(live_customers=leads)
    return {"status": "success", "step": 2, "output": output}


@app.post("/api/v1/gtm/step/outbound")
async def step_outbound():
    """Step 3: Execute Outbound Agent independently."""
    output = await orchestrator.run_step_outbound()
    return {"status": "success", "step": 3, "output": output}


@app.post("/api/v1/gtm/step/manager")
async def step_manager():
    """Step 4: Execute Manager Agent independently."""
    output = await orchestrator.run_step_manager()
    return {"status": "success", "step": 4, "output": output}


@app.post("/api/v1/gtm/reset")
async def reset_pipeline():
    """Reset current pipeline run state."""
    await orchestrator.reset_pipeline()
    return {"status": "success", "message": "Pipeline reset successfully"}


@app.get("/api/v1/strategy/latest")
async def get_latest_strategy():
    """Fetches the latest GTM strategy document."""
    if not orchestrator.latest_result:
        raise HTTPException(status_code=404, detail="No strategy run has completed yet.")
    return orchestrator.latest_result


# ============================================================================
# CLI Execution Logic
# ============================================================================

def run_cli():
    """Runs the 4 agents sequentially via CLI with rich formatting."""
    print("\n=======================================================")
    print("   GTM 4-AGENT SYSTEM: PRODUCTION REAL-TIME RUNNER     ")
    print("=======================================================")
    mode = "Gemini Live API" if settings.is_gemini_configured else "High-Fidelity Heuristic Fallback"
    print(f"Engine Mode: {mode} (Model: {settings.GEMINI_MODEL})\n")

    result = asyncio.run(orchestrator.run_pipeline())

    print("\n=== [1] DEMAND SENSING AGENT ===")
    print(json.dumps(result.demand.model_dump(mode="json"), indent=2))

    print("\n=== [2] CUSTOMER PROFILING AGENT ===")
    print(json.dumps(result.customer.model_dump(mode="json"), indent=2))

    print("\n=== [3] OUTBOUND AGENT ===")
    print(json.dumps(result.outbound.model_dump(mode="json"), indent=2))

    print("\n=== [4] MANAGER AGENT (FINAL GTM STRATEGY) ===")
    print(json.dumps(result.manager.model_dump(mode="json"), indent=2))

    print("\n-------------------------------------------------------")
    print(f"Status: {result.status.value.upper()}")
    print(f"Execution Time: {result.execution_time_seconds} seconds")
    print("Saved strategy payload to 'final_gtm_strategy.json'")
    print("-------------------------------------------------------\n")
    print("Tip: Run `python app/main.py --server` to launch the real-time web dashboard & API!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GTM 4-Agent Strategy System")
    parser.add_argument("--server", action="store_true", help="Launch real-time FastAPI server")
    parser.add_argument("--host", default=settings.HOST, help="Host address")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port number")
    args = parser.parse_args()

    if args.server:
        print(f"Starting GTM 4-Agent Real-Time Server on http://{args.host}:{args.port}")
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
    else:
        run_cli()

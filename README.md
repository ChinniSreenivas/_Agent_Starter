# 4-Agent GTM Strategy System — Production Real-Time Platform

A production-ready, event-driven multi-agent platform designed to continuously sense market demand, profile and qualify customer leads, generate hyper-personalized multi-channel outbound campaigns, and orchestrate master Go-To-Market (GTM) strategies in real-time environments.

Powered by **Google Gemini 2.5 Flash / Pro**, **FastAPI**, **Pydantic V2**, and an **event-driven Server-Sent Events (SSE) orchestrator**.

---

## 🏗️ Architecture

```
                              REAL-TIME EVENT INGESTION
               ┌───────────────────────┬───────────────────────────┐
               ▼                       ▼                           ▼
        [Live Market News /     [CRM Webhooks:              [SDR / Campaign
          Trends / Search]      HubSpot / Salesforce]       Feedback & Metrics]
               │                       │                           │
               ▼                       ▼                           │
      ┌─────────────────┐     ┌─────────────────┐                  │
      │ 1. DEMAND       │────▶│ 2. CUSTOMER     │                  │
      │    SENSING      │     │    PROFILING    │                  │
      │    AGENT        │     │    AGENT        │                  │
      └─────────────────┘     └─────────────────┘                  │
               │                       │                           │
               └───────────┬───────────┘                           │
                           ▼                                       ▼
                  ┌─────────────────┐                     ┌─────────────────┐
                  │ 3. OUTBOUND     │◀────────────────────│ 4. MANAGER      │
                  │    AGENT        │                     │    AGENT        │
                  └─────────────────┘                     └─────────────────┘
                           │                                       ▲
                           ▼                                       │
                  [HITL Approval Gateway] ─────────────────────────┘
                           │
                           ▼
                  [Real-Time Dispatch:
                  Email / LinkedIn / Slack]
```

### The 4 Specialized Production Agents:

1. **Demand Sensing Agent (`agents/demand_sensing.py`)**:
   - Ingests real-time market signals, search trends, competitive intelligence, and industry news.
   - Evaluates signal urgency, momentum, trajectory, and extracts high-conviction market opportunities and risk factors.

2. **Customer Profiling Agent (`agents/customer_profiling.py`)**:
   - Ingests inbound leads and CRM accounts in real time.
   - Computes multi-factor ICP fit scores (0-100) and segment tiers (High, Medium, Low, Disqualified) mapped against current demand signals.

3. **Outbound Agent (`agents/outbound.py`)**:
   - Crafts hyper-personalized multi-channel outreach sequences (Email, LinkedIn connection note <300 chars, InMail, and Cold Call talk tracks with objection rebuttals).
   - Enforces Human-In-The-Loop (HITL) review states (`pending_approval`) to ensure brand voice and compliance before dispatch.

4. **Manager Agent (`agents/manager.py`)**:
   - Synthesizes findings across all agents into an executive GTM strategy.
   - Formulates concrete validation hypotheses with test methods and KPIs, operational risk mitigations, and prioritized next actions (P0/P1/P2).

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone or navigate to the folder
cd gtm_4_agent_starter

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Add your Gemini API Key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
ENVIRONMENT=production
```
*(Note: If no API key is set, the system seamlessly uses intelligent heuristic fallback mode so you can test locally and run unit tests offline).*

---

## 💻 Running the Platform

### Option A: Real-Time Interactive Web Dashboard & Server

```bash
python app/main.py --server
# or
uvicorn app.main:app --reload --port 8000
```
- **Interactive Operations Dashboard**: Open [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: Open [http://localhost:8000/docs](http://localhost:8000/docs)

### Option B: Quick CLI Execution

```bash
python app/main.py
```
Executes the full pipeline, displays colorized structured agent readouts, and writes `final_gtm_strategy.json`.

---

## 📡 Real-Time Webhook & Streaming APIs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/gtm/run` | Triggers asynchronous 4-agent pipeline execution |
| `GET` | `/api/v1/gtm/stream` | Server-Sent Events (SSE) streaming real-time thoughts & outputs |
| `POST` | `/api/v1/signals/ingest` | Webhook to ingest external market signals / news in real-time |
| `POST` | `/api/v1/customers/ingest` | Webhook to ingest and score inbound CRM leads (HubSpot, Salesforce) |
| `POST` | `/api/v1/campaigns/{id}/approve` | HITL approval gateway for outbound campaigns |
| `GET` | `/api/v1/strategy/latest` | Retrieve the active GTM strategy document |
| `GET` | `/healthz` | Container healthcheck & readiness probe |

---

## 🧪 Testing

Run the comprehensive test suite (Pydantic schemas, asynchronous agents, orchestrator, and FastAPI endpoints):

```bash
pytest -v
```

---

## 🐳 Docker Deployment

Run with Docker Compose:

```bash
docker compose up --build -d
```
"# _Agent_Starter" 

# Chrimatos
### Autonomous Financial Due-Diligence Intelligence System

> From the Greek *χρήματα* — money, capital, wealth.

Chrimatos is a multi-agent AI pipeline that autonomously retrieves, analyzes, and synthesizes financial data for any US-listed equity into a structured due-diligence brief. A user inputs a stock ticker. The system dispatches specialized agents in an orchestrated sequence, each adding a distinct layer of intelligence, and returns a complete investment brief — with confidence scoring and full audit trail — in under 90 seconds.

---

## Current Build Status

| Component | Status |
|---|---|
| State Contract (state.py) | Complete |
| Cache Layer (cache.py) | Complete |
| Agent 1 — Financial Data Agent | Complete & Tested |
| Agent 2 — News & Sentiment Agent | In Progress |
| Agent 3 — Risk Analysis Agent | Pending |
| Agent 4 — Synthesis Agent | Pending |
| LangGraph Orchestrator | Pending |
| FastAPI Backend | Pending |
| Frontend | Pending |
| Deployment (Render) | Pending |

---

## Architecture

Chrimatos is built on a stateful multi-agent architecture using LangGraph. A shared typed state object flows through four specialized agents, each reading from and writing to its own namespace within that state. The orchestrator manages routing, validates completeness between agent steps, and handles failure escalation.

```
User Input (Ticker)
        │
        ▼
┌───────────────────┐
│    Orchestrator   │  ◄── LangGraph StateGraph
│  (State Machine)  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│     Agent 1       │  Financial Data Agent
│  Alpha Vantage    │  Retrieves: Revenue, Net Income, D/E Ratio,
│  Primary Source   │  PE Ratio, Cash Position, Market Cap,
│  + Cache Layer    │  Revenue Growth YoY
└────────┬──────────┘
         │ [data_complete check]
         ▼
┌───────────────────┐
│     Agent 2       │  News & Sentiment Agent
│  Google News RSS  │  Retrieves: Headlines → Gemini extraction →
│  + Gemini Flash   │  Sentiment Score, Key Events, Red Flags
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│     Agent 3       │  Risk Analysis Agent
│  Rule-Based +     │  Threshold checks + LLM reasoning →
│  Gemini Flash     │  Risk Score, Risk Factors, Risk Narrative
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│     Agent 4       │  Synthesis Agent
│  Gemini Flash     │  Produces structured brief with
│                   │  Confidence Score + Recommendation Label
└────────┬──────────┘
         │
         ▼
  Due-Diligence Brief
```

---

## Agent Responsibilities

**Agent 1 — Financial Data Agent**

Primary source is Alpha Vantage's OVERVIEW and INCOME_STATEMENT endpoints. Extracts seven financial fields with independent per-field error handling — a failure on one field does not abort extraction of others. Calculates revenue growth from the two most recent annual reports. Sets data_complete and adjusts confidence_score based on critical field availability. All API responses are cached locally for 24 hours to protect the 25-request daily free tier quota.

Verified test results across five edge cases: valid US equity (AAPL, TSLA), non-US ticker (RELIANCE.NS), delisted ticker (TWTR), and completely invalid string (ZZZINVALID). All five handled without unhandled exceptions.

**Agent 2 — News & Sentiment Agent** *(in progress)*

Source is Google News RSS — no API key required, no server-side blocking on deployment. Uses feedparser for XML parsing. Passes extracted headlines and summaries to Gemini 1.5 Flash in JSON mode for structured sentiment extraction. Returns sentiment score, key events, red flags, and a synthesis paragraph.

**Agent 3 — Risk Analysis Agent** *(pending)*

Combines deterministic threshold checks on financial metrics with a Gemini reasoning pass. Threshold checks are rule-based and produce no LLM calls — if debt-to-equity exceeds a defined threshold, that is a flagged risk regardless of model output. The LLM pass synthesizes patterns across multiple metrics into a risk narrative.

**Agent 4 — Synthesis Agent** *(pending)*

Takes all prior agent outputs and produces the final brief across six sections: Company Snapshot, Financial Health, Market Sentiment, Risk Assessment, Key Concerns, and Analyst Recommendation. Recommendation is one of four labels: Strong Buy Signal, Cautious Positive, Neutral, or Flag for Review. Includes a confidence score derived from the cumulative data completeness across all agents.

---

## State Contract

The shared state is a Python TypedDict — a typed, structured dictionary that all agents read from and write to. Each agent owns exactly one namespace within the state and writes only to that namespace. The orchestrator validates completeness between steps.

Key cross-cutting fields:

- **confidence_score** — float starting at 1.0, reduced by agents that encounter incomplete or unreliable data. Maximum reduction budgets are defined per agent to keep the final score interpretable.
- **errors** — list of strings. Every agent appends specific, descriptive failure messages here rather than raising exceptions. A pipeline with partial data is more useful than a crashed pipeline.

---

## Data Sources

| Source | Endpoint | Purpose | Limit |
|---|---|---|---|
| Alpha Vantage | OVERVIEW, INCOME_STATEMENT, GLOBAL_QUOTE | Financial fundamentals | 25 req/day (free) |
| Google News RSS | /rss/search | News & sentiment | No limit, no key |
| Gemini 1.5 Flash | /v1/messages | Structured extraction & synthesis | Free tier |

Alpha Vantage responses are cached locally for 24 hours per ticker per endpoint. Google News RSS results are fetched live on each pipeline run.

---

## Known Limitations

**US Equities Only** — Alpha Vantage's free tier does not reliably support non-US ticker symbols. Indian NSE/BSE tickers return empty responses. This is a deliberate scope decision for the current build. Expansion to international markets requires a paid Alpha Vantage tier or a supplementary data source with emerging market coverage.

**News Freshness** — Google News RSS has a median article age of approximately 6.6 days based on July 2026 sampling data. For a due-diligence tool this is acceptable signal. For a real-time trading system it would not be.

**Alpha Vantage Daily Quota** — 25 API requests per day on the free tier. The cache layer mitigates this during development by serving previously fetched responses for repeated ticker queries within the 24-hour TTL window.

**Gemini Structured Output Reliability** — Gemini 1.5 Flash occasionally produces malformed JSON despite JSON mode being enabled. All Gemini responses are validated against the expected schema before use. Failed validation triggers one retry with a stricter prompt before falling back to a degraded output state.

---

## Failure Handling Philosophy

Chrimatos treats every agent as a potentially unreliable component. The system is designed to produce a useful partial brief rather than crash when components fail. This means:

- Every external API call is wrapped in isolated try-except blocks
- Field-level failures append to the errors list without aborting the pipeline
- The confidence_score provides a quantified signal of output reliability
- The final brief explicitly flags sections where data was unavailable rather than omitting them silently

---

## What Gets Built Next

- Agent 2 completion and isolation testing
- Agent 3 risk threshold definition and LLM reasoning layer
- Agent 4 synthesis and recommendation label logic
- LangGraph orchestrator wiring all four agents with conditional routing
- FastAPI POST endpoint wrapping the full pipeline
- Single-page HTML frontend with loading state and brief rendering
- Render deployment with live public URL

---

## Tech Stack

- **Python 3.11**
- **LangGraph 0.2.x** — stateful multi-agent orchestration
- **Google Gemini 1.5 Flash** — structured extraction and synthesis
- **Alpha Vantage API** — financial fundamentals (primary)
- **Google News RSS + feedparser** — news retrieval
- **FastAPI + uvicorn** — API backend
- **python-dotenv** — environment configuration
- **httpx** — async HTTP client

---

## Project Structure

```
chrimatos/
├── agents/
│   ├── financial_agent.py     # Agent 1 — complete
│   ├── news_agent.py          # Agent 2 — in progress
│   ├── risk_agent.py          # Agent 3 — pending
│   └── synthesis_agent.py     # Agent 4 — pending
├── core/
│   ├── state.py               # Shared TypedDict state contract
│   ├── cache.py               # File-based API response cache
│   └── orchestrator.py        # LangGraph StateGraph — pending
├── api/
│   └── routes.py              # FastAPI endpoints — pending
├── frontend/
│   └── index.html             # Single-page UI — pending
├── cache/                     # Local cache storage (gitignored)
├── .env                       # API keys (gitignored)
├── .gitignore
├── requirements.txt
└── main.py
```

---

## Environment Variables

Three keys are required in your .env file:

```
GEMINI_API_KEY=your_gemini_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
NEWS_API_KEY=your_newsapi_key_here
```

The NEWS_API_KEY is retained in the environment configuration for potential future use. Current news retrieval uses Google News RSS and does not require it.

---

*Built as part of a 9-day intensive project targeting the intersection of agentic AI systems and financial intelligence engineering.*

# Chrimatos Financial Risk Analyser

### Enterprise Multi-Agent Due-Diligence & Quantitative Risk Pipeline

---

## 1. Project Overview

**Chrimatos** is an autonomous multi-agent AI pipeline that retrieves, analyzes, and synthesizes financial data for any US-listed equity into a structured due-diligence brief. A user inputs a stock ticker; the system dispatches four specialized agents in an orchestrated LangGraph sequence, each adding a distinct layer of intelligence, and returns a complete investment brief with confidence scoring and full audit trail.

### Core Capabilities

- **Hybrid Deterministic-AI Risk Analysis**: Pure Python threshold rules for scoring + LLM for narrative synthesis
- **4-Agent LangGraph Orchestration**: Sequential DAG with typed state passing and error accumulation
- **Fast Warm-Cache Execution**: 24-hour TTL file cache eliminates repeated Alpha Vantage calls (cold analyses take ~30-60s across 3 AV calls, RSS, and 3 LLM calls)
- **Fallback Resilience**: Finnhub fallback on rate limits, RSS retries with Finnhub company-news fallback, degraded LLM responses with deterministic overrides, graceful confidence docking
- **Audit Trail**: Append-only error log, confidence scoring (1.0 → 0.0), full pipeline traceability
- **Alpha Vantage Rate Limit Handling**: Token bucket rate limiter (5 req/min via `core/rate_limiter.py`); cache prevents repeated hits
- **Complete Debt-to-Equity Calculation**: Derived from BALANCE_SHEET (shortTermDebt + longTermDebt) / totalShareholderEquity since OVERVIEW omits it
- **Company Search Autocomplete**: Ticker/company-name search (`GET /api/v1/search/{query}`, Finnhub-first) with free-tier US-only gating and graceful partial-metrics UI
- **React SPA Frontend**: Served by FastAPI from `static/`; autocomplete dropdown, risk gauge, sentiment, synthesis tabs, raw-data debug view



### What It Can Do

- Fetch real-time fundamentals (revenue, P/E, D/E, YoY growth, current ratio, market cap, cash position) from Alpha Vantage
- Retrieve and parse 30-day Google News RSS with UTC-safe date filtering
- Extract structured sentiment (score, key events, red flags, summary) via Gemini Flash
- Compute deterministic risk scores from 5 financial rules (leverage, equity, growth, profitability, sentiment)
- Generate 6-section investment brief with programmatic recommendation labels
- Operate in mock mode for CI/CD and development without API keys (mock Finnhub data is complete, including revenue growth)
- **Finnhub fallback** when Alpha Vantage rate limits hit; `USE_FINNHUB_ONLY=true` skips Alpha Vantage entirely
- Search companies by name with autocomplete; non-US listings are grayed out (Finnhub free tier covers US only)



### What It Cannot Do

- **Non-US equities on the free tier**: Finnhub free tier 403s international tickers (grayed out in search; manual entry blocked with an explanatory error)
- **Real-time trading signals**: News median age ~6.6 days; not suitable for HFT
- **Guaranteed LLM availability**: Free tier 1,500 req/day; quota exhaustion degrades to deterministic-only output
- **Historical backtesting**: Single-point analysis; no time-series portfolio simulation
- **Options/derivatives data**: Equity fundamentals only

---



## 2. Architecture & Multi-Agent Execution Flow



### LangGraph DAG Diagram

```
[Client Request: POST /api/v1/analyze/{ticker}]
                    │
                    ▼
         ┌────────────────────┐
         │  init_state()      │  Factory: SystemState with defaults
         │  confidence=1.0    │
         └─────────┬──────────┘
                   │
                   ▼
          ┌────────────────────┐
          │  Financial Node    │  Agent 1: Alpha Vantage (3 calls)
          │  (Alpha Vantage)   │  OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET
          │  + Finnhub fallback│  clean_float(), D/E normalization
          │  data_available    │  Entity resolution → company_name
          └─────────┬──────────┘
                   │ (writes: financial_data, company_name, confidence, errors)
                   ▼
         ┌────────────────────┐
         │  News Node         │  Agent 2: Google News RSS
         │  (Google News RSS) │  feedparser + UTC date filter (30d)
         │  + Gemini Flash    │  Top 10 → JSON schema extraction
         │  sentiment ∈ [-1,1]│  Validation + 1 retry
         └─────────┬──────────┘
                   │ (writes: news_data, confidence, errors)
                   ▼
         ┌────────────────────┐
         │  Risk Node         │  Agent 3: Pure Python Rules + LLM
         │  (Deterministic)   │  5 threshold checks → risk_score (0-100)
         │  + LLM Narrative   │  risk_factors list, risk_narrative
         └─────────┬──────────┘
                   │ (writes: risk_data, errors)
                   ▼
         ┌────────────────────┐
         │  Synthesis Node    │  Agent 4: Deterministic Labels + LLM
         │  (Recommendation)  │  Python: confidence/risk/growth → label
         │  + Brief Gen       │  LLM: 6 sections, label overridden
         │  SynthesisBrief    │  6 keys + analyst_recommendation
         └─────────┬──────────┘
                   │
                   ▼
         [Unified Brief: SystemState]
```



### Agent Breakdown


| Agent         | Primary Source                                            | Key Outputs                                                                                                                                          | Fallback Behavior                                                                                                                                               |
| ------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Financial** | Alpha Vantage (OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET) | 11 fields: revenue, net_income, pe_ratio, debt_to_equity, yoy_revenue_growth, current_ratio, market_cap, cash_position, data_available, company_name | **Finnhub** (free tier) on 429/timeout; `data_available=False`, confidence -0.4. **Debt-to-Equity calculated from BALANCE_SHEET** (OVERVIEW doesn't provide it) |
| **News**      | Google News RSS + Gemini Flash                            | sentiment_score (-1.0 to 1.0), key_events[], red_flags[], summary, news_available                                                                    | 3 RSS attempts w/ backoff, then Finnhub company-news fallback; `sentiment_score=0.0`, `news_available=False`, confidence -0.1                                  |
| **Risk**      | Python Rules + Gemini Flash                               | risk_score (0-100), risk_factors[], risk_narrative                                                                                                   | Keeps Python-calculated score, narrative="unavailable"                                                                                                          |
| **Synthesis** | Deterministic Python + Gemini Flash                       | SynthesisBrief (6 sections), analyst_recommendation                                                                                                  | Fallback brief with deterministic label                                                                                                                         |


---



## 3. Tech Stack & Dependencies


| Category              | Technologies                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| **Core Frameworks**   | Python 3.11+ (deploy), LangGraph 1.x, FastAPI, Pydantic v2, httpx                                  |
| **AI Models**         | Google Gemini (`GEMINI_MODEL`, default `gemini-3.5-flash-lite`) via `google-genai` SDK             |
| **External APIs**     | Alpha Vantage (25/day, 5/min free), Finnhub (free tier: US listings only), Google News RSS         |
| **Testing & Quality** | Pytest 9.x, unittest.mock, 131 tests (100% pass), `tsc --noEmit` frontend typecheck                |
| **Infrastructure**    | File-based cache (24hr TTL, atomic writes, hit/miss debug logs), accumulating error reducer        |
| **Frontend**          | React 18 + Vite + TypeScript, served from `static/` (rebuilt via `frontend/dist`)                  |




### Key Dependencies (`pyproject.toml`)

```toml
dependencies = [
    "fastapi>=0.139.0",
    "feedparser>=6.0.13",
    "finnhub-python>=2.4.29",
    "google-genai>=2.14.0",
    "httpx>=0.28.1",
    "langgraph>=1.2.7",
    "pydantic>=2.13.4",
    "pydantic-settings>=2.15.0",
    "python-dotenv>=1.2.2",
    "uvicorn[standard]>=0.49.0",
    "gunicorn>=26.2.0",
]
# Single source of truth is pyproject.toml (+ uv.lock); requirements.txt mirrors it for Render.
```

---



## 4. Project Structure

```
financial-risk-analyser/
├── agents/
│   ├── financial_agent.py      # Agent 1: Alpha Vantage + Finnhub
│   ├── news_agent.py           # Agent 2: RSS (+retries/Finnhub fallback) + Gemini sentiment
│   ├── risk_agent.py           # Agent 3: Deterministic rules + LLM narrative
│   ├── synthesis_agent.py      # Agent 4: Labels + 6-section brief
│   └── mock_data.py            # Mock AV/Finnhub/search payloads (mock & test modes)
├── core/
│   ├── state.py                # SystemState, TypedDict contracts, init_state()
│   ├── cache.py                # File cache (24hr TTL, atomic writes, locking, debug logs)
│   ├── config.py               # Pydantic Settings (env-driven, reads .env)
│   ├── clients.py              # Lazy singleton clients (httpx, Gemini, Finnhub)
│   ├── resolver.py             # Company-name → ticker search + free-tier gating
│   └── orchestrator.py         # LangGraph StateGraph pipeline (parallel + sequential)
├── api/
│   └── routes.py               # FastAPI endpoints (/analyze, /search, /health)
├── frontend/                   # React 18 + Vite + TS SPA (autocomplete, gauge, tabs)
│   └── dist/                   # Production build (gitignored; copy to static/ to serve)
├── static/                     # Served bundle (build artifact, gitignored; see below)
├── tests/                      # Tracked test suite (conftest.py enables mock mode)
│   ├── test_financial_agent.py      # 20 tests
│   ├── test_news_agent.py           # 33 tests
│   ├── test_risk_agent.py           # 14 tests
│   ├── test_synthesis_agent.py      # 6 tests
│   ├── test_company_search.py       # 34 tests
│   └── test_pipeline_integration.py # 15 tests
├── cache/                       # Local cache (gitignored)
├── conftest.py                  # Session fixture: mock mode + _TEST_MODE_OVERRIDE
├── .env                         # API keys (gitignored; see .env.example)
├── .env.example                 # Documented template for all settings
├── Dockerfile                   # Multi-stage build (node → uv/python → runtime)
├── render.yaml                  # Render deploy (pip + frontend build + static sync)
├── requirements.txt             # Mirrors pyproject.toml for Render
├── pyproject.toml + uv.lock     # Single source of truth for Python deps
├── pytest.ini
├── main.py                      # FastAPI app entry (serves API + static/)
└── README.md
```

---



## 5. System Setup & Installation



### Prerequisites

- Python 3.11+
- Virtual environment recommended
- API keys for Alpha Vantage and Gemini



### Environment Variables (`.env` — see `.env.example` for the full template)

```bash
# API keys (GEMINI_API_KEY plus at least one of ALPHA_VANTAGE_KEY / FINNHUB_API_KEY)
GEMINI_API_KEY=your_gemini_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here

# Modes
GEMINI_MODEL=gemini-3.5-flash-lite
USE_MOCK_DATA=true       # mock mode: no API calls (startup validation skipped)
USE_FINNHUB_ONLY=true    # skip Alpha Vantage entirely, use Finnhub only
TESTING=true             # test harness escape hatch (like USE_MOCK_DATA)

# Tuning (defaults shown)
AV_MAX_RETRIES=3
AV_RETRY_BASE_DELAY=12
NEWS_LOOKBACK_DAYS=30
MAX_NEWS_ARTICLES=10
HOSTILE_NEWS_THRESHOLD=-0.4

# Server
PORT=8000
CORS_ORIGINS=*
ENABLE_DOCS=true
```

> Startup calls `validate_config()`, which reads these via pydantic-settings
> (`.env`-aware) and fails fast if keys are missing outside mock/test mode.



### Installation

```bash
# Clone and enter
cd financial-risk-analyser

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies (pyproject.toml is the source of truth)
pip install -e .
# ...or with uv:  uv sync
# ...or plain pip: pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

> Local dev uses Python 3.14 (`.python-version`); Docker and Render deploy on
> Python 3.11. Keep changes 3.11-compatible.

---



## 6. API Documentation & Endpoints



### Startup

```bash
# Development (mock mode - no API calls)
USE_MOCK_DATA=true python -m uvicorn main:app --reload --port 8000

# Production (real API calls)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
# ...or: python main.py  (reads PORT, defaults 8000)
```



### Endpoints


| Method | Endpoint                   | Description                                              |
| ------ | -------------------------- | -------------------------------------------------------- |
| GET    | `/`                        | React SPA (if `static/` built) else API info JSON        |
| GET    | `/health`, `/health/live`, `/health/ready` | Container liveness/readiness probes           |
| GET    | `/api/v1/health`           | API health check                                         |
| GET    | `/api/v1/search/{query}`   | Company-name → ranked ticker candidates with `freeTierSupported` flag (autocomplete) |
| POST   | `/api/v1/analyze/{ticker}` | Execute full 4-agent pipeline                            |
| GET    | `/api/v1/analyze/{ticker}` | Convenience GET (browser testing)                        |
| GET    | `/docs`                    | Swagger UI (disable in prod via `ENABLE_DOCS=false`)     |



### Frontend (React SPA)

```bash
# Dev with hot reload (proxies /api to localhost:8000)
cd frontend && npm run dev        # → http://localhost:3000

# Typecheck + production build (heap flag required - plotly bundle is huge)
cd frontend && npm run build      # runs tsc --noEmit && vite build
NODE_OPTIONS="--max-old-space-size=4096" npm run build

# Serve the fresh bundle from FastAPI (main.py serves static/)
rm -rf static/* && cp -r frontend/dist/* static/
```

Features: ticker/company-name search box with autocomplete dropdown (non-US
listings grayed out with `freeTierSupported: false`), financial metrics with
graceful partial display (`N/A` per missing field), custom SVG risk gauge,
news sentiment with per-article coverage list, 6-section synthesis brief,
pipeline trace (per-agent timings), raw-data debug tab.

UI identity is a financial research terminal: ink-on-paper neutrals, IBM Plex
Sans/Mono, metric ledger with group verdicts, rule list with stable IDs
(`R-01`…`R-05`) and plain-English explanations, verdict-first hero with a
plain-language one-liner. Color is disciplined: the risk ramp carries status,
directional green/red marks signed figures, and one interactive blue
(`--interactive`) marks links/active tab only. Dark mode follows the OS setting
by default with a header toggle (persisted in `localStorage`); print output
always renders light. Analyst depth (ledger, trace, raw JSON) and
normal-user guidance (verdicts, explanations, humanized empty states) come
from the same data — see `Chrimatos UI Design Document.md`.

New API fields (all additive, backward compatible): per-agent `timings`
(`financial`, `news`, `risk`, `synthesis` seconds), `risk_details`
(`{id, label, explanation}`), `news.articles` (`{title, summary, url, source}`).

### Deploy notes (Render / Docker)

- **Cold start is slow**: the container cache starts empty, so the first analysis after a deploy burns the 5/min Alpha Vantage quota (~1 min). Later requests are instant (24h cache).
- **Workers share nothing**: gunicorn runs 2 workers with per-process rate limiters — effective quota is ~2x a single process. Fine for solo use; add shared limiting before multi-user use.
- **Python**: deploys target 3.11 (`render.yaml`, `Dockerfile`); local dev uses 3.14 (`.python-version`). Keep code 3.11-compatible.
- **UI bundle**: `static/` is a build artifact, regenerated at deploy time (`frontend/dist` → `static/`). Never debug UI issues against a stale bundle — rebuild + sync + hard-refresh.
- **Timeouts**: gunicorn `--timeout 180` covers worst-case cold + throttled runs (AV backoffs 12s+24s+48s, RSS retries, 3 LLM calls).
- **Logging**: `httpx`/`httpcore`/`google_genai.models` loggers are capped at WARNING (httpx INFO logs full URLs including `apikey=...`), and `/health` probes are skipped in the request log. Debug cache activity with `--log-level debug`.




### Sample Request

```bash
# Primary endpoint (POST)
curl -X POST http://localhost:8000/api/v1/analyze/AAPL

# Browser-friendly GET
curl http://localhost:8000/api/v1/analyze/TSLA
```



### Sample Response (truncated)

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "confidence_score": 0.55,
  "errors": [],
  "financial_data": {
    "data_available": true,
    "debt_to_equity": 1.57,
    "pe_ratio": 35.48,
    "yoy_revenue_growth": 0.184,
    "current_ratio": 1.25,
    "market_cap": 4514709504000,
    "revenue": 466822988000,
    "net_income": 112010000000,
    "cash_position": 35934000000
  },
  "news_data": {
    "news_available": true,
    "sentiment_score": 0.35,
    "key_events": ["Strong iPhone 16 pre-orders"],
    "red_flags": ["China demand concerns"],
    "summary": "Apple shows resilient demand..."
  },
  "risk_data": {
    "risk_score": 15.0,
    "risk_factors": [],
    "risk_narrative": "Apple maintains a robust balance sheet..."
  },
  "synthesis_report": {
    "company_snapshot": "Apple Inc. is a global technology leader...",
    "financial_health": "Solid revenue growth and strong margins...",
    "market_sentiment": "Positive coverage around product launches...",
    "risk_assessment": "Low risk score with no flagged thresholds...",
    "key_concerns": ["China exposure", "Regulatory scrutiny"],
    "analyst_recommendation": "Cautious Positive"
  }
}
```

---



## 7. Error Handling & Resilience Matrix



### Degraded State Handling


| Failure Scenario             | Detection                              | Fallback                                            | Confidence Dock                         |
| ---------------------------- | -------------------------------------- | --------------------------------------------------- | --------------------------------------- |
| Alpha Vantage 429/timeout    | HTTP 429, timeout (3 tries + backoff)  | Finnhub (free tier, US only)                        | -0.2 on throttle, -0.4 on total failure |
| Alpha Vantage invalid ticker | "Information" in response              | None                                                | -0.4, `data_available=False`            |
| Alpha Vantage missing fields | `clean_float()` returns None           | Field = None (UI shows `N/A`)                       | -0.05 per secondary field               |
| Finnhub 403 (non-US / limits)| HTTP 403                               | Empty result, graceful degradation                  | via missing fields                      |
| News RSS timeout/empty       | httpx timeout, no entries (3 attempts) | Finnhub company-news, else `news_available=False`   | -0.1                                    |
| Gemini 429 quota exhausted   | HTTP 429                               | Deterministic-only output                           | via degraded outputs                    |
| Gemini 404 model not found   | HTTP 404                               | Deterministic-only output                           | via degraded outputs                    |
| Gemini malformed JSON        | Schema validation fail                 | 1 retry with stricter prompt, then fallback         | via degraded outputs                    |
| Risk LLM failure             | Exception caught                       | Keeps Python-calculated score, narrative="..."      | None (score is deterministic)           |
| Synthesis LLM failure        | Exception caught                       | Fallback brief + deterministic label                | None (passes confidence through)        |




### Confidence Score Docking Behavior

```
Base: 1.0
├── Financial Agent
│   ├── Alpha Vantage throttle (429)          → -0.2
│   ├── Total failure (all sources)           → -0.4
│   ├── Missing debt_to_equity                → -0.05
│   └── Missing cash_position                 → -0.05
├── News Agent
│   ├── No company_name/ticker                → -0.1
│   ├── No articles in 30 days (RSS + Finnhub)→ -0.1
│   ├── RSS network failure (after retries)   → -0.1
│   └── Hostile sentiment (< -0.4)            → -0.1
└── Risk / Synthesis Agents
    └── Pass confidence through unchanged (no docks)

Minimum: 0.0 (clamped)
```



### Example: AAPL with Gemini Quota Exhausted

```json
{
  "confidence_score": 0.55,
  "errors": [
    "Gemini sentiment primary attempt failed: 429 RESOURCE_EXHAUSTED...",
    "News sentiment validation failed completely. Degraded state recorded.",
    "Risk Agent execution failed: 429 RESOURCE_EXHAUSTED...",
    "Synthesis Agent execution failed: 429 RESOURCE_EXHAUSTED..."
  ],
  "financial_data": { "data_available": true, ... },
  "news_data": { "news_available": false, "sentiment_score": 0.0, ... },
  "risk_data": { "risk_score": 0.0, "risk_narrative": "Narrative unavailable..." },
  "synthesis_report": { "analyst_recommendation": "Neutral", ... }
}
```

---



## 8. Testing Suite



### Run Tests

```bash
# All tests (131 tests; integration hits live APIs, ~2 min)
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_financial_agent.py -v     # 20 tests
python -m pytest tests/test_news_agent.py -v          # 33 tests
python -m pytest tests/test_risk_agent.py -v          # 14 tests
python -m pytest tests/test_synthesis_agent.py -v     # 6 tests
python -m pytest tests/test_company_search.py -v      # 34 tests
python -m pytest tests/test_pipeline_integration.py -v # 15 tests

# Frontend typecheck (also runs as part of npm run build)
cd frontend && npm run typecheck
```



### Test Coverage Summary


| Test Suite                     | Tests | Coverage Focus                                                                                   |
| ------------------------------ | ----- | ------------------------------------------------------------------------------------------------ |
| `test_financial_agent.py`      | 20    | Cache, fallback, edge cases (invalid/delisted/non-US), field normalization, Finnhub-only paths   |
| `test_news_agent.py`           | 36    | RSS parsing, retries, Finnhub fallback, article shaping, UTC dates, schema validation, hostile sentiment |
| `test_risk_agent.py`           | 17    | Deterministic rules (boundaries, None-safety), LLM narrative, score-preserving fallback, rule IDs |
| `test_synthesis_agent.py`      | 6     | Label logic (boundaries), programmatic override, malformed JSON fallback                         |
| `test_company_search.py`       | 34    | Ranking, free-tier gating, cache self-heal, normalizers, `/search` endpoint validation          |
| `test_pipeline_integration.py` | 18    | E2E pipeline, recommendation logic, error accumulation without duplicates, timing channels, state preservation |


**Total: 131 tests, 100% pass rate**

> `conftest.py` enables mock mode session-wide (`USE_MOCK_DATA` + `_TEST_MODE_OVERRIDE`),
> but `test_pipeline_integration.py` still exercises live Gemini/RSS calls (~2 min).

### Key Test Scenarios

- Boundary conditions: confidence=0.5, risk=70.0, growth=0.05, D/E=2.5
- Missing data: `yoy_revenue_growth=None`, negative growth blocks Strong Buy
- Error accumulation: agents return only new errors; the LangGraph reducer accumulates; no duplicates
- LLM override: synthesis `analyst_recommendation` is always the deterministic label
- Cache behavior: hit/miss/expiry, rate-limit rejection, corruption handling (debug logs via `--log-level debug`)

---



## 9. Alpha Vantage Rate Limit Handling



### Free Tier Constraints

- **25 requests/day** total
- **5 requests/minute** burst limit
- 3 calls per analysis (OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET) = ~8 analyses/day max



### Implemented Solutions

1. **Token Bucket Rate Limiter**: Enforces 5 req/min via `core/rate_limiter.py` (token bucket with 12s interval)
2. **Exponential Backoff Retries**: 3 attempts with 12s, 24s, 48s delays before falling back
3. **24-Hour File Cache**: Successful responses cached; subsequent analyses use cached data (sub-second)
4. **Test Mode Bypass**: Delays skipped when `_TEST_MODE_OVERRIDE=True` or `USE_MOCK_DATA=true` (unit suites run in seconds; live-API integration takes ~2 min)
5. **Cache Rejects Errors**: Rate-limit responses (`{"Note": "..."}`) not cached to avoid poisoning cache; hit/miss/expiry visible with `--log-level debug`
6. **Cache Self-Heal**: `SEARCH` payloads are schema-validated on read; entries written before `freeTierSupported` existed are treated as misses and refetched



### Behavior


| Scenario           | Behavior                                           |
| ------------------ | -------------------------------------------------- |
| Warm cache (≤24hr) | Sub-second, no API calls                           |
| Cold cache         | ~3.5s total (rate limited), all 3 endpoints cached |
| Rate limited       | Falls back to Finnhub; confidence docked -0.2/-0.4 |


---



## 10. Debt-to-Equity Calculation

**Alpha Vantage OVERVIEW endpoint does not return** `DebtToEquity`**.** The pipeline calculates it from BALANCE_SHEET:

```
Debt-to-Equity = (shortTermDebt + longTermDebt) / totalShareholderEquity
```

- Uses `shortTermDebt` + `longTermDebt` (or `longTermDebtNoncurrent` fallback)
- Falls back to `shortTermDebt / equity` if long-term debt unavailable
- Normalized by `normalize_debt_to_equity()` to handle percentage vs ratio formats

**Finnhub Fallback**: When Alpha Vantage is rate-limited, Finnhub's `totalDebt/totalEquityAnnual` (or `totalDebt/totalEquityQuarterly`, `debtToEquity`, etc.) is used with multiple key fallbacks.

---



## 11. License

### License

MIT License — see `LICENSE` file for details.
# Chrimatos Financial Risk Analyser
### Enterprise Multi-Agent Due-Diligence & Quantitative Risk Pipeline

---

## 1. Project Overview

**Chrimatos** is an autonomous multi-agent AI pipeline that retrieves, analyzes, and synthesizes financial data for any US-listed equity into a structured due-diligence brief. A user inputs a stock ticker; the system dispatches four specialized agents in an orchestrated LangGraph sequence, each adding a distinct layer of intelligence, and returns a complete investment brief with confidence scoring and full audit trail.

### Core Capabilities
- **Hybrid Deterministic-AI Risk Analysis**: Pure Python threshold rules for scoring + LLM for narrative synthesis
- **4-Agent LangGraph Orchestration**: Sequential DAG with typed state passing and error accumulation
- **Sub-Second Execution** (with cache): 24-hour TTL file cache eliminates repeated Alpha Vantage calls
- **Fallback Resilience**: yfinance fallback on rate limits, degraded LLM responses with deterministic overrides, graceful confidence docking
- **Audit Trail**: Append-only error log, confidence scoring (1.0 → 0.0), full pipeline traceability
- **Alpha Vantage Rate Limit Handling**: 1.5s delays between calls respect 5 req/min free tier; cache prevents repeated hits
- **Complete Debt-to-Equity Calculation**: Derived from BALANCE_SHEET (shortTermDebt + longTermDebt) / totalShareholderEquity since OVERVIEW omits it

### What It Can Do
- Fetch real-time fundamentals (revenue, P/E, D/E, YoY growth, current ratio, market cap, cash position) from Alpha Vantage
- Retrieve and parse 30-day Google News RSS with UTC-safe date filtering
- Extract structured sentiment (score, key events, red flags, summary) via Gemini Flash
- Compute deterministic risk scores from 5 financial rules (leverage, equity, growth, profitability, sentiment)
- Generate 6-section investment brief with programmatic recommendation labels
- Operate in mock mode for CI/CD and development without API keys

### What It Cannot Do
- **Non-US equities**: Alpha Vantage free tier unreliable for international tickers
- **Real-time trading signals**: News median age ~6.6 days; not suitable for HFT
- **Guaranteed LLM availability**: Free tier 1,500 req/day; quota exhaustion degrades to deterministic-only output
- **Frontend/UI**: API-only backend; no dashboard or visualization layer
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
         │  + yfinance fallback│  clean_float(), D/E normalization
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

| Agent | Primary Source | Key Outputs | Fallback Behavior |
|-------|---------------|-------------|-------------------|
| **Financial** | Alpha Vantage (OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET) | 11 fields: revenue, net_income, pe_ratio, debt_to_equity, yoy_revenue_growth, current_ratio, market_cap, cash_position, data_available, company_name | yfinance (3s timeout) on 429/timeout; `data_available=False`, confidence -0.4. **Debt-to-Equity calculated from BALANCE_SHEET** (OVERVIEW doesn't provide it) |
| **News** | Google News RSS + Gemini Flash | sentiment_score (-1.0 to 1.0), key_events[], red_flags[], summary, news_available | `sentiment_score=0.0`, `news_available=False`, confidence -0.1 |
| **Risk** | Python Rules + Gemini Flash | risk_score (0-100), risk_factors[], risk_narrative | `risk_score=50.0`, narrative="unavailable" |
| **Synthesis** | Deterministic Python + Gemini Flash | SynthesisBrief (6 sections), analyst_recommendation | Fallback brief with deterministic label |

---

## 3. Tech Stack & Dependencies

| Category | Technologies |
|--------|--------------|
| **Core Frameworks** | Python 3.11+, LangGraph 1.x, FastAPI, Pydantic v2, httpx |
| **AI Models** | Google Gemini 2.5 Flash (`gemini-2.5-flash` or `gemini-flash-latest`) via `google-genai` SDK |
| **External APIs** | Alpha Vantage (25/day free), yfinance (fallback), Google News RSS (unlimited) |
| **Testing & Quality** | Pytest 9.x, unittest.mock, 79 tests (100% pass) |
| **Infrastructure** | File-based cache (24hr TTL, atomic writes), append-only error reducer |

### Key Dependencies (`pyproject.toml`)
```toml
dependencies = [
    "langgraph>=1.2.7",
    "fastapi>=0.139.0",
    "google-genai>=2.14.0",
    "httpx>=0.28.1",
    "yfinance==0.2.40",
    "feedparser>=6.0.13",
    "pydantic>=2.13.4",
    "pydantic-settings>=2.15.0",
    "pytest>=9.1.1",
]
```

---

## 4. Project Structure

```
financial-risk-analyser/
├── agents/
│   ├── financial_agent.py      # Agent 1: Alpha Vantage + yfinance
│   ├── news_agent.py           # Agent 2: RSS + Gemini sentiment
│   ├── risk_agent.py           # Agent 3: Deterministic rules + LLM narrative
│   └── synthesis_agent.py      # Agent 4: Labels + 6-section brief
├── core/
│   ├── state.py                # SystemState, TypedDict contracts, init_state()
│   ├── cache.py                # File cache (24hr TTL, atomic writes, locking)
│   ├── config.py               # Pydantic Settings (env-driven)
│   ├── clients.py              # Singleton clients (httpx, Gemini)
│   └── orchestrator.py         # LangGraph StateGraph pipeline
├── api/
│   └── routes.py               # FastAPI endpoints (/analyze, /health)
├── tests/
│   ├── test_financial_agent.py      # 18 tests
│   ├── test_news_agent.py           # 27 tests
│   ├── test_risk_agent.py           # 14 tests
│   ├── test_synthesis_agent.py      # 6 tests
│   └── test_pipeline_integration.py # 14 tests
├── cache/                       # Local cache (gitignored)
├── .env                         # API keys (gitignored)
├── .gitignore
├── pyproject.toml
├── pytest.ini
├── main.py                      # FastAPI app entry
└── README.md
```

---

## 5. System Setup & Installation

### Prerequisites
- Python 3.11+
- Virtual environment recommended
- API keys for Alpha Vantage and Gemini

### Environment Variables (`.env`)
```bash
# Required
GEMINI_API_KEY=your_gemini_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here

# Optional
GEMINI_MODEL=gemini-2.5-flash          # or gemini-flash-latest
USE_MOCK_DATA=true                      # enables mock mode (no API calls)
```

### Installation
```bash
# Clone and enter
cd financial-risk-analyser

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .

# Or with pip directly
pip install -r requirements.txt  # if requirements.txt exists
```

---

## 6. API Documentation & Endpoints

### Startup
```bash
# Development (mock mode - no API calls)
USE_MOCK_DATA=true python -m uvicorn main:app --reload --port 8000

# Production (real API calls)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Container health probe |
| GET | `/api/v1/health` | API health check |
| POST | `/api/v1/analyze/{ticker}` | Execute full 4-agent pipeline |
| GET | `/api/v1/analyze/{ticker}` | Convenience GET (browser testing) |
| GET | `/docs` | Swagger UI |

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

| Failure Scenario | Detection | Fallback | Confidence Dock |
|------------------|-----------|----------|-----------------|
| Alpha Vantage 429/timeout | HTTP 429, timeout | yfinance (3s) | -0.2 on throttle, -0.4 on total failure |
| Alpha Vantage invalid ticker | "Information" in response | None | -0.4, `data_available=False` |
| Alpha Vantage missing fields | `clean_float()` returns None | Field = None | -0.05 per secondary field |
| News RSS timeout/empty | requests timeout, no entries | `news_available=False` | -0.1 |
| Gemini 429 quota exhausted | HTTP 429 | Deterministic-only output | -0.1 per agent |
| Gemini 404 model not found | HTTP 404 | Deterministic-only output | -0.1 per agent |
| Gemini malformed JSON | Schema validation fail | 1 retry with stricter prompt | -0.1 on retry |
| Risk LLM failure | Exception caught | `risk_score=50.0` | None (risk is deterministic) |
| Synthesis LLM failure | Exception caught | Fallback brief + deterministic label | None |

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
│   ├── No articles in 30 days                → -0.1
│   ├── RSS network failure                   → -0.1
│   ├── LLM validation failed (after retry)   → -0.1
│   └── Hostile sentiment (< -0.4)            → -0.1
└── Synthesis Agent
    ├── Financial incomplete                  → -0.2
    ├── News unavailable                      → -0.1
    └── Risk narrative missing                → -0.1

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
  "risk_data": { "risk_score": 50.0, "risk_narrative": "Narrative unavailable..." },
  "synthesis_report": { "analyst_recommendation": "Neutral", ... }
}
```

---

## 8. Testing Suite

### Run Tests
```bash
# All tests (79 tests)
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_financial_agent.py -v     # 18 tests
python -m pytest tests/test_news_agent.py -v          # 27 tests
python -m pytest tests/test_risk_agent.py -v          # 14 tests
python -m pytest tests/test_synthesis_agent.py -v     # 6 tests
python -m pytest tests/test_pipeline_integration.py -v # 14 tests
```

### Test Coverage Summary

| Test Suite | Tests | Coverage Focus |
|------------|-------|----------------|
| `test_financial_agent.py` | 18 | Cache, fallback, edge cases (invalid/delisted/non-US), field normalization |
| `test_news_agent.py` | 27 | RSS parsing, UTC dates, schema validation, retry, hostile sentiment, error accumulation |
| `test_risk_agent.py` | 14 | Deterministic rules (boundaries, None-safety), LLM narrative, fallback |
| `test_synthesis_agent.py` | 6 | Label logic (boundaries), programmatic override, malformed JSON fallback |
| `test_pipeline_integration.py` | 14 | E2E mock pipeline, recommendation logic, state preservation |

**Total: 79 tests, 100% pass rate**

### Key Test Scenarios
- Boundary conditions: confidence=0.5, risk=70.0, growth=0.05, D/E=2.5
- Missing data: `yoy_revenue_growth=None`, negative growth blocks Strong Buy
- Error accumulation: prior errors preserved through pipeline
- LLM hallucination override: "MUST BUY IMMEDIATELY!!!" → corrected to deterministic label
- Cache behavior: hit/miss, rate-limit rejection, corruption handling

---

## 9. Alpha Vantage Rate Limit Handling

### Free Tier Constraints
- **25 requests/day** total
- **5 requests/minute** burst limit
- 3 calls per analysis (OVERVIEW, INCOME_STATEMENT, BALANCE_SHEET) = ~8 analyses/day max

### Implemented Solutions

1. **Automatic 1.5s Delays**: Between sequential API calls in `financial_agent.py` to respect 5 req/min limit
2. **24-Hour File Cache**: Successful responses cached; subsequent analyses use cached data (sub-second)
3. **Test Mode Bypass**: Delays skipped when `_TEST_MODE_OVERRIDE=True` for fast CI/CD (tests complete in ~1s)
4. **Cache Rejects Errors**: Rate-limit responses (`{"Note": "..."}`) not cached to avoid poisoning cache

### Behavior
| Scenario | Behavior |
|----------|----------|
| Warm cache (≤24hr) | Sub-second, no API calls |
| Cold cache | ~3.5s total (1.5s + 1.5s delays), all 3 endpoints cached |
| Rate limited | Falls back to yfinance; confidence docked -0.2/-0.4 |

---

## 10. Debt-to-Equity Calculation

**Alpha Vantage OVERVIEW endpoint does not return `DebtToEquity`.** The pipeline calculates it from BALANCE_SHEET:

```
Debt-to-Equity = (shortTermDebt + longTermDebt) / totalShareholderEquity
```

- Uses `shortTermDebt` + `longTermDebt` (or `longTermDebtNoncurrent` fallback)
- Falls back to `shortTermDebt / equity` if long-term debt unavailable
- Normalized by `normalize_debt_to_equity()` to handle percentage vs ratio formats

---

## 12. Testing Suite

### Run Tests
```bash
# All tests (79 tests)
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_financial_agent.py -v     # 18 tests
python -m pytest tests/test_news_agent.py -v          # 27 tests
python -m pytest tests/test_risk_agent.py -v          # 14 tests
python -m pytest tests/test_synthesis_agent.py -v     # 6 tests
python -m pytest tests/test_pipeline_integration.py -v # 14 tests
```

### Test Coverage Summary

| Test Suite | Tests | Coverage Focus |
|------------|-------|----------------|
| `test_financial_agent.py` | 18 | Cache, fallback, edge cases (invalid/delisted/non-US), field normalization |
| `test_news_agent.py` | 27 | RSS parsing, UTC dates, schema validation, retry, hostile sentiment, error accumulation |
| `test_risk_agent.py` | 14 | Deterministic rules (boundaries, None-safety), LLM narrative, fallback |
| `test_synthesis_agent.py` | 6 | Label logic (boundaries), programmatic override, malformed JSON fallback |
| `test_pipeline_integration.py` | 14 | E2E mock pipeline, recommendation logic, state preservation |

**Total: 79 tests, 100% pass rate**

### Key Test Scenarios
- Boundary conditions: confidence=0.5, risk=70.0, growth=0.05, D/E=2.5
- Missing data: `yoy_revenue_growth=None`, negative growth blocks Strong Buy
- Error accumulation: prior errors preserved through pipeline
- LLM hallucination override: "MUST BUY IMMEDIATELY!!!" → corrected to deterministic label
- Cache behavior: hit/miss, rate-limit rejection, corruption handling

---

## 13. License

### License
MIT License — see `LICENSE` file for details.
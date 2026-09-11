import { useState, useCallback, useEffect, useRef } from 'react';
import { Info } from 'lucide-react';
import { Header } from './components/Header';
import { MetricsCards, SkeletonLedger } from './components/MetricsCards';
import { RiskGauge } from './components/RiskGauge';
import { NewsSentiment } from './components/NewsSentiment';
import { SynthesisBrief } from './components/SynthesisBrief';
import { PipelineTrace } from './components/PipelineTrace';
import { ErrorAlert } from './components/ErrorAlert';
import { DegradedAlert } from './components/DegradedAlert';
import { analyzeTicker, searchCompanies } from './services/api';
import { isInternationalTicker } from './utils/tickers';
import type { PipelineResult, SearchCandidate } from './types';
import {
  getConfidenceLabel,
  getConfidenceSentence,
  getRecommendationBlurb,
  getRecommendationTone,
  getRiskColor,
  getRiskLevel,
  getRiskTone,
  getVerdictLine,
} from './utils/formatters';
import './App.css';

// Mirrors the backend TICKER_PATTERN (case-insensitive here; uppercased before use)
const TICKER_PATTERN = /^[A-Z0-9]{1,10}(?:\.[A-Z]{1,2})?$/i;
const SEARCH_DEBOUNCE_MS = 300;

function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [candidates, setCandidates] = useState<SearchCandidate[]>([]);
  const [searching, setSearching] = useState(false);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const searchRequestId = useRef(0);
  // Layer-3 analyst detail: collapsed by default, persisted, toggled with `d`.
  const [analystOpen, setAnalystOpen] = useState<boolean>(() => {
    try {
      return localStorage.getItem('chrimatos-analyst-open') === '1';
    } catch {
      return false;
    }
  });
  // Mirror of `loading` for use inside callbacks/effects without retriggering them
  const loadingRef = useRef(loading);
  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/health');
      setBackendHealthy(res.ok);
    } catch {
      setBackendHealthy(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  useEffect(() => {
    try {
      localStorage.setItem('chrimatos-analyst-open', analystOpen ? '1' : '0');
    } catch {
      // storage unavailable (private mode) - preference simply won't persist
    }
  }, [analystOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'd' && e.key !== 'D') return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      e.preventDefault();
      setAnalystOpen((v) => !v);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Refreshes candidates only; opening the dropdown is an explicit,
  // user-driven action (typing, Enter on a name, input focus) so background
  // refetches (e.g. after analysis completes) never pop it open.
  const runSearch = useCallback(async (query: string) => {
    const requestId = ++searchRequestId.current;
    setSearching(true);
    try {
      const results = await searchCompanies(query);
      if (requestId === searchRequestId.current) {
        setCandidates(results);
      }
    } finally {
      if (requestId === searchRequestId.current) {
        setSearching(false);
      }
    }
  }, []);

  // Debounced autocomplete as the user types. `loading` is read via ref so
  // the loading true->false flip after analysis cannot retrigger a fetch.
  useEffect(() => {
    if (loadingRef.current || ticker.trim().length < 2) {
      if (ticker.trim().length < 2) setCandidates([]);
      return;
    }
    const timer = setTimeout(() => {
      void runSearch(ticker);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [ticker, runSearch]);

  const runAnalysis = async (symbol: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSuggestionsOpen(false);

    try {
      const data = await analyzeTicker(symbol);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    if (isInternationalTicker(symbol)) {
      setError(
        `${symbol} looks like a non-US listing, which the Finnhub free tier does not cover. ` +
        `Pick a US-listed suggestion from the dropdown instead.`
      );
      return;
    }
    await runAnalysis(symbol);
  };

  const handleSearchChange = (value: string) => {
    setTicker(value);
    setSuggestionsOpen(true);
  };

  const handleSelectCandidate = async (candidate: SearchCandidate) => {
    setTicker(candidate.symbol);
    setCandidates([]);
    setSuggestionsOpen(false);
    await runAnalysis(candidate.symbol);
  };

  const handleEnterKey = async () => {
    const query = ticker.trim();
    if (!query) return;
    if (TICKER_PATTERN.test(query.toUpperCase())) {
      await handleAnalyze();
    } else if (query.length < 2) {
      setError('Type at least 2 characters of a ticker or company name.');
    } else {
      // Company name without a selection: fetch matches into the dropdown
      setError(null);
      await runSearch(query);
      setSuggestionsOpen(true);
    }
  };

  const handleInputFocus = () => {
    if (candidates.length > 0) setSuggestionsOpen(true);
  };

  const handleCloseSuggestions = () => {
    setSuggestionsOpen(false);
  };

  return (
    <div className="app">
      <Header 
        ticker={ticker}
        onSearchChange={handleSearchChange}
        onAnalyze={handleAnalyze}
        onEnterKey={handleEnterKey}
        loading={loading}
        backendHealthy={backendHealthy}
        suggestions={candidates}
        searching={searching}
        suggestionsOpen={suggestionsOpen}
        onSelectCandidate={handleSelectCandidate}
        onCloseSuggestions={handleCloseSuggestions}
        onInputFocus={handleInputFocus}
      />

      <main className="main-content">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {loading && <SkeletonLedger />}

        {result && (
          <>
            <DegradedAlert 
              confidence={result.confidence_score} 
              errors={result.errors} 
            />
            
            <div
              className="hero"
              style={{
                background: `color-mix(in srgb, ${getRiskColor(result.risk_data.risk_score)} 7%, var(--paper))`,
              }}
            >
              <div className="hero-main">
                <div className="ticker-hero mono">{result.ticker}</div>
                <div className="company-sub">{result.company_name}</div>
                <p className="verdict-line">
                  {getVerdictLine(
                    result.risk_data.risk_score,
                    result.confidence_score,
                    result.risk_data.risk_factors.length,
                    result.synthesis_report.analyst_recommendation,
                  )}
                </p>
                <button
                  className="analyst-toggle"
                  onClick={() => setAnalystOpen((v) => !v)}
                  aria-expanded={analystOpen}
                  title="Keyboard shortcut: d"
                >
                  {analystOpen ? 'Hide analyst detail ▾' : 'Show analyst detail ▸'}
                </button>
              </div>
              <div className="hero-side">
                <span className={`risk-tag tone-${getRiskTone(result.risk_data.risk_score)}`}>
                  {getRiskLevel(result.risk_data.risk_score)}
                </span>
                <div className="hero-meta mono">
                  score {result.risk_data.risk_score.toFixed(0)}/100 ·{' '}
                  {getConfidenceSentence(result.confidence_score, result.errors.length)}
                </div>
                <div className="hero-rec">
                  <span className={`hero-rec-label tone-${getRecommendationTone(result.synthesis_report.analyst_recommendation)}`}>
                    {result.synthesis_report.analyst_recommendation}
                  </span>
                  <span className="hero-rec-blurb">
                    {getRecommendationBlurb(result.synthesis_report.analyst_recommendation)} ·{' '}
                    {getConfidenceLabel(result.confidence_score)}
                  </span>
                </div>
              </div>
            </div>
            <hr className="rule-strong hero-rule" />

            <PipelineTrace
              timings={result.timings ?? {}}
              degraded={{
                financial: !result.financial_data.data_available,
                news: !result.news_data.news_available,
              }}
            />

            <div className="tabs">
              <div className="tab-buttons" role="tablist">
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 0 ? 'active' : ''}`}
                  aria-selected={activeTab === 0}
                  onClick={() => setActiveTab(0)}
                >
                  Financial Metrics
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 1 ? 'active' : ''}`}
                  aria-selected={activeTab === 1}
                  onClick={() => setActiveTab(1)}
                >
                  Risk Analysis
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 2 ? 'active' : ''}`}
                  aria-selected={activeTab === 2}
                  onClick={() => setActiveTab(2)}
                >
                  News & Sentiment
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 3 ? 'active' : ''}`}
                  aria-selected={activeTab === 3}
                  onClick={() => setActiveTab(3)}
                >
                  Synthesis Brief
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 4 ? 'active' : ''}`}
                  aria-selected={activeTab === 4}
                  onClick={() => setActiveTab(4)}
                >
                  Debug / Raw Data
                </button>
              </div>

              <div className="tab-panels">
                <div className={`tab-panel ${activeTab === 0 ? 'active' : ''}`}>
                  <MetricsCards data={result.financial_data} analystOpen={analystOpen} />
                </div>
                <div className={`tab-panel ${activeTab === 1 ? 'active' : ''}`}>
                  <RiskGauge data={result.risk_data} analystOpen={analystOpen} />
                </div>
                <div className={`tab-panel ${activeTab === 2 ? 'active' : ''}`}>
                  <NewsSentiment data={result.news_data} />
                </div>
                <div className={`tab-panel ${activeTab === 3 ? 'active' : ''}`}>
                  <SynthesisBrief data={result.synthesis_report} />
                </div>
                <div className={`tab-panel ${activeTab === 4 ? 'active' : ''}`}>
                  <pre className="raw-data">{JSON.stringify(result, null, 2)}</pre>
                </div>
              </div>
            </div>
          </>
        )}

        {!result && !loading && !error && (
          <div className="landing">
            <Info className="landing-icon" />
            <h2>Enter a ticker symbol or company name and click Analyze</h2>
            <p>Autonomous multi-agent due-diligence pipeline for US equities</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

import { useState, useCallback, useEffect } from 'react';
import { Info } from 'lucide-react';
import { Header } from './components/Header';
import { MetricsCards } from './components/MetricsCards';
import { RiskGauge } from './components/RiskGauge';
import { NewsSentiment } from './components/NewsSentiment';
import { SynthesisBrief } from './components/SynthesisBrief';
import { PipelineStatus } from './components/PipelineStatus';
import { ErrorAlert } from './components/ErrorAlert';
import { DegradedAlert } from './components/DegradedAlert';
import { analyzeTicker } from './services/api';
import type { PipelineResult } from './types';
import { RECOMMENDATION_COLORS, getConfidenceColor, getConfidenceLabel } from './utils/formatters';
import './App.css';

function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

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

  const handleAnalyze = async () => {
    if (!ticker.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeTicker(ticker.trim().toUpperCase());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAnalyze();
  };

  return (
    <div className="app">
      <Header 
        ticker={ticker}
        setTicker={setTicker}
        onAnalyze={handleAnalyze}
        onKeyDown={handleKeyDown}
        loading={loading}
        backendHealthy={backendHealthy}
      />

      <main className="main-content">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        
        {result && (
          <>
            <DegradedAlert 
              confidence={result.confidence_score} 
              errors={result.errors} 
            />
            
            <div className="header-row">
              <div className="ticker-info">
                <h1>{result.ticker} — {result.company_name}</h1>
              </div>
              <div className="confidence-badge" style={{ backgroundColor: getConfidenceColor(result.confidence_score) }}>
                {getConfidenceLabel(result.confidence_score)} ({Math.round(result.confidence_score * 100)}%)
              </div>
              <div className="recommendation-badge" style={{ backgroundColor: RECOMMENDATION_COLORS[result.synthesis_report.analyst_recommendation] }}>
                {result.synthesis_report.analyst_recommendation}
              </div>
            </div>

            <PipelineStatus 
              financial={result.financial_data.data_available ? 'available' : 'unavailable'}
              news={result.news_data.news_available ? 'available' : 'unavailable'}
              risk="complete"
              synthesis="complete"
            />

            <div className="tabs">
              <div className="tab-buttons" role="tablist">
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 0 ? 'active' : ''}`}
                  aria-selected={activeTab === 0}
                  onClick={() => setActiveTab(0)}
                >
                  📊 Financial Metrics
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 1 ? 'active' : ''}`}
                  aria-selected={activeTab === 1}
                  onClick={() => setActiveTab(1)}
                >
                  ⚠️ Risk Analysis
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 2 ? 'active' : ''}`}
                  aria-selected={activeTab === 2}
                  onClick={() => setActiveTab(2)}
                >
                  📰 News & Sentiment
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 3 ? 'active' : ''}`}
                  aria-selected={activeTab === 3}
                  onClick={() => setActiveTab(3)}
                >
                  📋 Synthesis Brief
                </button>
                <button 
                  role="tab" 
                  className={`tab-button ${activeTab === 4 ? 'active' : ''}`}
                  aria-selected={activeTab === 4}
                  onClick={() => setActiveTab(4)}
                >
                  🔍 Debug / Raw Data
                </button>
              </div>

              <div className="tab-panels">
                <div className={`tab-panel ${activeTab === 0 ? 'active' : ''}`}>
                  <MetricsCards data={result.financial_data} />
                </div>
                <div className={`tab-panel ${activeTab === 1 ? 'active' : ''}`}>
                  <RiskGauge data={result.risk_data} />
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
            <h2>Enter a ticker symbol and click Analyze</h2>
            <p>Autonomous multi-agent due-diligence pipeline for US equities</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
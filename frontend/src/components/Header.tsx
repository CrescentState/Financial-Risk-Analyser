import { Search, Loader2, CheckCircle, AlertCircle, Server } from 'lucide-react';
import './Header.css';

interface HeaderProps {
  ticker: string;
  setTicker: (value: string) => void;
  onAnalyze: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  loading: boolean;
  backendHealthy: boolean;
}

export function Header({ ticker, setTicker, onAnalyze, onKeyDown, loading, backendHealthy }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <Server className="logo-icon" />
          <div>
            <h1>Chrimatos</h1>
            <span className="subtitle">Financial Risk Analyser</span>
          </div>
        </div>
      </div>

      <div className="header-center">
        <div className="search-box">
          <Search className="search-icon" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={onKeyDown}
            placeholder="Enter ticker (e.g., AAPL, TSLA)"
            disabled={loading}
            autoComplete="off"
          />
          <button 
            className="analyze-btn" 
            onClick={onAnalyze} 
            disabled={loading || !ticker.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="spinner" />
                Analyzing...
              </>
            ) : (
              <>
                <Search />
                Analyze
              </>
            )}
          </button>
        </div>
      </div>

      <div className="header-right">
        <div className={`health-indicator ${backendHealthy ? 'healthy' : 'unhealthy'}`}>
          <span className="health-dot" />
          <span>{backendHealthy ? 'Backend Connected' : 'Backend Disconnected'}</span>
          {backendHealthy ? <CheckCircle className="health-icon" /> : <AlertCircle className="health-icon" />}
        </div>
      </div>
    </header>
  );
}
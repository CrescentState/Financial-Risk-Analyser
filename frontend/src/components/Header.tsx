import { useEffect, useState } from 'react';
import { Search, Loader2, CheckCircle, AlertCircle, Server } from 'lucide-react';
import type { SearchCandidate } from '../types';
import './Header.css';

interface HeaderProps {
  ticker: string;
  onSearchChange: (value: string) => void;
  onAnalyze: () => void;
  onEnterKey: () => void;
  loading: boolean;
  backendHealthy: boolean;
  suggestions: SearchCandidate[];
  searching: boolean;
  suggestionsOpen: boolean;
  onSelectCandidate: (candidate: SearchCandidate) => void;
  onCloseSuggestions: () => void;
  onInputFocus: () => void;
}

export function Header({
  ticker,
  onSearchChange,
  onAnalyze,
  onEnterKey,
  loading,
  backendHealthy,
  suggestions,
  searching,
  suggestionsOpen,
  onSelectCandidate,
  onCloseSuggestions,
  onInputFocus,
}: HeaderProps) {
  const [activeIndex, setActiveIndex] = useState(-1);

  // Reset highlight whenever the suggestion list changes
  useEffect(() => {
    setActiveIndex(-1);
  }, [suggestions]);

  const dropdownVisible = suggestionsOpen && (suggestions.length > 0 || searching);

  const isSelectable = (s: SearchCandidate) => s.freeTierSupported !== false;

  // Arrow navigation skips tickers unavailable on the free tier
  const moveHighlight = (dir: 1 | -1) => {
    let i = activeIndex;
    for (let step = 0; step < suggestions.length; step++) {
      i = (i + dir + suggestions.length) % suggestions.length;
      if (isSelectable(suggestions[i])) {
        setActiveIndex(i);
        return;
      }
    }
    // All suggestions disabled: leave highlight unchanged
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' && suggestions.length > 0) {
      e.preventDefault();
      moveHighlight(1);
    } else if (e.key === 'ArrowUp' && suggestions.length > 0) {
      e.preventDefault();
      moveHighlight(-1);
    } else if (e.key === 'Enter') {
      const highlighted = dropdownVisible && activeIndex >= 0 ? suggestions[activeIndex] : undefined;
      if (highlighted && isSelectable(highlighted)) {
        e.preventDefault();
        onSelectCandidate(highlighted);
      } else {
        onEnterKey();
      }
    } else if (e.key === 'Escape') {
      onCloseSuggestions();
    }
  };

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
          <div className="search-container">
            <input
              type="text"
              value={ticker}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={handleInputKeyDown}
              onFocus={onInputFocus}
              onBlur={onCloseSuggestions}
              placeholder="Enter ticker or company name (e.g., AAPL, Apple)"
              disabled={loading}
              autoComplete="off"
              role="combobox"
              aria-expanded={dropdownVisible}
              aria-autocomplete="list"
              aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
            />
            {dropdownVisible && (
              <ul className="suggestions-dropdown" role="listbox" aria-label="Matching companies">
                {searching && suggestions.length === 0 && (
                  <li className="suggestions-status">Searching…</li>
                )}
                {!searching && suggestions.length === 0 && (
                  <li className="suggestions-status">No matches found</li>
                )}
                {suggestions.map((s, i) => {
                  const disabled = s.freeTierSupported === false;
                  return (
                    <li
                      key={`${s.symbol}-${i}`}
                      id={`suggestion-${i}`}
                      role="option"
                      aria-selected={i === activeIndex}
                      aria-disabled={disabled || undefined}
                      title={
                        disabled
                          ? `${s.name || s.symbol} — not covered by the free tier (US listings only)`
                          : s.name || s.symbol
                      }
                      className={`suggestion-item${i === activeIndex && !disabled ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                      onMouseDown={(e) => {
                        // Select before input blur closes the dropdown
                        e.preventDefault();
                        if (!disabled) onSelectCandidate(s);
                      }}
                      onMouseEnter={() => {
                        if (!disabled) setActiveIndex(i);
                      }}
                    >
                      <span className="suggestion-symbol">{s.symbol}</span>
                      <span className="suggestion-name">{s.name}</span>
                      {(s.type || s.region || disabled) && (
                        <span className="suggestion-meta">
                          {disabled
                            ? 'US listings only'
                            : [s.type, s.region].filter(Boolean).join(' · ')}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
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

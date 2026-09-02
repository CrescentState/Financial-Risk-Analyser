import { formatNumber } from '../utils/formatters';
import type { NewsData } from '../types';
import './NewsSentiment.css';

interface NewsSentimentProps {
  data: NewsData;
}

function getSentimentColor(score: number): string {
  if (score >= 0.3) return '#00C851';
  if (score >= -0.1) return '#FFBB33';
  return '#FF4444';
}

function getSentimentLabel(score: number): string {
  if (score >= 0.3) return 'Positive';
  if (score >= -0.1) return 'Neutral';
  return 'Negative';
}

export function NewsSentiment({ data }: NewsSentimentProps) {
  const score = data.sentiment_score ?? 0;
  const color = getSentimentColor(score);
  const label = getSentimentLabel(score);

  if (!data.news_available) {
    return (
      <div className="news-unavailable">
        <div className="warning-banner">
          ⚠️ News data unavailable
          {score !== 0 && (
            <span className="fallback-score">
              Sentiment Score: {formatNumber(score)} (fallback)
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="news-container">
      <div className="sentiment-header">
        <div className="sentiment-score-card" style={{ borderColor: color }}>
          <div className="sentiment-value" style={{ color }}>
            {formatNumber(score)}
          </div>
          <div className="sentiment-label">
            {label} Sentiment
          </div>
        </div>
      </div>

      <div className="news-grid">
        <div className="news-section">
          <h3>Key Events</h3>
          {data.key_events && data.key_events.length > 0 ? (
            <ul className="events-list">
              {data.key_events.map((event, i) => (
                <li key={i}>{event}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No key events identified</p>
          )}
        </div>

        <div className="news-section">
          <h3>Red Flags</h3>
          {data.red_flags && data.red_flags.length > 0 ? (
            <ul className="flags-list">
              {data.red_flags.map((flag, i) => (
                <li key={i}>
                  <span className="flag-icon">🚩</span>
                  {flag}
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No red flags identified</p>
          )}
        </div>
      </div>

      <div className="news-section summary-section">
        <h3>Summary</h3>
        <p className="summary-text">{data.summary || 'No summary available'}</p>
      </div>

      <details className="raw-data-toggle">
        <summary>🔍 Raw News Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}
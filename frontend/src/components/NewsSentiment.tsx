import { useState } from 'react';
import type { NewsArticle, NewsData } from '../types';
import './NewsSentiment.css';

interface NewsSentimentProps {
  data: NewsData;
}

const VISIBLE_ARTICLES = 4;

function sentimentGlyph(score: number): string {
  if (score >= 0.3) return '▲';
  if (score >= -0.1) return '●';
  return '▼';
}

function sentimentColor(score: number): string {
  if (score >= 0.3) return 'var(--risk-low)';
  if (score >= -0.1) return 'var(--risk-moderate)';
  return 'var(--risk-high)';
}

function sentimentLabel(score: number): string {
  if (score >= 0.3) return 'Positive';
  if (score >= -0.1) return 'Neutral';
  return 'Negative';
}

function ArticleRows({ articles }: { articles: NewsArticle[] }) {
  const [expanded, setExpanded] = useState(false);
  if (articles.length === 0) return null;
  const visible = expanded ? articles : articles.slice(0, VISIBLE_ARTICLES);
  return (
    <div className="news-section">
      <div className="section-label">Coverage ({articles.length})</div>
      <ul className="article-list">
        {visible.map((a, i) => (
          <li key={i} className="article-row">
            {a.url ? (
              <a href={a.url} target="_blank" rel="noreferrer">
                {a.title}
              </a>
            ) : (
              <span>{a.title}</span>
            )}
            <span className="article-source">{a.source}</span>
          </li>
        ))}
      </ul>
      {articles.length > VISIBLE_ARTICLES && (
        <button className="link-button" onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Show fewer' : `Show ${articles.length - VISIBLE_ARTICLES} more`}
        </button>
      )}
    </div>
  );
}

export function NewsSentiment({ data }: NewsSentimentProps) {
  const score = data.sentiment_score ?? 0;
  const articles = data.articles ?? [];

  if (!data.news_available) {
    return (
      <div className="news-container">
        <p className="news-empty">Not enough recent news to judge sentiment.</p>
        <ArticleRows articles={articles} />
        <details className="raw-data-toggle">
          <summary>Raw News Data</summary>
          <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
        </details>
      </div>
    );
  }

  return (
    <div className="news-container">
      <div className="sentiment-line">
        <span className="sentiment-glyph" style={{ color: sentimentColor(score) }}>
          {sentimentGlyph(score)}
        </span>
        <span className="sentiment-value mono">{score.toFixed(2)}</span>
        <span className="sentiment-caption">
          {sentimentLabel(score)} sentiment
        </span>
      </div>

      <div className="news-section summary-section">
        <div className="section-label">Summary</div>
        <p className="summary-text">{data.summary || 'No summary available'}</p>
      </div>

      <div className="news-columns">
        <div className="news-section">
          <div className="section-label">Key events</div>
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
          <div className="section-label">Red flags</div>
          {data.red_flags && data.red_flags.length > 0 ? (
            <ul className="flags-list">
              {data.red_flags.map((flag, i) => (
                <li key={i}>{flag}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No red flags identified</p>
          )}
        </div>
      </div>

      <ArticleRows articles={articles} />

      <details className="raw-data-toggle">
        <summary>Raw News Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}

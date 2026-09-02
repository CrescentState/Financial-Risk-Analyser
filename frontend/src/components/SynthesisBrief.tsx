import { useState } from 'react';
import type { SynthesisReport } from '../types';
import './SynthesisBrief.css';

interface SynthesisBriefProps {
  data: SynthesisReport;
}

const sections: Array<{
  key: keyof SynthesisReport;
  title: string;
  icon: string;
}> = [
  { key: 'company_snapshot', title: 'Company Snapshot', icon: '🏢' },
  { key: 'financial_health', title: 'Financial Health', icon: '💰' },
  { key: 'market_sentiment', title: 'Market Sentiment', icon: '📈' },
  { key: 'risk_assessment', title: 'Risk Assessment', icon: '⚠️' },
];

export function SynthesisBrief({ data }: SynthesisBriefProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    company_snapshot: true,
    financial_health: true,
    market_sentiment: true,
    risk_assessment: true,
    key_concerns: true,
  });

  const toggleSection = (key: string) => {
    setOpenSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderSection = (section: { key: string; title: string; icon: string }) => (
    <div key={section.key} className="section-expansion">
      <button
        className="section-header"
        onClick={() => toggleSection(section.key)}
        aria-expanded={openSections[section.key]}
      >
        <span className="section-icon">{section.icon}</span>
        <span className="section-title">{section.title}</span>
        <span className="section-chevron">{openSections[section.key] ? '▼' : '▶'}</span>
      </button>
      {openSections[section.key] && (
        <div className="section-content">
          <p>{data[section.key as keyof SynthesisReport] || 'No data available'}</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="synthesis-container">
      <div className="recommendation-banner">
        <span className="rec-label">Analyst Recommendation:</span>
        <span className="rec-value">{data.analyst_recommendation}</span>
      </div>

      <div className="sections">
        {sections.map(renderSection)}

        <div className="section-expansion">
          <button
            className="section-header"
            onClick={() => toggleSection('key_concerns')}
            aria-expanded={openSections.key_concerns}
          >
            <span className="section-icon">🎯</span>
            <span className="section-title">Key Concerns</span>
            <span className="section-chevron">{openSections.key_concerns ? '▼' : '▶'}</span>
          </button>
          {openSections.key_concerns && (
            <div className="section-content">
              {data.key_concerns && data.key_concerns.length > 0 ? (
                <ul className="concerns-list">
                  {data.key_concerns.map((concern, i) => (
                    <li key={i}>{concern}</li>
                  ))}
                </ul>
              ) : (
                <p className="no-concerns">No specific concerns identified</p>
              )}
            </div>
          )}
        </div>
      </div>

      <details className="raw-data-toggle">
        <summary>🔍 Raw Synthesis Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}
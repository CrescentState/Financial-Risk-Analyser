import { useEffect, useState } from 'react';
import type { RiskData, RiskDetail } from '../types';
import { getRiskColor, getRiskLevel, getRiskTone } from '../utils/formatters';
import './RiskGauge.css';

interface RiskGaugeProps {
  data: RiskData;
  analystOpen: boolean;
}

const CX = 100;
const CY = 100;
const R = 78;

function polar(score: number, radius: number): [number, number] {
  const angle = ((180 - (Math.max(0, Math.min(100, score)) / 100) * 180) * Math.PI) / 180;
  return [CX + radius * Math.cos(angle), CY - radius * Math.sin(angle)];
}

function bandPath(from: number, to: number): string {
  const [x0, y0] = polar(from, R);
  const [x1, y1] = polar(to, R);
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

const BANDS: Array<{ from: number; to: number; color: string }> = [
  { from: 0, to: 20, color: 'var(--risk-low)' },
  { from: 20, to: 45, color: 'var(--risk-moderate)' },
  { from: 45, to: 70, color: 'var(--risk-elevated)' },
  { from: 70, to: 100, color: 'var(--risk-high)' },
];

const TICKS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

function useSweptScore(score: number): number {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(score);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 600);
      setShown(score * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);
  return shown;
}

export function RiskGauge({ data, analystOpen }: RiskGaugeProps) {
  const score = data.risk_score ?? 0;
  const color = getRiskColor(score);
  const level = getRiskLevel(score);
  const shown = useSweptScore(score);
  const [nx, ny] = polar(shown, R - 18);

  const details: RiskDetail[] =
    data.risk_details && data.risk_details.length > 0
      ? data.risk_details
      : (data.risk_factors ?? []).map((f) => ({
          id: 'R-–',
          label: f,
          explanation: 'Flagged by the risk engine.',
        }));

  return (
    <div className="risk-gauge-container">
      <div className="gauge-top">
        <svg
          className="gauge-svg"
          viewBox="0 0 200 118"
          role="img"
          aria-label={`Risk score ${score.toFixed(0)} out of 100, ${level}`}
        >
          <path d={bandPath(0, 100)} fill="none" stroke="var(--rule)" strokeWidth="8" />
          {BANDS.map((b) => (
            <path
              key={`${b.from}-${b.to}`}
              d={bandPath(b.from, b.to)}
              fill="none"
              stroke={b.color}
              strokeWidth="8"
            />
          ))}
          {TICKS.map((t) => {
            const [x0, y0] = polar(t, R - 12);
            const [x1, y1] = polar(t, R - 6);
            return (
              <line key={t} x1={x0} y1={y0} x2={x1} y2={y1} stroke="var(--ink-3)" strokeWidth="1" />
            );
          })}
          <line x1={CX} y1={CY} x2={nx} y2={ny} stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx={CX} cy={CY} r="4" fill="var(--ink)" />
          <text x="22" y="116" textAnchor="middle" className="gauge-tick-label">0</text>
          <text x="100" y="116" textAnchor="middle" className="gauge-tick-label">50</text>
          <text x="178" y="116" textAnchor="middle" className="gauge-tick-label">100</text>
        </svg>
        <div className="gauge-readout">
          <div className="gauge-score mono" style={{ color }}>
            {shown.toFixed(0)}
          </div>
          <div className="gauge-scale mono">/100</div>
          <span className={`risk-tag tone-${getRiskTone(score)}`}>
            {level}
          </span>
        </div>
      </div>

      <div className="risk-section">
        <div className="section-label">Rules triggered ({details.length})</div>
        {!analystOpen && details.length > 0 ? (
          <p className="rules-count">
            {details.length === 1
              ? '1 caution check triggered — show analyst detail to inspect it.'
              : `${details.length} caution checks triggered — show analyst detail to inspect them.`}
          </p>
        ) : details.length > 0 ? (
          <div className="rules-list">
            {details.map((d) => (
              <details key={d.id} className="rule-row">
                <summary>
                  <span className="rule-id mono">{d.id}</span>
                  <span className="rule-label">{d.label}</span>
                  <span className="rule-status">triggered</span>
                </summary>
                <p className="rule-explanation">{d.explanation}</p>
              </details>
            ))}
          </div>
        ) : (
          <p className="no-factors">No risk factors triggered</p>
        )}
      </div>

      <div className="risk-section">
        <div className="section-label">Risk narrative</div>
        <p className="risk-narrative">{data.risk_narrative || 'No narrative available'}</p>
      </div>

      <details className="raw-data-toggle">
        <summary>Raw Risk Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}

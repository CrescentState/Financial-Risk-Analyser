import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import type { RiskData } from '../types';
import './RiskGauge.css';

interface RiskGaugeProps {
  data: RiskData;
}

const GAUGE_COLORS = {
  low: '#00C851',
  moderate: '#FFBB33',    // Amber for moderate (matches badge)
  elevated: '#FF8800',    // Orange for elevated
  high: '#FF4444',
};

const GAUGE_STEP_COLORS = {
  low: 'rgba(0, 200, 81, 0.25)',
  moderate: 'rgba(255, 187, 51, 0.25)',
  elevated: 'rgba(255, 136, 0, 0.25)',
  high: 'rgba(255, 68, 68, 0.25)',
};

function getGaugeColor(score: number): string {
  if (score <= 20) return GAUGE_COLORS.low;
  if (score <= 45) return GAUGE_COLORS.moderate;
  if (score <= 70) return GAUGE_COLORS.elevated;
  return GAUGE_COLORS.high;
}

function getRiskLevel(score: number): string {
  if (score <= 20) return 'Low Risk';
  if (score <= 45) return 'Moderate Risk';
  if (score <= 70) return 'Elevated Risk';
  return 'High Risk';
}

const layout = {
  height: 300,
  margin: { l: 30, r: 30, t: 50, b: 40 },  // Increased margins for tick labels
  paper_bgcolor: 'white',
  font: { family: 'Inter, system-ui, sans-serif' },
};

export function RiskGauge({ data }: RiskGaugeProps) {
  const score = data.risk_score ?? 0;
  const color = getGaugeColor(score);
  const level = getRiskLevel(score);

  // Create gauge data fresh each render
  const gaugeData = useMemo(() => [{
    type: 'indicator' as const,
    mode: 'gauge+number' as const,
    value: score,
    domain: { x: [0, 1], y: [0, 1] },
    title: { text: 'Risk Score', font: { size: 16, color: '#374151' } },
    number: { font: { size: 36, color: color, family: 'Inter, system-ui, sans-serif' } },
    gauge: {
      axis: { 
        range: [0, 100], 
        tickwidth: 1, 
        tickcolor: '#9ca3af',
        tickmode: 'linear' as const,
        tick0: 0,
        dtick: 20,
        tickfont: { size: 11, color: '#6b7280' },
      },
      bar: { color, thickness: 0.35 },
      bgcolor: 'white',
      borderwidth: 2,
      bordercolor: '#e5e7eb',
      steps: [
        { range: [0, 20], color: GAUGE_STEP_COLORS.low },
        { range: [20, 45], color: GAUGE_STEP_COLORS.moderate },
        { range: [45, 70], color: GAUGE_STEP_COLORS.elevated },
        { range: [70, 100], color: GAUGE_STEP_COLORS.high },
      ],
      // Threshold at high-risk zone (70) - not at current score
      threshold: {
        line: { color: '#FF4444', width: 3, dash: 'dash' },
        thickness: 0.75,
        value: 70,
      },
    },
  }], [score, color]);

  return (
    <div className="risk-gauge-container">
      <div className="gauge-header">
        <h2>Risk Analysis</h2>
        <div className="risk-level" style={{ backgroundColor: color }}>
          {level} — {score.toFixed(1)}/100
        </div>
      </div>

      <div className="gauge-layout">
        <div className="gauge-chart">
          <Plot
            data={gaugeData}
            layout={layout}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
          />
        </div>

        <div className="risk-details">
          <div className="risk-section">
            <h3>Risk Factors</h3>
            {data.risk_factors && data.risk_factors.length > 0 ? (
              <ul className="risk-factors">
                {data.risk_factors.map((factor, i) => (
                  <li key={i}>
                    <span className="factor-dot" />
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="no-factors">No risk factors triggered</p>
            )}
          </div>

          <div className="risk-section">
            <h3>Risk Narrative</h3>
            <p className="risk-narrative">{data.risk_narrative || 'No narrative available'}</p>
          </div>
        </div>
      </div>

      <details className="raw-data-toggle">
        <summary>🔍 Raw Risk Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}
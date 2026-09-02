import { formatNumber, formatPercent } from '../utils/formatters';
import type { FinancialData } from '../types';
import './MetricsCards.css';

interface MetricsCardsProps {
  data: FinancialData;
}

type MetricKey = 'pe_ratio' | 'yoy_revenue_growth' | 'debt_to_equity' | 'current_ratio' | 'market_cap' | 'revenue' | 'net_income' | 'cash_position';

const metricItems: Array<{
  key: MetricKey;
  label: string;
  formatter: (val: number | null | undefined) => string;
}> = [
  { key: 'pe_ratio', label: 'P/E Ratio', formatter: formatNumber },
  { key: 'yoy_revenue_growth', label: 'YoY Revenue Growth', formatter: (v) => formatPercent(v) },
  { key: 'debt_to_equity', label: 'Debt-to-Equity', formatter: formatNumber },
  { key: 'current_ratio', label: 'Current Ratio', formatter: formatNumber },
  { key: 'market_cap', label: 'Market Cap', formatter: (v) => formatNumber(v, '$') },
  { key: 'revenue', label: 'Revenue', formatter: (v) => formatNumber(v, '$') },
  { key: 'net_income', label: 'Net Income', formatter: (v) => formatNumber(v, '$') },
  { key: 'cash_position', label: 'Cash Position', formatter: (v) => formatNumber(v, '$') },
];

export function MetricsCards({ data }: MetricsCardsProps) {
  if (!data.data_available) {
    return (
      <div className="metrics-unavailable">
        <div className="warning-banner">
          ⚠️ Financial data incomplete — some fields unavailable
        </div>
      </div>
    );
  }

  return (
    <div className="metrics-grid">
      {metricItems.map(({ key, label, formatter }) => (
        <div key={key} className="metric-card">
          <div className="metric-label">{label}</div>
          <div className="metric-value">{formatter(data[key] ?? null)}</div>
        </div>
      ))}
      
      <details className="raw-data-toggle">
        <summary>🔍 Raw Financial Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}
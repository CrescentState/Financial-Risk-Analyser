import { formatNumber, formatPercent } from '../utils/formatters';
import type { FinancialData } from '../types';
import './MetricsCards.css';

type MetricKey =
  | 'pe_ratio'
  | 'yoy_revenue_growth'
  | 'debt_to_equity'
  | 'current_ratio'
  | 'market_cap'
  | 'revenue'
  | 'net_income'
  | 'cash_position';

type Flag = 'ok' | 'watch' | 'flag' | 'na';

interface MetricDef {
  key: MetricKey;
  label: string;
  /** Plain-English tooltip — the UI teaches while it reports. */
  tooltip: string;
  formatter: (val: number | null | undefined) => string;
  /** Status dot; omitted for scale figures where no band applies. */
  flag?: (val: number | null | undefined) => Flag;
  /** Red-dot text. Must name a real backend rule, or say it is guidance. */
  flagTitle?: string;
}

const FLAG_TITLES: Record<Exclude<Flag, 'na'>, string> = {
  ok: 'Within healthy band',
  watch: 'Worth watching',
  flag: 'Outside healthy band',
};

/**
 * Red = outside the backend rule's safe band; amber = inside the band but
 * outside the healthy band; green = healthy. ok() is evaluated first so it
 * defines the red boundary, good() the green one.
 */
function banded(
  ok: (v: number) => boolean,
  good: (v: number) => boolean,
): (val: number | null | undefined) => Flag {
  return (val) => {
    if (val === null || val === undefined || isNaN(val)) return 'na';
    if (!ok(val)) return 'flag';
    if (!good(val)) return 'watch';
    return 'ok';
  };
}

const GROUPS: Array<{
  name: string;
  verdict: (d: FinancialData) => string;
  metrics: MetricDef[];
}> = [
  {
    name: 'Valuation',
    verdict: (d) => {
      const pe = d.pe_ratio;
      if (pe === null || pe === undefined) return 'No valuation read — earnings multiple unavailable.';
      if (pe <= 0) return 'No earnings to price — the multiple is not meaningful.';
      if (pe <= 15) return 'Modestly valued on earnings.';
      if (pe <= 25) return 'Fairly valued on earnings.';
      return 'Richly valued — market prices in a lot of growth.';
    },
    metrics: [
      {
        key: 'pe_ratio',
        label: 'Earnings multiple',
        tooltip: 'Price paid per dollar of earnings (price-to-earnings). Above 25 is richly valued; zero or below means no earnings.',
        formatter: formatNumber,
        flag: banded(
          (v) => v > 0,
          (v) => v <= 25,
        ),
        flagTitle: 'Zero or negative earnings triggers the unprofitable rule',
      },
      {
        key: 'market_cap',
        label: 'Market value',
        tooltip: 'Total value of all shares (market capitalization). Sets the size of the bet.',
        formatter: (v) => formatNumber(v, '$'),
      },
    ],
  },
  {
    name: 'Solvency',
    verdict: (d) => {
      const de = d.debt_to_equity;
      const cr = d.current_ratio;
      if ((de === null || de === undefined) && (cr === null || cr === undefined)) {
        return 'No solvency read — leverage and liquidity unavailable.';
      }
      if (de !== null && de !== undefined && de < 0) return 'Negative equity — liabilities exceed assets.';
      if (de !== null && de !== undefined && de > 2.5) return 'Highly leveraged balance sheet.';
      if (cr !== null && cr !== undefined && cr < 1) return 'Tight liquidity — short-term bills exceed short-term assets.';
      return 'Leverage and liquidity look manageable.';
    },
    metrics: [
      {
        key: 'debt_to_equity',
        label: 'Debt load',
        tooltip: 'Debt per dollar of equity (debt-to-equity). Above 2.5 is highly leveraged; below zero means negative equity.',
        formatter: formatNumber,
        flag: banded(
          (v) => v >= 0 && v <= 2.5,
          (v) => v <= 1.5,
        ),
        flagTitle: 'Debt over 2.5× size (or below zero) triggers a leverage rule',
      },
      {
        key: 'current_ratio',
        label: 'Short-term cushion',
        tooltip: 'Short-term assets per dollar of short-term bills (current ratio). Below 1.0 means tight liquidity.',
        formatter: formatNumber,
        flag: banded(
          (v) => v >= 1,
          (v) => v >= 1.5,
        ),
        flagTitle: 'Below 1.0 means tight liquidity (guidance band, not a backend rule)',
      },
      {
        key: 'cash_position',
        label: 'Cash Position',
        tooltip: 'Cash on hand. Buys time when earnings wobble.',
        formatter: (v) => formatNumber(v, '$'),
      },
    ],
  },
  {
    name: 'Performance',
    verdict: (d) => {
      const g = d.yoy_revenue_growth;
      if (g === null || g === undefined) return 'No growth read — revenue trend unavailable.';
      if (g < -0.1) return 'Contracting — revenue shrank year over year.';
      if (g < 0) return 'Slipping — revenue slightly down year over year.';
      if (g > 0.05) return 'Growing — revenue expanding year over year.';
      return 'Flat — revenue roughly unchanged year over year.';
    },
    metrics: [
      {
        key: 'revenue',
        label: 'Sales',
        tooltip: 'Total sales over the trailing twelve months (revenue). The top line.',
        formatter: (v) => formatNumber(v, '$'),
      },
      {
        key: 'yoy_revenue_growth',
        label: 'Sales growth',
        tooltip: 'Sales change vs a year ago (year-over-year growth). Below −10% triggers a contraction flag.',
        formatter: (v) => formatPercent(v),
        flag: banded(
          (v) => v >= -0.1,
          (v) => v >= 0,
        ),
        flagTitle: 'Growth below −10% triggers the contraction rule',
      },
      {
        key: 'net_income',
        label: 'Profit',
        tooltip: 'Profit left after all costs (net income). Negative means losing money.',
        formatter: (v) => formatNumber(v, '$'),
      },
    ],
  },
];

export function SkeletonLedger() {
  return (
    <div className="ledger" role="status" aria-label="Computing report">
      <div className="section-label mono">computing…</div>
      {['Valuation', 'Solvency', 'Performance'].map((group) => (
        <section key={group} aria-hidden="true">
          <div className="ledger-group">{group}</div>
          <div className="skeleton-block">
            <div className="skeleton-row" />
            <div className="skeleton-row" />
            <div className="skeleton-row short" />
          </div>
        </section>
      ))}
    </div>
  );
}

function StatusDot({ flag, title }: { flag: Flag; title: string }) {
  if (flag === 'na') {
    return <span className="ledger-dot dot-na" title="Unavailable" />;
  }
  return <span className={`ledger-dot dot-${flag}`} title={title} />;
}

function dotTitleFor(m: MetricDef, flag: Exclude<Flag, 'na'>): string {
  if (flag === 'flag' && m.flagTitle) return `${m.flagTitle} — ${m.tooltip}`;
  return `${FLAG_TITLES[flag]} — ${m.tooltip}`;
}

export function MetricsCards({
  data,
  analystOpen,
}: {
  data: FinancialData;
  analystOpen: boolean;
}) {
  return (
    <div className="ledger">
      {!data.data_available && (
        <div className="warning-banner metrics-incomplete-banner">
          Financial data incomplete — showing available fields
        </div>
      )}
      {GROUPS.map((group) => (
        <section key={group.name} aria-label={group.name}>
          <div className="ledger-group">{group.name}</div>
          <div className="ledger-verdict">{group.verdict(data)}</div>
          {analystOpen &&
            group.metrics.map((m) => {
            const val = data[m.key] ?? null;
            const flag = m.flag ? m.flag(val) : null;
            // Directional color for signed figures (terminal up/down convention)
            const directional = m.key === 'yoy_revenue_growth' || m.key === 'net_income';
            const direction =
              !directional || val === null || val === undefined || isNaN(val) || val === 0
                ? ''
                : val > 0
                  ? ' val-up'
                  : ' val-down';
            return (
              <div key={m.key} className="ledger-row">
                <span className="ledger-label" title={m.tooltip}>
                  {m.label}
                </span>
                <span className={`ledger-value mono${direction}`}>{m.formatter(val)}</span>
                {flag && (
                  <StatusDot
                    flag={flag}
                    title={flag === 'na' ? 'Unavailable' : dotTitleFor(m, flag)}
                  />
                )}
              </div>
            );
          })}
        </section>
      ))}

      <details className="raw-data-toggle">
        <summary>Raw Financial Data</summary>
        <pre className="raw-data">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}

import './PipelineTrace.css';

const ORDER = ['financial', 'news', 'risk', 'synthesis'] as const;
type AgentKey = (typeof ORDER)[number];

const LABELS: Record<AgentKey, string> = {
  financial: 'financial',
  news: 'sentiment',
  risk: 'risk',
  synthesis: 'synthesis',
};

interface PipelineTraceProps {
  timings: Record<string, number>;
  degraded: Partial<Record<AgentKey, boolean>>;
}

/** Audit trail as first-class UI: every agent's status and timing is visible. */
export function PipelineTrace({ timings, degraded }: PipelineTraceProps) {
  const total = ORDER.reduce((sum, k) => sum + (timings[k] ?? 0), 0);
  const line = ORDER.map((k) => {
    const mark = degraded[k] ? '⚠' : '✓';
    return `${LABELS[k]} ${mark} ${(timings[k] ?? 0).toFixed(1)}s`;
  }).join(' → ');

  return (
    <details className="pipeline-trace">
      <summary>
        <span className="section-label">Pipeline trace</span>
        <span className="trace-line mono" title="Per-agent wall-clock seconds (financial + news run in parallel)">
          {line} · {total.toFixed(1)}s
        </span>
      </summary>
      <ul className="trace-rows">
        {ORDER.map((k) => (
          <li key={k}>
            <span className="trace-agent mono">{LABELS[k]}</span>
            <span className="trace-status">{degraded[k] ? '⚠ degraded' : '✓ ok'}</span>
            <span className="trace-secs mono">{(timings[k] ?? 0).toFixed(2)}s</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

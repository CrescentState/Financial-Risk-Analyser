import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import './PipelineStatus.css';

interface PipelineStatusProps {
  financial: 'available' | 'unavailable';
  news: 'available' | 'unavailable';
  risk: 'complete' | 'incomplete';
  synthesis: 'complete' | 'incomplete';
}

const statusConfig = {
  available: { icon: CheckCircle, color: '#00C851', label: 'Available' },
  unavailable: { icon: XCircle, color: '#FF4444', label: 'Unavailable' },
  complete: { icon: CheckCircle, color: '#00C851', label: 'Complete' },
  incomplete: { icon: Loader2, color: '#FFBB33', label: 'Incomplete' },
};

function StatusBadge({ status, label }: { status: string; label: string }) {
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.unavailable;
  const Icon = config.icon;

  return (
    <div className="status-item">
      <div className="status-icon" style={{ color: config.color }}>
        <Icon size={16} />
      </div>
      <div className="status-info">
        <span className="status-label">{label}</span>
        <span className="status-value" style={{ color: config.color }}>
          {config.label}
        </span>
      </div>
    </div>
  );
}

export function PipelineStatus({ financial, news, risk, synthesis }: PipelineStatusProps) {
  return (
    <div className="pipeline-status" role="region" aria-label="Pipeline Status">
      <h3 className="status-title">Pipeline Status</h3>
      <div className="status-grid">
        <StatusBadge status={financial} label="Financial Data" />
        <StatusBadge status={news} label="News Data" />
        <StatusBadge status={risk} label="Risk Analysis" />
        <StatusBadge status={synthesis} label="Synthesis" />
      </div>
    </div>
  );
}
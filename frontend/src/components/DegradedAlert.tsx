import { AlertTriangle, Info } from 'lucide-react';
import './DegradedAlert.css';

interface DegradedAlertProps {
  confidence: number;
  errors: string[];
}

function getConfidenceColor(score: number): string {
  if (score >= 0.8) return '#00C851';
  if (score >= 0.6) return '#33B5E5';
  if (score >= 0.4) return '#FFBB33';
  return '#FF4444';
}

function getConfidenceLabel(score: number): string {
  if (score >= 0.8) return 'High Confidence';
  if (score >= 0.6) return 'Moderate Confidence';
  if (score >= 0.4) return 'Low Confidence';
  return 'Very Low Confidence';
}

export function DegradedAlert({ confidence, errors }: DegradedAlertProps) {
  const showAlert = confidence < 0.8 || errors.length > 0;

  if (!showAlert) return null;

  const color = getConfidenceColor(confidence);
  const label = getConfidenceLabel(confidence);

  return (
    <div className="degraded-alert" style={{ borderColor: color }} role="alert">
      <div className="alert-header">
        <div className="alert-icon" style={{ color }}>
          <AlertTriangle size={20} />
        </div>
        <div className="alert-title">
          <strong>Degraded State Detected</strong>
          <span className="confidence-badge" style={{ backgroundColor: color }}>
            {label} ({Math.round(confidence * 100)}%)
          </span>
        </div>
      </div>

      {errors.length > 0 && (
        <details className="error-details">
          <summary>🔍 Error Details ({errors.length} issue{errors.length !== 1 ? 's' : ''})</summary>
          <ul className="error-list">
            {errors.map((error, i) => (
              <li key={i}>
                <Info className="error-bullet" size={14} />
                {error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
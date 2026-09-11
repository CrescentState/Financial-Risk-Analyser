import { getConfidenceLabel, getConfidenceTone } from '../utils/formatters';
import './DegradedAlert.css';

interface DegradedAlertProps {
  confidence: number;
  errors: string[];
}

export function DegradedAlert({ confidence, errors }: DegradedAlertProps) {
  const showAlert = confidence < 0.8 || errors.length > 0;

  if (!showAlert) return null;

  return (
    <div className="degraded-note" role="alert">
      <span className="risk-tag tone-moderate">Degraded</span>
      <p className="degraded-line">
        Partial data —{' '}
        <span className={`tone-${getConfidenceTone(confidence)}`}>
          {getConfidenceLabel(confidence)} ({Math.round(confidence * 100)}%)
        </span>
        .{errors.length > 0 ? ' Technical details below.' : ' Proceed with care.'}
      </p>
      {errors.length > 0 && (
        <details className="error-details">
          <summary>
            Error details ({errors.length} issue{errors.length !== 1 ? 's' : ''})
          </summary>
          <ul className="error-list">
            {errors.map((error, i) => (
              <li key={i} className="mono">
                {error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

import { AlertCircle, X } from 'lucide-react';
import './ErrorAlert.css';

interface ErrorAlertProps {
  message: string;
  onDismiss: () => void;
}

export function ErrorAlert({ message, onDismiss }: ErrorAlertProps) {
  return (
    <div className="error-alert" role="alert">
      <div className="error-content">
        <AlertCircle className="error-icon" />
        <p className="error-message">{message}</p>
      </div>
      <button className="error-dismiss" onClick={onDismiss} aria-label="Dismiss error">
        <X size={18} />
      </button>
    </div>
  );
}
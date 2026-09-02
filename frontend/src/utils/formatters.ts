export function formatNumber(
  val: number | null | undefined,
  prefix: string = '',
  suffix: string = '',
  decimals: number = 2
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return 'N/A';
  }
  try {
    if (val >= 1e12) {
      return `${prefix}${(val / 1e12).toFixed(decimals)}T${suffix}`;
    }
    if (val >= 1e9) {
      return `${prefix}${(val / 1e9).toFixed(decimals)}B${suffix}`;
    }
    if (val >= 1e6) {
      return `${prefix}${(val / 1e6).toFixed(decimals)}M${suffix}`;
    }
    if (val >= 1e3) {
      return `${prefix}${(val / 1e3).toFixed(decimals)}K${suffix}`;
    }
    return `${prefix}${val.toFixed(decimals)}${suffix}`;
  } catch {
    return 'N/A';
  }
}

export function formatPercent(
  val: number | null | undefined,
  decimals: number = 2
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return 'N/A';
  }
  try {
    return `${(val * 100).toFixed(decimals)}%`;
  } catch {
    return 'N/A';
  }
}

export const RECOMMENDATION_COLORS: Record<string, string> = {
  'Strong Buy Signal': '#00C851',
  'Cautious Positive': '#33B5E5',
  Neutral: '#FFBB33',
  'Flag for Review': '#FF4444',
};

export const RECOMMENDATION_ICONS: Record<string, string> = {
  'Strong Buy Signal': '🟢',
  'Cautious Positive': '🔵',
  Neutral: '🟡',
  'Flag for Review': '🔴',
};

export function getConfidenceColor(score: number): string {
  if (score >= 0.8) return '#00C851';
  if (score >= 0.6) return '#33B5E5';
  if (score >= 0.4) return '#FFBB33';
  return '#FF4444';
}

export function getConfidenceLabel(score: number): string {
  if (score >= 0.8) return 'High Confidence';
  if (score >= 0.6) return 'Moderate Confidence';
  if (score >= 0.4) return 'Low Confidence';
  return 'Very Low Confidence';
}
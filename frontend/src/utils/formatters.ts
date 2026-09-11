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

export type RiskTone = 'low' | 'moderate' | 'elevated' | 'high';

export function getRiskTone(score: number): RiskTone {
  if (score <= 20) return 'low';
  if (score <= 45) return 'moderate';
  if (score <= 70) return 'elevated';
  return 'high';
}

export function getRecommendationTone(recommendation: string): RiskTone | 'info' {
  switch (recommendation) {
    case 'Strong Buy Signal':
      return 'low';
    case 'Cautious Positive':
      return 'info';
    case 'Neutral':
      return 'moderate';
    case 'Flag for Review':
      return 'high';
    default:
      return 'moderate';
  }
}

export function getConfidenceTone(score: number): RiskTone | 'info' {
  if (score >= 0.8) return 'low';
  if (score >= 0.6) return 'info';
  if (score >= 0.4) return 'moderate';
  return 'high';
}

export function getConfidenceLabel(score: number): string {
  if (score >= 0.8) return 'High Confidence';
  if (score >= 0.6) return 'Moderate Confidence';
  if (score >= 0.4) return 'Low Confidence';
  return 'Very Low Confidence';
}

// ---- Terminal identity helpers (risk color ramp mirrors backend thresholds) ----

export function getRiskColor(score: number): string {
  if (score <= 20) return 'var(--risk-low)';
  if (score <= 45) return 'var(--risk-moderate)';
  if (score <= 70) return 'var(--risk-elevated)';
  return 'var(--risk-high)';
}

export function getRiskLevel(score: number): string {
  if (score <= 20) return 'Low Risk';
  if (score <= 45) return 'Moderate Risk';
  if (score <= 70) return 'Elevated Risk';
  return 'High Risk';
}

/** One-line plain-English verdict for the hero zone (normals read this). */
export function getVerdictLine(
  riskScore: number,
  confidence: number,
  factorCount: number,
  recommendation: string,
): string {
  const flags = factorCount === 1 ? '1 risk flag' : `${factorCount} risk flags`;
  if (confidence < 0.5) {
    return `Low data confidence — treat this brief as preliminary; ${flags} raised.`;
  }
  if (recommendation === 'Flag for Review') {
    return `Flagged for review — ${flags} raised; read the risk section before deciding.`;
  }
  if (riskScore <= 20 && factorCount === 0) {
    return 'Looks stable — no risk flags raised on current data.';
  }
  return `${flags} raised — see what triggered them below.`;
}

/** Confidence as a sentence (Layer 1): never a bare number for normal users. */
export function getConfidenceSentence(confidence: number, errorCount: number): string {
  const pct = Math.round(confidence * 100);
  if (errorCount === 0) {
    return `${pct}% confident — all data sources agreed.`;
  }
  const gaps = errorCount === 1 ? '1 data gap' : `${errorCount} data gaps`;
  return `${pct}% confident — ${gaps} noted below.`;
}

/** Plain companion subtitle for the deterministic recommendation label. */
export function getRecommendationBlurb(recommendation: string): string {
  switch (recommendation) {
    case 'Strong Buy Signal':
      return 'Low risk with steady growth';
    case 'Cautious Positive':
      return 'Broadly sound, watch the flagged items';
    case 'Neutral':
      return 'Mixed picture — no clear edge either way';
    case 'Flag for Review':
      return 'Risks or data gaps need attention first';
    default:
      return '';
  }
}
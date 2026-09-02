export interface FinancialData {
  data_available: boolean;
  data_complete?: boolean;
  debt_to_equity: number | null;
  pe_ratio: number | null;
  yoy_revenue_growth: number | null;
  revenue_growth?: number | null;
  current_ratio: number | null;
  market_cap: number | null;
  revenue: number | null;
  net_income: number | null;
  cash_position: number | null;
}

export interface NewsData {
  sentiment_score: number;
  key_events: string[];
  red_flags: string[];
  news_available: boolean;
  summary: string;
}

export interface RiskData {
  risk_score: number;
  risk_factors: string[];
  risk_narrative: string;
}

export interface SynthesisReport {
  company_snapshot: string;
  financial_health: string;
  market_sentiment: string;
  risk_assessment: string;
  key_concerns: string[];
  analyst_recommendation: RecommendationType;
}

export type RecommendationType = 
  | 'Strong Buy Signal'
  | 'Cautious Positive'
  | 'Neutral'
  | 'Flag for Review';

export interface PipelineResult {
  ticker: string;
  company_name: string;
  confidence_score: number;
  errors: string[];
  financial_data: FinancialData;
  news_data: NewsData;
  risk_data: RiskData;
  synthesis_report: SynthesisReport;
}

export interface PipelineStatus {
  financial: 'available' | 'unavailable';
  news: 'available' | 'unavailable';
  risk: 'complete' | 'incomplete';
  synthesis: 'complete' | 'incomplete';
}
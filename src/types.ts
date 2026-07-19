export interface AssetSummary {
  asset_id: string;
  timestamp: string;
  failure_probability: number;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high' | 'unknown';
  prediction_id: number;
  rms?: number;
  kurtosis?: number;
  disagreement_flag?: boolean;
}

export interface JudgeOutput {
  failure_probability: number;
  confidence: number;
  rationale: string;
  disagreement_flag?: boolean;
}

export interface AssetDetail {
  id: number;
  asset_id: string;
  timestamp: string;
  actual_outcome: number | null;
  view1_text: string | null;
  view2_text: string | null;
  view3_text: string | null;
  view4_text: string | null;
  judge_output: JudgeOutput | null;
  created_at: string;
  rms?: number;
  kurtosis?: number;
  risk_level?: string;
  gate_reason?: string;
  sample_count?: number;
  failure_probability?: number;
  confidence?: number;
}

export interface CalibrationBin {
  bin_label: string;
  bin_mid: number;
  actual_rate: number;
  count: number;
}

export interface CalibrationPoint {
  predicted_probability: number;
  actual_outcome: number;
  confidence: number;
  squared_error: number;
}

export interface AgentTrustData {
  agent_name: string;
  label: string;
  accuracy: number;
  match_count: number;
  total_count: number;
}

export interface CalibrationData {
  brier_score: number;
  total_predictions: number;
  calibration_curve: CalibrationBin[];
  points: CalibrationPoint[];
  agent_trust: AgentTrustData[];
}
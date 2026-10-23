export type UserRole = 'ADMIN' | 'OFFICIAL' | 'INSTITUTION' | 'AUDITOR';

export type TrustLevel = 'L1_DECLARED' | 'L2_MACHINE_CHECKED' | 'L3_SOURCE_VERIFIED' | 'L4_SEALED';

export type CaseStatus = 'SUBMITTED' | 'IN_REVIEW' | 'VERIFIED' | 'FLAGGED' | 'RELEASE_REQUESTED' | 'RELEASED' | 'REJECTED';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  institution_id?: string | null;
  totp_enabled: boolean;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
}

export interface ExtractedField {
  id: string;
  field_name: string;
  raw_value: string | null;
  normalized_value: string | null;
  confidence_score: number;
  is_flagged_for_manual_review: boolean;
  manual_corrected_value?: string | null;
}

export interface ForensicFinding {
  id: string;
  check_name: string;
  category: string;
  status: 'PASS' | 'ANOMALY_FLAGGED' | 'ERROR';
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  details: Record<string, any>;
  is_resolved: boolean;
}

export interface DuplicateMatch {
  id: string;
  primary_case_id: string;
  matching_case_id: string;
  match_type: string;
  phash_distance: number | null;
  similarity_score: number;
  match_details: Record<string, any>;
  created_at: string;
}

export interface VerificationResult {
  id: string;
  connector_type: 'MOCK_ISSUER' | 'QR_CODE' | 'DIGITAL_SIGNATURE';
  status: 'CONFIRMED' | 'DISCREPANCY' | 'PENDING' | 'UNAVAILABLE';
  is_simulated: boolean;
  raw_response: Record<string, any>;
  created_at: string;
}

export interface RiskScore {
  id: string;
  overall_score: number;
  risk_band: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  shap_reasons: Array<{ feature: string; impact: number; reason: string }>;
  features_snapshot: Record<string, any>;
  created_at: string;
}

export interface TrustEvent {
  id: string;
  from_level: TrustLevel | null;
  to_level: TrustLevel;
  triggered_by: string;
  reason: string;
  notes?: string | null;
  created_at: string;
}

export interface FDRVersion {
  id: string;
  version_number: number;
  change_reason: string;
  created_at: string;
  extracted_fields: ExtractedField[];
  forensic_findings: ForensicFinding[];
  verification_results: VerificationResult[];
  risk_scores: RiskScore[];
}

export interface FDRCase {
  id: string;
  case_number: string;
  institution_id: string;
  institution?: { id: string; code: string; name: string; region: string } | null;
  bank_name: string;
  fdr_number: string;
  principal_amount: number;
  maturity_amount: number;
  interest_rate: number;
  issue_date: string;
  maturity_date: string;
  trust_level: TrustLevel;
  status: CaseStatus;
  current_version_id: string;
  created_at: string;
  updated_at: string;
  versions: FDRVersion[];
  trust_events: TrustEvent[];
  duplicate_matches?: DuplicateMatch[];
}

export interface FDRCaseListItem {
  id: string;
  case_number: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  fdr_number: string;
  principal_amount: number;
  maturity_amount: number;
  interest_rate: number;
  issue_date: string;
  maturity_date: string;
  trust_level: TrustLevel;
  status: CaseStatus;
  unresolved_flags_count: number;
  created_at: string;
}

export interface Alert {
  id: string;
  case_id: string;
  case_number?: string;
  alert_type: string;
  severity: 'INFO' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
  is_acknowledged: boolean;
  escalation_level: number;
  created_at: string;
}

export interface ReleaseRequest {
  id: string;
  case_id: string;
  institution_id: string;
  status: string;
  is_approved: boolean;
  approval_notes?: string | null;
  closure_report_path?: string | null;
  created_at: string;
}

export interface LiabilityForecastPoint {
  month: string;
  L1_DECLARED: number;
  L2_MACHINE_CHECKED: number;
  L3_SOURCE_VERIFIED: number;
  L4_SEALED: number;
  total_liability: number;
  maturing_count: number;
}

export interface LiabilityForecast {
  projection_months: number;
  total_active_liability: number;
  total_active_fdrs: number;
  timeline: LiabilityForecastPoint[];
}

export interface AuditLog {
  id: number;
  record_hash: string;
  prev_hash: string;
  actor_id: string;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: string;
  details_json: Record<string, any>;
  timestamp: string;
}

export interface AuditVerifyResult {
  is_valid: boolean;
  chain_length: number;
  last_verified_id: number | null;
  broken_index: number | null;
  message: string;
}

export interface AskSentinelResult {
  question: string;
  interpreted_query: {
    status?: string | null;
    trust_level?: string | null;
    bank_name?: string | null;
    min_amount?: number | null;
    max_amount?: number | null;
    region?: string | null;
    requires_attention?: boolean | null;
    intent: string;
  };
  total_matching: number;
  results: FDRCaseListItem[];
  audit_entry_id: number;
  latency_ms: number;
}

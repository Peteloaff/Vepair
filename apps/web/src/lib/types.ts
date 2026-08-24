export interface Profile {
  id: string;
  user_id: string;
  voice_use: string | null;
  is_singer: boolean | null;
  musical_style: string | null;
  practice_frequency: string | null;
  perceived_vocal_range: string | null;
  goals: string | null;
  vocal_coaching_history: string | null;
  under_professional_care: boolean | null;
  // Stage 9: set separately via PATCH /api/v1/profile/track, never through the onboarding PUT.
  track: VocalTrack | null;
  created_at: string;
  updated_at: string;
}

export type ProfileInput = Pick<
  Profile,
  | "voice_use"
  | "is_singer"
  | "musical_style"
  | "practice_frequency"
  | "perceived_vocal_range"
  | "goals"
  | "vocal_coaching_history"
  | "under_professional_care"
>;

export interface CheckIn {
  id: string;
  user_id: string;
  checkin_date: string;
  voice_quality: number | null;
  fatigue: number | null;
  throat_discomfort: number | null;
  speaking_load: string | null;
  singing_load: string | null;
  rehearsal_or_performance_yesterday: boolean | null;
  sleep_hours: number | null;
  hydration_estimate: string | null;
  alcohol_exposure: string | null;
  smoke_vape_exposure: string | null;
  illness_symptoms: string | null;
  reflux_symptoms: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type CheckInInput = Partial<
  Pick<
    CheckIn,
    | "voice_quality"
    | "fatigue"
    | "throat_discomfort"
    | "speaking_load"
    | "singing_load"
    | "rehearsal_or_performance_yesterday"
    | "sleep_hours"
    | "hydration_estimate"
    | "alcohol_exposure"
    | "smoke_vape_exposure"
    | "illness_symptoms"
    | "reflux_symptoms"
    | "notes"
  >
> & { checkin_date: string };

export interface RecordingQualityScore {
  score: number;
  label: "excellent" | "good" | "fair" | "poor";
  components: Record<string, string>;
}

export interface QualityFlags {
  duration_seconds: number;
  sample_rate: number;
  channels: number;
  peak_amplitude: number;
  rms: number;
  clipping: boolean;
  too_quiet: boolean;
  too_short: boolean;
  possible_background_noise: boolean;
  quality_score: RecordingQualityScore;
}

export interface AcousticMeasurement {
  f0_mean_hz: number | null;
  f0_median_hz: number | null;
  f0_min_hz: number | null;
  f0_max_hz: number | null;
  pitch_stability_semitones: number | null;
  jitter_percent: number | null;
  shimmer_percent: number | null;
  hnr_db: number | null;
  rms_loudness: number | null;
  spectral_centroid_hz: number | null;
  spectral_rolloff_hz: number | null;
  zero_crossing_rate: number | null;
  voiced_ratio: number | null;
}

export interface VoiceSession {
  id: string;
  started_at: string;
  completed_at: string | null;
  notes: string | null;
  device_metadata_id: string | null;
}

export interface Anomaly {
  metric_name: string;
  current_value: number;
  baseline_median: number;
  modified_z_score: number;
  message: string;
}

export interface Recording {
  id: string;
  voice_session_id: string;
  sample_type: string;
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
  quality_flags: QualityFlags | null;
  measurement: AcousticMeasurement | null;
  created_at: string;
  anomalies: Anomaly[];
}

export interface VoiceSessionWithRecordings extends VoiceSession {
  recordings: Recording[];
}

export interface Baseline {
  metric_name: string;
  median_value: number | null;
  mad_value: number | null;
  sample_count: number;
  confidence_pct: number | null;
  confidence_label: "insufficient" | "building" | "developing" | "established" | null;
  window_start: string | null;
  window_end: string | null;
}

export interface BaselineSummary {
  voice_baselines: Baseline[];
  voice_confidence_pct: number;
  voice_confidence_label: "insufficient" | "building" | "developing" | "established";
  usable_session_count: number;
  fatigue_baseline: Baseline | null;
}

export interface RecoveryScoreComponent {
  key: string;
  label: string;
  score: number | null;
  weight: number;
  included: boolean;
}

export interface RecoveryScoreFactor {
  direction: "positive" | "negative";
  text: string;
}

export type RecoveryStatus = "green" | "yellow" | "red" | "unknown";

export interface RecoveryScore {
  score_date: string;
  score_value: number | null;
  confidence_label: "insufficient" | "low" | "moderate" | "high";
  status: RecoveryStatus;
  status_label: string;
  safety_message: string | null;
  components: RecoveryScoreComponent[];
  factors: RecoveryScoreFactor[];
}

export interface Exercise {
  id: string;
  name: string;
  category: string;
  purpose: string;
  instructions: string;
  duration_seconds: number;
  difficulty: "easy" | "moderate" | "hard";
  audio_demo_url: string | null;
  contraindications: string | null;
  target_measurement: string | null;
  expected_result: string;
}

export const ROUTINE_LENGTHS_MINUTES = [5, 10, 15, 20] as const;
export type RoutineLengthMinutes = (typeof ROUTINE_LENGTHS_MINUTES)[number];

export interface Routine {
  length_minutes: number;
  intensity_cap: "low" | "moderate" | "high";
  total_duration_seconds: number;
  safety_message: string | null;
  reasons: string[];
  items: Exercise[];
  assigned_exercise_ids: string[];
  rest_day_recommended: boolean;
  rest_day_reason: string | null;
  exercise_tone_targets: Record<string, string>;
}

export interface RestCheck {
  rest_day_recommended: boolean;
  rest_day_reason: string | null;
}

export interface ExerciseSessionRecord {
  id: string;
  routine_length_minutes: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface ExerciseTrend {
  exercise_id: string;
  exercise_name: string;
  metric_name: string;
  direction: "improving" | "declining" | "stable" | "insufficient_data";
  recent_median: number | null;
  prior_median: number | null;
  attempt_count: number;
}

export interface RangeChange {
  semitones: number | null;
  from_note: string | null;
  to_note: string | null;
}

export interface VocalRangeHistoryEntry {
  measured_at: string;
  comfortable_low_note: string | null;
  comfortable_high_note: string | null;
  falsetto_high_note: string | null;
}

export interface VocalRangeSummary {
  current_low_note: string | null;
  current_high_note: string | null;
  current_falsetto_note: string | null;
  historical_best_low_note: string | null;
  historical_best_high_note: string | null;
  change_30d_high: RangeChange;
  change_90d_high: RangeChange;
  change_30d_low: RangeChange;
  change_90d_low: RangeChange;
  history: VocalRangeHistoryEntry[];
  stretch_target_note: string | null;
  stretch_target_reason: string | null;
}

export interface VocalGoal {
  target_low_note: string | null;
  target_avg_note: string | null;
  target_high_note: string | null;
  source: "ai" | "manual";
}

export type VocalTrack = "repair" | "improvement";

export interface VocalPlanTargetMilestones {
  goal: "stability" | "range_extension";
  description: string;
  target_stable_days?: number;
  target_semitones?: number;
  from_note?: string | null;
}

export interface VocalPlan {
  id: string;
  track: VocalTrack;
  start_date: string;
  target_end_date: string;
  status: "active" | "completed" | "superseded";
  baseline_snapshot: Record<string, unknown>;
  target_milestones: VocalPlanTargetMilestones;
  created_at: string;
  updated_at: string;
}

export interface PlanReadiness {
  ready: boolean;
  reasons: string[];
}

export interface VocalPlanView {
  plan: VocalPlan | null;
  readiness: PlanReadiness | null;
  just_graduated: boolean;
}

export interface TrackSetResult {
  track: VocalTrack;
  plan: VocalPlan | null;
  plan_pending_reason: string | null;
}

export interface TodaySnapshot {
  for_date: string;
  score_value: number | null;
  score_delta: number | null;
  measurement_confidence_label: string | null;
  low_measurement_confidence: boolean;
  comfortable_low_note: string | null;
  comfortable_high_note: string | null;
  range_span_semitones: number | null;
  pitch_stability_pct: number | null;
  vocal_endurance_seconds: number | null;
  reported_fatigue: number | null;
  vocal_load: string | null;
  training_completed_pct: number | null;
}

export interface RangeProgress {
  start_low_note: string | null;
  start_high_note: string | null;
  now_low_note: string | null;
  now_high_note: string | null;
  high_note_semitone_delta: number | null;
  start_basis: string;
}

export interface NumericProgress {
  start_value: number;
  now_value: number;
  delta: number;
  start_basis: string;
}

export interface ScoreHistoryPoint {
  score_date: string;
  score_value: number | null;
  confidence_label: string | null;
  status: RecoveryStatus | null;
}

export interface ConsistencyDay {
  for_date: string;
  sessions_completed: number;
}

export interface TrainingConsistency {
  days: ConsistencyDay[];
  current_streak_days: number;
  longest_streak_days: number;
  total_sessions_in_range: number;
}

export interface ProgressSnapshot {
  for_date: string;
  insufficient_data: boolean;
  valid_session_count: number;
  comfortable_range: RangeProgress | null;
  pitch_stability_pct: NumericProgress | null;
  vocal_endurance_seconds: NumericProgress | null;
  reported_fatigue: NumericProgress | null;
  days_tracked: number;
  sessions_completed: number;
  training_compliance_pct: number | null;
}

export type ConsentType =
  | "product_analytics"
  | "model_training"
  | "clinician_sharing"
  | "notifications";

export interface ConsentStatus {
  consent_type: ConsentType;
  granted: boolean | null;
  granted_at: string | null;
}

// --- Stage 12 Phase II: VepAIr Coach (dev-only, not yet linked into the live nav) ---

export type CoachShareCategory =
  | "recovery_trends"
  | "vocal_range"
  | "exercise_history"
  | "recordings";

export const COACH_SHARE_CATEGORIES: CoachShareCategory[] = [
  "recovery_trends",
  "vocal_range",
  "exercise_history",
  "recordings",
];

export const COACH_SHARE_CATEGORY_LABEL: Record<CoachShareCategory, string> = {
  recovery_trends: "Your recovery score & trends",
  vocal_range: "Your vocal range history",
  exercise_history: "Your exercise routine & completion history",
  recordings: "Your voice recordings (for side-by-side comparison)",
};

export interface SingerInvite {
  id: string;
  coach_display_name: string;
  coach_studio_name: string | null;
  message: string | null;
  created_at: string;
}

export interface CoachConnection {
  id: string;
  coach_display_name: string;
  coach_studio_name: string | null;
  status: "active" | "revoked";
  granted_categories: CoachShareCategory[];
  granted_at: string;
  revoked_at: string | null;
}

export interface SingerCoachNote {
  id: string;
  body: string;
  flagged_terms: string[] | null;
  created_at: string;
}

export interface CoachProfile {
  id: string;
  display_name: string;
  studio_name: string | null;
  created_at: string;
}

export interface CoachSingerListItem {
  singer_user_id: string;
  singer_email: string;
  coach_access_id: string;
  granted_categories: CoachShareCategory[];
  granted_at: string;
}

export interface CoachSentInvite {
  id: string;
  singer_email: string;
  status: "pending" | "accepted" | "declined" | "revoked";
  message: string | null;
  created_at: string;
  responded_at: string | null;
}

export interface CoachSingerSummary {
  singer_id: string;
  granted_categories: CoachShareCategory[];
  recovery_score: RecoveryScore | null;
  vocal_range: VocalRangeSummary | null;
  vocal_goal: VocalGoal | null;
  exercise_trends: ExerciseTrend[] | null;
  training_consistency: TrainingConsistency | null;
  todays_routine: Routine | null;
}

export interface CoachSingerHistory {
  granted_categories: CoachShareCategory[];
  score_history: ScoreHistoryPoint[] | null;
  checkins: CheckIn[] | null;
  training_consistency: TrainingConsistency | null;
  exercise_trends: ExerciseTrend[] | null;
}

export interface CoachAssignment {
  id: string;
  exercise_ids: string[];
  note_to_singer: string | null;
  status: "active" | "superseded";
  created_at: string;
  exercise_tone_targets: Record<string, string> | null;
}

export interface CoachVoiceSession {
  id: string;
  started_at: string;
  completed_at: string | null;
  device_metadata_id: string | null;
  recordings: Recording[];
}

// --- Backend Admin (post-Stage-12, minimal/unstyled v1) ---

export interface AdminUserListItem {
  id: string;
  email: string;
  account_type: "singer" | "coach";
  created_at: string;
  is_active: boolean;
  is_admin: boolean;
  onboarding_complete: boolean;
}

export interface AdminUserDetail extends AdminUserListItem {
  last_session_at: string | null;
  last_checkin_date: string | null;
  last_recording_at: string | null;
}

// SaaS billing, coach side (post-Stage-12 Part 2) -- see app.models.Organization.
export interface AdminOrganization {
  id: string;
  name: string | null;
  coach_email: string;
  coach_display_name: string;
  is_coach_pro_active: boolean;
  coach_pro_period_start: string | null;
  coach_pro_period_end: string | null;
  invite_quota_included: number;
  invites_used_this_period: number;
}

export interface AdminReportsSummary {
  total_users: number;
  singer_count: number;
  coach_count: number;
  active_count: number;
  deactivated_count: number;
  onboarding_completion_rate: number;
  signups_last_7_days: number;
  signups_last_90_days: number;
  dau: number;
  wau: number;
}

export interface AdminSiteSettings {
  signups_enabled: boolean;
  nda_required: boolean;
}

export interface NdaStatus {
  required: boolean;
  accepted_at: string | null;
}

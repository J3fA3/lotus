/**
 * TypeScript types for Intelligent Task Descriptions - Phase 6 Stage 2
 *
 * Mirrors Pydantic models from backend/models/intelligent_task.py
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum PriorityLevel {
  P0_CRITICAL = "P0_CRITICAL",
  P1_HIGH = "P1_HIGH",
  P2_MEDIUM = "P2_MEDIUM",
  P3_LOW = "P3_LOW"
}

export enum EffortEstimate {
  XS_15MIN = "XS_15MIN",
  S_1HR = "S_1HR",
  M_3HR = "M_3HR",
  L_1DAY = "L_1DAY",
  XL_3DAYS = "XL_3DAYS",
  XXL_1WEEK_PLUS = "XXL_1WEEK_PLUS"
}

export enum ConfidenceTier {
  HIGH = "HIGH",
  MEDIUM = "MEDIUM",
  LOW = "LOW"
}

// ============================================================================
// CONTEXT GAPS
// ============================================================================

export interface ContextGap {
  field_name: string;
  question: string;
  importance: "HIGH" | "MEDIUM" | "LOW";
  suggested_answer?: string;
  confidence: number; // 0.0-1.0
}

// ============================================================================
// SIMILAR TASKS
// ============================================================================

export interface SimilarTaskMatch {
  task_id: string;
  task_title: string;
  similarity_score: number; // 0.0-1.0
  explanation: string;
  outcome?: "COMPLETED" | "CANCELLED" | "IGNORED";
  completion_quality?: number; // 0.0-5.0
}

export interface RelatedTask {
  task_id: string;
  task_title: string;
  relationship_type: "BLOCKS" | "BLOCKED_BY" | "RELATED_TO" | "DEPENDS_ON";
  explanation: string;
}

// ============================================================================
// STAKEHOLDERS
// ============================================================================

export interface Stakeholder {
  name: string;
  role: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
}

// ============================================================================
// EXPANDABLE SECTIONS (TIER 2)
// ============================================================================

export interface WhyItMattersSection {
  business_value: string;
  user_impact: string;
  urgency_reason?: string;
  related_concepts: string[];
}

export interface WhatWasDiscussedSection {
  key_decisions: string[];
  open_questions: string[];
  conversation_thread_id?: string;
}

export interface HowToApproachSection {
  focus_areas: string[]; // 1-5 items
  potential_blockers: string[];
  success_criteria: string[];
  lessons_from_similar?: string;
}

export interface RelatedWorkSection {
  similar_tasks: SimilarTaskMatch[];
  blocking_tasks: RelatedTask[];
  stakeholders: Stakeholder[];
}

// ============================================================================
// AUTO-FILL METADATA
// ============================================================================

export interface AutoFillMetadata {
  field_name: string;
  confidence: number; // 0.0-1.0
  confidence_tier: ConfidenceTier;
  source: string; // "urgency_keywords", "concepts", "similar_tasks", etc.
  auto_filled: boolean;
  reasoning: string;
}

// ============================================================================
// INTELLIGENT TASK DESCRIPTION
// ============================================================================

export interface IntelligentTaskDescription {
  // Tier 1: Always Visible
  title: string;
  summary: string; // 50-75 words

  // Auto-fillable fields
  priority?: PriorityLevel;
  effort_estimate?: EffortEstimate;
  primary_project?: string;
  related_markets: string[];
  suggested_assignee?: string;

  // Tier 2: Expandable Sections
  why_it_matters?: WhyItMattersSection;
  what_was_discussed?: WhatWasDiscussedSection;
  how_to_approach?: HowToApproachSection;
  related_work?: RelatedWorkSection;

  // Metadata
  context_gaps: ContextGap[];
  auto_fill_metadata: AutoFillMetadata[];
  created_at: string;
  last_updated_at: string;
}

// ============================================================================
// QUALITY METRICS
// ============================================================================

export interface TaskDescriptionQuality {
  task_id: string;

  // Metrics
  sections_populated: number;
  sections_total: number;
  completeness_score: number; // 0.0-1.0

  total_word_count: number;
  richness_score: number; // 0.0-1.0

  has_focus_areas: boolean;
  actionability_score: number; // 0.0-1.0

  has_related_tasks: boolean;
  has_stakeholders: boolean;
  context_depth_score: number; // 0.0-1.0

  fields_auto_filled: number;
  fields_with_questions: number;
  auto_fill_success_rate: number; // 0.0-1.0

  // Trust signals (tracked over time)
  user_acted_without_editing?: boolean;
  user_made_minor_edits?: boolean;
  user_rewrote_completely?: boolean;

  // Overall
  overall_quality: number; // 0.0-1.0
  measured_at: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getPriorityLabel(priority: PriorityLevel): string {
  const labels: Record<PriorityLevel, string> = {
    [PriorityLevel.P0_CRITICAL]: "P0 Critical",
    [PriorityLevel.P1_HIGH]: "P1 High",
    [PriorityLevel.P2_MEDIUM]: "P2 Medium",
    [PriorityLevel.P3_LOW]: "P3 Low"
  };
  return labels[priority];
}

export function getEffortLabel(effort: EffortEstimate): string {
  const labels: Record<EffortEstimate, string> = {
    [EffortEstimate.XS_15MIN]: "XS (15 min)",
    [EffortEstimate.S_1HR]: "S (1 hour)",
    [EffortEstimate.M_3HR]: "M (3 hours)",
    [EffortEstimate.L_1DAY]: "L (1 day)",
    [EffortEstimate.XL_3DAYS]: "XL (3 days)",
    [EffortEstimate.XXL_1WEEK_PLUS]: "XXL (1+ week)"
  };
  return labels[effort];
}

export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-green-600 bg-green-50";
  if (confidence >= 0.6) return "text-yellow-600 bg-yellow-50";
  return "text-red-600 bg-red-50";
}

export function getConfidenceTierColor(tier: ConfidenceTier): string {
  const colors: Record<ConfidenceTier, string> = {
    [ConfidenceTier.HIGH]: "text-green-600 bg-green-50 border-green-200",
    [ConfidenceTier.MEDIUM]: "text-yellow-600 bg-yellow-50 border-yellow-200",
    [ConfidenceTier.LOW]: "text-red-600 bg-red-50 border-red-200"
  };
  return colors[tier];
}

// ============================================================================
// TASK VERSION CONTROL (Phase 6 Stage 3)
// ============================================================================

export interface TaskVersion {
  id: number;
  task_id: string;
  version_number: number;
  created_at: string;

  // Versioning type
  is_snapshot: boolean;
  is_milestone: boolean;

  // Provenance
  changed_by?: string;
  change_source: string;
  ai_model?: string;

  // Change detection
  change_type: string;
  changed_fields: string[];

  // Data (one will be populated)
  snapshot_data?: Record<string, any>;
  delta_data?: {
    old: Record<string, any>;
    new: Record<string, any>;
  };

  // PR-style comment
  pr_comment?: string;
  pr_comment_generated_at?: string;

  // Learning signals
  ai_suggestion_overridden: boolean;
  overridden_fields: string[];
  override_reason?: string;

  // Quality
  change_confidence?: number;
  user_approved?: boolean;
}

export interface TaskVersionHistoryResponse {
  task_id: string;
  total_versions: number;
  versions: TaskVersion[];
  has_more: boolean;
}

export interface VersionComparison {
  task_id: string;
  version_a: number;
  version_b: number;
  created_at_a: string;
  created_at_b: string;
  changed_fields: string[];
  diff: Record<string, { old: any; new: any }>;
}

// Helper functions for version display

export function getChangeTypeIcon(changeType: string): string {
  const icons: Record<string, string> = {
    created: "✨",
    status_change: "🔄",
    field_update: "📝",
    description_edit: "📄",
    ai_override: "💡"
  };
  return icons[changeType] || "📝";
}

export function getChangeTypeColor(changeType: string): string {
  const colors: Record<string, string> = {
    created: "bg-purple-50 text-purple-700 border-purple-200",
    status_change: "bg-blue-50 text-blue-700 border-blue-200",
    field_update: "bg-gray-50 text-gray-700 border-gray-200",
    description_edit: "bg-green-50 text-green-700 border-green-200",
    ai_override: "bg-amber-50 text-amber-700 border-amber-200"
  };
  return colors[changeType] || "bg-gray-50 text-gray-700 border-gray-200";
}

export function getChangeSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    user_edit: "User Edit",
    user_create: "User Created",
    ai_synthesis: "AI Created",
    ai_enrichment: "AI Enriched",
    system: "System"
  };
  return labels[source] || source;
}

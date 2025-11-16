/**
 * TypeScript types for Cognitive Nexus - LangGraph Agentic System
 */

/**
 * Entity extracted by the Entity Extraction Agent
 */
export interface Entity {
  id: number;
  name: string;
  type: "PERSON" | "PROJECT" | "COMPANY" | "DATE";
  confidence: number;
  created_at: string;
}

/**
 * Relationship between entities inferred by the Relationship Synthesis Agent
 */
export interface Relationship {
  id: number;
  subject: string;
  predicate: "WORKS_ON" | "COMMUNICATES_WITH" | "HAS_DEADLINE" | "MENTIONED_WITH";
  object: string;
  confidence: number;
}

/**
 * Quality metrics from agent self-evaluation
 */
export interface QualityMetrics {
  entity_quality: number;
  relationship_quality: number;
  task_quality: number;
  context_complexity: number;
}

/**
 * Response from context ingestion endpoint
 */
export interface ContextIngestResponse {
  context_item_id: number;
  entities_extracted: number;
  relationships_inferred: number;
  tasks_generated: number;
  quality_metrics: QualityMetrics;
  reasoning_steps: string[];
}

/**
 * Reasoning trace for a processed context item
 */
export interface ReasoningTrace {
  context_item_id: number;
  reasoning_steps: string[];
  extraction_strategy: "fast" | "detailed";
  quality_metrics: QualityMetrics;
}

/**
 * Context item summary
 */
export interface ContextSummary {
  id: number;
  source_type: "slack" | "transcript" | "manual";
  source_identifier: string | null;
  created_at: string;
  extraction_strategy: "fast" | "detailed";
  context_complexity: number;
  entity_count: number;
  relationship_count: number;
  quality_metrics: QualityMetrics;
}

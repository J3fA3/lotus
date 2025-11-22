"""
Intelligent Task Description Models - Phase 6 Stage 2

2-tier information architecture for contextual task synthesis:
Tier 1: Summary (50-75 words) - Always visible
Tier 2: Expandable sections - User expands on demand

Design Decisions:
- JSON storage with strict Pydantic validation (flexibility + consistency)
- Auto-fill confidence thresholds by field type (0.6-0.8)
- Quality measurement metrics (completeness, richness, actionability, context depth)
- Trust signal tracking (user acted on without editing)
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class PriorityLevel(str, Enum):
    """Task priority levels."""
    P0_CRITICAL = "P0_CRITICAL"  # Immediate action required
    P1_HIGH = "P1_HIGH"  # Important, schedule soon
    P2_MEDIUM = "P2_MEDIUM"  # Normal priority
    P3_LOW = "P3_LOW"  # Nice to have


class EffortEstimate(str, Enum):
    """Effort estimation buckets."""
    XS_15MIN = "XS_15MIN"  # 15 minutes
    S_1HR = "S_1HR"  # 1 hour
    M_3HR = "M_3HR"  # 3 hours
    L_1DAY = "L_1DAY"  # 1 day
    XL_3DAYS = "XL_3DAYS"  # 3 days
    XXL_1WEEK_PLUS = "XXL_1WEEK_PLUS"  # 1+ weeks


class ConfidenceTier(str, Enum):
    """Confidence levels for auto-filled fields."""
    HIGH = "HIGH"  # >0.8 - Can auto-fill without question
    MEDIUM = "MEDIUM"  # 0.6-0.8 - Auto-fill but flag for review
    LOW = "LOW"  # <0.6 - Generate question instead


# ============================================================================
# CONTEXT GAP DETECTION
# ============================================================================

class ContextGap(BaseModel):
    """Represents missing information that should be clarified."""
    field_name: str = Field(..., description="Field that needs clarification")
    question: str = Field(..., description="Specific question to ask user")
    importance: str = Field(..., description="HIGH/MEDIUM/LOW")
    suggested_answer: Optional[str] = Field(None, description="Best guess if available")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in suggested answer")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "assignee",
                "question": "Who should be assigned to implement the Gmail OAuth fix?",
                "importance": "MEDIUM",
                "suggested_answer": "backend-team",
                "confidence": 0.4
            }
        }


# ============================================================================
# RELATED TASKS AND SIMILARITY
# ============================================================================

class SimilarTaskMatch(BaseModel):
    """Similar task with explanation of relevance."""
    task_id: str
    task_title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., description="Why this task is similar/relevant")
    outcome: Optional[str] = Field(None, description="COMPLETED/CANCELLED/IGNORED if available")
    completion_quality: Optional[float] = Field(None, description="0.0-5.0 if available")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-123",
                "task_title": "Fix Gmail API rate limiting",
                "similarity_score": 0.87,
                "explanation": "Both involve Gmail API error handling and OAuth flows",
                "outcome": "COMPLETED",
                "completion_quality": 4.2
            }
        }


class RelatedTask(BaseModel):
    """Task with explicit relationship."""
    task_id: str
    task_title: str
    relationship_type: str = Field(..., description="BLOCKS/BLOCKED_BY/RELATED_TO/DEPENDS_ON")
    explanation: str = Field(..., description="Nature of the relationship")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-456",
                "task_title": "Deploy Gmail service to production",
                "relationship_type": "BLOCKED_BY",
                "explanation": "Cannot deploy until OAuth bug is fixed"
            }
        }


# ============================================================================
# STAKEHOLDER INFORMATION
# ============================================================================

class Stakeholder(BaseModel):
    """Person or team affected by this task."""
    name: str = Field(..., description="Person or team name")
    role: str = Field(..., description="Their role/interest in this task")
    priority: str = Field(..., description="HIGH/MEDIUM/LOW importance to them")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Sales Team",
                "role": "Needs Gmail integration for client demos",
                "priority": "HIGH"
            }
        }


# ============================================================================
# EXPANDABLE SECTIONS (TIER 2)
# ============================================================================

class WhyItMattersSection(BaseModel):
    """Context about strategic importance."""
    business_value: str = Field(..., description="Why this matters to the business/user")
    user_impact: str = Field(..., description="Who benefits and how")
    urgency_reason: Optional[str] = Field(None, description="Why this is time-sensitive")
    related_concepts: List[str] = Field(default_factory=list, description="Strategic concepts from KG")

    @validator('business_value', 'user_impact')
    def validate_non_empty(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Section must have meaningful content (>10 chars)")
        return v


class WhatWasDiscussedSection(BaseModel):
    """Conversation history and decisions."""
    key_decisions: List[str] = Field(default_factory=list, description="Major decisions made")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")
    conversation_thread_id: Optional[str] = Field(None, description="Link to KG conversation node")

    @validator('key_decisions', 'open_questions')
    def validate_at_least_one(cls, v, values):
        # Must have either key_decisions or open_questions
        return v


class HowToApproachSection(BaseModel):
    """Implementation guidance."""
    focus_areas: List[str] = Field(..., min_items=1, description="What to focus on (2-4 items)")
    potential_blockers: List[str] = Field(default_factory=list, description="Known obstacles")
    success_criteria: List[str] = Field(default_factory=list, description="What 'done' looks like")
    lessons_from_similar: Optional[str] = Field(None, description="Lessons from similar tasks")

    @validator('focus_areas')
    def validate_focus_areas(cls, v):
        if len(v) < 1 or len(v) > 5:
            raise ValueError("Focus areas should have 1-5 items")
        return v


class RelatedWorkSection(BaseModel):
    """Links to related tasks and context."""
    similar_tasks: List[SimilarTaskMatch] = Field(default_factory=list, description="Similar tasks with explanations")
    blocking_tasks: List[RelatedTask] = Field(default_factory=list, description="Tasks blocking this one")
    stakeholders: List[Stakeholder] = Field(default_factory=list, description="People/teams affected")


# ============================================================================
# AUTO-FILL METADATA
# ============================================================================

class AutoFillMetadata(BaseModel):
    """Metadata about auto-filled fields and confidence."""
    field_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    source: str = Field(..., description="Where this value came from (e.g., 'similar_tasks', 'concepts', 'conversation')")
    auto_filled: bool = Field(..., description="True if we auto-filled, False if we generated question")
    reasoning: str = Field(..., description="Why we chose this value")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "priority",
                "confidence": 0.85,
                "confidence_tier": "HIGH",
                "source": "urgency_keywords",
                "auto_filled": True,
                "reasoning": "Detected urgency keywords: 'ASAP', 'blocking production'"
            }
        }


# ============================================================================
# MAIN INTELLIGENT TASK DESCRIPTION
# ============================================================================

class IntelligentTaskDescription(BaseModel):
    """
    Intelligent Task Description with 2-tier architecture.

    Tier 1 (Always Visible):
    - Title
    - Summary (50-75 words)
    - Priority, effort, project, assignee

    Tier 2 (Expandable):
    - Why it Matters
    - What Was Discussed
    - How to Approach
    - Related Work
    """

    # ========== TIER 1: ALWAYS VISIBLE ==========

    title: str = Field(..., min_length=5, max_length=200, description="Clear, actionable title")

    summary: str = Field(
        ...,
        min_length=50,
        max_length=500,
        description="Concise summary (50-75 words) - what, why, who"
    )

    # Auto-fillable fields (with confidence tracking)
    priority: Optional[PriorityLevel] = Field(None, description="Inferred from urgency signals")
    effort_estimate: Optional[EffortEstimate] = Field(None, description="Inferred from similar tasks")
    primary_project: Optional[str] = Field(None, description="Inferred from concepts")
    related_markets: List[str] = Field(default_factory=list, description="Inferred from concepts")
    suggested_assignee: Optional[str] = Field(None, description="Inferred from relationships")

    # ========== TIER 2: EXPANDABLE SECTIONS ==========

    why_it_matters: Optional[WhyItMattersSection] = None
    what_was_discussed: Optional[WhatWasDiscussedSection] = None
    how_to_approach: Optional[HowToApproachSection] = None
    related_work: Optional[RelatedWorkSection] = None

    # ========== METADATA ==========

    context_gaps: List[ContextGap] = Field(
        default_factory=list,
        description="Questions to ask user for missing info"
    )

    auto_fill_metadata: List[AutoFillMetadata] = Field(
        default_factory=list,
        description="Confidence tracking for auto-filled fields"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('summary')
    def validate_summary_word_count(cls, v):
        """Ensure summary is 50-75 words (target), allow 50-100 (acceptable)."""
        word_count = len(v.split())
        if word_count < 50:
            raise ValueError(f"Summary too short ({word_count} words). Target: 50-75 words.")
        if word_count > 150:
            raise ValueError(f"Summary too long ({word_count} words). Target: 50-75 words, max 150.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Fix Gmail OAuth token refresh bug",
                "summary": "Gmail service is failing to refresh OAuth tokens, causing authentication errors for 15+ users. Need to update token refresh logic in email polling service and add retry mechanism. This is blocking production Gmail integration for new clients and affecting current user satisfaction.",
                "priority": "P1_HIGH",
                "effort_estimate": "M_3HR",
                "primary_project": "Lotus Email Integration",
                "related_markets": ["SaaS", "Email Automation"],
                "suggested_assignee": "backend-team",
                "why_it_matters": {
                    "business_value": "Gmail integration is a key selling point for new clients. Current failures are preventing demos and affecting sales pipeline.",
                    "user_impact": "15 active users cannot access their Gmail data, impacting their daily workflow",
                    "urgency_reason": "Sales demo scheduled in 2 days requires working Gmail integration",
                    "related_concepts": ["OAuth 2.0", "Gmail API", "Email Polling"]
                },
                "context_gaps": [
                    {
                        "field_name": "assignee",
                        "question": "Should this be assigned to the backend team or a specific developer?",
                        "importance": "MEDIUM",
                        "suggested_answer": "backend-team",
                        "confidence": 0.5
                    }
                ],
                "auto_fill_metadata": [
                    {
                        "field_name": "priority",
                        "confidence": 0.85,
                        "confidence_tier": "HIGH",
                        "source": "urgency_keywords",
                        "auto_filled": True,
                        "reasoning": "Detected urgency: 'blocking production', '15+ users affected'"
                    }
                ]
            }
        }


# ============================================================================
# QUALITY MEASUREMENT
# ============================================================================

class TaskDescriptionQuality(BaseModel):
    """
    Quality metrics for task descriptions.

    Ultimate metric: Trust Index (user acted on without editing)
    Supporting metrics: Completeness, richness, actionability, context depth
    """

    task_id: str

    # Completeness: % of sections populated
    sections_populated: int = Field(..., description="Number of Tier 2 sections with content")
    sections_total: int = Field(default=4, description="Total possible Tier 2 sections")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="sections_populated / sections_total")

    # Richness: Total word count in expandable sections
    total_word_count: int = Field(..., description="Words across all Tier 2 sections")
    richness_score: float = Field(..., ge=0.0, le=1.0, description="0.0 if <100 words, 1.0 if >300 words")

    # Actionability: Has specific focus areas
    has_focus_areas: bool = Field(..., description="True if how_to_approach has focus_areas")
    actionability_score: float = Field(..., ge=0.0, le=1.0, description="1.0 if has_focus_areas else 0.0")

    # Context depth: Has related tasks + stakeholders
    has_related_tasks: bool = Field(..., description="True if related_work has similar/blocking tasks")
    has_stakeholders: bool = Field(..., description="True if related_work has stakeholders")
    context_depth_score: float = Field(..., ge=0.0, le=1.0, description="0.0, 0.5, or 1.0 based on depth")

    # Auto-fill success: % of fields auto-filled vs questions generated
    fields_auto_filled: int = Field(..., description="Number of fields auto-filled with high confidence")
    fields_with_questions: int = Field(..., description="Number of fields that generated questions")
    auto_fill_success_rate: float = Field(..., ge=0.0, le=1.0)

    # ULTIMATE METRIC: Trust signal
    user_acted_without_editing: Optional[bool] = Field(None, description="True if user used task as-is")
    user_made_minor_edits: Optional[bool] = Field(None, description="True if user made small tweaks")
    user_rewrote_completely: Optional[bool] = Field(None, description="True if user rewrote from scratch")

    # Overall quality score (0.0-1.0)
    overall_quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted average of all quality metrics"
    )

    # Timestamps
    measured_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('completeness_score')
    def calculate_completeness(cls, v, values):
        """Auto-calculate completeness from sections."""
        if 'sections_populated' in values and 'sections_total' in values:
            return values['sections_populated'] / max(values['sections_total'], 1)
        return v

    @validator('richness_score')
    def calculate_richness(cls, v, values):
        """Auto-calculate richness from word count."""
        if 'total_word_count' in values:
            word_count = values['total_word_count']
            if word_count < 100:
                return 0.0
            elif word_count > 300:
                return 1.0
            else:
                return (word_count - 100) / 200  # Linear 100-300
        return v

    @validator('context_depth_score')
    def calculate_context_depth(cls, v, values):
        """Auto-calculate context depth."""
        has_tasks = values.get('has_related_tasks', False)
        has_stakeholders = values.get('has_stakeholders', False)

        if has_tasks and has_stakeholders:
            return 1.0
        elif has_tasks or has_stakeholders:
            return 0.5
        else:
            return 0.0

    @validator('overall_quality')
    def calculate_overall_quality(cls, v, values):
        """
        Calculate weighted overall quality.

        Weights:
        - Completeness: 25%
        - Richness: 20%
        - Actionability: 30% (most important - user needs to know what to do)
        - Context depth: 15%
        - Auto-fill success: 10%
        """
        completeness = values.get('completeness_score', 0.0)
        richness = values.get('richness_score', 0.0)
        actionability = values.get('actionability_score', 0.0)
        context_depth = values.get('context_depth_score', 0.0)
        auto_fill = values.get('auto_fill_success_rate', 0.0)

        overall = (
            completeness * 0.25 +
            richness * 0.20 +
            actionability * 0.30 +
            context_depth * 0.15 +
            auto_fill * 0.10
        )

        return round(overall, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-123",
                "sections_populated": 3,
                "sections_total": 4,
                "completeness_score": 0.75,
                "total_word_count": 250,
                "richness_score": 0.75,
                "has_focus_areas": True,
                "actionability_score": 1.0,
                "has_related_tasks": True,
                "has_stakeholders": True,
                "context_depth_score": 1.0,
                "fields_auto_filled": 4,
                "fields_with_questions": 1,
                "auto_fill_success_rate": 0.8,
                "user_acted_without_editing": True,
                "overall_quality": 0.82
            }
        }


# ============================================================================
# GEMINI STRUCTURED OUTPUT SCHEMAS
# ============================================================================

class TaskSynthesisRequest(BaseModel):
    """Request schema for task synthesis."""
    raw_input: str = Field(..., description="User's original input")
    user_profile: Optional[Dict] = Field(None, description="User preferences and context")
    rich_context: Optional[Dict] = Field(None, description="KG context (concepts, conversations, outcomes)")
    similar_tasks: List[SimilarTaskMatch] = Field(default_factory=list, description="Pre-computed similar tasks")


class TaskSynthesisResult(BaseModel):
    """
    Result from Gemini task synthesis.

    This is what Gemini returns when synthesizing a task from raw input + context.
    """
    task_description: IntelligentTaskDescription
    synthesis_reasoning: str = Field(..., description="Gemini's reasoning for how it synthesized this")
    confidence_overall: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in synthesis")

    class Config:
        json_schema_extra = {
            "example": {
                "task_description": {
                    "title": "Fix Gmail OAuth token refresh bug",
                    "summary": "Gmail service failing to refresh OAuth tokens..."
                },
                "synthesis_reasoning": "Based on similar OAuth issues in the past and urgency keywords, this appears to be a high-priority backend fix requiring token refresh logic update.",
                "confidence_overall": 0.82
            }
        }

/**
 * Intelligent Task Display Component - Phase 6 Stage 2
 *
 * 2-tier information architecture:
 * - Tier 1: Summary (always visible) - Title, summary, auto-filled fields
 * - Tier 2: Expandable sections - User expands on demand
 *
 * Features:
 * - Auto-fill confidence indicators
 * - Context gap badges
 * - Expandable rich sections
 * - Quality metrics display
 */

import { useState } from "react";
import {
  IntelligentTaskDescription,
  TaskDescriptionQuality,
  AutoFillMetadata,
  ContextGap,
  getPriorityLabel,
  getEffortLabel,
  getConfidenceTierColor,
  PriorityLevel,
  EffortEstimate
} from "@/types/intelligent-task";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ChevronDown,
  ChevronRight,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Target,
  Lightbulb,
  Users,
  Link as LinkIcon,
  TrendingUp
} from "lucide-react";
import { cn } from "@/lib/utils";

// ============================================================================
// PROPS
// ============================================================================

interface IntelligentTaskDisplayProps {
  taskDescription: IntelligentTaskDescription;
  quality?: TaskDescriptionQuality;
  onAnswerGap?: (gap: ContextGap) => void;
  onEdit?: (field: string, value: any) => void;
  className?: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function IntelligentTaskDisplay({
  taskDescription,
  quality,
  onAnswerGap,
  onEdit,
  className
}: IntelligentTaskDisplayProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const toggleSection = (sectionName: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionName)) {
        next.delete(sectionName);
      } else {
        next.add(sectionName);
      }
      return next;
    });
  };

  // Get metadata for a field
  const getFieldMetadata = (fieldName: string): AutoFillMetadata | undefined => {
    return taskDescription.auto_fill_metadata.find(m => m.field_name === fieldName);
  };

  // Get context gap for a field
  const getFieldGap = (fieldName: string): ContextGap | undefined => {
    return taskDescription.context_gaps.find(g => g.field_name === fieldName);
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* TIER 1: ALWAYS VISIBLE */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              {taskDescription.title}
              {quality && quality.overall_quality >= 0.7 && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Sparkles className="h-5 w-5 text-purple-500" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="text-sm">
                        <div className="font-semibold">High Quality Task</div>
                        <div className="text-muted-foreground">
                          Quality Score: {(quality.overall_quality * 100).toFixed(0)}%
                        </div>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </CardTitle>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Summary */}
          <div className="text-base text-muted-foreground leading-relaxed">
            {taskDescription.summary}
          </div>

          <Separator />

          {/* Auto-Filled Fields */}
          <div className="grid grid-cols-2 gap-4">
            {/* Priority */}
            <AutoFilledField
              label="Priority"
              value={taskDescription.priority ? getPriorityLabel(taskDescription.priority) : undefined}
              metadata={getFieldMetadata("priority")}
              gap={getFieldGap("priority")}
              onAnswerGap={onAnswerGap}
              icon={<Target className="h-4 w-4" />}
            />

            {/* Effort */}
            <AutoFilledField
              label="Effort"
              value={taskDescription.effort_estimate ? getEffortLabel(taskDescription.effort_estimate) : undefined}
              metadata={getFieldMetadata("effort_estimate")}
              gap={getFieldGap("effort_estimate")}
              onAnswerGap={onAnswerGap}
              icon={<TrendingUp className="h-4 w-4" />}
            />

            {/* Project */}
            <AutoFilledField
              label="Project"
              value={taskDescription.primary_project}
              metadata={getFieldMetadata("primary_project")}
              gap={getFieldGap("primary_project")}
              onAnswerGap={onAnswerGap}
              icon={<LinkIcon className="h-4 w-4" />}
            />

            {/* Assignee */}
            <AutoFilledField
              label="Assignee"
              value={taskDescription.suggested_assignee}
              metadata={getFieldMetadata("suggested_assignee")}
              gap={getFieldGap("suggested_assignee")}
              onAnswerGap={onAnswerGap}
              icon={<Users className="h-4 w-4" />}
            />
          </div>

          {/* Related Markets (if any) */}
          {taskDescription.related_markets.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">Markets:</span>
              {taskDescription.related_markets.map(market => (
                <Badge key={market} variant="outline" className="text-xs">
                  {market}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* TIER 2: EXPANDABLE SECTIONS */}
      <div className="space-y-2">
        {/* Why It Matters */}
        {taskDescription.why_it_matters && (
          <ExpandableSection
            title="Why It Matters"
            icon={<Sparkles className="h-4 w-4" />}
            isExpanded={expandedSections.has("why")}
            onToggle={() => toggleSection("why")}
          >
            <div className="space-y-3">
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-1">Business Value</div>
                <div className="text-sm">{taskDescription.why_it_matters.business_value}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-1">User Impact</div>
                <div className="text-sm">{taskDescription.why_it_matters.user_impact}</div>
              </div>
              {taskDescription.why_it_matters.urgency_reason && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Urgency</div>
                  <div className="text-sm text-orange-600">{taskDescription.why_it_matters.urgency_reason}</div>
                </div>
              )}
              {taskDescription.why_it_matters.related_concepts.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Related Concepts</div>
                  <div className="flex flex-wrap gap-1">
                    {taskDescription.why_it_matters.related_concepts.map(concept => (
                      <Badge key={concept} variant="secondary" className="text-xs">
                        {concept}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ExpandableSection>
        )}

        {/* What Was Discussed */}
        {taskDescription.what_was_discussed && (
          <ExpandableSection
            title="What Was Discussed"
            icon={<AlertCircle className="h-4 w-4" />}
            isExpanded={expandedSections.has("discussed")}
            onToggle={() => toggleSection("discussed")}
          >
            <div className="space-y-3">
              {taskDescription.what_was_discussed.key_decisions.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Key Decisions</div>
                  <ul className="list-disc list-inside space-y-1">
                    {taskDescription.what_was_discussed.key_decisions.map((decision, idx) => (
                      <li key={idx} className="text-sm">{decision}</li>
                    ))}
                  </ul>
                </div>
              )}
              {taskDescription.what_was_discussed.open_questions.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Open Questions</div>
                  <ul className="list-disc list-inside space-y-1">
                    {taskDescription.what_was_discussed.open_questions.map((question, idx) => (
                      <li key={idx} className="text-sm text-yellow-700">{question}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </ExpandableSection>
        )}

        {/* How to Approach */}
        {taskDescription.how_to_approach && (
          <ExpandableSection
            title="How to Approach"
            icon={<Lightbulb className="h-4 w-4" />}
            isExpanded={expandedSections.has("approach")}
            onToggle={() => toggleSection("approach")}
            defaultExpanded={true} // This is most actionable - default open
          >
            <div className="space-y-3">
              {/* Focus Areas (REQUIRED) */}
              <div>
                <div className="text-sm font-medium text-muted-foreground mb-2">Focus Areas</div>
                <ul className="space-y-2">
                  {taskDescription.how_to_approach.focus_areas.map((area, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{area}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Potential Blockers */}
              {taskDescription.how_to_approach.potential_blockers.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Potential Blockers</div>
                  <ul className="list-disc list-inside space-y-1">
                    {taskDescription.how_to_approach.potential_blockers.map((blocker, idx) => (
                      <li key={idx} className="text-sm text-red-600">{blocker}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Success Criteria */}
              {taskDescription.how_to_approach.success_criteria.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Success Criteria</div>
                  <ul className="list-disc list-inside space-y-1">
                    {taskDescription.how_to_approach.success_criteria.map((criteria, idx) => (
                      <li key={idx} className="text-sm">{criteria}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Lessons from Similar Tasks */}
              {taskDescription.how_to_approach.lessons_from_similar && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <div className="text-sm font-medium text-purple-900 mb-1">💡 Lessons from Similar Tasks</div>
                  <div className="text-sm text-purple-700">{taskDescription.how_to_approach.lessons_from_similar}</div>
                </div>
              )}
            </div>
          </ExpandableSection>
        )}

        {/* Related Work */}
        {taskDescription.related_work && (
          <ExpandableSection
            title="Related Work"
            icon={<LinkIcon className="h-4 w-4" />}
            isExpanded={expandedSections.has("related")}
            onToggle={() => toggleSection("related")}
          >
            <div className="space-y-4">
              {/* Similar Tasks */}
              {taskDescription.related_work.similar_tasks.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Similar Tasks</div>
                  <div className="space-y-2">
                    {taskDescription.related_work.similar_tasks.map((task) => (
                      <div key={task.task_id} className="border rounded-lg p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{task.task_title}</span>
                          <Badge variant="outline" className="text-xs">
                            {(task.similarity_score * 100).toFixed(0)}% similar
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">{task.explanation}</div>
                        {task.outcome && (
                          <div className="flex items-center gap-2 text-xs">
                            <Badge variant={task.outcome === "COMPLETED" ? "default" : "secondary"}>
                              {task.outcome}
                            </Badge>
                            {task.completion_quality && (
                              <span className="text-muted-foreground">
                                Quality: {task.completion_quality.toFixed(1)}/5.0
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Blocking Tasks */}
              {taskDescription.related_work.blocking_tasks.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Blocking Tasks</div>
                  <div className="space-y-2">
                    {taskDescription.related_work.blocking_tasks.map((task) => (
                      <div key={task.task_id} className="border border-orange-200 bg-orange-50 rounded-lg p-3 space-y-1">
                        <div className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4 text-orange-600" />
                          <span className="text-sm font-medium">{task.task_title}</span>
                          <Badge variant="outline" className="text-xs">{task.relationship_type}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground pl-6">{task.explanation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Stakeholders */}
              {taskDescription.related_work.stakeholders.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-2">Stakeholders</div>
                  <div className="grid grid-cols-2 gap-2">
                    {taskDescription.related_work.stakeholders.map((stakeholder, idx) => (
                      <div key={idx} className="border rounded-lg p-2 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{stakeholder.name}</span>
                          <Badge variant={stakeholder.priority === "HIGH" ? "default" : "secondary"} className="text-xs">
                            {stakeholder.priority}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">{stakeholder.role}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ExpandableSection>
        )}
      </div>

      {/* CONTEXT GAPS SECTION */}
      {taskDescription.context_gaps.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              Questions ({taskDescription.context_gaps.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {taskDescription.context_gaps.map((gap, idx) => (
                <div key={idx} className="bg-white border border-yellow-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="text-sm font-medium">{gap.question}</div>
                      {gap.suggested_answer && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Suggestion: {gap.suggested_answer} (confidence: {(gap.confidence * 100).toFixed(0)}%)
                        </div>
                      )}
                    </div>
                    <Badge variant={gap.importance === "HIGH" ? "default" : "secondary"} className="text-xs">
                      {gap.importance}
                    </Badge>
                  </div>
                  {onAnswerGap && (
                    <Button size="sm" variant="outline" onClick={() => onAnswerGap(gap)} className="w-full">
                      Answer Question
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* QUALITY METRICS (DEBUG/ADMIN) */}
      {quality && process.env.NODE_ENV === 'development' && (
        <Card className="border-purple-200 bg-purple-50">
          <CardHeader>
            <CardTitle className="text-sm text-purple-900">Quality Metrics (Dev Only)</CardTitle>
          </CardHeader>
          <CardContent className="text-xs space-y-1 text-purple-800">
            <div>Overall Quality: {(quality.overall_quality * 100).toFixed(0)}%</div>
            <div>Completeness: {(quality.completeness_score * 100).toFixed(0)}%</div>
            <div>Actionability: {(quality.actionability_score * 100).toFixed(0)}%</div>
            <div>Auto-Fill Success: {(quality.auto_fill_success_rate * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

interface AutoFilledFieldProps {
  label: string;
  value?: string;
  metadata?: AutoFillMetadata;
  gap?: ContextGap;
  onAnswerGap?: (gap: ContextGap) => void;
  icon: React.ReactNode;
}

function AutoFilledField({ label, value, metadata, gap, onAnswerGap, icon }: AutoFilledFieldProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>
      {value && metadata ? (
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{value}</span>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Badge className={cn("text-xs", getConfidenceTierColor(metadata.confidence_tier))}>
                  AI {metadata.confidence_tier}
                </Badge>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-1 text-xs">
                  <div><strong>Confidence:</strong> {(metadata.confidence * 100).toFixed(0)}%</div>
                  <div><strong>Source:</strong> {metadata.source}</div>
                  <div><strong>Reasoning:</strong> {metadata.reasoning}</div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ) : gap ? (
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs text-yellow-600">
            Needs Input
          </Badge>
          {onAnswerGap && (
            <Button size="sm" variant="ghost" onClick={() => onAnswerGap(gap)} className="h-6 px-2 text-xs">
              Answer
            </Button>
          )}
        </div>
      ) : value ? (
        <span className="text-sm">{value}</span>
      ) : (
        <span className="text-sm text-muted-foreground">Not set</span>
      )}
    </div>
  );
}

interface ExpandableSectionProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

function ExpandableSection({ title, icon, isExpanded, onToggle, children, defaultExpanded = false }: ExpandableSectionProps) {
  return (
    <Collapsible open={isExpanded} onOpenChange={onToggle} defaultOpen={defaultExpanded}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors p-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                {icon}
                {title}
              </CardTitle>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 pb-4">
            {children}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

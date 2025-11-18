/**
 * Context Analysis Dialog - Main UI for Cognitive Nexus
 *
 * Allows users to:
 * 1. Input context (Slack messages, meeting notes, etc.)
 * 2. Process through LangGraph agents
 * 3. View results: entities, relationships, reasoning traces, quality metrics
 */
import { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Brain, Loader2, Sparkles, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

import { ingestContext, getEntities, getRelationships } from "@/api/cognitivenexus";
import { ContextIngestResponse, Entity, Relationship } from "@/types/cognitivenexus";
import { ReasoningTraceView } from "./ReasoningTraceView";
import { EntityVisualization } from "./EntityVisualization";
import { QualityMetricsDisplay } from "./QualityMetricsDisplay";

const PLACEHOLDER_TEXT = `Paste Slack messages, meeting notes, or any context here.

Example:
Hey Jef, can you share the CRESCO data with Andy by Friday?
Also, please check with Sarah from Co-op about the deployment timeline.
We need to get the API integration done before November 26th.`;

interface ContextAnalysisDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ContextAnalysisDialog = ({
  open,
  onOpenChange,
}: ContextAnalysisDialogProps) => {
  const [inputText, setInputText] = useState("");
  const [sourceType, setSourceType] = useState<"slack" | "transcript" | "manual">("manual");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ContextIngestResponse | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleClose = useCallback(() => {
    setInputText("");
    setSourceType("manual");
    setResult(null);
    setEntities([]);
    setRelationships([]);
    setError(null);
    setIsAnalyzing(false);
    onOpenChange(false);
  }, [onOpenChange]);

  const handleAnalyze = useCallback(async () => {
    if (!inputText.trim()) {
      toast.error("Please enter some context to analyze");
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // Process context through LangGraph agents
      const analysisResult = await ingestContext(inputText, sourceType);
      setResult(analysisResult);

      // Fetch detailed entities and relationships
      const [entitiesData, relationshipsData] = await Promise.all([
        getEntities(analysisResult.context_item_id),
        getRelationships(analysisResult.context_item_id),
      ]);

      setEntities(entitiesData);
      setRelationships(relationshipsData);

      // Show success toast
      const entityCount = analysisResult.entities_extracted;
      const relCount = analysisResult.relationships_inferred;
      toast.success(
        `Analysis complete! Found ${entityCount} entities and ${relCount} relationships.`,
        {
          description: `Quality: ${(analysisResult.quality_metrics.entity_quality * 100).toFixed(0)}% entity, ${(analysisResult.quality_metrics.relationship_quality * 100).toFixed(0)}% relationship`,
        }
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to analyze context";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, [inputText, sourceType]);

  const handleReset = useCallback(() => {
    setInputText("");
    setResult(null);
    setEntities([]);
    setRelationships([]);
    setError(null);
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-600" />
            Cognitive Nexus - Context Analysis
          </DialogTitle>
          <DialogDescription>
            Process context through autonomous AI agents that extract entities, infer relationships,
            and generate tasks with transparency.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Input Section */}
          {!result && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="context-input">Context to Analyze</Label>
                <Textarea
                  id="context-input"
                  placeholder={PLACEHOLDER_TEXT}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  rows={12}
                  className="font-mono text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="source-type">Source Type</Label>
                <Select value={sourceType} onValueChange={(value: any) => setSourceType(value)}>
                  <SelectTrigger id="source-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual Input</SelectItem>
                    <SelectItem value="slack">Slack Message</SelectItem>
                    <SelectItem value="transcript">Meeting Transcript</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Source type helps agents choose the right extraction strategy
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
                  {error}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing || !inputText.trim()}
                  className="flex-1"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Agents Processing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Analyze with AI Agents
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Results Section */}
          {result && (
            <div className="space-y-4">
              {/* Success Header */}
              <div className="flex items-center gap-2 p-4 rounded-lg bg-green-50 border border-green-200">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div className="flex-1">
                  <div className="font-semibold text-green-900">
                    Analysis Complete!
                  </div>
                  <div className="text-sm text-green-700">
                    {result.entities_extracted} entities extracted, {result.relationships_inferred} relationships inferred,{" "}
                    {result.tasks_generated} tasks generated
                  </div>
                </div>
              </div>

              {/* Results Tabs */}
              <Tabs defaultValue="entities" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="entities">Entities & Relationships</TabsTrigger>
                  <TabsTrigger value="reasoning">Reasoning Trace</TabsTrigger>
                  <TabsTrigger value="quality">Quality Metrics</TabsTrigger>
                </TabsList>

                <TabsContent value="entities" className="space-y-4 mt-4">
                  <EntityVisualization entities={entities} relationships={relationships} />
                </TabsContent>

                <TabsContent value="reasoning" className="space-y-4 mt-4">
                  <ReasoningTraceView
                    steps={result.reasoning_steps}
                    extractionStrategy={
                      result.reasoning_steps.some(s => s.includes("DETAILED"))
                        ? "detailed"
                        : "fast"
                    }
                  />
                </TabsContent>

                <TabsContent value="quality" className="space-y-4 mt-4">
                  <QualityMetricsDisplay metrics={result.quality_metrics} />
                </TabsContent>
              </Tabs>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button onClick={handleReset} variant="outline" className="flex-1">
                  <Sparkles className="mr-2 h-4 w-4" />
                  Analyze More Context
                </Button>
                <Button onClick={handleClose}>
                  Done
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

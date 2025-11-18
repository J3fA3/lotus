/**
 * Reasoning Trace View Component
 *
 * Shows agent decision-making process step-by-step
 * Provides transparency into why agents made specific choices
 */
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { ChevronDown, ChevronRight, Brain, Zap } from "lucide-react";
import { useState } from "react";

interface ReasoningTraceViewProps {
  steps: string[];
  extractionStrategy?: "fast" | "detailed";
}

export const ReasoningTraceView = ({
  steps,
  extractionStrategy,
}: ReasoningTraceViewProps) => {
  const [isOpen, setIsOpen] = useState(true);

  // Group steps by agent phase
  const groupSteps = (steps: string[]): { agent: string; steps: string[] }[] => {
    const groups: { agent: string; steps: string[] }[] = [];
    let currentAgent = "Context Analysis";
    let currentSteps: string[] = [];

    steps.forEach((step) => {
      // Detect agent transitions
      if (step.includes("Using DETAILED prompt") || step.includes("Using SIMPLE prompt")) {
        if (currentSteps.length > 0) {
          groups.push({ agent: currentAgent, steps: currentSteps });
        }
        currentAgent = "Entity Extraction";
        currentSteps = [step];
      } else if (step.includes("entities →") || step.includes("EXHAUSTIVE") || step.includes("SELECTIVE")) {
        if (currentSteps.length > 0) {
          groups.push({ agent: currentAgent, steps: currentSteps });
        }
        currentAgent = "Relationship Synthesis";
        currentSteps = [step];
      } else if (step.includes("Context:") && step.includes("people")) {
        if (currentSteps.length > 0) {
          groups.push({ agent: currentAgent, steps: currentSteps });
        }
        currentAgent = "Task Intelligence";
        currentSteps = [step];
      } else {
        currentSteps.push(step);
      }
    });

    if (currentSteps.length > 0) {
      groups.push({ agent: currentAgent, steps: currentSteps });
    }

    return groups;
  };

  const stepGroups = groupSteps(steps);

  const getAgentIcon = (agent: string) => {
    return agent.includes("Entity") || agent.includes("Relationship") || agent.includes("Task")
      ? <Brain className="h-4 w-4" />
      : <Zap className="h-4 w-4" />;
  };

  const getStepStyle = (step: string): string => {
    if (step.includes("→") || step.includes("Decision:")) return "font-semibold text-blue-700";
    if (step.includes("RETRY") || step.includes("below threshold")) return "text-yellow-700";
    if (step.includes("CONTINUE") || step.includes("acceptable")) return "text-green-700";
    if (step.includes("Quality:") || step.includes("quality:")) return "font-medium";
    return "";
  };

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="cursor-pointer" onClick={() => setIsOpen(!isOpen)}>
          <CollapsibleTrigger className="w-full">
            <CardTitle className="flex items-center gap-2 text-sm">
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <Brain className="h-4 w-4" />
              <span>Agent Reasoning Trace</span>
              <Badge variant="outline" className="ml-auto">
                {steps.length} steps
              </Badge>
              {extractionStrategy && (
                <Badge variant="secondary">
                  {extractionStrategy === "detailed" ? "Detailed" : "Fast"} Strategy
                </Badge>
              )}
            </CardTitle>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="space-y-4">
            {stepGroups.map((group, groupIdx) => (
              <div key={groupIdx} className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground border-b pb-1">
                  {getAgentIcon(group.agent)}
                  <span>{group.agent} Agent</span>
                </div>
                <div className="space-y-1 pl-6">
                  {group.steps.map((step, stepIdx) => (
                    <div
                      key={stepIdx}
                      className={`flex items-start gap-2 text-sm p-1.5 rounded-md hover:bg-gray-50 transition-colors ${getStepStyle(step)}`}
                    >
                      <Badge variant="outline" className="mt-0.5 shrink-0 h-5 w-5 p-0 flex items-center justify-center text-xs">
                        {stepIdx + 1}
                      </Badge>
                      <span className="text-gray-700 leading-relaxed">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <div className="pt-2 border-t">
              <div className="text-xs text-muted-foreground">
                <strong>Transparency:</strong> Every agent decision is logged with reasoning to build trust and aid debugging.
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

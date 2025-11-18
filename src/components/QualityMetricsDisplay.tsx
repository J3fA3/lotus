/**
 * Quality Metrics Display Component
 *
 * Shows quality scores from agent self-evaluation with visual indicators
 */
import { QualityMetrics } from "@/types/cognitivenexus";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { CheckCircle, AlertCircle, XCircle } from "lucide-react";
import { Progress } from "./ui/progress";

interface QualityMetricsDisplayProps {
  metrics: QualityMetrics;
}

export const QualityMetricsDisplay = ({ metrics }: QualityMetricsDisplayProps) => {
  const getQualityIcon = (score: number) => {
    if (score >= 0.7) return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (score >= 0.5) return <AlertCircle className="h-4 w-4 text-yellow-600" />;
    return <XCircle className="h-4 w-4 text-red-600" />;
  };

  const getQualityColor = (score: number): string => {
    if (score >= 0.7) return "bg-green-100 text-green-800 border-green-300";
    if (score >= 0.5) return "bg-yellow-100 text-yellow-800 border-yellow-300";
    return "bg-red-100 text-red-800 border-red-300";
  };

  const getQualityLabel = (score: number): string => {
    if (score >= 0.7) return "Good";
    if (score >= 0.5) return "Fair";
    return "Low";
  };

  const getProgressColor = (score: number): string => {
    if (score >= 0.7) return "bg-green-500";
    if (score >= 0.5) return "bg-yellow-500";
    return "bg-red-500";
  };

  const qualityItems = [
    {
      label: "Entity Extraction",
      score: metrics.entity_quality,
      description: "How well entities were extracted",
    },
    {
      label: "Relationships",
      score: metrics.relationship_quality,
      description: "Quality of inferred relationships",
    },
    {
      label: "Task Generation",
      score: metrics.task_quality,
      description: "Accuracy of generated tasks",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <span>Agent Quality Metrics</span>
          <Badge variant="outline" className="ml-auto">
            Complexity: {(metrics.context_complexity * 100).toFixed(0)}%
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {qualityItems.map((item) => (
          <div key={item.label} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getQualityIcon(item.score)}
                <div>
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.description}</div>
                </div>
              </div>
              <Badge variant="outline" className={getQualityColor(item.score)}>
                {getQualityLabel(item.score)} - {(item.score * 100).toFixed(0)}%
              </Badge>
            </div>
            <div className="relative">
              <Progress value={item.score * 100} className="h-2" />
              <div
                className={`absolute inset-0 h-2 rounded-full ${getProgressColor(item.score)} transition-all`}
                style={{ width: `${item.score * 100}%` }}
              />
            </div>
          </div>
        ))}

        <div className="pt-2 border-t">
          <div className="text-xs text-muted-foreground">
            <strong>Quality Threshold:</strong> Agents retry extraction when quality drops below 70%
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

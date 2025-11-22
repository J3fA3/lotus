/**
 * Quality Dashboard Component - Phase 6 Stage 6
 *
 * Comprehensive dashboard for task quality evaluation and trust metrics.
 *
 * Features:
 * - Trust Index gauge with color-coded levels
 * - Trust component breakdown (Quality, Engagement, Outcomes, Performance)
 * - Quality tier distribution visualization
 * - Quality trends over time
 * - Actionable insights and recommendations
 * - Recent quality scores table
 *
 * Design: Clean, data-dense, actionable insights
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { Skeleton } from "./ui/skeleton";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  Users,
  CheckCircle2,
  Zap,
  AlertTriangle,
  Lightbulb,
  Award,
  BarChart3,
  Calendar
} from "lucide-react";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "./ui/chart";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend
} from "recharts";

// Trust Index data structure
interface TrustIndexData {
  trust_index: number;
  trust_level: "high" | "medium" | "low" | "very_low";
  scope: string;
  scope_id?: string;
  window_days: number;
  components: {
    quality_consistency: {
      score: number;
      metrics: {
        sample_size: number;
        avg_quality: number;
        quality_variance: number;
        excellent_pct: number;
        good_or_better_pct: number;
      };
    };
    user_engagement: {
      score: number;
      metrics: {
        sample_size: number;
        acceptance_rate: number;
        edit_rate: number;
        question_answer_rate: number;
        auto_fill_acceptance_rate: number;
      };
    };
    outcome_success: {
      score: number;
      metrics: {
        sample_size: number;
        completion_rate: number;
        avg_time_to_complete: number;
        fast_completion_pct: number;
      };
    };
    system_performance: {
      score: number;
      metrics: {
        sample_size: number;
        avg_evaluation_time_ms: number;
        fast_evaluation_pct: number;
      };
    };
  };
  insights: {
    overall: string;
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
  };
  calculated_at: string;
}

// Quality trend data
interface QualityTrendPoint {
  date: string;
  quality: number;
  excellent: number;
  good: number;
  fair: number;
  needs_improvement: number;
}

interface QualityDashboardProps {
  projectId?: string;
  userId?: string;
  windowDays?: number;
}

export const QualityDashboard = ({
  projectId,
  userId,
  windowDays = 30
}: QualityDashboardProps) => {
  const [trustData, setTrustData] = useState<TrustIndexData | null>(null);
  const [trendData, setTrendData] = useState<QualityTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedView, setSelectedView] = useState<"overview" | "details">("overview");

  useEffect(() => {
    fetchTrustData();
    fetchTrendData();
  }, [projectId, userId, windowDays]);

  const fetchTrustData = async () => {
    try {
      setLoading(true);

      // Build query params
      const params = new URLSearchParams({
        window_days: windowDays.toString(),
      });

      if (projectId) params.append("project_id", projectId);
      if (userId) params.append("user_id", userId);

      const response = await fetch(`/api/quality/trust-index?${params}`);
      const data = await response.json();

      setTrustData(data);
    } catch (error) {
      console.error("Failed to fetch trust data:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrendData = async () => {
    try {
      const params = new URLSearchParams({
        window_days: windowDays.toString(),
        period: "daily",
      });

      if (projectId) params.append("project_id", projectId);
      if (userId) params.append("user_id", userId);

      const response = await fetch(`/api/quality/trends?${params}`);
      const data = await response.json();

      setTrendData(data);
    } catch (error) {
      console.error("Failed to fetch trend data:", error);
    }
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (!trustData) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>No Data Available</AlertTitle>
        <AlertDescription>
          No quality data found for the selected time period. Create some tasks to see quality metrics.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Quality Dashboard</h2>
          <p className="text-muted-foreground">
            AI task quality metrics and trust index
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Calendar className="h-3 w-3" />
            Last {windowDays} days
          </Badge>
          <Badge variant="outline">
            {trustData.components.quality_consistency.metrics.sample_size} tasks evaluated
          </Badge>
        </div>
      </div>

      {/* Trust Index Gauge */}
      <TrustIndexGauge trustData={trustData} />

      {/* Tabs for different views */}
      <Tabs value={selectedView} onValueChange={(v) => setSelectedView(v as any)}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="details">Detailed Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Trust Components Breakdown */}
          <TrustComponentsCard components={trustData.components} />

          {/* Two-column layout */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Quality Distribution */}
            <QualityDistributionCard
              excellent={trustData.components.quality_consistency.metrics.excellent_pct}
              good={trustData.components.quality_consistency.metrics.good_or_better_pct - trustData.components.quality_consistency.metrics.excellent_pct}
              fair={100 - trustData.components.quality_consistency.metrics.good_or_better_pct}
            />

            {/* Insights */}
            <InsightsCard insights={trustData.insights} />
          </div>

          {/* Quality Trends */}
          {trendData.length > 0 && (
            <QualityTrendsCard trendData={trendData} />
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-6">
          {/* Detailed metrics for each component */}
          <DetailedMetricsCards components={trustData.components} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Trust Index Gauge Component
const TrustIndexGauge = ({ trustData }: { trustData: TrustIndexData }) => {
  const { trust_index, trust_level } = trustData;

  const getTrustColor = (level: string) => {
    switch (level) {
      case "high": return "text-green-600 bg-green-50 border-green-200";
      case "medium": return "text-blue-600 bg-blue-50 border-blue-200";
      case "low": return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "very_low": return "text-red-600 bg-red-50 border-red-200";
      default: return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getTrustLabel = (level: string) => {
    switch (level) {
      case "high": return "High Trust";
      case "medium": return "Medium Trust";
      case "low": return "Low Trust";
      case "very_low": return "Very Low Trust";
      default: return "Unknown";
    }
  };

  const getTrustIcon = (level: string) => {
    switch (level) {
      case "high": return <Award className="h-6 w-6" />;
      case "medium": return <Target className="h-6 w-6" />;
      case "low": return <AlertTriangle className="h-6 w-6" />;
      case "very_low": return <AlertTriangle className="h-6 w-6" />;
      default: return <Minus className="h-6 w-6" />;
    }
  };

  const getProgressColor = (level: string) => {
    switch (level) {
      case "high": return "bg-green-500";
      case "medium": return "bg-blue-500";
      case "low": return "bg-yellow-500";
      case "very_low": return "bg-red-500";
      default: return "bg-gray-500";
    }
  };

  return (
    <Card className={`border-2 ${getTrustColor(trust_level)}`}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {getTrustIcon(trust_level)}
              <span className="text-sm font-medium text-muted-foreground">Trust Index</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-5xl font-bold tracking-tight">
                {trust_index.toFixed(1)}
              </span>
              <span className="text-2xl text-muted-foreground">/100</span>
            </div>
            <Badge className={getTrustColor(trust_level)} variant="outline">
              {getTrustLabel(trust_level)}
            </Badge>
          </div>

          {/* Visual gauge */}
          <div className="relative h-48 w-48">
            <svg viewBox="0 0 200 200" className="w-full h-full">
              {/* Background circle */}
              <circle
                cx="100"
                cy="100"
                r="80"
                fill="none"
                stroke="currentColor"
                strokeWidth="20"
                className="text-gray-200"
              />
              {/* Progress circle */}
              <circle
                cx="100"
                cy="100"
                r="80"
                fill="none"
                stroke="currentColor"
                strokeWidth="20"
                strokeLinecap="round"
                className={trust_level === "high" ? "text-green-500" :
                          trust_level === "medium" ? "text-blue-500" :
                          trust_level === "low" ? "text-yellow-500" : "text-red-500"}
                strokeDasharray={`${trust_index * 5.03} ${502 - trust_index * 5.03}`}
                transform="rotate(-90 100 100)"
              />
              <text
                x="100"
                y="105"
                textAnchor="middle"
                className="text-2xl font-bold fill-current"
              >
                {trust_index.toFixed(0)}%
              </text>
            </svg>
          </div>
        </div>

        <div className="mt-4">
          <Progress value={trust_index} className="h-2" />
          <p className="mt-2 text-sm text-muted-foreground">
            {trustData.insights.overall}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

// Trust Components Breakdown
const TrustComponentsCard = ({ components }: { components: TrustIndexData["components"] }) => {
  const componentData = [
    {
      name: "Quality Consistency",
      score: components.quality_consistency.score,
      weight: 35,
      icon: <CheckCircle2 className="h-4 w-4" />,
      description: "Consistent high-quality outputs"
    },
    {
      name: "User Engagement",
      score: components.user_engagement.score,
      weight: 30,
      icon: <Users className="h-4 w-4" />,
      description: "Trust reflected in usage"
    },
    {
      name: "Outcome Success",
      score: components.outcome_success.score,
      weight: 25,
      icon: <Target className="h-4 w-4" />,
      description: "Tasks completed successfully"
    },
    {
      name: "System Performance",
      score: components.system_performance.score,
      weight: 10,
      icon: <Zap className="h-4 w-4" />,
      description: "Reliable and fast"
    },
  ];

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-blue-600";
    if (score >= 40) return "text-yellow-600";
    return "text-red-600";
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-blue-500";
    if (score >= 40) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Trust Components
        </CardTitle>
        <CardDescription>
          Weighted breakdown of trust index (Quality 35%, Engagement 30%, Outcomes 25%, Performance 10%)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {componentData.map((component) => (
          <div key={component.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {component.icon}
                <div>
                  <div className="text-sm font-medium">{component.name}</div>
                  <div className="text-xs text-muted-foreground">{component.description}</div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-lg font-bold ${getScoreColor(component.score)}`}>
                  {component.score.toFixed(1)}
                </div>
                <div className="text-xs text-muted-foreground">{component.weight}% weight</div>
              </div>
            </div>
            <div className="relative">
              <Progress value={component.score} className="h-2" />
              <div
                className={`absolute inset-0 h-2 rounded-full ${getProgressColor(component.score)} transition-all`}
                style={{ width: `${component.score}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

// Quality Distribution (Pie Chart)
const QualityDistributionCard = ({
  excellent,
  good,
  fair
}: {
  excellent: number;
  good: number;
  fair: number;
}) => {
  const data = [
    { name: "Excellent", value: excellent, color: "#22c55e" },
    { name: "Good", value: good, color: "#3b82f6" },
    { name: "Fair/Needs Improvement", value: fair, color: "#eab308" },
  ].filter(d => d.value > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quality Distribution</CardTitle>
        <CardDescription>Percentage of tasks by quality tier</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <ChartTooltip content={<ChartTooltipContent />} />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// Insights Card
const InsightsCard = ({ insights }: { insights: TrustIndexData["insights"] }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Insights & Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Strengths */}
        {insights.strengths.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-green-600 mb-2 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" />
              Strengths
            </h4>
            <ul className="space-y-1">
              {insights.strengths.map((strength, idx) => (
                <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Weaknesses */}
        {insights.weaknesses.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-yellow-600 mb-2 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" />
              Areas for Improvement
            </h4>
            <ul className="space-y-1">
              {insights.weaknesses.map((weakness, idx) => (
                <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-yellow-500 mt-1">•</span>
                  <span>{weakness}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {insights.recommendations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-blue-600 mb-2 flex items-center gap-1">
              <Lightbulb className="h-4 w-4" />
              Recommendations
            </h4>
            <ul className="space-y-1">
              {insights.recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Quality Trends Chart
const QualityTrendsCard = ({ trendData }: { trendData: QualityTrendPoint[] }) => {
  // Calculate trend direction
  const firstQuality = trendData[0]?.quality || 0;
  const lastQuality = trendData[trendData.length - 1]?.quality || 0;
  const trendDirection = lastQuality > firstQuality ? "up" : lastQuality < firstQuality ? "down" : "stable";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              Quality Trends
              {trendDirection === "up" && <TrendingUp className="h-5 w-5 text-green-600" />}
              {trendDirection === "down" && <TrendingDown className="h-5 w-5 text-red-600" />}
              {trendDirection === "stable" && <Minus className="h-5 w-5 text-gray-600" />}
            </CardTitle>
            <CardDescription>Quality score over time</CardDescription>
          </div>
          <Badge variant={trendDirection === "up" ? "default" : trendDirection === "down" ? "destructive" : "secondary"}>
            {trendDirection === "up" ? "Improving" : trendDirection === "down" ? "Declining" : "Stable"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              className="text-xs"
              tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            />
            <YAxis className="text-xs" domain={[0, 100]} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              type="monotone"
              dataKey="quality"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: "#3b82f6", r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// Detailed Metrics Cards
const DetailedMetricsCards = ({ components }: { components: TrustIndexData["components"] }) => {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Quality Consistency Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quality Consistency Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricRow
            label="Average Quality"
            value={`${components.quality_consistency.metrics.avg_quality.toFixed(1)}/100`}
          />
          <MetricRow
            label="Quality Variance"
            value={components.quality_consistency.metrics.quality_variance.toFixed(1)}
          />
          <MetricRow
            label="Excellent Tasks"
            value={`${components.quality_consistency.metrics.excellent_pct.toFixed(1)}%`}
          />
          <MetricRow
            label="Good or Better"
            value={`${components.quality_consistency.metrics.good_or_better_pct.toFixed(1)}%`}
          />
        </CardContent>
      </Card>

      {/* User Engagement Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">User Engagement Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricRow
            label="AI Acceptance Rate"
            value={`${components.user_engagement.metrics.acceptance_rate.toFixed(1)}%`}
          />
          <MetricRow
            label="Edit Rate"
            value={`${components.user_engagement.metrics.edit_rate.toFixed(1)}%`}
            lowIsBetter
          />
          <MetricRow
            label="Question Answer Rate"
            value={`${components.user_engagement.metrics.question_answer_rate.toFixed(1)}%`}
          />
          <MetricRow
            label="Auto-fill Acceptance"
            value={`${components.user_engagement.metrics.auto_fill_acceptance_rate.toFixed(1)}%`}
          />
        </CardContent>
      </Card>

      {/* Outcome Success Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Outcome Success Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricRow
            label="Completion Rate"
            value={`${components.outcome_success.metrics.completion_rate.toFixed(1)}%`}
          />
          <MetricRow
            label="Avg Time to Complete"
            value={`${(components.outcome_success.metrics.avg_time_to_complete / 60).toFixed(1)} min`}
          />
          <MetricRow
            label="Fast Completions"
            value={`${components.outcome_success.metrics.fast_completion_pct.toFixed(1)}%`}
          />
        </CardContent>
      </Card>

      {/* System Performance Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">System Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricRow
            label="Avg Evaluation Time"
            value={`${components.system_performance.metrics.avg_evaluation_time_ms.toFixed(0)}ms`}
            lowIsBetter
          />
          <MetricRow
            label="Fast Evaluations (<50ms)"
            value={`${components.system_performance.metrics.fast_evaluation_pct.toFixed(1)}%`}
          />
        </CardContent>
      </Card>
    </div>
  );
};

// Metric Row Component
const MetricRow = ({
  label,
  value,
  lowIsBetter = false
}: {
  label: string;
  value: string;
  lowIsBetter?: boolean;
}) => {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
};

// Loading Skeleton
const DashboardSkeleton = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-6 w-32" />
      </div>
      <Skeleton className="h-48 w-full" />
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  );
};

/**
 * Task Scheduler Component
 * 
 * Minimal, zen-inspired scheduling interface that integrates seamlessly
 * into the task detail view. Provides AI-powered time block suggestions
 * with a calm, lotus-papyrus aesthetic.
 */

import { useState } from "react";
import { Calendar, Sparkles, Clock, ChevronRight, Check, X } from "lucide-react";
import "./TaskScheduler.css";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { toast } from "sonner";
import { format } from "date-fns";
import {
  scheduleTask,
  approveTimeBlock,
  checkCalendarAuth,
  getAuthorizationUrl,
  type TimeBlockSuggestion,
} from "@/api/calendar";

interface TaskSchedulerProps {
  taskId: string;
  taskTitle: string;
  onScheduled?: () => void;
}

export const TaskScheduler = ({ taskId, taskTitle, onScheduled }: TaskSchedulerProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<TimeBlockSuggestion[]>([]);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [approving, setApproving] = useState<number | null>(null);

  const handleExpand = async () => {
    if (isExpanded) {
      setIsExpanded(false);
      setSuggestions([]);
      return;
    }

    setIsExpanded(true);
    setIsLoading(true);

    try {
      // Check calendar authorization
      const authStatus = await checkCalendarAuth();
      setIsAuthorized(authStatus.authorized);

      if (!authStatus.authorized) {
        setIsLoading(false);
        return;
      }

      // Generate scheduling suggestions
      const response = await scheduleTask(taskId);

      if (response.suggestions.length === 0) {
        toast.info("No available time slots found in the next 7 days");
        setSuggestions([]);
      } else {
        setSuggestions(response.suggestions);
        toast.success(`Found ${response.suggestions.length} optimal time${response.suggestions.length > 1 ? 's' : ''}`);
      }
    } catch (error) {
      console.error("Scheduling error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to generate suggestions");
      setIsExpanded(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAuthorize = async () => {
    try {
      const { authorization_url } = await getAuthorizationUrl();
      window.open(authorization_url, "_blank");
      toast.info("Please authorize calendar access in the new window");
    } catch (error) {
      console.error("Authorization error:", error);
      toast.error("Failed to get authorization URL");
    }
  };

  const handleApprove = async (suggestion: TimeBlockSuggestion) => {
    setApproving(suggestion.id);

    try {
      await approveTimeBlock(suggestion.id);
      toast.success("Time block added to your calendar");
      
      // Remove approved suggestion with smooth animation
      setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
      
      if (onScheduled) {
        onScheduled();
      }

      // Collapse if no more suggestions
      if (suggestions.length === 1) {
        setTimeout(() => {
          setIsExpanded(false);
        }, 300);
      }
    } catch (error) {
      console.error("Approval error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to approve time block");
    } finally {
      setApproving(null);
    }
  };

  const handleReject = (suggestion: TimeBlockSuggestion) => {
    setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
    toast.info("Suggestion dismissed");

    // Collapse if no more suggestions
    if (suggestions.length === 1) {
      setTimeout(() => {
        setIsExpanded(false);
      }, 150);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return "text-[hsl(var(--lotus-green-medium))]";
    if (confidence >= 60) return "text-[hsl(var(--lotus-green-medium)/0.7)]";
    return "text-muted-foreground";
  };

  const getConfidenceBg = (confidence: number) => {
    if (confidence >= 80) return "bg-[hsl(var(--lotus-green-light)/0.15)]";
    if (confidence >= 60) return "bg-[hsl(var(--lotus-green-light)/0.08)]";
    return "bg-muted/30";
  };

  return (
    <div className="space-y-3 transition-all duration-300">
      {/* Collapsed State - Subtle Integration */}
      {!isExpanded && (
        <div className="space-y-3">
          <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5 opacity-60" />
            AI Scheduling
          </Label>
          <Button
            variant="outline"
            onClick={handleExpand}
            disabled={isLoading}
            className="w-full h-10 justify-between border-border/50 hover:border-primary/50 hover:bg-accent/30 transition-all duration-200 group"
          >
            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
              Let AI find the best time
            </span>
            <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
          </Button>
        </div>
      )}

      {/* Expanded State - Scheduling Interface */}
      {isExpanded && (
        <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between">
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <Sparkles className="h-3.5 w-3.5 opacity-60" />
              AI Scheduling
            </Label>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsExpanded(false);
                setSuggestions([]);
              }}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5 mr-1" />
              Close
            </Button>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="py-8 flex flex-col items-center justify-center gap-3">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-2 border-border/30" />
                <div className="absolute inset-0 w-12 h-12 rounded-full border-2 border-t-[hsl(var(--lotus-green-medium))] border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                <Sparkles className="absolute inset-0 m-auto h-5 w-5 text-[hsl(var(--lotus-green-medium))] animate-pulse" />
              </div>
              <p className="text-sm text-muted-foreground">Finding optimal times...</p>
            </div>
          )}

          {/* Not Authorized State */}
          {!isLoading && isAuthorized === false && (
            <div className="py-6 px-4 bg-accent/30 rounded-lg border border-border/30 space-y-3">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[hsl(var(--lotus-green-light)/0.2)] flex items-center justify-center">
                  <Calendar className="h-4 w-4 text-[hsl(var(--lotus-green-medium))]" />
                </div>
                <div className="flex-1 space-y-2">
                  <p className="text-sm font-medium text-foreground">
                    Connect your calendar
                  </p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    To find the perfect time for "{taskTitle}", I need access to your Google Calendar
                  </p>
                </div>
              </div>
              <Button
                onClick={handleAuthorize}
                className="w-full h-9 bg-[hsl(var(--lotus-green-medium))] hover:bg-[hsl(var(--lotus-green-dark))] text-white transition-all"
              >
                <Calendar className="h-3.5 w-3.5 mr-2" />
                Connect Calendar
              </Button>
            </div>
          )}

          {/* Suggestions List */}
          {!isLoading && suggestions.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground px-1">
                {suggestions.length} optimal time{suggestions.length > 1 ? 's' : ''} available
              </p>
              <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1 task-scheduler-scroll">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={suggestion.id}
                    className={`group p-3 rounded-lg border transition-all duration-200 hover:shadow-zen-sm ${getConfidenceBg(
                      suggestion.confidence
                    )} border-border/30 hover:border-primary/30 animate-in fade-in slide-in-from-top-1`}
                    style={{
                      animationDelay: `${index * 50}ms`,
                      animationFillMode: "backwards",
                    }}
                  >
                    {/* Time & Confidence */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Clock className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-foreground">
                            {format(new Date(suggestion.start_time), "EEE, MMM d")}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {format(new Date(suggestion.start_time), "h:mm a")} -{" "}
                            {format(new Date(suggestion.end_time), "h:mm a")}
                            {" • "}
                            {suggestion.duration_minutes}min
                          </p>
                        </div>
                      </div>
                      <div
                        className={`flex items-center gap-1 ${getConfidenceColor(
                          suggestion.confidence
                        )}`}
                      >
                        <Sparkles className="h-3 w-3" />
                        <span className="text-[10px] font-medium">
                          {suggestion.confidence}%
                        </span>
                      </div>
                    </div>

                    {/* Reasoning */}
                    {suggestion.reasoning && (
                      <p className="text-xs text-muted-foreground leading-relaxed mb-3 pl-5">
                        {suggestion.reasoning}
                      </p>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pl-5">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleReject(suggestion)}
                        disabled={approving !== null}
                        className="flex-1 h-7 text-xs hover:bg-destructive/10 hover:text-destructive transition-all"
                      >
                        <X className="h-3 w-3 mr-1" />
                        Pass
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(suggestion)}
                        disabled={approving !== null}
                        className="flex-1 h-7 text-xs bg-[hsl(var(--lotus-green-medium))] hover:bg-[hsl(var(--lotus-green-dark))] text-white transition-all"
                      >
                        {approving === suggestion.id ? (
                          <>
                            <div className="h-3 w-3 mr-1 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                            Scheduling...
                          </>
                        ) : (
                          <>
                            <Check className="h-3 w-3 mr-1" />
                            Add to Calendar
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Suggestions State */}
          {!isLoading && isAuthorized === true && suggestions.length === 0 && (
            <div className="py-6 px-4 bg-accent/30 rounded-lg border border-border/30 text-center">
              <Calendar className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No available time slots found in the next 7 days
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Your calendar appears to be full
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

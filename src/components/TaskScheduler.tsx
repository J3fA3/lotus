/**
 * Task Scheduler Component
 * 
 * Minimal, zen-inspired scheduling interface that integrates seamlessly
 * into the task detail view. Provides AI-powered time block suggestions
 * with a calm, lotus-papyrus aesthetic.
 */

import { useState, useEffect, useMemo, useRef } from "react";
import { Calendar, Sparkles, Clock, ChevronRight, Check, X, CheckCircle2 } from "lucide-react";
import "./TaskScheduler.css";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { toast } from "sonner";
import { format, formatDistanceToNow, parse } from "date-fns";
import {
  scheduleTask,
  approveTimeBlock,
  checkCalendarAuth,
  getAuthorizationUrl,
  cancelScheduledBlock,
  type TimeBlockSuggestion,
} from "@/api/calendar";
import { Comment } from "@/types/task";

interface ScheduledBlockInfo {
  start_time: string;
  end_time: string;
  duration_minutes: number;
  quality_score: number | null;
}

interface TaskSchedulerProps {
  taskId: string;
  taskTitle: string;
  comments?: Comment[];
  onScheduled?: (action?: 'approved' | 'cancelled') => void;
}

/**
 * Helper: Check if a comment is a cancellation comment
 */
function isCancellationComment(comment: Comment): boolean {
  return (
    comment.author === "Lotus" &&
    comment.text.includes("❌") &&
    (comment.text.includes("cancelled") || comment.text.includes("You cancelled"))
  );
}

/**
 * Helper: Check if a comment is a scheduling comment
 */
function isSchedulingComment(comment: Comment): boolean {
  return comment.author === "Lotus" && comment.text.includes("⏰ Time blocked:");
}

/**
 * Helper: Find most recent cancellation comment timestamp
 */
function getMostRecentCancellationTime(comments: Comment[]): number | null {
  const cancellationComments = comments
    .filter(isCancellationComment)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  
  return cancellationComments.length > 0
    ? new Date(cancellationComments[0].createdAt).getTime()
    : null;
}

/**
 * Helper: Find most recent scheduling comment
 */
function getMostRecentSchedulingComment(comments: Comment[]): Comment | null {
  const schedulingComments = comments
    .filter(isSchedulingComment)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  
  return schedulingComments.length > 0 ? schedulingComments[0] : null;
}

/**
 * Parse scheduling comment to extract block information
 * Format: "⏰ Time blocked: Friday, November 28 at 02:30 PM - 03:00 PM (30 minutes) I've added this to your calendar as '🪷 Katie Data Deep Dive'. Quality score: 85/100 (Great time for this task)"
 */
function parseSchedulingComment(comment: Comment): ScheduledBlockInfo | null {
  if (comment.author !== "Lotus" || !comment.text.includes("⏰ Time blocked:")) {
    return null;
  }

  try {
    const text = comment.text;
    
    // Extract time range: "Friday, November 28 at 02:30 PM - 03:00 PM"
    const timeMatch = text.match(/Time blocked:\s*([^•]+?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM))/i);
    if (!timeMatch) return null;

    const dateTimeStr = timeMatch[1].trim(); // "Friday, November 28 at 02:30 PM"
    const endTimeStr = timeMatch[2].trim(); // "03:00 PM"

    // Parse the date and start time
    const dateTimeMatch = dateTimeStr.match(/(.+?)\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM))/i);
    if (!dateTimeMatch) return null;

    const datePart = dateTimeMatch[1].trim(); // "Friday, November 28"
    const startTimeStr = dateTimeMatch[2].trim(); // "02:30 PM"

    // Parse date: "Friday, November 28" -> we need the year, assume current year
    const currentYear = new Date().getFullYear();
    const fullDateStr = `${datePart}, ${currentYear}`;
    
    // Try to parse: "Friday, November 28, 2025"
    let startDate: Date;
    try {
      startDate = parse(`${fullDateStr} ${startTimeStr}`, "EEEE, MMMM d, yyyy h:mm a", new Date());
    } catch {
      // Fallback: try without day name
      const datePartMatch = datePart.match(/(\w+)\s+(\d+)/);
      if (datePartMatch) {
        const monthName = datePartMatch[1];
        const day = datePartMatch[2];
        startDate = parse(`${monthName} ${day}, ${currentYear} ${startTimeStr}`, "MMMM d, yyyy h:mm a", new Date());
      } else {
        return null;
      }
    }

    // Parse end time (same date, different time)
    let endDate: Date;
    try {
      endDate = parse(`${fullDateStr} ${endTimeStr}`, "EEEE, MMMM d, yyyy h:mm a", new Date());
    } catch {
      const datePartMatch = datePart.match(/(\w+)\s+(\d+)/);
      if (datePartMatch) {
        const monthName = datePartMatch[1];
        const day = datePartMatch[2];
        endDate = parse(`${monthName} ${day}, ${currentYear} ${endTimeStr}`, "MMMM d, yyyy h:mm a", new Date());
      } else {
        return null;
      }
    }

    // Extract duration: "(30 minutes)"
    const durationMatch = text.match(/\((\d+)\s*minutes?\)/i);
    const duration_minutes = durationMatch ? parseInt(durationMatch[1], 10) : 
      Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60));

    // Extract quality score: "Quality score: 85/100"
    const qualityMatch = text.match(/Quality score:\s*(\d+)\/100/i);
    const quality_score = qualityMatch ? parseInt(qualityMatch[1], 10) : null;

    return {
      start_time: startDate.toISOString(),
      end_time: endDate.toISOString(),
      duration_minutes,
      quality_score,
    };
  } catch (error) {
    console.error("Failed to parse scheduling comment:", error);
    return null;
  }
}

export const TaskScheduler = ({ taskId, taskTitle, comments = [], onScheduled }: TaskSchedulerProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<TimeBlockSuggestion[]>([]);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [approving, setApproving] = useState<number | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [optimisticScheduledBlock, setOptimisticScheduledBlock] = useState<ScheduledBlockInfo | null>(null);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  const previousTaskIdRef = useRef<string>(taskId);

  // Reset optimistic state when taskId changes (e.g., task deleted or switched)
  useEffect(() => {
    if (taskId !== previousTaskIdRef.current) {
      setOptimisticScheduledBlock(null);
      setIsExpanded(false);
      setSuggestions([]);
      setIsCancelled(false);
      setIsAnimatingOut(false);
      previousTaskIdRef.current = taskId;
    }
  }, [taskId]);

  // Clear optimistic state if comments no longer contain scheduling comments or if cancelled
  useEffect(() => {
    if (!optimisticScheduledBlock || !comments) return;

    const hasSchedulingComment = comments.some(isSchedulingComment);
    const hasCancellation = comments.some(isCancellationComment);
    
    if (!hasSchedulingComment || hasCancellation) {
      setOptimisticScheduledBlock(null);
    }
  }, [comments, optimisticScheduledBlock]);

  // Check for cancellation comments and update cancelled state
  // This helps with immediate UI feedback, but scheduledBlock useMemo is the source of truth
  useEffect(() => {
    if (!comments || comments.length === 0) {
      setIsCancelled(false);
      return;
    }

    const schedulingComment = getMostRecentSchedulingComment(comments);
    const cancellationTime = getMostRecentCancellationTime(comments);

    if (schedulingComment && cancellationTime) {
      const schedulingTime = new Date(schedulingComment.createdAt).getTime();
      setIsCancelled(cancellationTime > schedulingTime);
    } else {
      setIsCancelled(false);
    }
  }, [comments]);

  /**
   * Determine if task has an active scheduled block
   * 
   * This is the source of truth for scheduled state. It:
   * 1. Checks if currently animating out (cancelling)
   * 2. Finds most recent scheduling comment
   * 3. Checks if cancellation comment exists after scheduling
   * 4. Returns null if cancelled, otherwise parses and returns block info
   * 
   * This works on fresh mounts because it checks comments directly, not state.
   */
  const scheduledBlock = useMemo(() => {
    // Don't show scheduled block if animating out
    if (isAnimatingOut) {
      return null;
    }

    if (!comments || comments.length === 0) {
      return null;
    }

    // Find the most recent scheduling comment
    const schedulingComment = getMostRecentSchedulingComment(comments);
    if (!schedulingComment) {
      return null;
    }

    const schedulingTime = new Date(schedulingComment.createdAt).getTime();
    const cancellationTime = getMostRecentCancellationTime(comments);

    // CRITICAL: If cancellation is after scheduling, don't show as scheduled
    // This check works on fresh mounts because it reads comments directly
    if (cancellationTime && cancellationTime > schedulingTime) {
      return null;
    }

    // Check optimistic state (for immediate feedback after approval)
    if (optimisticScheduledBlock) {
      // Verify scheduling comment still exists
      if (!comments.some(isSchedulingComment)) {
        return null;
      }
      // Verify not cancelled
      if (cancellationTime && cancellationTime > schedulingTime) {
        return null;
      }
      return optimisticScheduledBlock;
    }

    // Parse and return the scheduling comment
    return parseSchedulingComment(schedulingComment);
  }, [comments, optimisticScheduledBlock, isAnimatingOut]);

  // Handle approval with optimistic update and smooth animation
  const handleApprove = async (suggestion: TimeBlockSuggestion) => {
    setApproving(suggestion.id);

    try {
      // Optimistically set scheduled block immediately for instant feedback
      const startDate = new Date(suggestion.start_time);
      const endDate = new Date(suggestion.end_time);
      const duration = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60));
      
      // Remove approved suggestion first (smooth animation)
      setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
      
      // Collapse the expanded view with animation
      setTimeout(() => {
        setIsExpanded(false);
      }, 150);

      // Set optimistic state after a brief delay for smooth transition
      setTimeout(() => {
        setOptimisticScheduledBlock({
          start_time: suggestion.start_time,
          end_time: suggestion.end_time,
          duration_minutes: duration,
          quality_score: suggestion.quality_score,
        });
      }, 200);

      await approveTimeBlock(suggestion.id);
      toast.success("Time block added to your calendar");
      
      // Call onScheduled to trigger task refresh (which will update comments)
      if (onScheduled) {
        onScheduled('approved');
      }
    } catch (error) {
      console.error("Approval error:", error);
      // Clear optimistic state on error
      setOptimisticScheduledBlock(null);
      toast.error(error instanceof Error ? error.message : "Failed to approve time block");
    } finally {
      setApproving(null);
    }
  };

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
        const message = response.message || "No available time slots found in the next 7 days";
        toast.info(message, { duration: 5000 });
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

  /**
   * Handle cancellation of scheduled block
   * 
   * Flow:
   * 1. Immediately set animation state (for smooth UX)
   * 2. Clear optimistic state (prevent reappearing)
   * 3. Call API to cancel and delete calendar event
   * 4. After animation completes, refresh task data
   */
  const handleCancel = async () => {
    if (!scheduledBlock) return;
    
    setCancelling(true);
    setIsAnimatingOut(true);
    setIsCancelled(true);
    setOptimisticScheduledBlock(null);
    
    try {
      await cancelScheduledBlock(taskId);
      
      // Wait for animation to complete before clearing animation state
      setTimeout(() => {
        setIsAnimatingOut(false);
        toast.success("Scheduled block cancelled");
        
        // Trigger task refresh to get updated comments
        if (onScheduled) {
          onScheduled('cancelled');
        }
      }, 300); // Match animation duration
    } catch (error) {
      console.error("Cancellation error:", error);
      // Reset state on error
      setIsAnimatingOut(false);
      setIsCancelled(false);
      toast.error(
        error instanceof Error 
          ? error.message 
          : "Failed to cancel scheduled block"
      );
    } finally {
      setCancelling(false);
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

  // Compact scheduled state - replaces the button
  // Show during animation, then hide after animation completes
  if (scheduledBlock) {
    const startDate = new Date(scheduledBlock.start_time);
    const endDate = new Date(scheduledBlock.end_time);
    const isToday = format(startDate, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");
    const isTomorrow = format(startDate, "yyyy-MM-dd") === format(new Date(Date.now() + 86400000), "yyyy-MM-dd");
    const isPast = startDate < new Date();

    return (
      <div className="space-y-3 transition-all duration-300">
        <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          <Sparkles className="h-3.5 w-3.5 opacity-60" />
          Scheduled
        </Label>
        
        {/* Compact Scheduled State - Replaces Button */}
        <div 
          className={`relative overflow-hidden rounded-lg border border-[hsl(var(--lotus-green-medium)/0.3)] bg-gradient-to-br from-[hsl(var(--lotus-green-light)/0.08)] to-[hsl(var(--lotus-green-light)/0.03)] p-3 transition-all duration-300 ${
            isAnimatingOut 
              ? 'animate-out slide-out-to-right-full fade-out-0' 
              : 'animate-in slide-in-from-top-2 fade-in-0 hover:border-[hsl(var(--lotus-green-medium)/0.5)] hover:shadow-zen-sm'
          }`}
          style={{ 
            animationDuration: isAnimatingOut ? '300ms' : '400ms',
            animationFillMode: 'forwards'
          }}
        >
          {/* Subtle left accent */}
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[hsl(var(--lotus-green-medium))] to-[hsl(var(--lotus-green-medium)/0.5)]" />
          
          <div className="pl-3 flex items-center gap-3">
            {/* Clock icon */}
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[hsl(var(--lotus-green-medium)/0.15)] flex items-center justify-center ring-1 ring-[hsl(var(--lotus-green-medium)/0.2)] animate-in zoom-in-50"
              style={{ animationDuration: '300ms', animationDelay: '100ms' }}
            >
              <Clock className="h-3.5 w-3.5 text-[hsl(var(--lotus-green-medium))]" />
            </div>
            
            {/* Time info - compact */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-foreground">
                  {isPast ? "Past" : isToday ? "Today" : isTomorrow ? "Tomorrow" : format(startDate, "MMM d")}
                </p>
                <span className="text-xs text-muted-foreground">
                  {format(startDate, "h:mm a")} - {format(endDate, "h:mm a")}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5 ml-0">
                {scheduledBlock.duration_minutes} min
                {scheduledBlock.quality_score !== null && scheduledBlock.quality_score >= 75 && (
                  <span className="ml-1.5 text-[hsl(var(--lotus-green-medium))]">
                    • {scheduledBlock.quality_score >= 90 ? "Excellent" : "Great"} time
                  </span>
                )}
              </p>
            </div>

            {/* Cancel button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all flex-shrink-0"
            >
              {cancelling ? (
                <>
                  <div className="h-3 w-3 mr-1 rounded-full border-2 border-destructive/30 border-t-destructive animate-spin" />
                  Cancelling...
                </>
              ) : (
                <>
                  <X className="h-3 w-3 mr-1" />
                  Cancel
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 transition-all duration-300">
      {/* Collapsed State - Subtle Integration */}
      {!isExpanded && (
        <div className="space-y-3">
          <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5 opacity-60" />
            Schedule
          </Label>
          <Button
            variant="outline"
            onClick={handleExpand}
            disabled={isLoading}
            className="w-full h-10 justify-between border-border/50 hover:border-primary/50 hover:bg-accent/30 transition-all duration-200 group"
          >
            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
              Find the best time
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
              Schedule
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

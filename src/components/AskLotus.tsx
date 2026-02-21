import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Loader2, Send, X } from "lucide-react";
import { LotusIcon } from "./LotusIcon";
import { askLotus, type AIAssistResponse } from "@/api/ai";

interface AskLotusProps {
  taskId: string;
}

export function AskLotus({ taskId }: AskLotusProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIAssistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Floating vs Inline state
  const [isFloating, setIsFloating] = useState(false);
  const placeholderRef = useRef<HTMLDivElement>(null);

  // FAB Expanded state
  const [isExpanded, setIsExpanded] = useState(false);
  const fabInputRef = useRef<HTMLTextAreaElement>(null);
  const inlineInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsFloating(!entry.isIntersecting);
      },
      {
        threshold: 0,
        // Make it float slightly before it completely exits the viewport so the morph feels proactive.
        rootMargin: "-40px 0px -40px 0px"
      }
    );

    if (placeholderRef.current) observer.observe(placeholderRef.current);
    return () => observer.disconnect();
  }, []);

  // Sync focus
  useEffect(() => {
    if (isFloating && isExpanded && fabInputRef.current) {
      setTimeout(() => fabInputRef.current?.focus(), 100);
    }
  }, [isExpanded, isFloating]);

  const handleAsk = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await askLotus(taskId, prompt);
      setResult(response);
      setPrompt("");
      if (isFloating) setIsExpanded(true); // Ensure FAB is expanded to show result
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      if (isFloating) setIsExpanded(true);
    } finally {
      setLoading(false);
    }
  };

  const clearResult = () => {
    setResult(null);
    setError(null);
  };

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
    if (isExpanded) {
      clearResult();
      setPrompt("");
    }
  };

  return (
    <>
      {/* INLINE PLACEHOLDER & VIEW */}
      <div
        ref={placeholderRef}
        className="w-full relative z-20 flex flex-col items-center justify-center transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        <div className={`w-full max-w-2xl mx-auto flex flex-col gap-4 transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${isFloating ? "opacity-0 scale-y-90 blur-[2px] pointer-events-none -translate-y-4" : "opacity-100 scale-100 blur-0 translate-y-0"}`}>

          {/* Inline Input Box */}
          <div className="group relative flex items-center p-2 rounded-[24px] border border-primary/20 bg-background/70 backdrop-blur-xl shadow-sm hover:shadow-md hover:border-primary/40 transition-all duration-300">
            {/* Subtle Focus Glow */}
            <div className="absolute inset-0 rounded-[24px] bg-gradient-to-r from-primary/10 via-transparent to-primary/10 opacity-0 transition-opacity duration-300 inline-focus-glow pointer-events-none" />

            <div className="h-10 w-10 shrink-0 flex items-center justify-center rounded-full bg-primary/5 ml-1">
              <LotusIcon className="h-5 w-5 text-primary transition-transform duration-300 group-hover:scale-110" />
            </div>

            <div className="flex-1 py-1 px-3 relative flex items-center">
              <Textarea
                ref={inlineInputRef}
                placeholder="Ask Lotus to pull context, summarize, or draft responses based on this task..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onFocus={(e) => {
                  const glow = e.target.parentElement?.parentElement?.querySelector('.inline-focus-glow');
                  if (glow) glow.classList.replace('opacity-0', 'opacity-100');
                }}
                onBlur={(e) => {
                  const glow = e.target.parentElement?.parentElement?.querySelector('.inline-focus-glow');
                  if (glow) glow.classList.replace('opacity-100', 'opacity-0');
                }}
                rows={1}
                className="text-sm border-0 bg-transparent focus-visible:ring-0 shadow-none resize-none min-h-[22px] max-h-[160px] w-full p-0 m-0 leading-relaxed task-sheet-scroll"
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    handleAsk();
                  }
                }}
              />
            </div>

            <Button
              size="icon"
              onClick={handleAsk}
              disabled={loading || prompt.trim().length === 0}
              className={`h-10 w-10 shrink-0 rounded-full transition-all duration-300 mr-1 ${prompt.trim().length > 0
                ? 'bg-primary text-primary-foreground shadow-md hover:scale-105 active:scale-95'
                : 'bg-muted text-muted-foreground/50'
                }`}
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 transform translate-x-[1px]" />}
            </Button>
          </div>

          {/* Inline Error & Result */}
          {error && !isFloating && (
            <div className="w-full max-w-2xl px-5 py-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-2xl animate-in slide-in-from-top-2 fade-in duration-500">
              {error}
            </div>
          )}

          {result && !isFloating && (
            <div className="w-full max-w-2xl rounded-[24px] border border-primary/20 bg-background/80 backdrop-blur-xl shadow-lg p-6 space-y-4 animate-in slide-in-from-top-4 fade-in duration-500 task-sheet-scroll max-h-[60vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-primary/10 pb-4 mb-4">
                <div className="flex items-center gap-2">
                  <LotusIcon className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium text-primary tracking-wide">Lotus Insights</span>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="text-[10px] uppercase tracking-wider font-medium bg-muted/50 border-none text-muted-foreground">
                    {result.similar_cases} past case{result.similar_cases !== 1 ? "s" : ""}
                  </Badge>
                  {result.model !== "fallback" && (
                    <Badge variant="outline" className="text-[10px] uppercase tracking-wider font-medium bg-primary/5 border-primary/20 text-primary/80">
                      {result.model}
                    </Badge>
                  )}
                  <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full hover:bg-muted ml-2" onClick={clearResult}>
                    <X className="h-3 w-3 text-muted-foreground" />
                  </Button>
                </div>
              </div>
              <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed prose prose-sm max-w-none dark:prose-invert font-medium px-1">
                {result.response}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* FLOATING ACTION BUTTON VIEW */}
      <div
        className={`fixed bottom-6 right-6 z-50 flex flex-col items-end gap-4 transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${isFloating ? "opacity-100 translate-y-0 scale-100 blur-0 pointer-events-auto" : "opacity-0 translate-y-8 scale-90 blur-[2px] pointer-events-none"
          }`}
      >
        {/* FAB Error Card */}
        {error && isExpanded && (
          <div className="w-[380px] p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-2xl shadow-lg backdrop-blur-md animate-in slide-in-from-bottom-8 fade-in duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]">
            {error}
          </div>
        )}

        {/* FAB Result Card */}
        {result && isExpanded && (
          <div className="w-[380px] max-h-[60vh] overflow-y-auto rounded-[24px] border border-primary/20 bg-background/95 backdrop-blur-xl shadow-2xl p-5 space-y-4 animate-in slide-in-from-bottom-8 fade-in duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] task-sheet-scroll">
            <div className="flex items-center justify-between sticky top-0 bg-background/95 pt-1 pb-3 z-10">
              <div className="flex items-center gap-2">
                <LotusIcon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium text-primary tracking-wide">Insights</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-[10px] uppercase tracking-wider font-medium bg-muted/50 border-none text-muted-foreground">
                  {result.similar_cases} past case{result.similar_cases !== 1 ? "s" : ""}
                </Badge>
                {result.model !== "fallback" && (
                  <Badge variant="outline" className="text-[10px] uppercase tracking-wider font-medium bg-primary/5 border-primary/20 text-primary/80">
                    {result.model}
                  </Badge>
                )}
                <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full hover:bg-muted ml-1" onClick={clearResult}>
                  <X className="h-3 w-3 text-muted-foreground" />
                </Button>
              </div>
            </div>
            <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed prose prose-sm max-w-none dark:prose-invert font-medium">
              {result.response}
            </div>
          </div>
        )}

        {/* Morphing FAB / Input Container */}
        <div
          className={
            `group relative flex justify-end overflow-hidden transition-all duration-500 ease-[cubic-bezier(0.25,1,0.5,1)] origin-bottom-right shadow-[0_8px_30px_rgb(0,0,0,0.12)] ` +
            (isExpanded
              ? "w-[380px] rounded-[24px] bg-background/95 backdrop-blur-xl border border-primary/20 hover:border-primary/40 "
              : "w-14 h-14 rounded-full bg-primary text-primary-foreground hover:-translate-y-1 hover:shadow-2xl border border-transparent ")
          }
        >
          {/* Expanded UI */}
          <div
            className={`flex shrink-0 items-end p-2 gap-2 w-[380px] transition-all duration-400 ease-[cubic-bezier(0.25,1,0.5,1)] ${isExpanded
              ? 'opacity-100 translate-x-0 delay-75 pointer-events-auto'
              : 'opacity-0 translate-x-8 pointer-events-none absolute inset-0'
              }`}
          >
            <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-0 transition-opacity duration-300 pointer-events-none fab-focus-glow" />

            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-full hover:bg-muted text-muted-foreground transition-colors"
              onClick={toggleExpand}
            >
              <X className="h-5 w-5" />
            </Button>

            <div className="flex-1 py-2 px-1 relative flex items-center">
              <Textarea
                ref={fabInputRef}
                placeholder="Ask Lotus to summarize or suggest..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onFocus={(e) => {
                  const glow = e.target.parentElement?.parentElement?.querySelector('.fab-focus-glow');
                  if (glow) glow.classList.replace('opacity-0', 'opacity-100');
                }}
                onBlur={(e) => {
                  const glow = e.target.parentElement?.parentElement?.querySelector('.fab-focus-glow');
                  if (glow) glow.classList.replace('opacity-100', 'opacity-0');
                }}
                rows={1}
                className="text-sm resize-none bg-transparent border-0 p-0 m-0 focus-visible:ring-0 shadow-none min-h-[20px] max-h-[120px] w-full leading-relaxed task-sheet-scroll"
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    handleAsk();
                  }
                }}
              />
            </div>

            <Button
              size="icon"
              onClick={handleAsk}
              disabled={loading || prompt.trim().length === 0}
              className={`h-10 w-10 shrink-0 rounded-full transition-all duration-300 ${prompt.trim().length > 0
                ? 'bg-primary text-primary-foreground shadow-md hover:scale-105 active:scale-95'
                : 'bg-muted text-muted-foreground/50'
                }`}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4 transform translate-x-[1px]" />
              )}
            </Button>
          </div>

          {/* FAB Icon */}
          <div
            className={`absolute flex h-14 w-14 items-center justify-center right-0 bottom-0 transition-all duration-400 ease-[cubic-bezier(0.25,1,0.5,1)] ${isExpanded
              ? 'opacity-0 scale-50 -rotate-90 pointer-events-none'
              : 'opacity-100 scale-100 rotate-0 cursor-pointer delay-100'
              }`}
            onClick={!isExpanded ? toggleExpand : undefined}
            title="Ask Lotus"
          >
            <div className="absolute inset-0 -z-10 rounded-full bg-primary/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <LotusIcon className={`h-6 w-6 text-primary-foreground transition-transform duration-300 ${!isExpanded ? 'group-hover:scale-110' : ''}`} />
          </div>
        </div>
      </div>
    </>
  );
}


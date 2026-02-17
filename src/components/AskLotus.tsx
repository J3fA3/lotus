import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "./ui/collapsible";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Sparkles, ChevronRight, Loader2 } from "lucide-react";
import { askLotus, type AIAssistResponse } from "@/api/ai";

interface AskLotusProps {
  taskId: string;
}

export function AskLotus({ taskId }: AskLotusProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIAssistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await askLotus(taskId, prompt || undefined);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-4">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground">
          <ChevronRight
            className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`}
          />
          <Sparkles className="h-4 w-4" />
          Ask Lotus
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-2 space-y-3 px-2">
        <Textarea
          placeholder="What would you like help with? (optional — leave blank for general advice)"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={2}
          className="text-sm"
        />
        <Button
          size="sm"
          onClick={handleAsk}
          disabled={loading}
          className="gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {loading ? "Thinking..." : "Ask"}
        </Button>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {result && (
          <div className="rounded-md border bg-muted/50 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">
                {result.similar_cases} past case{result.similar_cases !== 1 ? "s" : ""} referenced
              </Badge>
              {result.model !== "fallback" && (
                <Badge variant="outline" className="text-xs">
                  {result.model}
                </Badge>
              )}
            </div>
            <div className="text-sm whitespace-pre-wrap leading-relaxed">
              {result.response}
            </div>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

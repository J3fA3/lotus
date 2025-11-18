import { useState, useRef, useCallback } from "react";
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
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Sparkles, FileText, Loader2, CheckCircle, AlertCircle, Upload } from "lucide-react";
import { inferTasksFromText, inferTasksFromDocument, InferenceResponse } from "@/api/tasks";
import { toast } from "sonner";
import { DocumentUpload } from "./DocumentUpload";

// Constants
const CLOSE_DELAY = 1500; // ms
const PLACEHOLDER_TEXT = `Paste Slack messages, meeting notes, emails, etc.

Example:
@john We need to update the API docs before Friday.
@sarah Can someone review the auth PR?
Let's schedule a meeting to discuss Q4 roadmap.`;

interface AIInferenceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTasksInferred: (result: InferenceResponse) => void;
}

export const AIInferenceDialog = ({
  open,
  onOpenChange,
  onTasksInferred,
}: AIInferenceDialogProps) => {
  const [inputText, setInputText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isInferring, setIsInferring] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<InferenceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = useCallback(() => {
    setInputText("");
    setSelectedFile(null);
    setInferenceResult(null);
    setError(null);
    setIsInferring(false);
    onOpenChange(false);
  }, [onOpenChange]);

  const handleInferFromText = useCallback(async () => {
    if (!inputText.trim()) {
      toast.error("Please enter some text to analyze");
      return;
    }

    setIsInferring(true);
    setError(null);

    try {
      const result = await inferTasksFromText(inputText);
      setInferenceResult(result);

      const taskCount = result.tasks_inferred;
      if (taskCount === 0) {
        toast.info("No tasks found in the text");
      } else {
        const taskWord = taskCount === 1 ? "task" : "tasks";
        toast.success(`Found ${taskCount} ${taskWord}!`);
        onTasksInferred(result);

        // Close dialog after short delay
        setTimeout(() => {
          onOpenChange(false);
          setInputText("");
          setInferenceResult(null);
          setError(null);
        }, CLOSE_DELAY);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to infer tasks";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsInferring(false);
    }
  }, [inputText, onTasksInferred, onOpenChange]);

  const handleInferFromDocument = useCallback(async () => {
    if (!selectedFile) {
      toast.error("Please select a document file");
      return;
    }

    setIsInferring(true);
    setError(null);

    try {
      const result = await inferTasksFromDocument(selectedFile);
      setInferenceResult(result);

      const taskCount = result.tasks_inferred;
      if (taskCount === 0) {
        toast.info("No tasks found in the document");
      } else {
        const taskWord = taskCount === 1 ? "task" : "tasks";
        toast.success(`Found ${taskCount} ${taskWord}!`);
        onTasksInferred(result);

        // Close dialog after short delay
        setTimeout(() => {
          onOpenChange(false);
          setSelectedFile(null);
          setInferenceResult(null);
          setError(null);
        }, CLOSE_DELAY);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to process document";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsInferring(false);
    }
  }, [selectedFile, onTasksInferred, onOpenChange]);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError(null);
  }, []);

  const handleFileRemove = useCallback(() => {
    setSelectedFile(null);
    setError(null);
  }, []);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Sparkles className="h-5 w-5 text-primary" />
            AI Task Inference
          </DialogTitle>
          <DialogDescription className="truncate">
            Paste text or upload documents (PDF, Word, Excel, Markdown). AI will automatically extract tasks.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="text" className="w-full overflow-hidden">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="text" className="gap-2">
              <FileText className="h-4 w-4" />
              Paste Text
            </TabsTrigger>
            <TabsTrigger value="pdf" className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Document
            </TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="space-y-4 mt-4">
            <div className="space-y-3">
              <Label htmlFor="input-text" className="text-sm font-medium">
                Paste your content here
              </Label>
              <Textarea
                id="input-text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={PLACEHOLDER_TEXT}
                rows={12}
                className="resize-none font-mono text-sm"
                disabled={isInferring}
              />
              <p className="text-xs text-muted-foreground">
                💡 Tip: Include dates, assignees, and context for better results
              </p>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            {inferenceResult && !error && (
              <div className="flex items-start gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-green-700 dark:text-green-400 font-medium">
                    Found {inferenceResult.tasks_inferred} task{inferenceResult.tasks_inferred > 1 ? 's' : ''}
                  </p>
                  <p className="text-xs text-green-600/80 dark:text-green-500/80 mt-1">
                    Inference time: {(inferenceResult.inference_time_ms / 1000).toFixed(1)}s
                  </p>
                </div>
              </div>
            )}

            <Button
              onClick={handleInferFromText}
              disabled={isInferring || !inputText.trim()}
              className="w-full"
              size="lg"
            >
              {isInferring ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Analyzing with AI...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Infer Tasks
                </>
              )}
            </Button>
          </TabsContent>

          <TabsContent value="pdf" className="space-y-4 mt-4 overflow-hidden">
            <div className="space-y-3 overflow-hidden">
              <Label className="text-sm font-medium">
                Upload Document
              </Label>

              <DocumentUpload
                onFileSelect={handleFileSelect}
                onFileRemove={handleFileRemove}
                selectedFile={selectedFile}
                disabled={isInferring}
                showFileInfo={true}
              />

              <p className="text-xs text-muted-foreground">
                💡 Works best with meeting transcripts, project plans, status reports, and meeting notes
              </p>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            {inferenceResult && !error && (
              <div className="flex items-start gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-green-700 dark:text-green-400 font-medium">
                    Found {inferenceResult.tasks_inferred} task{inferenceResult.tasks_inferred > 1 ? 's' : ''}
                  </p>
                  <p className="text-xs text-green-600/80 dark:text-green-500/80 mt-1">
                    Inference time: {(inferenceResult.inference_time_ms / 1000).toFixed(1)}s
                  </p>
                </div>
              </div>
            )}

            <Button
              onClick={handleInferFromDocument}
              disabled={isInferring || !selectedFile}
              className="w-full"
              size="lg"
            >
              {isInferring ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Processing Document with AI...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Infer Tasks from Document
                </>
              )}
            </Button>
          </TabsContent>
        </Tabs>

        {isInferring && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">
              This may take 10-30 seconds depending on your system...
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

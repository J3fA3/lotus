import { useState, useRef } from "react";
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
import { inferTasksFromText, inferTasksFromPDF, InferenceResponse } from "@/api/tasks";
import { toast } from "sonner";

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

  const handleInferFromText = async () => {
    if (!inputText.trim()) {
      toast.error("Please enter some text to analyze");
      return;
    }

    setIsInferring(true);
    setError(null);

    try {
      const result = await inferTasksFromText(inputText);
      setInferenceResult(result);

      if (result.tasks_inferred === 0) {
        toast.info("No tasks found in the text");
      } else {
        toast.success(`Found ${result.tasks_inferred} task${result.tasks_inferred > 1 ? 's' : ''}!`);
        onTasksInferred(result);

        // Close dialog after short delay
        setTimeout(() => {
          handleClose();
        }, 1500);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to infer tasks";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsInferring(false);
    }
  };

  const handleInferFromPDF = async () => {
    if (!selectedFile) {
      toast.error("Please select a PDF file");
      return;
    }

    setIsInferring(true);
    setError(null);

    try {
      const result = await inferTasksFromPDF(selectedFile);
      setInferenceResult(result);

      if (result.tasks_inferred === 0) {
        toast.info("No tasks found in the PDF");
      } else {
        toast.success(`Found ${result.tasks_inferred} task${result.tasks_inferred > 1 ? 's' : ''}!`);
        onTasksInferred(result);

        // Close dialog after short delay
        setTimeout(() => {
          handleClose();
        }, 1500);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to process PDF";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsInferring(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== "application/pdf") {
        toast.error("Please select a PDF file");
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleClose = () => {
    setInputText("");
    setSelectedFile(null);
    setInferenceResult(null);
    setError(null);
    setIsInferring(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Sparkles className="h-5 w-5 text-primary" />
            AI Task Inference
          </DialogTitle>
          <DialogDescription>
            Paste Slack messages, meeting notes, or upload a PDF. AI will automatically extract tasks.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="text" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="text" className="gap-2">
              <FileText className="h-4 w-4" />
              Paste Text
            </TabsTrigger>
            <TabsTrigger value="pdf" className="gap-2">
              <Upload className="h-4 w-4" />
              Upload PDF
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
                placeholder="Paste Slack messages, meeting notes, emails, etc.&#10;&#10;Example:&#10;@john We need to update the API docs before Friday.&#10;@sarah Can someone review the auth PR?&#10;Let's schedule a meeting to discuss Q4 roadmap."
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

          <TabsContent value="pdf" className="space-y-4 mt-4">
            <div className="space-y-3">
              <Label htmlFor="pdf-upload" className="text-sm font-medium">
                Upload PDF Document
              </Label>

              <div
                className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                {selectedFile ? (
                  <div>
                    <p className="font-medium text-sm">{selectedFile.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-muted-foreground">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      PDF files only (max 10MB)
                    </p>
                  </div>
                )}
              </div>

              <Input
                ref={fileInputRef}
                id="pdf-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />

              <p className="text-xs text-muted-foreground">
                💡 Works best with meeting transcripts, project plans, and status reports
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
              onClick={handleInferFromPDF}
              disabled={isInferring || !selectedFile}
              className="w-full"
              size="lg"
            >
              {isInferring ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Processing PDF with AI...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Infer Tasks from PDF
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

/**
 * OAuth Prompt Component
 * 
 * Minimal inline prompt that appears when user is not connected.
 * One-click to start OAuth - no intermediate pages.
 * 
 * @example
 * ```tsx
 * <OAuthPrompt onDismiss={() => setShowPrompt(false)} compact={false} />
 * ```
 */

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { X, Loader2, Calendar, Mail } from "lucide-react";
import { useOAuth } from "@/hooks/useOAuth";

interface OAuthPromptProps {
  /** Callback when user dismisses the prompt */
  onDismiss?: () => void;
  /** Use compact layout */
  compact?: boolean;
}

export const OAuthPrompt = ({ onDismiss, compact = false }: OAuthPromptProps) => {
  const { connect, isConnecting } = useOAuth();

  const handleConnect = async () => {
    await connect();
  };

  if (compact) {
    return (
      <Alert className="border-blue-200 bg-blue-50/50">
        <Calendar className="h-4 w-4 text-blue-600" />
        <AlertDescription className="flex items-center justify-between gap-4">
          <span className="text-sm">Connect Google Calendar & Gmail for AI-powered features</span>
          <Button
            size="sm"
            onClick={handleConnect}
            disabled={isConnecting}
            className="shrink-0"
          >
            {isConnecting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              "Connect"
            )}
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert className="border-blue-200 bg-gradient-to-r from-blue-50/50 to-indigo-50/50">
      <div className="flex items-start gap-3">
        <div className="flex gap-2 shrink-0">
          <Calendar className="h-5 w-5 text-blue-600 mt-0.5" />
          <Mail className="h-5 w-5 text-indigo-600 mt-0.5" />
        </div>
        <div className="flex-1 space-y-2">
          <AlertDescription className="text-sm">
            <strong>Connect your Google account</strong> to unlock AI-powered scheduling, 
            email task extraction, and meeting preparation.
          </AlertDescription>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleConnect}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <>
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Connecting...
                </>
              ) : (
                "Connect Google Account"
              )}
            </Button>
            {onDismiss && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDismiss}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </Alert>
  );
};


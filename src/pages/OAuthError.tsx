/**
 * OAuth Error Page
 * 
 * Helpful error page shown when OAuth authorization fails.
 * Provides clear error messages and recovery options.
 * 
 * @example
 * Route: `/oauth/error?error=access_denied` - Displays user-friendly error message
 */

import { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, RefreshCw, Home, HelpCircle, Shield } from "lucide-react";
import { useOAuth } from "@/hooks/useOAuth";
import { parseOAuthError, shouldAutoRetry } from "@/utils/oauthErrorParser";
import { toast } from "sonner";

const OAuthError = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { connect, isConnecting } = useOAuth({
    onError: () => {
      toast.error("Failed to start authorization. Please try again.");
    },
  });

  const error = searchParams.get("error") || "An unknown error occurred";
  const errorCode = searchParams.get("error_code");
  const errorDescription = searchParams.get("error_description");

  // Parse error message for better UX
  const errorDetails = parseOAuthError(error, errorDescription);
  
  // Map icon string to React component
  const getErrorIcon = () => {
    switch (errorDetails.icon) {
      case "shield":
        return <Shield className="h-6 w-6 text-amber-600" />;
      case "server":
        return <AlertCircle className="h-6 w-6 text-red-600" />;
      default:
        return <AlertCircle className="h-6 w-6 text-red-600" />;
    }
  };

  const handleRetry = async () => {
    await connect();
  };

  // Auto-retry for certain errors after a brief moment
  useEffect(() => {
    if (shouldAutoRetry(error)) {
      // Auto-retry after 3 seconds for temporary errors
      const timer = setTimeout(async () => {
        await connect();
      }, 3000);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 via-rose-50 to-pink-50 p-4">
      <Card className="w-full max-w-lg border-2 shadow-2xl">
        <CardHeader className="text-center pb-4">
          {/* Error Icon */}
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-red-100">
            {getErrorIcon()}
          </div>

          <CardTitle className="text-2xl font-bold text-red-700 mb-2">
            {errorDetails.title}
          </CardTitle>
          <CardDescription className="text-base">
            {errorDetails.description}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Error Details */}
          {errorCode && (
            <div className="p-3 rounded-lg bg-muted border">
              <p className="text-xs font-mono text-muted-foreground">
                Error Code: {errorCode}
              </p>
            </div>
          )}

          {/* Suggestion */}
          <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-100">
            <div className="flex items-start gap-3">
              <HelpCircle className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
              <p className="text-sm text-muted-foreground">
                {errorDetails.suggestion}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <Button
              onClick={handleRetry}
              disabled={isConnecting}
              size="lg"
              className="w-full"
            >
              {isConnecting ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try Again
                </>
              )}
            </Button>

            <Button
              onClick={() => navigate("/")}
              variant="outline"
              size="lg"
              className="w-full"
            >
              <Home className="mr-2 h-4 w-4" />
              Go to Dashboard
            </Button>
          </div>

          {/* Help Text */}
          <div className="pt-4 border-t">
            <p className="text-xs text-center text-muted-foreground">
              Need help? Check our{" "}
              <a href="/docs" className="text-primary hover:underline">
                documentation
              </a>
              {" "}or contact support.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default OAuthError;


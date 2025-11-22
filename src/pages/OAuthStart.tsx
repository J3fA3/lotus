/**
 * OAuth Start Page
 * 
 * Ultra-minimal page that immediately redirects to Google OAuth.
 * No button clicks, no delays - just instant redirect.
 * 
 * @example
 * Route: `/oauth/start` - Automatically redirects to Google OAuth
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useOAuth } from "@/hooks/useOAuth";
import { toast } from "sonner";

const OAuthStart = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<"checking" | "redirecting" | "authorized" | "error">("checking");
  const { connect, checkStatus } = useOAuth({
    onError: () => {
      setStatus("error");
      setTimeout(() => {
        navigate("/oauth/error?error=Failed to start authorization", { replace: true });
      }, 2000);
    },
  });

  useEffect(() => {
    const startOAuth = async () => {
      try {
        // Quick status check - if already authorized, go to dashboard
        const authStatus = await checkStatus();
        if (authStatus?.authorized) {
          setStatus("authorized");
          navigate("/", { replace: true });
          return;
        }

        // Not authorized - immediately redirect to Google
        setStatus("redirecting");
        await connect();
      } catch (error) {
        setStatus("error");
        toast.error("Failed to start authorization. Please try again.");
        setTimeout(() => {
          navigate("/oauth/error?error=Failed to start authorization", { replace: true });
        }, 2000);
      }
    };

    startOAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  // Minimal loading state - just show spinner
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="text-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
        <p className="text-sm text-muted-foreground">
          {status === "authorized" 
            ? "Already connected, redirecting..." 
            : status === "redirecting"
            ? "Redirecting to Google..."
            : status === "error"
            ? "Something went wrong..."
            : "Starting authorization..."}
        </p>
      </div>
    </div>
  );
};

export default OAuthStart;

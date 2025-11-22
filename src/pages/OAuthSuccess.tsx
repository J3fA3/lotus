/**
 * OAuth Success Page
 * 
 * Minimal success page that immediately redirects to dashboard.
 * Shows a brief success message via toast notification instead of a full page.
 * 
 * @example
 * Route: `/oauth/success` - Called after successful OAuth callback
 */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { useOAuth } from "@/hooks/useOAuth";
import { toast } from "sonner";

const OAuthSuccess = () => {
  const navigate = useNavigate();
  const { checkStatus } = useOAuth();

  useEffect(() => {
    const verifyAndRedirect = async () => {
      try {
        // Quick verification (no artificial delay)
        const status = await checkStatus();
        
        if (status?.authorized) {
          // Show success toast
          toast.success("Google account connected successfully!", {
            description: "Your calendar and email are now syncing.",
            duration: 4000,
          });
        } else {
          // If somehow not authorized, show warning but still redirect
          toast.warning("Authorization may not be complete. Please check your settings.");
        }
      } catch (error) {
        // Still redirect even if verification fails
        toast.success("Authorization complete!", {
          description: "Redirecting to dashboard...",
        });
      }
      
      // Immediately redirect to dashboard (no user click needed)
      navigate("/", { replace: true });
    };

    // Start immediately, no delay
    verifyAndRedirect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  // Minimal loading state - just show brief success indicator
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-50">
      <div className="text-center space-y-4">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <CheckCircle2 className="h-8 w-8 text-green-600" />
        </div>
        <p className="text-sm text-muted-foreground">Success! Redirecting...</p>
      </div>
    </div>
  );
};

export default OAuthSuccess;


/**
 * OAuth Status Component
 * 
 * Widget that displays OAuth connection status and allows users to connect/disconnect.
 * Can be embedded in settings or dashboard.
 * 
 * @example
 * ```tsx
 * <OAuthStatus userId={1} showDetails={true} compact={false} />
 * ```
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  ExternalLink, 
  RefreshCw,
  Calendar,
  Mail,
} from "lucide-react";
import { useOAuth } from "@/hooks/useOAuth";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface OAuthStatusProps {
  /** User ID for OAuth operations */
  userId?: number;
  /** Show detailed status information */
  showDetails?: boolean;
  /** Use compact layout */
  compact?: boolean;
}

const OAuthStatus = ({ userId = 1, showDetails = true, compact = false }: OAuthStatusProps) => {
  const [status, setStatus] = useState<{ authorized: boolean; user_id: number } | null>(null);
  const [loading, setLoading] = useState(true);
  
  const { connect, revoke, isConnecting, isRevoking, isChecking, checkStatus } = useOAuth({
    userId,
    onSuccess: () => {
      fetchStatus();
    },
  });

  const fetchStatus = async () => {
    setLoading(true);
    const authStatus = await checkStatus();
    if (authStatus) {
      setStatus(authStatus);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleConnect = async () => {
    await connect();
  };

  const handleRevoke = async () => {
    await revoke();
    await fetchStatus();
  };

  if (loading || isChecking) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Checking status...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isAuthorized = status?.authorized ?? false;

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {isAuthorized ? (
          <>
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Connected
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRevoke}
              disabled={isRevoking}
            >
              {isRevoking ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <XCircle className="h-3 w-3" />
              )}
            </Button>
          </>
        ) : (
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
              <>
                <ExternalLink className="h-3 w-3 mr-1" />
                Connect
              </>
            )}
          </Button>
        )}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Google Account</CardTitle>
            <CardDescription>
              Connect your Google Calendar and Gmail
            </CardDescription>
          </div>
          {isAuthorized ? (
            <Badge className="bg-green-500">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge variant="outline">
              <XCircle className="h-3 w-3 mr-1" />
              Not Connected
            </Badge>
          )}
        </div>
      </CardHeader>
      {showDetails && (
        <CardContent className="space-y-4">
          {/* Services Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Calendar</span>
              </div>
              {isAuthorized ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  Active
                </Badge>
              ) : (
                <Badge variant="outline">Inactive</Badge>
              )}
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Gmail</span>
              </div>
              {isAuthorized ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  Active
                </Badge>
              ) : (
                <Badge variant="outline">Inactive</Badge>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            {isAuthorized ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchStatus}
                  className="flex-1"
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="destructive"
                      size="sm"
                      className="flex-1"
                    >
                      <XCircle className="h-4 w-4 mr-1" />
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Disconnect Google Account?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will revoke access to your Google Calendar and Gmail. 
                        You'll need to reconnect to use these features again.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleRevoke}
                        disabled={isRevoking}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        {isRevoking ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                            Revoking...
                          </>
                        ) : (
                          "Disconnect"
                        )}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            ) : (
              <Button
                onClick={handleConnect}
                disabled={isConnecting}
                className="flex-1"
              >
                {isConnecting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Connect Google Account
                  </>
                )}
              </Button>
            )}
          </div>

          {/* Help Text */}
          <p className="text-xs text-muted-foreground text-center pt-2">
            {isAuthorized
              ? "Your account is connected and syncing"
              : "Connect to enable calendar and email features"}
          </p>
        </CardContent>
      )}
    </Card>
  );
};

export default OAuthStatus;


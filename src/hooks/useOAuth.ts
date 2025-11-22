/**
 * OAuth Hook
 * 
 * Shared hook for OAuth operations that eliminates duplicate connection logic
 * across OAuthPrompt, OAuthStatus, OAuthStart, and OAuthError components.
 * 
 * @example
 * ```tsx
 * const { connect, isConnecting, error } = useOAuth();
 * 
 * const handleConnect = async () => {
 *   await connect();
 * };
 * ```
 */

import { useState, useCallback } from "react";
import { getAuthorizationUrl, checkAuthStatus, revokeAuthorization } from "@/api/oauth";
import { toast } from "sonner";

interface UseOAuthOptions {
  userId?: number;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

interface UseOAuthReturn {
  /** Connect to Google OAuth - redirects immediately */
  connect: () => Promise<void>;
  /** Check current authorization status */
  checkStatus: () => Promise<{ authorized: boolean; user_id: number } | null>;
  /** Revoke OAuth authorization */
  revoke: () => Promise<void>;
  /** Whether a connection attempt is in progress */
  isConnecting: boolean;
  /** Whether a revocation is in progress */
  isRevoking: boolean;
  /** Whether a status check is in progress */
  isChecking: boolean;
  /** Last error encountered */
  error: Error | null;
}

/**
 * Hook for OAuth operations
 * 
 * @param options - Configuration options
 * @returns OAuth operations and state
 */
export function useOAuth(options: UseOAuthOptions = {}): UseOAuthReturn {
  const { userId = 1, onSuccess, onError } = options;
  const [isConnecting, setIsConnecting] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const connect = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    try {
      const authUrl = await getAuthorizationUrl(userId);
      // Immediate redirect - no intermediate page
      window.location.href = authUrl;
      // Note: onSuccess won't be called due to redirect, but included for API consistency
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to start authorization");
      setError(error);
      toast.error("Failed to start authorization");
      setIsConnecting(false);
      onError?.(error);
    }
  }, [userId, onError]);

  const checkStatus = useCallback(async () => {
    setIsChecking(true);
    setError(null);
    try {
      const status = await checkAuthStatus(userId);
      return status;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to check auth status");
      setError(error);
      toast.error("Failed to check connection status");
      return null;
    } finally {
      setIsChecking(false);
    }
  }, [userId]);

  const revoke = useCallback(async () => {
    setIsRevoking(true);
    setError(null);
    try {
      await revokeAuthorization(userId);
      toast.success("Authorization revoked successfully");
      onSuccess?.();
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to revoke authorization");
      setError(error);
      toast.error("Failed to revoke authorization");
    } finally {
      setIsRevoking(false);
    }
  }, [userId, onSuccess]);

  return {
    connect,
    checkStatus,
    revoke,
    isConnecting,
    isRevoking,
    isChecking,
    error,
  };
}


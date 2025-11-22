/**
 * OAuth Error Parser
 * 
 * Centralized error parsing logic for OAuth errors.
 * Extracted from OAuthError component to eliminate duplication.
 */

export interface OAuthErrorDetails {
  title: string;
  description: string;
  suggestion: string;
  icon: "shield" | "alert" | "server";
  color: "amber" | "red";
}

/**
 * Parse OAuth error message into user-friendly details
 * 
 * @param error - Error message from query params
 * @param errorDescription - Optional detailed error description
 * @returns Parsed error details with UI-friendly information
 */
export function parseOAuthError(
  error: string,
  errorDescription?: string | null
): OAuthErrorDetails {
  const errorLower = error.toLowerCase();

  if (errorLower.includes("access_denied") || errorLower.includes("denied")) {
    return {
      title: "Authorization Denied",
      description: "You chose not to authorize the application. No changes were made to your account.",
      suggestion: "If you'd like to connect your Google account, you can try again.",
      icon: "shield",
      color: "amber",
    };
  }

  if (errorLower.includes("invalid_request") || errorLower.includes("invalid")) {
    return {
      title: "Invalid Request",
      description: "The authorization request was invalid. This might be a temporary issue.",
      suggestion: "Please try again. If the problem persists, contact support.",
      icon: "alert",
      color: "red",
    };
  }

  if (errorLower.includes("server") || errorLower.includes("500")) {
    return {
      title: "Server Error",
      description: "We encountered an issue processing your authorization.",
      suggestion: "Please try again in a few moments. Our team has been notified.",
      icon: "server",
      color: "red",
    };
  }

  // Default error
  return {
    title: "Authorization Failed",
    description: errorDescription || error,
    suggestion: "Please try again. If the problem continues, contact support.",
    icon: "alert",
    color: "red",
  };
}

/**
 * Check if an error should trigger auto-retry
 * 
 * @param error - Error message
 * @returns True if error is temporary and should be auto-retried
 */
export function shouldAutoRetry(error: string): boolean {
  const errorLower = error.toLowerCase();
  return (
    errorLower.includes("server") ||
    errorLower.includes("500") ||
    errorLower.includes("temporary")
  );
}


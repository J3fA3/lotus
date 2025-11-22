/**
 * OAuth API Client
 *
 * Handles Google OAuth authentication flow for Calendar and Gmail integration.
 * 
 * @module api/oauth
 */

const API_BASE = "/api/auth/google";

// ============================================================================
// TYPES
// ============================================================================

/**
 * OAuth authorization status
 */
export interface OAuthStatus {
  /** Whether the user is currently authorized */
  authorized: boolean;
  /** User ID */
  user_id: number;
}

/**
 * OAuth authorization response
 */
export interface OAuthAuthorizeResponse {
  /** URL to redirect user to for authorization */
  authorization_url: string;
  /** Status message */
  message: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Get OAuth authorization URL to start the authentication flow.
 * 
 * @param userId - User ID (default: 1)
 * @returns Promise resolving to the authorization URL
 * @throws Error if the request fails
 * 
 * @example
 * ```ts
 * const url = await getAuthorizationUrl(1);
 * window.location.href = url;
 * ```
 */
export async function getAuthorizationUrl(userId: number = 1): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/authorize?user_id=${userId}`);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to get authorization URL" }));
      throw new Error(error.detail || "Failed to get authorization URL");
    }
    
    const data: OAuthAuthorizeResponse = await response.json();
    return data.authorization_url;
  } catch (error) {
    // Re-throw to allow caller to handle
    throw error;
  }
}

/**
 * Check if user is currently authorized.
 * 
 * @param userId - User ID (default: 1)
 * @returns Promise resolving to the authorization status
 * @throws Error if the request fails
 * 
 * @example
 * ```ts
 * const status = await checkAuthStatus(1);
 * if (status.authorized) {
 *   // User is authorized
 * }
 * ```
 */
export async function checkAuthStatus(userId: number = 1): Promise<OAuthStatus> {
  try {
    const response = await fetch(`${API_BASE}/status?user_id=${userId}`);
    
    if (!response.ok) {
      throw new Error("Failed to check auth status");
    }
    
    return await response.json();
  } catch (error) {
    // Re-throw to allow caller to handle
    throw error;
  }
}

/**
 * Revoke OAuth authorization.
 * 
 * @param userId - User ID (default: 1)
 * @returns Promise that resolves when revocation is complete
 * @throws Error if the request fails
 * 
 * @example
 * ```ts
 * await revokeAuthorization(1);
 * // Authorization has been revoked
 * ```
 */
export async function revokeAuthorization(userId: number = 1): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/revoke?user_id=${userId}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to revoke authorization" }));
      throw new Error(error.detail || "Failed to revoke authorization");
    }
  } catch (error) {
    // Re-throw to allow caller to handle
    throw error;
  }
}


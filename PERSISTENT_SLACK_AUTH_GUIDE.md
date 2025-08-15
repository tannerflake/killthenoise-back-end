# Persistent Slack Authentication Guide

This guide explains how to implement persistent Slack authentication so users only need to authenticate once and stay logged in across app restarts.

## Problem Solved

**Before:** Users had to re-authenticate with Slack every time they used the app because:
- Bot tokens were stored but had limited scopes
- No OAuth flow was implemented for user-level access
- Frontend always showed "Connect to Slack" button

**After:** Users authenticate once and stay connected because:
- OAuth tokens are stored for long-term access
- Access tokens are automatically refreshed when they expire
- Frontend checks authentication status before showing connect button

## Backend Changes Made

### 1. Enhanced Token Storage
- **Before:** Only stored `token` (bot token)
- **After:** Stores `access_token`, `refresh_token`, `expires_in`, and `token_created_at`

### 2. Automatic Token Refresh
- **Before:** Tokens expired and required re-authentication
- **After:** Tokens are automatically refreshed using refresh tokens

### 3. New API Endpoints
- `GET /api/slack/auth-status/{tenant_id}` - Check if user is authenticated
- `GET /api/slack/authorize/{tenant_id}` - Get OAuth authorization URL
- `GET /api/slack/oauth/callback` - Handle OAuth callback
- `POST /api/slack/refresh-token/{tenant_id}/{integration_id}` - Manually refresh tokens

## Frontend Implementation

### Step 1: Update API Client

Add the new auth-status method to your API client:

```typescript
// In client/src/lib/api.ts

export interface SlackAuthStatus {
  authenticated: boolean;
  message: string;
  needs_auth: boolean;
  integration_id?: string;
  team?: string;
  scopes?: string[];
  can_refresh?: boolean;
}

export const api = {
  // ... existing methods

  async getSlackAuthStatus(tenantId: string): Promise<SlackAuthStatus> {
    const response = await api.get<SlackAuthStatus>(`/api/slack/auth-status/${tenantId}`);
    return response.data;
  },

  async getSlackAuthUrl(tenantId: string): Promise<{ success: boolean; authorization_url: string; integration_id: string }> {
    const response = await api.get<{ success: boolean; authorization_url: string; integration_id: string }>(`/api/slack/authorize/${tenantId}`);
    return response.data;
  },

  async refreshSlackToken(tenantId: string, integrationId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(`/api/slack/refresh-token/${tenantId}/${integrationId}`);
    return response.data;
  }
};
```

### Step 2: Create Authentication Hook

Create a custom hook to manage Slack authentication state:

```typescript
// In client/src/hooks/useSlackAuth.ts

import { useState, useEffect } from 'react';
import { api, SlackAuthStatus } from '../lib/api';

interface UseSlackAuthProps {
  tenantId: string;
}

interface UseSlackAuthReturn {
  authStatus: SlackAuthStatus | null;
  loading: boolean;
  error: string | null;
  checkAuth: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

export const useSlackAuth = ({ tenantId }: UseSlackAuthProps): UseSlackAuthReturn => {
  const [authStatus, setAuthStatus] = useState<SlackAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await api.getSlackAuthStatus(tenantId);
      setAuthStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check authentication status');
    } finally {
      setLoading(false);
    }
  };

  const refreshToken = async (): Promise<boolean> => {
    if (!authStatus?.integration_id) return false;
    
    try {
      setLoading(true);
      setError(null);
      const result = await api.refreshSlackToken(tenantId, authStatus.integration_id);
      
      if (result.success) {
        // Re-check auth status after refresh
        await checkAuth();
        return true;
      }
      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh token');
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, [tenantId]);

  return {
    authStatus,
    loading,
    error,
    checkAuth,
    refreshToken
  };
};
```

### Step 3: Update Slack Connect Component

Update your existing Slack connect component to use the new authentication flow:

```typescript
// In client/src/components/SlackConnectCard.tsx

import React, { useState } from 'react';
import { useSlackAuth } from '../hooks/useSlackAuth';
import { api } from '../lib/api';

interface SlackConnectCardProps {
  tenantId: string;
}

export const SlackConnectCard: React.FC<SlackConnectCardProps> = ({ tenantId }) => {
  const { authStatus, loading, error, checkAuth, refreshToken } = useSlackAuth({ tenantId });
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    try {
      setConnecting(true);
      const result = await api.getSlackAuthUrl(tenantId);
      
      if (result.success) {
        // Open OAuth URL in new window
        window.open(result.authorization_url, '_blank', 'width=600,height=700');
        
        // Poll for authentication completion
        const pollInterval = setInterval(async () => {
          await checkAuth();
          if (authStatus?.authenticated) {
            clearInterval(pollInterval);
            setConnecting(false);
          }
        }, 2000);
        
        // Stop polling after 5 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          setConnecting(false);
        }, 300000);
      }
    } catch (err) {
      console.error('Failed to start OAuth flow:', err);
      setConnecting(false);
    }
  };

  const handleRefresh = async () => {
    const success = await refreshToken();
    if (success) {
      console.log('Token refreshed successfully');
    }
  };

  if (loading) {
    return (
      <div className="slack-connect-card">
        <div className="loading">Checking Slack connection...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="slack-connect-card">
        <div className="error">Error: {error}</div>
        <button onClick={checkAuth}>Retry</button>
      </div>
    );
  }

  if (authStatus?.authenticated) {
    return (
      <div className="slack-connect-card connected">
        <div className="status">
          <span className="icon">✅</span>
          <span className="text">Connected to Slack</span>
        </div>
        {authStatus.team && (
          <div className="details">
            <strong>Workspace:</strong> {authStatus.team}
          </div>
        )}
        {authStatus.scopes && authStatus.scopes.length > 0 && (
          <div className="details">
            <strong>Scopes:</strong> {authStatus.scopes.join(', ')}
          </div>
        )}
        <button onClick={handleRefresh} disabled={connecting}>
          Refresh Token
        </button>
      </div>
    );
  }

  if (authStatus?.can_refresh) {
    return (
      <div className="slack-connect-card needs-refresh">
        <div className="status">
          <span className="icon">⚠️</span>
          <span className="text">Token expired, but can be refreshed</span>
        </div>
        <button onClick={handleRefresh} disabled={connecting}>
          Refresh Connection
        </button>
      </div>
    );
  }

  return (
    <div className="slack-connect-card">
      <div className="status">
        <span className="icon">🔗</span>
        <span className="text">Connect to Slack</span>
      </div>
      <p>Connect your Slack workspace to sync messages and channels.</p>
      <button onClick={handleConnect} disabled={connecting}>
        {connecting ? 'Connecting...' : 'Connect to Slack'}
      </button>
    </div>
  );
};
```

### Step 4: Update Main App Component

Update your main app component to handle authentication state:

```typescript
// In client/src/App.tsx or your main component

import React from 'react';
import { useSlackAuth } from './hooks/useSlackAuth';
import { SlackConnectCard } from './components/SlackConnectCard';
import { Dashboard } from './components/Dashboard';

const App: React.FC = () => {
  const tenantId = "550e8400-e29b-41d4-a716-446655440000"; // Replace with actual tenant ID
  const { authStatus, loading } = useSlackAuth({ tenantId });

  if (loading) {
    return <div className="app-loading">Loading...</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>KillTheNoise</h1>
        <SlackConnectCard tenantId={tenantId} />
      </header>
      
      <main className="app-main">
        {authStatus?.authenticated ? (
          <Dashboard tenantId={tenantId} />
        ) : (
          <div className="auth-required">
            <h2>Welcome to KillTheNoise</h2>
            <p>Please connect your Slack workspace to get started.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
```

## Testing the Implementation

### 1. Test Authentication Flow

```bash
# Check if user is authenticated
curl "http://localhost:8000/api/slack/auth-status/550e8400-e29b-41d4-a716-446655440000"

# Expected response if not authenticated:
{
  "authenticated": false,
  "message": "No active Slack integration found",
  "needs_auth": true
}
```

### 2. Test OAuth Flow

```bash
# Get authorization URL
curl "http://localhost:8000/api/slack/authorize/550e8400-e29b-41d4-a716-446655440000"

# Expected response:
{
  "success": true,
  "authorization_url": "https://slack.com/oauth/v2/authorize?...",
  "integration_id": "uuid",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. Test After Authentication

After completing OAuth, check auth status again:

```bash
curl "http://localhost:8000/api/slack/auth-status/550e8400-e29b-41d4-a716-446655440000"

# Expected response if authenticated:
{
  "authenticated": true,
  "message": "Slack integration is active and working",
  "needs_auth": false,
  "integration_id": "uuid",
  "team": "Your Workspace",
  "scopes": ["channels:read", "channels:history", "groups:read", "groups:history"]
}
```

## Environment Configuration

Add these environment variables to your `.env` file:

```bash
# Slack OAuth Configuration
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_REDIRECT_URI=http://localhost:8000/api/slack/oauth/callback
```

## Slack App Configuration

### 1. Create a Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Enter app name and select workspace

### 2. Configure OAuth Settings

1. Go to "OAuth & Permissions" in the sidebar
2. Add redirect URL: `http://localhost:8000/api/slack/oauth/callback`
3. Add required scopes:
   - `channels:read`
   - `channels:history`
   - `groups:read`
   - `groups:history`

### 3. Install App to Workspace

1. Go to "Install App" in the sidebar
2. Click "Install to Workspace"
3. Copy the Client ID and Client Secret to your `.env` file

## Benefits

1. **Persistent Authentication:** Users only need to authenticate once
2. **Automatic Token Refresh:** Tokens are refreshed automatically when they expire
3. **Better UX:** No more repeated authentication prompts
4. **Reliable Integration:** Tokens are managed server-side with proper error handling
5. **Scalable:** Works for multiple tenants and integrations
6. **Enhanced Scopes:** OAuth provides better access to Slack APIs

## Troubleshooting

### Common Issues

1. **"No refresh token available"**
   - Old integrations don't have refresh tokens
   - Solution: Create a new integration via OAuth

2. **"Token refresh failed"**
   - Refresh token may have expired
   - Solution: User needs to re-authenticate

3. **"Multiple integrations found"**
   - Clean up old integrations using the setup script
   - Solution: Run `python3 scripts/setup_persistent_slack_auth.py`

4. **"Invalid OAuth state"**
   - OAuth callback state parameter is malformed
   - Solution: Check that the integration record exists and matches the tenant

### Debug Commands

```bash
# Check integration status
python3 scripts/check_slack_integrations.py

# Test persistent auth
python3 scripts/test_persistent_slack_auth.py

# Setup fresh integration
python3 scripts/setup_persistent_slack_auth.py
```

## Migration Guide

If you have existing bot token integrations:

1. Run the setup script to clean up old integrations:
   ```bash
   python3 scripts/setup_persistent_slack_auth.py
   ```

2. Update your frontend to use the new authentication flow

3. Users will need to authenticate once more via OAuth, but then they'll have persistent access

## Security Considerations

- Refresh tokens are stored securely in the database
- Access tokens are automatically refreshed before they expire
- Failed refresh attempts are logged and handled gracefully
- Users can manually refresh tokens if needed
- All API calls validate tokens before use
- OAuth provides better security than bot tokens

## Differences from HubSpot Implementation

1. **OAuth Endpoint:** Uses `https://slack.com/api/oauth.v2.access` instead of HubSpot's endpoint
2. **Token Refresh:** Uses the same endpoint as initial OAuth
3. **Scopes:** Different scope format and permissions
4. **Team Info:** Includes workspace/team information in the response
5. **API Calls:** Uses Slack's Web API endpoints for validation

## Next Steps

1. **Test the OAuth Flow:** Complete the OAuth flow with a test Slack workspace
2. **Update Frontend:** Implement the frontend components using the provided examples
3. **Add Error Handling:** Implement comprehensive error handling for token refresh failures
4. **Monitor Usage:** Add logging and monitoring for OAuth token usage and refresh patterns
5. **Documentation:** Update API documentation to reflect the new OAuth endpoints

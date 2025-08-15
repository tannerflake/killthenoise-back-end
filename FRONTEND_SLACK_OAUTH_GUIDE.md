# Frontend Slack OAuth Integration Guide

This guide explains how to integrate the new persistent Slack OAuth authentication into your frontend application.

## 🎯 **What's New**

The backend now supports persistent Slack authentication with OAuth, similar to the HubSpot integration. Users authenticate once and stay connected across app restarts.

## 📋 **New API Endpoints**

### 1. Check Authentication Status
```typescript
GET /api/slack/auth-status/{tenant_id}

Response:
{
  "authenticated": boolean;
  "message": string;
  "needs_auth": boolean;
  "integration_id"?: string;
  "team"?: string;
  "scopes"?: string[];
  "can_refresh"?: boolean;
}
```

### 2. Get OAuth Authorization URL
```typescript
GET /api/slack/authorize/{tenant_id}

Response:
{
  "success": boolean;
  "authorization_url": string;
  "integration_id": string;
  "tenant_id": string;
}
```

### 3. Manual Token Refresh
```typescript
POST /api/slack/refresh-token/{tenant_id}/{integration_id}

Response:
{
  "success": boolean;
  "message": string;
  "integration_id": string;
  "tenant_id": string;
}
```

## 🔧 **Frontend Implementation**

### Step 1: Update API Client

Add these methods to your API client:

```typescript
// In your API client (e.g., src/lib/api.ts)

export interface SlackAuthStatus {
  authenticated: boolean;
  message: string;
  needs_auth: boolean;
  integration_id?: string;
  team?: string;
  scopes?: string[];
  can_refresh?: boolean;
}

export interface SlackAuthUrlResponse {
  success: boolean;
  authorization_url: string;
  integration_id: string;
  tenant_id: string;
}

export interface SlackRefreshResponse {
  success: boolean;
  message: string;
  integration_id: string;
  tenant_id: string;
}

export const api = {
  // ... existing methods

  // Check Slack authentication status
  async getSlackAuthStatus(tenantId: string): Promise<SlackAuthStatus> {
    const response = await fetch(`/api/slack/auth-status/${tenantId}`);
    if (!response.ok) {
      throw new Error('Failed to check Slack auth status');
    }
    return response.json();
  },

  // Get OAuth authorization URL
  async getSlackAuthUrl(tenantId: string): Promise<SlackAuthUrlResponse> {
    const response = await fetch(`/api/slack/authorize/${tenantId}`);
    if (!response.ok) {
      throw new Error('Failed to get Slack auth URL');
    }
    return response.json();
  },

  // Manually refresh Slack token
  async refreshSlackToken(tenantId: string, integrationId: string): Promise<SlackRefreshResponse> {
    const response = await fetch(`/api/slack/refresh-token/${tenantId}/${integrationId}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to refresh Slack token');
    }
    return response.json();
  }
};
```

### Step 2: Create Authentication Hook

Create a custom hook to manage Slack authentication state:

```typescript
// In src/hooks/useSlackAuth.ts

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
  startOAuth: () => Promise<void>;
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

  const startOAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await api.getSlackAuthUrl(tenantId);
      
      if (result.success) {
        // Open OAuth URL in new window
        const popup = window.open(
          result.authorization_url,
          'slack-oauth',
          'width=600,height=700,scrollbars=yes,resizable=yes'
        );
        
        if (!popup) {
          throw new Error('Popup blocked. Please allow popups for this site.');
        }
        
        // Poll for authentication completion
        const pollInterval = setInterval(async () => {
          try {
            await checkAuth();
            if (authStatus?.authenticated) {
              clearInterval(pollInterval);
              popup.close();
              setLoading(false);
            }
          } catch (err) {
            // Continue polling on error
          }
        }, 2000);
        
        // Stop polling after 5 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          popup.close();
          setLoading(false);
        }, 300000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start OAuth flow');
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
    refreshToken,
    startOAuth
  };
};
```

### Step 3: Create Slack Connect Component

Create a component to handle Slack connection:

```typescript
// In src/components/SlackConnectCard.tsx

import React from 'react';
import { useSlackAuth } from '../hooks/useSlackAuth';

interface SlackConnectCardProps {
  tenantId: string;
}

export const SlackConnectCard: React.FC<SlackConnectCardProps> = ({ tenantId }) => {
  const { authStatus, loading, error, checkAuth, refreshToken, startOAuth } = useSlackAuth({ tenantId });

  const handleConnect = async () => {
    await startOAuth();
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
        <button onClick={handleRefresh} disabled={loading}>
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
        <button onClick={handleRefresh} disabled={loading}>
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
      <button onClick={handleConnect} disabled={loading}>
        {loading ? 'Connecting...' : 'Connect to Slack'}
      </button>
    </div>
  );
};
```

### Step 4: Update Main App Component

Update your main app component to handle authentication state:

```typescript
// In src/App.tsx or your main component

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

## 🎨 **CSS Styles (Optional)**

Add these styles for the Slack connect card:

```css
/* In your CSS file */

.slack-connect-card {
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 20px;
  margin: 10px 0;
  background: white;
}

.slack-connect-card.connected {
  border-color: #36a64f;
  background: #f0f9f0;
}

.slack-connect-card.needs-refresh {
  border-color: #f59e0b;
  background: #fffbeb;
}

.slack-connect-card .status {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.slack-connect-card .icon {
  margin-right: 8px;
  font-size: 18px;
}

.slack-connect-card .details {
  margin: 8px 0;
  font-size: 14px;
  color: #666;
}

.slack-connect-card button {
  background: #36a64f;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.slack-connect-card button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.slack-connect-card .loading {
  color: #666;
  font-style: italic;
}

.slack-connect-card .error {
  color: #dc2626;
  margin-bottom: 10px;
}
```

## 🔄 **OAuth Flow Process**

1. **User clicks "Connect to Slack"**
2. **Frontend calls** `GET /api/slack/authorize/{tenant_id}`
3. **Backend creates temporary integration and returns OAuth URL**
4. **Frontend opens OAuth URL in popup window**
5. **User authorizes the app in Slack**
6. **Slack redirects to webhook URL with authorization code**
7. **Backend exchanges code for tokens and activates integration**
8. **Frontend polls** `GET /api/slack/auth-status/{tenant_id}` until authenticated
9. **User is now connected and can use Slack features**

## 🚀 **Testing the Integration**

1. **Start your backend server**:
   ```bash
   python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test the auth status endpoint**:
   ```bash
   curl "http://localhost:8000/api/slack/auth-status/550e8400-e29b-41d4-a716-446655440000"
   ```

3. **Test the OAuth flow**:
   - Open your frontend app
   - Click "Connect to Slack"
   - Complete the OAuth flow
   - Verify the connection status

## 🔧 **Environment Variables**

Make sure your backend has these environment variables set:
```bash
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_REDIRECT_URI=https://webhook.site/your-webhook-url
```

## 🎯 **Benefits**

- **Persistent Authentication**: Users only need to authenticate once
- **Automatic Token Refresh**: Tokens are refreshed automatically when they expire
- **Better UX**: No more repeated authentication prompts
- **Enhanced Scopes**: OAuth provides better access to Slack APIs
- **Reliable Integration**: Server-side token management with proper error handling

## 🐛 **Troubleshooting**

### Common Issues

1. **"redirect_uri did not match"**
   - Make sure the redirect URI is exactly configured in your Slack app
   - Check for extra spaces or characters

2. **"No active Slack integration found"**
   - User needs to complete the OAuth flow
   - Check if integration was properly created

3. **"Token expired"**
   - Use the refresh token functionality
   - If refresh fails, user needs to re-authenticate

4. **Popup blocked**
   - Ask user to allow popups for your site
   - Provide fallback to open in new tab

### Debug Commands

```bash
# Check integration status
python3 scripts/setup_persistent_slack_auth.py status

# Test OAuth configuration
python3 scripts/setup_persistent_slack_auth.py test

# Clean up old integrations
python3 scripts/setup_persistent_slack_auth.py clean
```

## 📚 **Next Steps**

1. **Implement the frontend components** using the provided code
2. **Test the complete OAuth flow** with your Slack workspace
3. **Add error handling** for edge cases
4. **Implement loading states** and user feedback
5. **Add analytics** to track OAuth success/failure rates
6. **Consider adding** a "Disconnect" feature for users who want to remove the integration

The persistent Slack authentication is now ready for production use! 🎉

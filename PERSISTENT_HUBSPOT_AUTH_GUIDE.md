# Persistent HubSpot Authentication Guide

This guide explains how to implement persistent HubSpot authentication so users only need to authenticate once and stay logged in across app restarts.

## Problem Solved

**Before:** Users had to re-authenticate with HubSpot every time they used the app because:
- Access tokens were stored but expired quickly (1-6 hours)
- No refresh token mechanism was implemented
- Frontend always showed "Connect to HubSpot" button

**After:** Users authenticate once and stay connected because:
- Refresh tokens are stored for long-term access
- Access tokens are automatically refreshed when they expire
- Frontend checks authentication status before showing connect button

## Backend Changes Made

### 1. Enhanced Token Storage
- **Before:** Only stored `access_token`
- **After:** Stores `access_token`, `refresh_token`, `expires_in`, and `token_created_at`

### 2. Automatic Token Refresh
- **Before:** Tokens expired and required re-authentication
- **After:** Tokens are automatically refreshed using refresh tokens

### 3. New API Endpoints
- `GET /api/hubspot/auth-status/{tenant_id}` - Check if user is authenticated
- `POST /api/hubspot/refresh-token/{tenant_id}/{integration_id}` - Manually refresh tokens

## Frontend Implementation

### Step 1: Update API Client

Add the new auth-status method to your API client:

```typescript
// In client/src/lib/api.ts

export interface HubSpotAuthStatus {
  authenticated: boolean;
  message: string;
  needs_auth: boolean;
  integration_id?: string;
  hub_domain?: string;
  scopes?: string[];
  can_refresh?: boolean;
}

export const api = {
  // ... existing methods

  async getHubSpotAuthStatus(tenantId: string): Promise<HubSpotAuthStatus> {
    const response = await api.get<HubSpotAuthStatus>(`/api/hubspot/auth-status/${tenantId}`);
    return response.data;
  },

  async refreshHubSpotToken(tenantId: string, integrationId: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(`/api/hubspot/refresh-token/${tenantId}/${integrationId}`);
    return response.data;
  }
};
```

### Step 2: Create Authentication Hook

Create a custom hook to manage HubSpot authentication state:

```typescript
// In client/src/hooks/useHubSpotAuth.ts

import { useState, useEffect } from 'react';
import { api, HubSpotAuthStatus } from '../lib/api';

interface UseHubSpotAuthProps {
  tenantId: string;
}

interface UseHubSpotAuthReturn {
  authStatus: HubSpotAuthStatus | null;
  loading: boolean;
  error: string | null;
  checkAuth: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

export const useHubSpotAuth = ({ tenantId }: UseHubSpotAuthProps): UseHubSpotAuthReturn => {
  const [authStatus, setAuthStatus] = useState<HubSpotAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await api.getHubSpotAuthStatus(tenantId);
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
      const result = await api.refreshHubSpotToken(tenantId, authStatus.integration_id);
      
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

### Step 3: Update HubSpot Connect Component

Update your existing HubSpot connect component to use the new authentication flow:

```typescript
// In client/src/components/HubSpotConnectCard.tsx

import React, { useState } from 'react';
import { useHubSpotAuth } from '../hooks/useHubSpotAuth';
import { api } from '../lib/api';

interface HubSpotConnectCardProps {
  tenantId: string;
}

export const HubSpotConnectCard: React.FC<HubSpotConnectCardProps> = ({ tenantId }) => {
  const { authStatus, loading, error, checkAuth, refreshToken } = useHubSpotAuth({ tenantId });
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    try {
      setConnecting(true);
      const result = await api.getHubSpotAuthUrl(tenantId);
      
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
      <div className="hubspot-connect-card">
        <div className="loading">Checking HubSpot connection...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hubspot-connect-card">
        <div className="error">Error: {error}</div>
        <button onClick={checkAuth}>Retry</button>
      </div>
    );
  }

  if (authStatus?.authenticated) {
    return (
      <div className="hubspot-connect-card connected">
        <div className="status">
          <span className="icon">✅</span>
          <span className="text">Connected to HubSpot</span>
        </div>
        {authStatus.hub_domain && (
          <div className="details">
            <strong>Hub Domain:</strong> {authStatus.hub_domain}
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
      <div className="hubspot-connect-card needs-refresh">
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
    <div className="hubspot-connect-card">
      <div className="status">
        <span className="icon">🔗</span>
        <span className="text">Connect to HubSpot</span>
      </div>
      <p>Connect your HubSpot account to sync tickets and issues.</p>
      <button onClick={handleConnect} disabled={connecting}>
        {connecting ? 'Connecting...' : 'Connect to HubSpot'}
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
import { useHubSpotAuth } from './hooks/useHubSpotAuth';
import { HubSpotConnectCard } from './components/HubSpotConnectCard';
import { Dashboard } from './components/Dashboard';

const App: React.FC = () => {
  const tenantId = "550e8400-e29b-41d4-a716-446655440000"; // Replace with actual tenant ID
  const { authStatus, loading } = useHubSpotAuth({ tenantId });

  if (loading) {
    return <div className="app-loading">Loading...</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>KillTheNoise</h1>
        <HubSpotConnectCard tenantId={tenantId} />
      </header>
      
      <main className="app-main">
        {authStatus?.authenticated ? (
          <Dashboard tenantId={tenantId} />
        ) : (
          <div className="auth-required">
            <h2>Welcome to KillTheNoise</h2>
            <p>Please connect your HubSpot account to get started.</p>
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
curl "http://localhost:8000/api/hubspot/auth-status/550e8400-e29b-41d4-a716-446655440000"

# Expected response if not authenticated:
{
  "authenticated": false,
  "message": "No active HubSpot integration found",
  "needs_auth": true
}
```

### 2. Test OAuth Flow

```bash
# Get authorization URL
curl "http://localhost:8000/api/hubspot/authorize/550e8400-e29b-41d4-a716-446655440000"

# Expected response:
{
  "success": true,
  "authorization_url": "https://app.hubspot.com/oauth/authorize?...",
  "integration_id": "uuid",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. Test After Authentication

After completing OAuth, check auth status again:

```bash
curl "http://localhost:8000/api/hubspot/auth-status/550e8400-e29b-41d4-a716-446655440000"

# Expected response if authenticated:
{
  "authenticated": true,
  "message": "HubSpot integration is active and working",
  "needs_auth": false,
  "integration_id": "uuid",
  "hub_domain": "your-company.hubspot.com",
  "scopes": ["tickets"]
}
```

## Benefits

1. **Persistent Authentication:** Users only need to authenticate once
2. **Automatic Token Refresh:** Tokens are refreshed automatically when they expire
3. **Better UX:** No more repeated authentication prompts
4. **Reliable Integration:** Tokens are managed server-side with proper error handling
5. **Scalable:** Works for multiple tenants and integrations

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
   - Solution: Run `python3 scripts/setup_persistent_auth.py`

### Debug Commands

```bash
# Check integration status
python3 scripts/check_hubspot_integrations.py

# Test persistent auth
python3 scripts/test_persistent_auth.py

# Setup fresh integration
python3 scripts/setup_persistent_auth.py
```

## Migration Guide

If you have existing integrations without refresh tokens:

1. Run the setup script to clean up old integrations:
   ```bash
   python3 scripts/setup_persistent_auth.py
   ```

2. Update your frontend to use the new authentication flow

3. Users will need to authenticate once more, but then they'll have persistent access

## Security Considerations

- Refresh tokens are stored securely in the database
- Access tokens are automatically refreshed before they expire
- Failed refresh attempts are logged and handled gracefully
- Users can manually refresh tokens if needed
- All API calls validate tokens before use

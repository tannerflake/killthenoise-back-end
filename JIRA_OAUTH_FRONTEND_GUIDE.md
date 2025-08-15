# 🚀 Jira OAuth Frontend Implementation Guide

## 📋 Overview

This guide provides everything your frontend team needs to implement the Jira OAuth flow. The backend is fully functional and ready to support the OAuth integration.

### ✅ Backend Status
- **OAuth endpoints are working** (confirmed by logs)
- Authorization URL generation: `/api/jira/authorize/{tenant_id}`
- OAuth callback handling: `/api/jira/oauth/callback`
- Token refresh functionality
- Error handling and validation

---

## 🔧 Environment Setup

### Frontend Environment Variables
Add these to your frontend environment (`.env` or `.env.local`):

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_JIRA_CALLBACK_URL=http://localhost:3000/jira/oauth/callback
```

---

## 🎯 Step-by-Step Implementation

### Step 1: Create the Connect Button Component

```typescript
// components/JiraConnectButton.tsx
import React, { useState } from 'react';

interface JiraConnectProps {
  tenantId: string;
  onSuccess?: (integrationId: string) => void;
  onError?: (error: string) => void;
}

const JiraConnectButton: React.FC<JiraConnectProps> = ({ 
  tenantId, 
  onSuccess, 
  onError 
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      // Step 1: Get authorization URL from backend
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/jira/authorize/${tenantId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start OAuth flow');
      }

      // Step 2: Redirect user to Jira OAuth page
      window.location.href = data.authorization_url;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <div className="jira-connect-container">
      <button 
        onClick={handleConnect}
        disabled={isConnecting}
        className="connect-button"
      >
        {isConnecting ? 'Connecting...' : 'Connect to Jira'}
      </button>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
};

export default JiraConnectButton;
```

### Step 2: Create the OAuth Callback Handler

```typescript
// components/JiraOAuthCallback.tsx
import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

interface OAuthCallbackProps {
  onSuccess?: (data: any) => void;
  onError?: (error: string) => void;
}

const JiraOAuthCallback: React.FC<OAuthCallbackProps> = ({ 
  onSuccess, 
  onError 
}) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Handle OAuth errors
      if (error) {
        setError(`OAuth error: ${error}`);
        onError?.(error);
        setIsProcessing(false);
        return;
      }

      // Check for authorization code
      if (!code) {
        setError('No authorization code received');
        onError?.('No authorization code received');
        setIsProcessing(false);
        return;
      }

      try {
        // The backend handles the OAuth callback automatically
        // We just need to check if the integration was created successfully
        const response = await fetch(
          `${process.env.REACT_APP_API_BASE_URL}/api/jira/oauth/callback?code=${code}&state=${state || ''}`
        );
        const data = await response.json();

        if (response.ok) {
          onSuccess?.(data);
          // Redirect to success page or integration list
          navigate('/integrations?success=jira');
        } else {
          throw new Error(data.detail || 'OAuth callback failed');
        }

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'OAuth callback failed';
        setError(errorMessage);
        onError?.(errorMessage);
      } finally {
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, onSuccess, onError, navigate]);

  if (isProcessing) {
    return (
      <div className="oauth-callback-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Connecting to Jira...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="oauth-callback-container">
        <div className="error-message">
          <h3>Connection Failed</h3>
          <p>{error}</p>
          <button onClick={() => navigate('/integrations')}>
            Back to Integrations
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default JiraOAuthCallback;
```

### Step 3: Create Integration Status Component

```typescript
// components/JiraIntegrationStatus.tsx
import React, { useEffect, useState } from 'react';

interface JiraIntegration {
  id: string;
  tenant_id: string;
  is_active: boolean;
  connection_status: {
    connected: boolean;
    user?: {
      account_id: string;
      display_name: string;
      email: string;
    };
    base_url?: string;
    error?: string;
  };
}

interface JiraIntegrationStatusProps {
  tenantId: string;
  integrationId: string;
}

const JiraIntegrationStatus: React.FC<JiraIntegrationStatusProps> = ({ 
  tenantId, 
  integrationId 
}) => {
  const [integration, setIntegration] = useState<JiraIntegration | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/api/jira/status/${tenantId}/${integrationId}`
      );
      const data = await response.json();

      if (response.ok) {
        setIntegration(data);
      } else {
        throw new Error(data.detail || 'Failed to fetch integration status');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch status';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [tenantId, integrationId]);

  if (loading) {
    return <div className="status-loading">Loading...</div>;
  }

  if (error) {
    return <div className="status-error">Error: {error}</div>;
  }

  if (!integration) {
    return <div className="status-not-found">Integration not found</div>;
  }

  const { connection_status } = integration;

  return (
    <div className="jira-integration-status">
      <div className={`status-indicator ${connection_status.connected ? 'connected' : 'disconnected'}`}>
        {connection_status.connected ? '✅ Connected' : '❌ Disconnected'}
      </div>
      
      {connection_status.connected && connection_status.user && (
        <div className="user-info">
          <p><strong>User:</strong> {connection_status.user.display_name}</p>
          <p><strong>Email:</strong> {connection_status.user.email}</p>
          <p><strong>Instance:</strong> {connection_status.base_url}</p>
        </div>
      )}
      
      {connection_status.error && (
        <div className="connection-error">
          <p><strong>Error:</strong> {connection_status.error}</p>
        </div>
      )}
      
      <button onClick={fetchStatus} className="refresh-button">
        Refresh Status
      </button>
    </div>
  );
};

export default JiraIntegrationStatus;
```

### Step 4: Create Integration List Component

```typescript
// components/JiraIntegrationList.tsx
import React, { useEffect, useState } from 'react';
import JiraIntegrationStatus from './JiraIntegrationStatus';

interface JiraIntegration {
  id: string;
  tenant_id: string;
  is_active: boolean;
  connection_status: {
    connected: boolean;
    user?: {
      account_id: string;
      display_name: string;
      email: string;
    };
    base_url?: string;
    error?: string;
  };
}

interface JiraIntegrationListProps {
  tenantId: string;
}

const JiraIntegrationList: React.FC<JiraIntegrationListProps> = ({ tenantId }) => {
  const [integrations, setIntegrations] = useState<JiraIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/api/jira/integrations/${tenantId}`
      );
      const data = await response.json();

      if (response.ok) {
        setIntegrations(data.integrations || []);
      } else {
        throw new Error(data.detail || 'Failed to fetch integrations');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch integrations';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, [tenantId]);

  if (loading) {
    return <div className="integrations-loading">Loading integrations...</div>;
  }

  if (error) {
    return <div className="integrations-error">Error: {error}</div>;
  }

  return (
    <div className="jira-integrations-list">
      <h3>Jira Integrations</h3>
      
      {integrations.length === 0 ? (
        <div className="no-integrations">
          <p>No Jira integrations found.</p>
        </div>
      ) : (
        <div className="integrations-grid">
          {integrations.map((integration) => (
            <div key={integration.id} className="integration-card">
              <h4>Integration {integration.id.slice(0, 8)}...</h4>
              <JiraIntegrationStatus 
                tenantId={tenantId} 
                integrationId={integration.id} 
              />
            </div>
          ))}
        </div>
      )}
      
      <button onClick={fetchIntegrations} className="refresh-button">
        Refresh Integrations
      </button>
    </div>
  );
};

export default JiraIntegrationList;
```

### Step 5: Create Main Integration Page

```typescript
// pages/IntegrationsPage.tsx
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import JiraConnectButton from '../components/JiraConnectButton';
import JiraIntegrationList from '../components/JiraIntegrationList';

interface IntegrationsPageProps {
  tenantId: string;
}

const IntegrationsPage: React.FC<IntegrationsPageProps> = ({ tenantId }) => {
  const [searchParams] = useSearchParams();
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    // Check for success parameter from OAuth callback
    const success = searchParams.get('success');
    if (success === 'jira') {
      setShowSuccess(true);
      // Clear the success parameter from URL
      window.history.replaceState({}, '', '/integrations');
    }
  }, [searchParams]);

  return (
    <div className="integrations-page">
      <h2>Integrations</h2>
      
      {showSuccess && (
        <div className="success-message">
          <h3>✅ Jira Connected Successfully!</h3>
          <p>Your Jira integration has been set up and is ready to use.</p>
          <button onClick={() => setShowSuccess(false)}>Dismiss</button>
        </div>
      )}
      
      <div className="integration-section">
        <h3>Connect to Jira</h3>
        <p>Connect your Jira instance to sync issues and track your backlog.</p>
        
        <JiraConnectButton 
          tenantId={tenantId}
          onSuccess={(integrationId) => {
            console.log('Integration created:', integrationId);
          }}
          onError={(error) => {
            console.error('Connection failed:', error);
          }}
        />
      </div>
      
      <div className="integration-section">
        <JiraIntegrationList tenantId={tenantId} />
      </div>
    </div>
  );
};

export default IntegrationsPage;
```

### Step 6: Set Up Routing

```typescript
// App.tsx or your main routing file
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import IntegrationsPage from './pages/IntegrationsPage';
import JiraOAuthCallback from './components/JiraOAuthCallback';

const App: React.FC = () => {
  // Replace with your actual tenant ID logic
  const tenantId = 'your-tenant-id';

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route 
            path="/integrations" 
            element={<IntegrationsPage tenantId={tenantId} />} 
          />
          <Route 
            path="/jira/oauth/callback" 
            element={<JiraOAuthCallback />} 
          />
          {/* Add other routes as needed */}
        </Routes>
      </div>
    </Router>
  );
};

export default App;
```

---

## 🎨 CSS Styling

```css
/* styles/JiraIntegration.css */

/* Connect Button */
.jira-connect-container {
  margin: 20px 0;
}

.connect-button {
  background: linear-gradient(135deg, #0052cc 0%, #0065ff 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 82, 204, 0.2);
}

.connect-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 82, 204, 0.3);
}

.connect-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* OAuth Callback */
.oauth-callback-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  padding: 40px;
}

.loading-spinner {
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0052cc;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 6px;
  padding: 20px;
  text-align: center;
  max-width: 400px;
}

.error-message h3 {
  color: #c53030;
  margin-bottom: 10px;
}

.error-message button {
  background: #0052cc;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 15px;
}

/* Integration Status */
.jira-integration-status {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  margin: 10px 0;
}

.status-indicator {
  font-weight: 600;
  margin-bottom: 15px;
}

.status-indicator.connected {
  color: #38a169;
}

.status-indicator.disconnected {
  color: #e53e3e;
}

.user-info {
  background: #f7fafc;
  padding: 15px;
  border-radius: 6px;
  margin: 15px 0;
}

.user-info p {
  margin: 5px 0;
}

.connection-error {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 6px;
  padding: 15px;
  margin: 15px 0;
  color: #c53030;
}

.refresh-button {
  background: #718096;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.refresh-button:hover {
  background: #4a5568;
}

/* Integration List */
.jira-integrations-list {
  margin: 20px 0;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.integration-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.integration-card h4 {
  margin: 0 0 15px 0;
  color: #2d3748;
}

.no-integrations {
  text-align: center;
  padding: 40px;
  color: #718096;
}

/* Success Message */
.success-message {
  background: #f0fff4;
  border: 1px solid #9ae6b4;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  text-align: center;
}

.success-message h3 {
  color: #38a169;
  margin-bottom: 10px;
}

.success-message button {
  background: #38a169;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 15px;
}

/* Loading States */
.status-loading,
.integrations-loading {
  text-align: center;
  padding: 40px;
  color: #718096;
}

.status-error,
.integrations-error {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 6px;
  padding: 15px;
  margin: 15px 0;
  color: #c53030;
}

.status-not-found {
  text-align: center;
  padding: 20px;
  color: #718096;
}

/* Integration Page */
.integrations-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.integration-section {
  margin: 40px 0;
  padding: 30px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.integration-section h3 {
  margin-bottom: 15px;
  color: #2d3748;
}

.integration-section p {
  color: #718096;
  margin-bottom: 20px;
}
```

---

## 🧪 Testing Instructions

### 1. Test the Connect Button
```typescript
// Test that clicking the connect button redirects to Jira OAuth
const mockFetch = jest.fn();
global.fetch = mockFetch;

mockFetch.mockResolvedValueOnce({
  ok: true,
  json: async () => ({ authorization_url: 'https://auth.atlassian.com/authorize?...' })
});

// Click the connect button
fireEvent.click(screen.getByText('Connect to Jira'));

// Verify the redirect
expect(window.location.href).toContain('auth.atlassian.com');
```

### 2. Test the OAuth Callback
```typescript
// Test successful OAuth callback
const mockSearchParams = new URLSearchParams('?code=test-code&state=test-state');
jest.spyOn(require('react-router-dom'), 'useSearchParams')
  .mockReturnValue([mockSearchParams]);

// Mock the callback API call
mockFetch.mockResolvedValueOnce({
  ok: true,
  json: async () => ({ success: true })
});

// Render the callback component
render(<JiraOAuthCallback />);

// Verify success handling
await waitFor(() => {
  expect(mockNavigate).toHaveBeenCalledWith('/integrations?success=jira');
});
```

### 3. Test Integration Status
```typescript
// Test integration status display
mockFetch.mockResolvedValueOnce({
  ok: true,
  json: async () => ({
    id: 'test-id',
    connection_status: {
      connected: true,
      user: {
        display_name: 'Test User',
        email: 'test@example.com'
      },
      base_url: 'https://test.atlassian.net'
    }
  })
});

render(<JiraIntegrationStatus tenantId="test" integrationId="test" />);

await waitFor(() => {
  expect(screen.getByText('✅ Connected')).toBeInTheDocument();
  expect(screen.getByText('Test User')).toBeInTheDocument();
});
```

---

## 🚀 Deployment Checklist

### Frontend Deployment
- [ ] Environment variables configured
- [ ] OAuth callback URL updated in Atlassian Developer Console
- [ ] CORS settings configured on backend
- [ ] Error handling implemented
- [ ] Loading states implemented
- [ ] Success/error messages styled
- [ ] Mobile responsiveness tested

### Backend Configuration
- [ ] Jira OAuth credentials configured
- [ ] Redirect URI matches frontend callback URL
- [ ] CORS headers allow frontend domain
- [ ] Error logging implemented
- [ ] Token refresh logic tested

---

## 🔧 Troubleshooting

### Common Issues

1. **OAuth callback fails**
   - Check that the redirect URI in Atlassian Developer Console matches your frontend callback URL
   - Verify the backend is running and accessible
   - Check browser console for CORS errors

2. **State parameter issues**
   - The backend handles missing state parameters gracefully
   - Check that the authorization URL is being generated correctly

3. **Token refresh failures**
   - The backend automatically handles token refresh
   - Check that refresh tokens are being stored correctly

4. **Integration status not updating**
   - Verify the integration ID is correct
   - Check that the backend status endpoint is responding
   - Ensure the tenant ID matches

### Debug Steps

1. **Check Network Tab**
   - Look for failed API calls
   - Verify request/response formats
   - Check for CORS errors

2. **Check Console Logs**
   - Look for JavaScript errors
   - Verify environment variables are loaded
   - Check for authentication errors

3. **Test Backend Directly**
   - Use the test scripts provided
   - Verify OAuth endpoints are working
   - Check database for integration records

---

## 📞 Support

If you encounter issues during implementation:

1. **Check the backend logs** for detailed error messages
2. **Verify environment variables** are correctly set
3. **Test the OAuth flow** using the provided test scripts
4. **Review the API documentation** for endpoint details

The backend is fully functional and ready to support your frontend implementation. All OAuth endpoints are working correctly as confirmed by the logs. 
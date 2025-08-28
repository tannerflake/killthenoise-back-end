# Frontend Slack Integration Guide

## Overview

The backend has been updated to prevent duplicate Slack integrations. This guide explains the new flow and what changes are needed in the frontend.

## Key Changes

### 1. Authorization Endpoint Now Checks for Existing Integrations

**Endpoint:** `GET /api/slack/authorize/{tenant_id}`

**New Behavior:**
- If an active Slack integration already exists, the endpoint returns an error instead of creating a new one
- This prevents duplicate integrations from being created

**Response Format:**
```json
// Success (no existing integration)
{
  "success": true,
  "authorization_url": "https://slack.com/oauth/v2/authorize?...",
  "integration_id": "uuid",
  "tenant_id": "uuid"
}

// Error (existing integration found)
{
  "success": false,
  "error": "Slack integration already exists",
  "message": "This tenant already has an active Slack integration. Please disconnect the existing integration first if you want to reconnect.",
  "existing_integration_id": "uuid",
  "needs_disconnect": true
}
```

### 2. New Disconnect Endpoint

**Endpoint:** `DELETE /api/slack/disconnect/{tenant_id}`

**Purpose:** Remove all Slack integrations for a tenant before reconnecting

**Response Format:**
```json
{
  "success": true,
  "message": "Slack integration disconnected successfully",
  "integrations_removed": 1
}
```

### 3. Cleanup Endpoint (for emergencies)

**Endpoint:** `POST /api/slack/cleanup-duplicates/{tenant_id}`

**Purpose:** Clean up duplicate integrations if they somehow get created

**Response Format:**
```json
{
  "success": true,
  "message": "Duplicate integrations cleaned up successfully",
  "integrations_found": 5,
  "integrations_removed": 4,
  "kept_integration_id": "uuid",
  "removed_integration_ids": ["uuid1", "uuid2", ...]
}
```

## Frontend Implementation Guide

### 1. Connect Slack Flow

```javascript
async function connectSlack(tenantId) {
  try {
    // Step 1: Try to get authorization URL
    const response = await fetch(`/api/slack/authorize/${tenantId}`);
    const data = await response.json();
    
    if (!data.success) {
      if (data.needs_disconnect) {
        // Show disconnect confirmation dialog
        const shouldDisconnect = await showDisconnectConfirmation(data.message);
        
        if (shouldDisconnect) {
          // Step 2: Disconnect existing integration
          await disconnectSlack(tenantId);
          
          // Step 3: Try authorization again
          return await connectSlack(tenantId);
        } else {
          throw new Error("User cancelled disconnect");
        }
      } else {
        throw new Error(data.message || "Failed to start Slack authorization");
      }
    }
    
    // Step 4: Open OAuth popup
    const popup = window.open(
      data.authorization_url,
      'slack-oauth',
      'width=600,height=700,scrollbars=yes,resizable=yes'
    );
    
    // Step 5: Wait for OAuth completion
    return new Promise((resolve, reject) => {
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          // Check auth status to confirm success
          checkSlackAuthStatus(tenantId).then(resolve).catch(reject);
        }
      }, 1000);
    });
    
  } catch (error) {
    console.error('Slack connection failed:', error);
    throw error;
  }
}
```

### 2. Disconnect Slack Flow

```javascript
async function disconnectSlack(tenantId) {
  try {
    const response = await fetch(`/api/slack/disconnect/${tenantId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || "Failed to disconnect Slack");
    }
    
    return data;
  } catch (error) {
    console.error('Slack disconnection failed:', error);
    throw error;
  }
}
```

### 3. Check Auth Status Flow

```javascript
async function checkSlackAuthStatus(tenantId) {
  try {
    const response = await fetch(`/api/slack/auth-status/${tenantId}`);
    const data = await response.json();
    
    return data;
  } catch (error) {
    console.error('Failed to check Slack auth status:', error);
    throw error;
  }
}
```

### 4. UI Components

#### Connect Button Component
```javascript
function SlackConnectButton({ tenantId, onConnect, onDisconnect }) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [authStatus, setAuthStatus] = useState(null);
  
  useEffect(() => {
    // Check initial auth status
    checkSlackAuthStatus(tenantId).then(setAuthStatus);
  }, [tenantId]);
  
  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      await connectSlack(tenantId);
      const newStatus = await checkSlackAuthStatus(tenantId);
      setAuthStatus(newStatus);
      onConnect?.(newStatus);
    } catch (error) {
      // Handle error (show toast, etc.)
      console.error('Connection failed:', error);
    } finally {
      setIsConnecting(false);
    }
  };
  
  const handleDisconnect = async () => {
    try {
      await disconnectSlack(tenantId);
      setAuthStatus(null);
      onDisconnect?.();
    } catch (error) {
      console.error('Disconnection failed:', error);
    }
  };
  
  if (authStatus?.authenticated) {
    return (
      <div>
        <span>✅ Connected to {authStatus.team}</span>
        <button onClick={handleDisconnect}>Disconnect</button>
      </div>
    );
  }
  
  return (
    <button 
      onClick={handleConnect} 
      disabled={isConnecting}
    >
      {isConnecting ? 'Connecting...' : 'Connect Slack'}
    </button>
  );
}
```

#### Disconnect Confirmation Dialog
```javascript
function DisconnectConfirmationDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="modal">
      <div className="modal-content">
        <h3>Disconnect Existing Integration?</h3>
        <p>{message}</p>
        <div className="modal-actions">
          <button onClick={onCancel}>Cancel</button>
          <button onClick={onConfirm} className="danger">
            Disconnect & Reconnect
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 5. Error Handling

```javascript
function showDisconnectConfirmation(message) {
  return new Promise((resolve) => {
    // Show modal/dialog and resolve with user's choice
    // This is just a placeholder - implement based on your UI framework
    const confirmed = window.confirm(
      `${message}\n\nWould you like to disconnect the existing integration and reconnect?`
    );
    resolve(confirmed);
  });
}
```

## Migration Strategy

### For Existing Integrations

1. **No immediate action required** - existing integrations will continue to work
2. **The cleanup has already been performed** for the problematic tenant
3. **New connections will be prevented** from creating duplicates

### Testing the New Flow

1. **Test with no existing integration:**
   - Should work as before
   - Creates new integration successfully

2. **Test with existing integration:**
   - Should show disconnect confirmation
   - Should allow user to disconnect and reconnect
   - Should prevent duplicate creation

3. **Test error scenarios:**
   - Network failures
   - OAuth failures
   - Invalid tenant IDs

## Best Practices

### 1. Always Check Auth Status First
```javascript
// Before showing connect button, check current status
const authStatus = await checkSlackAuthStatus(tenantId);
if (authStatus.authenticated) {
  // Show connected state
} else {
  // Show connect button
}
```

### 2. Handle OAuth Popup Properly
```javascript
// Always check if popup was closed by user
if (popup.closed) {
  // User cancelled OAuth
  throw new Error('OAuth was cancelled');
}
```

### 3. Provide Clear User Feedback
```javascript
// Show loading states
setIsConnecting(true);

// Show success/error messages
if (success) {
  showToast('Slack connected successfully!');
} else {
  showToast('Failed to connect Slack. Please try again.');
}
```

### 4. Handle Edge Cases
```javascript
// Check for multiple integrations (shouldn't happen anymore, but good to handle)
if (authStatus.message?.includes('Multiple Slack integrations found')) {
  // Show cleanup option or contact support
  await cleanupDuplicates(tenantId);
}
```

## Troubleshooting

### Common Issues

1. **"Slack integration already exists" error:**
   - This is expected behavior
   - Guide user to disconnect first

2. **OAuth popup doesn't open:**
   - Check if popup blockers are enabled
   - Use a different approach (redirect instead of popup)

3. **Integration not found after OAuth:**
   - Check if OAuth callback completed successfully
   - Verify the integration was created in the database

### Debug Endpoints

Use these endpoints to debug integration issues:

- `GET /api/slack/auth-status/{tenant_id}` - Check current status
- `POST /api/slack/cleanup-duplicates/{tenant_id}` - Clean up duplicates
- `DELETE /api/slack/disconnect/{tenant_id}` - Remove all integrations

## Summary

The new flow prevents duplicate integrations by:

1. **Checking for existing integrations** before starting OAuth
2. **Requiring explicit disconnection** before reconnection
3. **Cleaning up duplicates** during OAuth completion
4. **Providing cleanup tools** for edge cases

This ensures a clean, single-integration state for each tenant while maintaining a good user experience.

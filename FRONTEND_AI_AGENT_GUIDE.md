# Frontend AI Agent Guide: Jira API Token Integration

## 🎯 **Mission**

Implement a Jira integration using **API tokens** instead of OAuth. This approach is simpler, more reliable, and provides direct access to Jira issues.

## 📋 **Current State**

- ✅ **Backend is ready** - All API endpoints are working
- ✅ **OAuth is working** - But can't access Jira issues (limitation)
- ❌ **Frontend needs API token implementation** - Replace OAuth with API token form

## 🔧 **Why API Tokens Instead of OAuth?**

- **OAuth Limitation**: OAuth tokens can't access Jira instance APIs directly
- **API Token Benefits**: Direct access to all Jira data (issues, projects, etc.)
- **Simpler UX**: No redirect flow, just enter token and connect
- **More Reliable**: No token refresh issues

## 🚀 **Implementation Plan**

### **Phase 1: Replace OAuth with API Token Form**

#### **Step 1: Create API Token Input Component**

```typescript
// components/JiraApiTokenForm.tsx
import React, { useState } from 'react';
import { Button, TextField, Alert, Box, Typography, Paper } from '@mui/material';

interface JiraApiTokenFormProps {
  tenantId: string;
  onSuccess: (integrationId: string) => void;
  onError: (error: string) => void;
}

export const JiraApiTokenForm: React.FC<JiraApiTokenFormProps> = ({
  tenantId,
  onSuccess,
  onError
}) => {
  const [apiToken, setApiToken] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/jira/integrations/${tenantId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          access_token: apiToken,
          base_url: baseUrl
        })
      });

      const result = await response.json();

      if (response.ok && result.success) {
        onSuccess(result.integration_id);
      } else {
        const errorMessage = result.detail?.error || result.detail || 'Failed to create integration';
        setError(errorMessage);
        onError(errorMessage);
      }
    } catch (err) {
      const errorMessage = 'Network error occurred';
      setError(errorMessage);
      onError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 500 }}>
      <Typography variant="h6" gutterBottom>
        Connect to Jira with API Token
      </Typography>
      
      <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
        Get your API token from Jira > Settings > Personal Access Tokens
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="Jira Base URL"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://your-domain.atlassian.net"
          margin="normal"
          required
          helperText="Your Jira instance URL (e.g., https://killthenoise.atlassian.net)"
        />
        
        <TextField
          fullWidth
          label="API Token"
          type="password"
          value={apiToken}
          onChange={(e) => setApiToken(e.target.value)}
          margin="normal"
          required
          helperText="Get this from https://id.atlassian.com/manage-profile/security/api-tokens"
        />

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disabled={isLoading || !apiToken || !baseUrl}
          sx={{ mt: 3 }}
        >
          {isLoading ? 'Connecting...' : 'Connect to Jira'}
        </Button>
      </Box>
    </Paper>
  );
};
```

#### **Step 2: Create Integration Status Component**

```typescript
// components/JiraIntegrationStatus.tsx
import React, { useEffect, useState } from 'react';
import { Card, CardContent, Typography, Chip, Box, Button, Alert } from '@mui/material';
import { CheckCircle, Error, Refresh, Info } from '@mui/icons-material';

interface JiraIntegrationStatusProps {
  tenantId: string;
  integrationId: string;
  onRefresh?: () => void;
}

export const JiraIntegrationStatus: React.FC<JiraIntegrationStatusProps> = ({
  tenantId,
  integrationId,
  onRefresh
}) => {
  const [status, setStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchStatus = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/jira/status/${tenantId}/${integrationId}`);
      const result = await response.json();

      if (response.ok) {
        setStatus(result);
      } else {
        setError(result.detail || 'Failed to fetch status');
      }
    } catch (err) {
      setError('Network error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [tenantId, integrationId]);

  const handleRefresh = () => {
    fetchStatus();
    onRefresh?.();
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography>Loading status...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            Error: {error}
          </Alert>
          <Button onClick={handleRefresh} startIcon={<Refresh />}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          {status?.connected ? (
            <CheckCircle color="success" />
          ) : (
            <Error color="error" />
          )}
          <Typography variant="h6">
            Jira Integration Status
          </Typography>
          <Chip
            label={status?.connected ? 'Connected' : 'Disconnected'}
            color={status?.connected ? 'success' : 'error'}
            size="small"
          />
        </Box>

        {status?.connected && (
          <Box>
            <Typography variant="body2" color="textSecondary">
              Base URL: {status.base_url}
            </Typography>
            {status.user && (
              <Typography variant="body2" color="textSecondary">
                User: {status.user.display_name} ({status.user.email})
              </Typography>
            )}
            <Typography variant="body2" color="textSecondary">
              Method: {status.method}
            </Typography>
          </Box>
        )}

        {status?.error && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              {status.error}
            </Typography>
          </Alert>
        )}

        <Button
          onClick={handleRefresh}
          startIcon={<Refresh />}
          sx={{ mt: 2 }}
        >
          Refresh Status
        </Button>
      </CardContent>
    </Card>
  );
};
```

#### **Step 3: Create Issues List Component**

```typescript
// components/JiraIssuesList.tsx
import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  Button,
  CircularProgress,
  Alert
} from '@mui/material';
import { Bug, Task, Story, OpenInNew } from '@mui/icons-material';

interface JiraIssue {
  id: string;
  summary: string;
  status: string;
  priority: string;
  assignee: string;
  issue_type: string;
  project: string;
  created: string;
  updated: string;
  url: string;
}

interface JiraIssuesListProps {
  tenantId: string;
  integrationId: string;
}

export const JiraIssuesList: React.FC<JiraIssuesListProps> = ({
  tenantId,
  integrationId
}) => {
  const [issues, setIssues] = useState<JiraIssue[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);

  const fetchIssues = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/jira/issues/${tenantId}/${integrationId}`);
      const result = await response.json();

      if (response.ok && result.success) {
        setIssues(result.issues);
        setTotal(result.total);
      } else {
        setError(result.error || 'Failed to fetch issues');
      }
    } catch (err) {
      setError('Network error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchIssues();
  }, [tenantId, integrationId]);

  const getIssueIcon = (issueType: string) => {
    switch (issueType.toLowerCase()) {
      case 'bug':
        return <Bug />;
      case 'story':
        return <Story />;
      default:
        return <Task />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'highest':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            Error: {error}
          </Alert>
          <Button onClick={fetchIssues} variant="outlined">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Jira Issues ({total})
        </Typography>

        {issues.length === 0 ? (
          <Typography color="textSecondary">
            No issues found
          </Typography>
        ) : (
          <List>
            {issues.map((issue) => (
              <ListItem key={issue.id} divider>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      {getIssueIcon(issue.issue_type)}
                      <Typography variant="subtitle1">
                        {issue.id} - {issue.summary}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        Project: {issue.project} | Status: {issue.status}
                      </Typography>
                      {issue.assignee && (
                        <Typography variant="body2" color="textSecondary">
                          Assignee: {issue.assignee}
                        </Typography>
                      )}
                      <Typography variant="body2" color="textSecondary">
                        Updated: {new Date(issue.updated).toLocaleDateString()}
                      </Typography>
                    </Box>
                  }
                />
                <Box display="flex" gap={1} alignItems="center">
                  {issue.priority && (
                    <Chip
                      label={issue.priority}
                      color={getPriorityColor(issue.priority)}
                      size="small"
                    />
                  )}
                  <Chip
                    label={issue.issue_type}
                    variant="outlined"
                    size="small"
                  />
                  <Button
                    size="small"
                    startIcon={<OpenInNew />}
                    onClick={() => window.open(issue.url, '_blank')}
                  >
                    View
                  </Button>
                </Box>
              </ListItem>
            ))}
          </List>
        )}

        <Button
          onClick={fetchIssues}
          variant="outlined"
          sx={{ mt: 2 }}
        >
          Refresh Issues
        </Button>
      </CardContent>
    </Card>
  );
};
```

### **Phase 2: Update Main Integration Page**

#### **Step 4: Create Main Integration Page**

```typescript
// pages/IntegrationsPage.tsx
import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  Paper,
  Alert
} from '@mui/material';
import { JiraApiTokenForm } from '../components/JiraApiTokenForm';
import { JiraIntegrationStatus } from '../components/JiraIntegrationStatus';
import { JiraIssuesList } from '../components/JiraIssuesList';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`integration-tabpanel-${index}`}
      aria-labelledby={`integration-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const IntegrationsPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [selectedIntegration, setSelectedIntegration] = useState<any>(null);
  const [successMessage, setSuccessMessage] = useState('');

  const tenantId = "550e8400-e29b-41d4-a716-446655440000"; // Replace with actual tenant ID

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(`/api/jira/integrations/${tenantId}`);
      const result = await response.json();

      if (response.ok && result.success) {
        setIntegrations(result.integrations);
        
        // Select the first active integration
        const activeIntegration = result.integrations.find((i: any) => i.is_active);
        if (activeIntegration) {
          setSelectedIntegration(activeIntegration);
        }
      }
    } catch (err) {
      console.error('Failed to fetch integrations:', err);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleIntegrationSuccess = (integrationId: string) => {
    setSuccessMessage('Jira integration created successfully!');
    
    // Refresh integrations list
    fetchIntegrations();
    
    // Switch to status tab
    setTabValue(1);
    
    // Clear success message after 5 seconds
    setTimeout(() => setSuccessMessage(''), 5000);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" gutterBottom>
        Integrations
      </Typography>

      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {successMessage}
        </Alert>
      )}

      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Connect" />
          <Tab label="Status" />
          <Tab label="Issues" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <JiraApiTokenForm
            tenantId={tenantId}
            onSuccess={handleIntegrationSuccess}
            onError={(error) => console.error('Integration error:', error)}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {selectedIntegration ? (
            <JiraIntegrationStatus
              tenantId={tenantId}
              integrationId={selectedIntegration.id}
              onRefresh={fetchIntegrations}
            />
          ) : (
            <Typography>No active integration found</Typography>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {selectedIntegration ? (
            <JiraIssuesList
              tenantId={tenantId}
              integrationId={selectedIntegration.id}
            />
          ) : (
            <Typography>No active integration found</Typography>
          )}
        </TabPanel>
      </Paper>
    </Container>
  );
};
```

## 🔑 **Getting API Token Instructions**

### **For Users:**

1. **Get API Token:**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Name it "KillTheNoise Integration"
   - Copy the token (you won't see it again!)

2. **Get Base URL:**
   - Your Jira instance URL (e.g., `https://killthenoise.atlassian.net`)

3. **Connect:**
   - Enter base URL and API token in the form
   - Click "Connect to Jira"
   - Check status tab to verify connection
   - View issues in issues tab

## 🚀 **API Endpoints Reference**

### **Create Integration**
```http
POST /api/jira/integrations/{tenant_id}
Content-Type: application/json

{
  "access_token": "your_api_token",
  "base_url": "https://your-domain.atlassian.net"
}
```

### **Check Status**
```http
GET /api/jira/status/{tenant_id}/{integration_id}
```

### **List Issues**
```http
GET /api/jira/issues/{tenant_id}/{integration_id}
```

### **List All Integrations**
```http
GET /api/jira/integrations/{tenant_id}
```

## 🎯 **Implementation Checklist**

### **Phase 1: Core Components**
- [ ] Create `JiraApiTokenForm` component
- [ ] Create `JiraIntegrationStatus` component  
- [ ] Create `JiraIssuesList` component
- [ ] Create main `IntegrationsPage` component

### **Phase 2: Integration**
- [ ] Replace existing OAuth form with API token form
- [ ] Update routing to use new components
- [ ] Test with real API token
- [ ] Add error handling and loading states

### **Phase 3: Polish**
- [ ] Add success/error notifications
- [ ] Implement pagination for issues
- [ ] Add issue creation/editing features
- [ ] Add real-time sync capabilities

## 🔧 **Testing Strategy**

1. **Test with Real API Token:**
   - Get a real Jira API token
   - Test the integration creation
   - Verify status shows as connected
   - Test issues listing

2. **Error Handling:**
   - Test with invalid token
   - Test with invalid base URL
   - Test network errors
   - Verify helpful error messages

3. **Edge Cases:**
   - Test with no issues
   - Test with many issues
   - Test with different issue types
   - Test with different priorities

## 📝 **Key Differences from OAuth**

1. **No Redirect Flow** - Direct form submission
2. **No Token Refresh** - API tokens don't expire
3. **Direct API Access** - Can access all Jira data
4. **Simpler Error Handling** - Clear validation errors
5. **Better Performance** - No OAuth overhead

## 🎉 **Success Criteria**

- ✅ User can enter API token and base URL
- ✅ Integration creates successfully
- ✅ Status shows as connected
- ✅ Issues list displays correctly
- ✅ Error messages are helpful
- ✅ Loading states work properly
- ✅ Refresh functionality works

## 🚨 **Important Notes**

1. **API Token Security** - Never log or expose API tokens
2. **Base URL Format** - Must be `https://domain.atlassian.net`
3. **Error Handling** - Always show helpful error messages
4. **Loading States** - Show loading indicators during API calls
5. **Validation** - Validate inputs before submission

## 📞 **Backend Support**

The backend is ready and tested. All endpoints are working:

- ✅ Integration creation
- ✅ Status checking  
- ✅ Issues listing
- ✅ Error handling

The backend will provide detailed error messages for debugging.

## 🎯 **Next Steps After Implementation**

1. **Test thoroughly** with real API tokens
2. **Add pagination** for large issue lists
3. **Implement issue creation** functionality
4. **Add real-time sync** capabilities
5. **Optimize performance** for large datasets
6. **Add advanced filtering** and search

Good luck! The backend is ready and waiting for your frontend implementation. 🚀 
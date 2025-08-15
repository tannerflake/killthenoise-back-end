# Jira API Token Integration - Frontend Guide

## 🎯 **Overview**

This guide shows how to implement Jira integration using **API tokens** instead of OAuth. API tokens are simpler, more reliable, and can directly access Jira issues.

## 🔧 **Why API Tokens Instead of OAuth?**

- ✅ **Simpler setup** - No OAuth flow complexity
- ✅ **Direct access** - Can access Jira instance APIs directly
- ✅ **More reliable** - No token refresh issues
- ✅ **Better performance** - No OAuth overhead
- ✅ **Full access** - Can read/write issues, projects, etc.

## 📋 **Frontend Implementation**

### **1. API Token Input Form**

```typescript
// components/JiraApiTokenForm.tsx
import React, { useState } from 'react';
import { Button, TextField, Alert, Box, Typography } from '@mui/material';

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
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 400 }}>
      <Typography variant="h6" gutterBottom>
        Connect to Jira with API Token
      </Typography>
      
      <TextField
        fullWidth
        label="Jira Base URL"
        value={baseUrl}
        onChange={(e) => setBaseUrl(e.target.value)}
        placeholder="https://your-domain.atlassian.net"
        margin="normal"
        required
        helperText="Your Jira instance URL"
      />
      
      <TextField
        fullWidth
        label="API Token"
        type="password"
        value={apiToken}
        onChange={(e) => setApiToken(e.target.value)}
        margin="normal"
        required
        helperText="Get this from Jira > Settings > Personal Access Tokens"
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
        sx={{ mt: 2 }}
      >
        {isLoading ? 'Connecting...' : 'Connect to Jira'}
      </Button>
    </Box>
  );
};
```

### **2. Integration Status Component**

```typescript
// components/JiraIntegrationStatus.tsx
import React, { useEffect, useState } from 'react';
import { Card, CardContent, Typography, Chip, Box, Button } from '@mui/material';
import { CheckCircle, Error, Refresh } from '@mui/icons-material';

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
    return <Typography>Loading status...</Typography>;
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Typography color="error" gutterBottom>
            Error: {error}
          </Typography>
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
          <Typography color="error" variant="body2" sx={{ mt: 1 }}>
            Error: {status.error}
          </Typography>
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

### **3. Issues List Component**

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
  CircularProgress
} from '@mui/material';
import { Bug, Task, Story } from '@mui/icons-material';

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
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Typography color="error" gutterBottom>
            Error: {error}
          </Typography>
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

### **4. Main Integration Page**

```typescript
// pages/IntegrationsPage.tsx
import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  Paper
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
    // Refresh integrations list
    fetchIntegrations();
    
    // Switch to status tab
    setTabValue(1);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" gutterBottom>
        Integrations
      </Typography>

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

## 🔑 **Getting a Jira API Token**

### **Step 1: Create API Token**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "KillTheNoise Integration")
4. Copy the token (you won't see it again!)

### **Step 2: Get Your Jira Base URL**
- Your Jira instance URL (e.g., `https://killthenoise.atlassian.net`)
- This is the URL you use to access Jira

### **Step 3: Test the Integration**
1. Enter the base URL and API token in the form
2. Click "Connect to Jira"
3. Check the status tab to verify connection
4. View issues in the issues tab

## 🚀 **API Endpoints**

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

## 🎯 **Benefits of API Token Approach**

1. **Simpler UX** - No OAuth redirect flow
2. **More reliable** - No token refresh issues
3. **Better performance** - Direct API access
4. **Full access** - Can read/write all Jira data
5. **Easier debugging** - Clear error messages

## 🔧 **Error Handling**

The backend provides detailed error messages for common issues:

- **Invalid token** - Check your API token
- **Invalid base URL** - Verify the Jira instance URL
- **Network errors** - Check connectivity
- **Permission errors** - Verify token has necessary permissions

## 📝 **Next Steps**

1. Implement the components above
2. Test with a real Jira API token
3. Add error handling and loading states
4. Implement issue creation/editing features
5. Add pagination for large issue lists
6. Implement real-time sync capabilities 
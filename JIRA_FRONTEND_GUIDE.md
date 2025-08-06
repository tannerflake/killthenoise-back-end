# Jira Integration Frontend Development Guide

## Overview
This guide provides everything needed to build the frontend for the Jira integration feature. The backend API is complete and ready to use.

## Backend API Status
✅ **Backend is fully implemented and running on `http://localhost:8000`**

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Authentication
- No authentication required for this implementation
- Uses tenant_id and integration_id for multi-tenancy

### Core Endpoints

#### 1. List Jira Integrations
```http
GET /api/jira/integrations/{tenant_id}
```

**Response:**
```json
{
  "success": true,
  "integrations": [
    {
      "id": "uuid",
      "tenant_id": "uuid", 
      "is_active": true,
      "last_synced_at": "2024-01-01T00:00:00Z",
      "last_sync_status": "success",
      "sync_error_message": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "connection_status": {
        "connected": true,
        "user": {
          "account_id": "user123",
          "display_name": "John Doe",
          "email": "john@example.com"
        },
        "base_url": "https://example.atlassian.net"
      }
    }
  ],
  "total_count": 1,
  "tenant_id": "uuid"
}
```

#### 2. Create Jira Integration
```http
POST /api/jira/integrations/{tenant_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "access_token": "your-jira-access-token",
  "base_url": "https://your-domain.atlassian.net"
}
```

**Response:**
```json
{
  "success": true,
  "integration_id": "uuid",
  "tenant_id": "uuid",
  "message": "Jira integration created successfully"
}
```

#### 3. Test Connection
```http
GET /api/jira/status/{tenant_id}/{integration_id}
```

**Response:**
```json
{
  "connected": true,
  "user": {
    "account_id": "user123",
    "display_name": "John Doe", 
    "email": "john@example.com"
  },
  "base_url": "https://example.atlassian.net"
}
```

#### 4. List Jira Issues (Backlog)
```http
GET /api/jira/issues/{tenant_id}/{integration_id}?limit=50&jql=ORDER BY updated DESC
```

**Query Parameters:**
- `limit` (optional): Number of issues to return (default: 50)
- `jql` (optional): JQL query to filter issues

**Response:**
```json
{
  "success": true,
  "issues": [
    {
      "id": "PROJ-123",
      "summary": "Fix login bug",
      "status": "In Progress",
      "priority": "High",
      "assignee": "John Doe",
      "issue_type": "Bug",
      "project": "Project Alpha",
      "created": "2024-01-01T00:00:00Z",
      "updated": "2024-01-01T12:00:00Z",
      "url": "https://example.atlassian.net/browse/PROJ-123"
    }
  ],
  "total": 150,
  "max_results": 50
}
```

#### 5. Get Specific Issue
```http
GET /api/jira/issues/{tenant_id}/{integration_id}/{issue_key}
```

**Response:**
```json
{
  "success": true,
  "issue": {
    "id": "PROJ-123",
    "summary": "Fix login bug",
    "description": "Users cannot log in with valid credentials",
    "status": "In Progress",
    "priority": "High",
    "assignee": "John Doe",
    "reporter": "Jane Smith",
    "issue_type": "Bug",
    "project": "Project Alpha",
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T12:00:00Z",
    "url": "https://example.atlassian.net/browse/PROJ-123"
  }
}
```

#### 6. Create Issue
```http
POST /api/jira/issues/{tenant_id}/{integration_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "project_key": "PROJ",
  "summary": "New feature request",
  "description": "Add dark mode support",
  "issue_type": "Task"
}
```

**Response:**
```json
{
  "success": true,
  "issue_key": "PROJ-124",
  "issue_id": "12345",
  "url": "https://example.atlassian.net/browse/PROJ-124"
}
```

#### 7. Update Issue
```http
PUT /api/jira/issues/{tenant_id}/{integration_id}/{issue_key}
Content-Type: application/json
```

**Request Body:**
```json
{
  "summary": "Updated summary",
  "description": "Updated description"
}
```

**Response:**
```json
{
  "success": true
}
```

#### 8. List Projects
```http
GET /api/jira/projects/{tenant_id}/{integration_id}
```

**Response:**
```json
{
  "success": true,
  "projects": [
    {
      "key": "PROJ",
      "name": "Project Alpha",
      "id": "12345"
    }
  ]
}
```

#### 9. Trigger Sync
```http
POST /api/jira/sync/{tenant_id}/{integration_id}?sync_type=full
```

**Query Parameters:**
- `sync_type`: "full" or "incremental"

**Response:**
```json
{
  "success": true,
  "message": "Jira full sync started in background",
  "tenant_id": "uuid",
  "integration_id": "uuid"
}
```

## Error Handling

### Common Error Responses

**Invalid Credentials:**
```json
{
  "detail": "Invalid Jira access token or base URL"
}
```

**Integration Not Found:**
```json
{
  "connected": false,
  "error": "Integration not properly configured - missing access token or base URL"
}
```

**Connection Failed:**
```json
{
  "success": false,
  "error": "Jira connection failed",
  "details": {
    "connected": false,
    "error": "Request failed"
  }
}
```

## Frontend Requirements

### 1. Integration Management Page

**Features needed:**
- List existing Jira integrations
- Create new Jira integration form
- Test connection button
- Delete integration option
- Connection status indicator

**Form fields for creating integration:**
- Access Token (password field)
- Base URL (text field with validation for Atlassian domain)
- Test Connection button
- Save button

### 2. Backlog/Issues Page

**Features needed:**
- Display list of Jira issues
- Filter by status, priority, assignee
- Search functionality
- Pagination
- Sort by date, priority, etc.
- Click to view issue details
- Create new issue button

**Issue card should display:**
- Issue key (PROJ-123)
- Summary
- Status (with color coding)
- Priority (with icon)
- Assignee
- Issue type
- Project
- Last updated date
- Direct link to Jira

### 3. Issue Detail Modal/Page

**Features needed:**
- Full issue details
- Edit issue form
- Status change dropdown
- Priority change dropdown
- Assignee change dropdown
- Description editor
- Comments section (if available)
- Link to open in Jira

### 4. Project Selection

**Features needed:**
- Dropdown to select Jira project
- Auto-populate from API
- Create issue in selected project

## UI/UX Guidelines

### Color Scheme
- Use Jira's brand colors where appropriate
- Status colors:
  - To Do: #42526E (gray)
  - In Progress: #0052CC (blue)
  - Done: #36B37E (green)
  - High Priority: #FF5630 (red)
  - Medium Priority: #FF8B00 (orange)
  - Low Priority: #36B37E (green)

### Icons
- Use standard issue type icons
- Priority icons (exclamation marks)
- Status icons (circles, checkmarks)
- Project icons

### Loading States
- Show loading spinners for API calls
- Skeleton loaders for issue lists
- Progress indicators for sync operations

### Error Handling
- Display user-friendly error messages
- Retry buttons for failed operations
- Validation feedback for forms

## Data Flow

### 1. Initial Setup
1. User navigates to Jira integration page
2. Check if tenant has existing integrations
3. Show integration list or empty state
4. Provide "Add Integration" button

### 2. Creating Integration
1. User clicks "Add Integration"
2. Show form with access token and base URL fields
3. User enters credentials
4. Test connection before saving
5. Save integration to backend
6. Show success message and redirect to issues

### 3. Viewing Backlog
1. User navigates to issues page
2. Load issues from API with pagination
3. Display issues in cards/list
4. Provide filters and search
5. Handle loading and error states

### 4. Issue Management
1. User clicks on issue to view details
2. Load full issue data
3. Show edit form if user has permissions
4. Handle updates and validation

## Testing Considerations

### API Testing
- Test with valid Jira credentials
- Test with invalid credentials
- Test network failures
- Test rate limiting

### UI Testing
- Test form validation
- Test loading states
- Test error handling
- Test responsive design
- Test accessibility

## Security Notes

- Access tokens should be masked in UI
- Don't log sensitive data
- Validate URLs before sending to API
- Handle token expiration gracefully

## Performance Considerations

- Implement pagination for large issue lists
- Cache project lists
- Debounce search inputs
- Lazy load issue details
- Optimize re-renders

## Integration Points

### With Existing App
- Use existing tenant management
- Follow existing UI patterns
- Use existing error handling
- Integrate with existing navigation

### With HubSpot Integration
- Follow similar patterns to HubSpot integration
- Use consistent terminology
- Share common components where possible
- Maintain consistent UX

## Development Checklist

- [ ] Create integration management page
- [ ] Implement create integration form
- [ ] Add connection testing
- [ ] Build issues/backlog page
- [ ] Implement issue filtering and search
- [ ] Create issue detail view
- [ ] Add issue creation form
- [ ] Implement issue editing
- [ ] Add project selection
- [ ] Implement sync functionality
- [ ] Add error handling
- [ ] Test with real Jira instance
- [ ] Add loading states
- [ ] Implement responsive design
- [ ] Add accessibility features
- [ ] Write unit tests
- [ ] Add integration tests

## Backend Status
✅ **Ready for frontend development**
- All API endpoints implemented
- Error handling complete
- Multi-tenant support working
- Test script available at `scripts/test_jira_integration.py`

## Support
For backend API questions, refer to:
- API documentation: http://localhost:8000/docs
- Test script: `scripts/test_jira_integration.py`
- Backend code: `app/api/jira.py` and `app/services/jira_service.py` 
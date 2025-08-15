# Backend Implementation: Create Jira Tickets from AI Issues

## Overview
The frontend now has a modal that allows users to create Jira tickets directly from AI issue groups. You need to implement the backend endpoint to handle this functionality.

## Required Endpoint

### `POST /api/issues/ai/{ai_issue_id}/create-jira-ticket`

**Purpose**: Create a new Jira ticket from an AI issue group and associate it with the group.

**Path Parameters**:
- `ai_issue_id` (string): The UUID of the AI issue group

**Request Body**:
```json
{
  "title": "User-edited ticket title",
  "description": "User-edited ticket description"
}
```

**Response** (Success - 200):
```json
{
  "success": true,
  "data": {
    "ticket_key": "SCRUM-123",
    "ticket_url": "https://killthenoise.atlassian.net/browse/SCRUM-123"
  },
  "message": "Jira ticket created successfully"
}
```

**Response** (Error - 400/500):
```json
{
  "success": false,
  "error": "Error message",
  "message": "User-friendly error message"
}
```

## Implementation Requirements

### 1. **Validation**
- Verify the AI issue group exists and belongs to the tenant
- Ensure title and description are not empty
- Validate user has active Jira integration

### 2. **Jira API Integration**
- Use the tenant's Jira integration credentials (from existing integrations)
- Create ticket using Jira REST API v3: `POST /rest/api/3/issue`
- Use appropriate project key and issue type from the integration settings

### 3. **Database Operations**
After successful Jira ticket creation:
- Create a new report record linking the AI issue group to the Jira ticket
- Store the Jira ticket key and URL for future reference
- Update any necessary relationships

### 4. **Suggested Database Schema**
You may need to add a new report record like:
```python
{
  "id": "uuid",
  "group_id": "ai_issue_group_id", 
  "source": "jira",
  "title": "Jira ticket title",
  "url": "https://killthenoise.atlassian.net/browse/SCRUM-123",
  "external_id": "SCRUM-123",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Implementation Steps

### Step 1: Create the endpoint
```python
@router.post("/issues/ai/{ai_issue_id}/create-jira-ticket")
async def create_jira_ticket_from_ai_issue(
    ai_issue_id: str,
    request: CreateJiraTicketRequest,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    # Implementation here
    pass
```

### Step 2: Request/Response Models
```python
class CreateJiraTicketRequest(BaseModel):
    title: str
    description: str

class CreateJiraTicketResponse(BaseModel):
    ticket_key: str
    ticket_url: str
```

### Step 3: Core Logic
1. **Get AI Issue Group**: Fetch and validate the AI issue group exists
2. **Get Jira Integration**: Find active Jira integration for the tenant
3. **Create Jira Ticket**: Call Jira API to create the ticket
4. **Store Association**: Create report record linking AI group to Jira ticket
5. **Return Response**: Return ticket key and URL

### Step 4: Error Handling
- **404**: AI issue group not found
- **400**: No active Jira integration
- **400**: Invalid title/description
- **500**: Jira API errors
- **500**: Database errors

## Expected Jira API Call

**Endpoint**: `POST {base_url}/rest/api/3/issue`

**Headers**:
```
Authorization: Basic {base64(email:api_token)}
Content-Type: application/json
```

**Body**:
```json
{
  "fields": {
    "project": {
      "key": "SCRUM"
    },
    "summary": "User-provided title",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": "User-provided description"
            }
          ]
        }
      ]
    },
    "issuetype": {
      "name": "Task"
    }
  }
}
```

## Frontend Integration Notes

The frontend will:
1. Call this endpoint when user clicks "🎫 Create Jira Ticket"
2. Automatically refresh the AI issues table after successful creation
3. The new Jira ticket should appear in the "Jira Ticket" column immediately

## Testing

Test with:
1. Valid AI issue group ID and credentials
2. Invalid AI issue group ID (should return 404)
3. Tenant without Jira integration (should return 400)
4. Invalid Jira credentials (should return 500 with helpful message)
5. Jira API errors (network, permission, etc.)

## Security Notes

- Validate tenant ownership of AI issue group
- Use existing Jira integration credentials (don't require new ones)
- Sanitize user input for title/description
- Log ticket creation for audit purposes

This endpoint will complete the "Create Jira Ticket" feature, allowing users to seamlessly escalate AI-detected issues to their Jira project management workflow.
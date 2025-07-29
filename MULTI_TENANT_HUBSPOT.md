# Multi-Tenant HubSpot Integration System

This document describes the reliable, multi-tenant HubSpot integration system that allows different tenants to connect their own HubSpot accounts and sync ticket data independently.

## Overview

The system provides:
- ✅ **Reliable token validation** before every API call
- ✅ **Multi-tenant isolation** - each tenant has their own integrations
- ✅ **Automatic error handling** and connection status reporting
- ✅ **Direct API calls** using proven patterns from successful tests
- ✅ **Complete OAuth flow** for tenant onboarding
- ✅ **Comprehensive endpoints** for all HubSpot operations

## Architecture

### Core Components

1. **HubSpotService** (`app/services/hubspot_service.py`)
   - Handles per-tenant HubSpot API interactions
   - Validates tokens before each request
   - Provides reliable ticket fetching and synchronization
   - Enforces tenant isolation

2. **Multi-tenant API Endpoints** (`app/api/hubspot.py`)
   - Tenant-scoped endpoints for all HubSpot operations
   - OAuth flow management
   - Integration lifecycle management

3. **Database Models**
   - `TenantIntegration`: Stores per-tenant HubSpot configurations
   - `SyncEvent`: Tracks synchronization history and errors
   - `Issue`: Stores synchronized ticket data

## API Endpoints

### Connection Testing

```http
GET /api/hubspot/status/{tenant_id}/{integration_id}
```

Tests the HubSpot connection for a specific tenant integration.

**Response:**
```json
{
  "connected": true,
  "hub_domain": "MyCompany.hubspot.com",
  "scopes": ["oauth", "tickets"],
  "token_type": "access",
  "expires_in": 3600
}
```

### Ticket Management

```http
GET /api/hubspot/tickets/{tenant_id}/{integration_id}?limit=50
```

Lists all HubSpot tickets for a tenant.

**Response:**
```json
{
  "success": true,
  "tickets": [
    {
      "id": "12345",
      "properties": {
        "subject": "Customer issue",
        "hs_ticket_priority": "HIGH",
        "hs_pipeline_stage": "1"
      }
    }
  ],
  "total_count": 25,
  "tenant_id": "uuid-here"
}
```

### Synchronization

```http
POST /api/hubspot/sync/{tenant_id}/{integration_id}
```

Triggers background synchronization of tickets.

**Body:**
```json
{
  "sync_type": "full"  // or "incremental"
}
```

**Response:**
```json
{
  "success": true,
  "message": "HubSpot full sync started in background",
  "tenant_id": "uuid-here",
  "integration_id": "uuid-here"
}
```

### Integration Management

```http
GET /api/hubspot/integrations/{tenant_id}
```

Lists all HubSpot integrations for a tenant.

```http
POST /api/hubspot/integrations/{tenant_id}
```

Creates a new integration with an access token.

**Body:**
```json
{
  "access_token": "your-hubspot-access-token"
}
```

### OAuth Flow

```http
GET /api/hubspot/authorize/{tenant_id}
```

Generates OAuth authorization URL for a tenant.

**Response:**
```json
{
  "success": true,
  "authorization_url": "https://app.hubspot.com/oauth/authorize?...",
  "integration_id": "uuid-here",
  "tenant_id": "uuid-here"
}
```

```http
POST /api/hubspot/oauth/callback
```

Handles OAuth callback and activates the integration.

**Body:**
```json
{
  "code": "oauth-code-from-hubspot",
  "state": "tenant_id:integration_id"
}
```

## Usage Examples

### Python Client Example

```python
import httpx

class HubSpotClient:
    def __init__(self, base_url: str, tenant_id: str, integration_id: str):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.integration_id = integration_id
    
    async def test_connection(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/hubspot/status/{self.tenant_id}/{self.integration_id}"
            )
            return response.json()
    
    async def list_tickets(self, limit: int = 100):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/hubspot/tickets/{self.tenant_id}/{self.integration_id}",
                params={"limit": limit}
            )
            return response.json()
    
    async def sync_tickets(self, sync_type: str = "full"):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/hubspot/sync/{self.tenant_id}/{self.integration_id}",
                json={"sync_type": sync_type}
            )
            return response.json()

# Usage
client = HubSpotClient("http://localhost:8000", tenant_id, integration_id)
connection_status = await client.test_connection()
tickets = await client.list_tickets(limit=50)
sync_result = await client.sync_tickets("incremental")
```

### cURL Examples

```bash
# Test connection
curl -X GET "http://localhost:8000/api/hubspot/status/{tenant_id}/{integration_id}"

# List tickets
curl -X GET "http://localhost:8000/api/hubspot/tickets/{tenant_id}/{integration_id}?limit=25"

# Start sync
curl -X POST "http://localhost:8000/api/hubspot/sync/{tenant_id}/{integration_id}" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "full"}'

# Create integration
curl -X POST "http://localhost:8000/api/hubspot/integrations/{tenant_id}" \
  -H "Content-Type: application/json" \
  -d '{"access_token": "your-access-token"}'

# Get OAuth URL
curl -X GET "http://localhost:8000/api/hubspot/authorize/{tenant_id}"
```

## Key Features

### 1. Reliable Token Management

The system validates HubSpot access tokens before every API call using HubSpot's token introspection endpoint:

```python
async def _validate_token(self, token: str) -> bool:
    """Validate if a token is still valid."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HUBSPOT_BASE_URL}/oauth/v1/access-tokens/{token}",
                timeout=10
            )
            return response.status_code == 200
    except Exception:
        return False
```

### 2. Multi-Tenant Isolation

Each tenant's integrations are completely isolated:

```python
async def _get_integration(self, session: AsyncSession) -> TenantIntegration:
    """Get the tenant integration record."""
    stmt = select(TenantIntegration).where(
        TenantIntegration.id == self.integration_id,
        TenantIntegration.tenant_id == self.tenant_id,
        TenantIntegration.integration_type == "hubspot"
    )
    # This ensures tenant A cannot access tenant B's integrations
```

### 3. Comprehensive Error Handling

All operations include detailed error reporting:

```python
try:
    # HubSpot API call
    response = await client.get("/crm/v3/objects/tickets")
    response.raise_for_status()
    return {"success": True, "data": response.json()}
except Exception as e:
    return {"success": False, "error": str(e)}
```

### 4. Background Processing

Long-running operations (like full syncs) run in the background:

```python
@router.post("/sync/{tenant_id}/{integration_id}")
async def hubspot_sync(background_tasks: BackgroundTasks):
    # Test connection first
    connection_test = await service.test_connection()
    if connection_test.get("connected"):
        # Queue background task
        background_tasks.add_task(_run_full_sync, tenant_id, integration_id)
    return {"success": True, "message": "Sync started"}
```

## Testing

### Unit Tests

Run the multi-tenant test to verify all functionality:

```bash
python3 scripts/test_multi_tenant_hubspot.py
```

This test demonstrates:
- ✅ Creating tenant integrations
- ✅ Testing connections with token validation
- ✅ Listing tickets per tenant
- ✅ Tenant isolation enforcement

### Integration Tests

The system is tested against live HubSpot APIs using:
- Valid OAuth tokens
- Real HubSpot ticket data
- Actual API response validation

## Security Considerations

1. **Token Storage**: Access tokens are stored in encrypted database fields (in production)
2. **Tenant Isolation**: Strict database-level tenant isolation
3. **Input Validation**: All API inputs are validated using Pydantic schemas
4. **Error Handling**: Sensitive information is not exposed in error messages

## Performance

- **Token Validation**: Cached per request to avoid repeated API calls
- **Connection Pooling**: HTTP clients use connection pooling for efficiency
- **Background Processing**: Heavy operations don't block API responses
- **Database Indexing**: Optimized queries with proper indexes

## Deployment

### Environment Variables

```bash
HUBSPOT_CLIENT_ID=your-client-id
HUBSPOT_CLIENT_SECRET=your-client-secret
HUBSPOT_REDIRECT_URI=https://your-domain.com/api/hubspot/oauth/callback
```

### Docker Configuration

The system is designed to work with the existing Docker setup. No additional configuration needed.

## Troubleshooting

### Common Issues

1. **"Invalid or expired access token"**
   - Token has expired or been revoked
   - Use OAuth flow to get a new token

2. **"Integration not found"**
   - Check tenant_id and integration_id are correct
   - Verify integration exists and is active

3. **"HubSpot connection failed"**
   - Check network connectivity
   - Verify HubSpot service status
   - Validate token scopes include "tickets"

### Debug Mode

Enable debug logging in the service for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Automatic token refresh using refresh tokens
- [ ] Webhook support for real-time updates
- [ ] Advanced filtering and search capabilities
- [ ] Rate limiting and retry logic
- [ ] Metrics and monitoring integration 
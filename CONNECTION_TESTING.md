# Connection Testing Guide

This guide explains how to test connections to all external services used by the KillTheNoise backend.

## Overview

The application connects to several external services:
- **HubSpot**: CRM API for ticket synchronization
- **Claude API**: AI service for issue analysis
- **Supabase**: Backend-as-a-Service for authentication, data storage, and database access

## Environment Variables

Make sure your `.env` file contains all required credentials:

```env
HUBSPOT_CLIENT_ID=your-hubspot-client-id
HUBSPOT_CLIENT_SECRET=your-hubspot-client-secret
HUBSPOT_REDIRECT_URI=http://localhost:5001/api/hubspot/callback
CLAUDE_API_KEY=your-claude-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

## Testing Methods

### 1. Standalone Script (Recommended)

Run the connection test script to verify all services:

```bash
python3 scripts/test_connections.py
```

This script will:
- ✅ Check all environment variables are set
- ✅ Test HubSpot API access
- ✅ Test Claude API authentication
- ✅ Test Supabase connection (includes database access)
- 📊 Provide a summary with success rates and response times

### 2. API Endpoints

Once the FastAPI server is running, you can test connections via HTTP endpoints:

```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test all connections
curl http://localhost:8000/health/connections

# Test individual services
curl http://localhost:8000/health/connections/hubspot
curl http://localhost:8000/health/connections/claude
curl http://localhost:8000/health/connections/supabase
```

### 3. API Testing Script

Test all health endpoints programmatically:

```bash
python3 scripts/test_api_endpoints.py
```

## Expected Results

### Successful Test Output

```
🔍 Testing external service connections...
==================================================
📋 Environment Variables Check:
  ✅ HUBSPOT_CLIENT_ID: c4f6d977-f797-4c43-9e9d-9bc867ea01ac
  ✅ HUBSPOT_CLIENT_SECRET: 1ba8cccc...1e07
  ✅ HUBSPOT_REDIRECT_URI: http://localhost:5001/api/hubspot/callback
  ✅ CLAUDE_API_KEY: sk-ant-a...KQAA
  ✅ SUPABASE_URL: https://mzsoczeglgguffjwwgsu.supabase.co
  ✅ SUPABASE_SERVICE_ROLE_KEY: eyJhbGci...gHKc

🚀 Testing Service Connections:
------------------------------
✅ HubSpot: 0.304s
✅ Claude API: 0.550s
✅ Supabase: 0.004s

📊 Summary:
  Total Tests: 3
  Successful: 3
  Failed: 0
  Success Rate: 100.0%
  Average Response Time: 0.286s

🎉 All connections successful!
```

### API Response Format

```json
{
  "total_tests": 3,
  "successful_tests": 3,
  "failed_tests": 0,
  "success_rate": 100.0,
  "average_response_time": 0.286,
  "results": [
    {
      "service": "HubSpot",
      "success": true,
      "response_time": 0.304,
      "error": null
    },
    {
      "service": "Claude API",
      "success": true,
      "response_time": 0.550,
      "error": null
    },
    {
      "service": "Supabase",
      "success": true,
      "response_time": 0.004,
      "error": null
    }
  ]
}
```

## Troubleshooting

### Common Issues



#### 1. HubSpot Connection Failed
**Error**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
- Verify `HUBSPOT_CLIENT_ID` and `HUBSPOT_CLIENT_SECRET` are correct
- Check that the redirect URI matches your HubSpot app configuration
- Ensure the HubSpot app has the necessary scopes enabled

#### 2. Claude API Connection Failed
**Error**: `404 - model not found` or `401 Unauthorized`

**Solutions**:
- Verify `CLAUDE_API_KEY` is valid and not expired
- Check that the API key has sufficient credits
- Ensure you're using a valid model name

#### 3. Supabase Connection Failed
**Error**: `401 Unauthorized` or connection timeout

**Solutions**:
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are correct
- Check that the service role key has the necessary permissions
- Ensure the Supabase project is active and accessible

### Debug Mode

For more detailed error information, you can modify the connection service to include debug logging:

```python
# In app/services/connection_service.py
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug logging to connection tests
logger.debug(f"Testing {service_name} connection...")
```

## Monitoring

### Health Check Integration

The connection testing is integrated into the application's health check system:

- **Basic Health**: `/health/` - Simple application status
- **Connection Health**: `/health/connections` - All external service status
- **Individual Service Health**: `/health/connections/{service}` - Specific service status

### Automated Monitoring

You can set up automated monitoring by:

1. **Cron Job**: Run the test script periodically
```bash
# Add to crontab
*/5 * * * * cd /path/to/app && python3 scripts/test_connections.py >> /var/log/connection_tests.log
```

2. **Health Check Endpoint**: Monitor the `/health/connections` endpoint
```bash
# Example monitoring script
curl -f http://localhost:8000/health/connections || echo "Connection test failed"
```

3. **Alerting**: Set up alerts for failed connections
```bash
# Example alert script
if ! python3 scripts/test_connections.py; then
    # Send alert (email, Slack, etc.)
    echo "Connection test failed" | mail -s "Service Alert" admin@example.com
fi
```

## Security Considerations

### Environment Variables
- ✅ Never commit `.env` files to version control
- ✅ Use strong, unique API keys for each service
- ✅ Rotate API keys regularly
- ✅ Use service-specific accounts when possible

### Network Security
- ✅ Use HTTPS for all external API calls
- ✅ Implement proper firewall rules
- ✅ Monitor for unusual connection patterns
- ✅ Use VPN if accessing from untrusted networks

### API Key Management
- ✅ Store keys securely (environment variables, secrets manager)
- ✅ Limit API key permissions to minimum required
- ✅ Monitor API usage and costs
- ✅ Set up alerts for unusual usage patterns

## Performance Considerations

### Response Times
- **HubSpot API**: < 1s
- **Claude API**: < 2s
- **Supabase**: < 500ms (includes database access)

### Optimization Tips
- Use connection pooling for database connections
- Implement caching for frequently accessed data
- Batch API calls when possible
- Monitor and optimize slow queries

## Support

If you encounter persistent connection issues:

1. **Check the logs**: Look for detailed error messages
2. **Verify credentials**: Ensure all API keys are valid
3. **Test individually**: Use the individual service endpoints
4. **Check documentation**: Refer to each service's official docs
5. **Contact support**: Reach out to the development team

---

**Last Updated**: 2024
**Version**: 1.0 
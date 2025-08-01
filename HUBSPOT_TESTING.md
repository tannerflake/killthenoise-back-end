# HubSpot Integration Testing

This document explains how to test the HubSpot integration with real credentials.

## Prerequisites

1. **HubSpot Access Token**: You need a valid HubSpot access token in your `.env` file:
   ```
   HUBSPOT_ACCESS_TOKEN=your_hubspot_access_token_here
   HUBSPOT_DOMAIN=api.hubapi.com  # Optional, defaults to api.hubapi.com
   ```

2. **Python Dependencies**: Make sure you have all required dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Tests

### Option 1: Standalone Script (Recommended)

Run the standalone script for quick testing:

```bash
python scripts/test_hubspot_connection.py
```

This script will:
- Load credentials from your `.env` file
- Test the HubSpot connection
- Fetch and display sample tickets
- Test ticket transformation
- Perform a full sync test

### Option 2: Pytest Tests

Run the comprehensive test suite:

```bash
# Run all HubSpot tests
pytest tests/test_hubspot_integration.py -v -s

# Run specific test
pytest tests/test_hubspot_integration.py::TestHubSpotIntegration::test_fetch_tickets_from_hubspot -v -s

# Run with detailed output
pytest tests/test_hubspot_integration.py -v -s --tb=long
```

## Test Coverage

The tests cover:

1. **Connection Testing**: Verifies HubSpot API connectivity
2. **Ticket Fetching**: Tests pulling tickets from HubSpot
3. **Data Transformation**: Tests converting HubSpot tickets to internal issue format
4. **Full Sync**: Tests complete synchronization process
5. **Incremental Sync**: Tests delta synchronization
6. **Error Handling**: Tests behavior with invalid credentials
7. **Service Configuration**: Tests service setup and configuration

## Expected Output

When running successfully, you should see output like:

```
🔍 Testing HubSpot Connection and Ticket Fetching
============================================================

📊 Setting up test database...
🔧 Creating test integration with HubSpot credentials...
✅ Integration created: 12345678-1234-1234-1234-123456789abc
🚀 Creating HubSpot service...
✅ Service created

🔌 Testing HubSpot connection...
Connection status: ✅ Connected

📋 Fetching tickets from HubSpot...
✅ Found 15 tickets

📄 Sample ticket details:
  Ticket ID: 12345
  Subject: Customer Support Request
  Status: open
  Priority: medium
  Category: bug
  Created: 1640995200000
  Modified: 1640995200000

📋 First 5 tickets:
  1. Customer Support Request (ID: 12345)
  2. Feature Request (ID: 12346)
  3. Bug Report (ID: 12347)
  4. General Inquiry (ID: 12348)
  5. Technical Issue (ID: 12349)

🔄 Testing ticket transformation...
✅ Ticket transformed to issue format:
  Issue ID: 98765432-4321-4321-4321-987654321cba
  Title: Customer Support Request
  Source: hubspot
  Severity: 3
  Status: open

🔄 Testing full sync...
✅ Sync completed:
  Success: True
  Processed: 15
  Updated: 15
  Duration: 3 seconds

🎉 All tests completed successfully!
```

## Troubleshooting

### Common Issues

1. **Missing Access Token**:
   ```
   ValueError: HUBSPOT_ACCESS_TOKEN not found in environment variables
   ```
   **Solution**: Add your HubSpot access token to the `.env` file.

2. **Invalid Access Token**:
   ```
   Connection status: ❌ Failed
   ```
   **Solution**: Verify your access token is valid and has the necessary permissions.

3. **Network Issues**:
   ```
   httpx.ConnectError: Connection failed
   ```
   **Solution**: Check your internet connection and firewall settings.

4. **Rate Limiting**:
   ```
   httpx.HTTPStatusError: 429 Too Many Requests
   ```
   **Solution**: Wait a few minutes and try again, or implement rate limiting.

### Getting HubSpot Access Token

1. Go to your HubSpot Developer account
2. Create a new app or use an existing one
3. Generate a private app access token
4. Add the token to your `.env` file

## Test Data

The tests use real HubSpot data from your account. Make sure you have:
- At least one ticket in your HubSpot account
- Proper permissions to read tickets
- A valid access token with the necessary scopes

## Security Notes

- Never commit your `.env` file to version control
- Use environment variables for sensitive data
- Rotate access tokens regularly
- Monitor API usage to avoid rate limits

## Next Steps

After successful testing, you can:

1. **Integrate with your application**: Use the `HubSpotService` in your main application
2. **Set up webhooks**: Configure real-time updates from HubSpot
3. **Implement scheduling**: Set up regular sync intervals
4. **Add monitoring**: Track sync performance and errors
5. **Scale up**: Handle multiple tenants and integrations 
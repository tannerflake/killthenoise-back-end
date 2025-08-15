# Jira Integration Error Handling Guide

## Current Error Response Format

When the Jira integration creation fails, the API now returns a detailed error response:

```json
{
  "detail": {
    "error": "Invalid Jira access token or base URL",
    "message": "Please check your access token and ensure the base URL is correct (e.g., https://your-domain.atlassian.net)",
    "suggestions": [
      "Verify your Jira access token is correct",
      "Ensure the base URL follows the format: https://your-domain.atlassian.net", 
      "Check that your Jira instance is accessible",
      "Verify the token has the necessary permissions"
    ]
  }
}
```

## Frontend Error Handling Implementation

### 1. Update Error Handling in JiraConnectCard.tsx

```typescript
// In your error handling function
const handleConnect = async () => {
  try {
    const response = await createJiraIntegration({
      access_token: accessToken,
      base_url: baseUrl
    });
    
    // Handle success
    console.log('Jira integration created successfully');
    
  } catch (error) {
    if (error.response?.status === 400) {
      const errorData = error.response.data.detail;
      
      // Check if it's the new detailed error format
      if (typeof errorData === 'object' && errorData.error) {
        console.error('Jira connection error:', errorData.error);
        console.error('Message:', errorData.message);
        console.error('Suggestions:', errorData.suggestions);
        
        // Display user-friendly error message
        setError({
          title: 'Connection Failed',
          message: errorData.message,
          suggestions: errorData.suggestions
        });
      } else {
        // Handle legacy error format
        setError({
          title: 'Connection Failed',
          message: errorData || 'Invalid Jira credentials',
          suggestions: [
            'Check your access token',
            'Verify the base URL format',
            'Ensure your Jira instance is accessible'
          ]
        });
      }
    } else {
      // Handle other errors
      setError({
        title: 'Connection Error',
        message: 'An unexpected error occurred',
        suggestions: ['Please try again']
      });
    }
  }
};
```

### 2. Enhanced Error Display Component

```typescript
interface ErrorDisplayProps {
  error: {
    title: string;
    message: string;
    suggestions: string[];
  };
  onRetry?: () => void;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onRetry }) => {
  return (
    <div className="error-container">
      <div className="error-header">
        <h3>{error.title}</h3>
      </div>
      
      <div className="error-message">
        <p>{error.message}</p>
      </div>
      
      {error.suggestions.length > 0 && (
        <div className="error-suggestions">
          <h4>Suggestions:</h4>
          <ul>
            {error.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
      
      {onRetry && (
        <button onClick={onRetry} className="retry-button">
          Try Again
        </button>
      )}
    </div>
  );
};
```

### 3. Form Validation

Add client-side validation before making the API call:

```typescript
const validateJiraCredentials = (accessToken: string, baseUrl: string) => {
  const errors: string[] = [];
  
  if (!accessToken.trim()) {
    errors.push('Access token is required');
  }
  
  if (!baseUrl.trim()) {
    errors.push('Base URL is required');
  } else {
    // Validate URL format
    try {
      const url = new URL(baseUrl);
      if (!url.protocol.startsWith('https')) {
        errors.push('Base URL must use HTTPS');
      }
      if (!url.hostname.includes('atlassian.net')) {
        errors.push('Base URL should be an Atlassian domain (e.g., your-domain.atlassian.net)');
      }
    } catch {
      errors.push('Base URL must be a valid URL');
    }
  }
  
  return errors;
};

// In your form submission
const handleSubmit = async () => {
  const validationErrors = validateJiraCredentials(accessToken, baseUrl);
  
  if (validationErrors.length > 0) {
    setError({
      title: 'Validation Error',
      message: 'Please fix the following issues:',
      suggestions: validationErrors
    });
    return;
  }
  
  // Proceed with API call
  await handleConnect();
};
```

### 4. Loading States

Add proper loading states during connection testing:

```typescript
const [isConnecting, setIsConnecting] = useState(false);

const handleConnect = async () => {
  setIsConnecting(true);
  setError(null);
  
  try {
    // API call here
    await createJiraIntegration({ access_token: accessToken, base_url: baseUrl });
  } catch (error) {
    // Error handling here
  } finally {
    setIsConnecting(false);
  }
};
```

### 5. Success Handling

```typescript
const handleSuccess = (response: any) => {
  // Show success message
  setSuccess({
    title: 'Connection Successful',
    message: 'Jira integration has been created successfully',
    integrationId: response.integration_id
  });
  
  // Redirect to issues page or refresh integration list
  // navigate('/jira/issues');
};
```

## Testing Scenarios

### Valid Credentials
- Use a real Jira access token
- Use correct Atlassian domain (e.g., `https://your-domain.atlassian.net`)

### Invalid Credentials (for testing)
- Wrong access token
- Invalid base URL format
- Empty fields
- Non-Atlassian domain

## Error Message Examples

### Invalid Token
```
Error: Invalid Jira access token or base URL
Message: Please check your access token and ensure the base URL is correct
Suggestions:
- Verify your Jira access token is correct
- Ensure the base URL follows the format: https://your-domain.atlassian.net
- Check that your Jira instance is accessible
- Verify the token has the necessary permissions
```

### Invalid URL
```
Error: Invalid Jira access token or base URL
Message: Please check your access token and ensure the base URL is correct
Suggestions:
- Verify your Jira access token is correct
- Ensure the base URL follows the format: https://your-domain.atlassian.net
- Check that your Jira instance is accessible
- Verify the token has the necessary permissions
```

## Backend Status
✅ **Error handling improved**
- Detailed error messages
- Helpful suggestions
- Consistent error format
- Graceful validation

## Next Steps
1. Update your frontend error handling to use the new detailed error format
2. Add client-side validation for better UX
3. Test with both valid and invalid credentials
4. Add proper loading states
5. Implement retry functionality 
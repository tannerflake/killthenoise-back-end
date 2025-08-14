# AI-Powered Dashboard Testing Guide

This guide shows you how to use AI to generate realistic test issues in both HubSpot and Jira accounts, then test the full dashboard integration pipeline.

## 🎯 Overview

The testing suite includes three main scripts:

1. **`setup_ai_testing.py`** - Environment setup and validation
2. **`generate_ai_test_issues.py`** - AI-powered issue generation
3. **`test_dashboard_integration.py`** - Full integration testing

## 🚀 Quick Start

### Step 1: Environment Setup

```bash
# Run the setup script to check your environment
python scripts/setup_ai_testing.py
```

This will:
- ✅ Check required environment variables
- ✅ Verify Python dependencies
- ✅ Test database connectivity
- ✅ Create `.env` template if needed

### Step 2: Configure Environment Variables

Set these required environment variables:

```bash
# Required for AI generation
export CLAUDE_API_KEY="your_claude_api_key_here"

# Required for database
export DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/killthenoise"

# Optional for integrations
export HUBSPOT_CLIENT_ID="your_hubspot_client_id"
export HUBSPOT_CLIENT_SECRET="your_hubspot_client_secret"
export JIRA_CLIENT_ID="your_jira_client_id"
export JIRA_CLIENT_SECRET="your_jira_client_secret"
```

### Step 3: Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Generate AI Test Issues

```bash
python scripts/generate_ai_test_issues.py
```

This script will:
- 🤖 Use Claude AI to generate realistic issue content
- 📝 Create varied issue types (bugs, feature requests, support, etc.)
- 🔄 Create issues in both HubSpot and Jira accounts
- 📊 Provide detailed results and statistics

### Step 5: Test Dashboard Integration

```bash
python scripts/test_dashboard_integration.py
```

This script will:
- 🔍 Check integration status
- 🔄 Run sync processes
- 📊 Test dashboard analytics
- 🤖 Verify AI clustering
- 📄 Save detailed test results

## 📋 Detailed Script Documentation

### `generate_ai_test_issues.py`

**Purpose**: Generate realistic test issues using AI and create them in actual HubSpot and Jira accounts.

**Features**:
- AI-generated realistic issue content
- Creates issues in actual HubSpot and Jira accounts
- Tests the full sync and dashboard pipeline
- Configurable issue types and quantities
- Comprehensive logging and error handling

**Usage**:
```bash
python scripts/generate_ai_test_issues.py
```

**Configuration**:
- Set `CLAUDE_API_KEY` environment variable
- Ensure active HubSpot and Jira integrations
- Adjust `TENANT_ID` in script if needed

**Output**:
```
🤖 AI-Powered Test Issue Generator for KillTheNoise Dashboard
============================================================
Enter number of issues to generate (default 10): 15

🎯 Generating 15 realistic test issues...
📝 This will create issues in both HubSpot and Jira accounts
⏳ Please wait, this may take a few minutes...

📝 Generating issue 1/15...
✅ Created HubSpot ticket: 12345
✅ Created Jira issue: TEST-123

============================================================
📊 GENERATION SUMMARY
============================================================
✅ HubSpot tickets created: 8
❌ HubSpot tickets failed: 0
✅ Jira issues created: 7
❌ Jira issues failed: 0
📝 Total issues generated: 15

📋 SAMPLE GENERATED ISSUES:
----------------------------------------
1. [HUBSPOT] Critical bug in login system
   Severity: 5, Status: open
   HubSpot ID: 12345

2. [JIRA] Performance issue with database queries
   Severity: 4, Status: in-progress
   Jira Key: TEST-124

🎉 Test issue generation complete!
🔄 You can now run your sync processes to test the dashboard integration
📈 Check your dashboard to see the new issues appear
```

### `test_dashboard_integration.py`

**Purpose**: Test the complete dashboard integration pipeline from sync to analytics.

**Features**:
- Tests HubSpot and Jira connections
- Runs sync processes
- Verifies dashboard analytics
- Tests AI clustering functionality
- Generates comprehensive test reports

**Usage**:
```bash
python scripts/test_dashboard_integration.py
```

**Test Coverage**:
1. **Integration Status** - Check active integrations
2. **HubSpot Integration** - Test connection and sync
3. **Jira Integration** - Test connection and sync
4. **Database Issues** - Verify data storage
5. **Dashboard Analytics** - Test API endpoints
6. **AI Clustering** - Test AI grouping functionality

**Output**:
```
🧪 Dashboard Integration Test Suite
==================================================
✅ API server is running

==================================================
TEST 1: Integration Status
==================================================
🔍 Checking active integrations...
✅ Found 2 active integrations

==================================================
TEST 2: HubSpot Integration
==================================================
🔗 Testing HubSpot connection...
🔄 Running HubSpot sync...
✅ HubSpot connection and sync successful

==================================================
TEST 3: Jira Integration
==================================================
🔗 Testing Jira connection...
🔄 Fetching Jira issues...
✅ Jira connection and sync successful

==================================================
TEST 4: Database Issues
==================================================
📊 Checking issues in database...
✅ Database contains 25 issues
   HubSpot: 12, Jira: 13

==================================================
TEST 5: Dashboard Analytics
==================================================
📈 Testing dashboard analytics...
✅ Dashboard analytics working

==================================================
TEST 6: AI Clustering
==================================================
🤖 Testing AI clustering...
✅ AI clustering working - 8 groups found

==================================================
INTEGRATION TEST SUMMARY
==================================================
✅ integrations: PASSED
✅ hubspot: PASSED
✅ jira: PASSED
✅ database: PASSED
✅ analytics: PASSED
✅ ai_clustering: PASSED
📊 Overall: 6/6 tests passed

📄 Test results saved to: integration_test_results_20241201_143022.json

🎯 NEXT STEPS:
✅ Integration is working well! You can now:
   - View the dashboard in your frontend
   - Monitor real-time sync status
   - Use AI clustering features
```

### `setup_ai_testing.py`

**Purpose**: Validate environment setup and provide guidance for testing.

**Features**:
- Environment variable validation
- Dependency checking
- Database connectivity testing
- Setup guidance and next steps

**Usage**:
```bash
python scripts/setup_ai_testing.py
```

## 🔧 Configuration Options

### Issue Types Generated

The AI generator creates these issue types:
- **Bug** - Technical issues and defects
- **Feature Request** - Enhancement requests
- **Support** - Customer support questions
- **Performance** - Performance-related issues
- **Security** - Security concerns and vulnerabilities
- **Integration** - Integration-related problems

### Severity Levels

Issues are generated with realistic severity levels:
- **1 (Minimal)** - Info requests, minor questions
- **2 (Low)** - Non-urgent issues, workarounds available
- **3 (Medium)** - Affects functionality, no workaround
- **4 (High)** - Significant business impact, urgent
- **5 (Critical)** - System down, revenue impact, security issue

### Status Distribution

Issues are created with varied statuses:
- **Open** - New issues
- **In Progress** - Being worked on
- **Pending** - Waiting for information
- **Resolved** - Completed issues
- **Closed** - Finalized issues

## 🎛️ Customization

### Modifying Issue Generation

Edit `scripts/generate_ai_test_issues.py` to customize:

```python
# Change issue types
ISSUE_TYPES = ["bug", "feature_request", "support", "performance", "security", "integration"]

# Adjust severity distribution
SEVERITY_LEVELS = [1, 2, 3, 4, 5]

# Modify status options
STATUS_OPTIONS = ["open", "in-progress", "pending", "resolved", "closed"]

# Change tenant ID
TENANT_ID = UUID("your-tenant-id-here")
```

### Customizing AI Prompts

Modify the AI prompt in `generate_realistic_issue()`:

```python
prompt = f"""Generate a realistic {issue_type} issue for a SaaS application. 
This should be a {source} ticket that a real customer might submit.

# Add your custom requirements here
# Include specific business context
# Add industry-specific details
"""
```

## 🐛 Troubleshooting

### Common Issues

**1. Claude API Key Not Set**
```
❌ Error: CLAUDE_API_KEY environment variable not set
```
**Solution**: Set your Claude API key:
```bash
export CLAUDE_API_KEY="your-key-here"
```

**2. Database Connection Failed**
```
❌ Database connection failed: connection refused
```
**Solution**: Check your DATABASE_URL and ensure PostgreSQL is running.

**3. Integration Not Found**
```
❌ No active HubSpot integration found
```
**Solution**: Ensure you have active integrations in the database.

**4. API Server Not Responding**
```
❌ Cannot connect to API server at http://localhost:8000
```
**Solution**: Start the API server:
```bash
uvicorn app.main:app --reload
```

### Debug Mode

Enable detailed logging by modifying the logging level:

```python
# In any script, change:
logging.basicConfig(level=logging.INFO)

# To:
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Expected Results

After running the complete test suite, you should see:

### Dashboard Analytics
- **Total Issues**: 10-50 issues (depending on generation count)
- **Source Distribution**: Mix of HubSpot and Jira issues
- **Severity Distribution**: Realistic spread across levels 1-5
- **Status Distribution**: Varied statuses reflecting real workflow

### AI Clustering
- **Issue Groups**: 5-15 AI-generated groups
- **Cross-Source Groups**: Issues from both HubSpot and Jira in same groups
- **Confidence Scores**: AI confidence levels for categorization

### Sync Results
- **HubSpot Sync**: 80-100% success rate
- **Jira Sync**: 80-100% success rate
- **Data Consistency**: Issues appear in both source systems and dashboard

## 🎉 Success Criteria

Your integration is working correctly when:

1. ✅ **Issue Generation**: AI creates realistic, varied issues
2. ✅ **Sync Process**: Issues sync from both sources to database
3. ✅ **Dashboard Analytics**: All metrics calculate correctly
4. ✅ **AI Clustering**: Related issues are grouped together
5. ✅ **Cross-Source Integration**: Issues from both sources appear unified
6. ✅ **Real-Time Updates**: New issues appear in dashboard after sync

## 📈 Performance Monitoring

Monitor these metrics during testing:

- **Generation Speed**: 1-2 seconds per issue
- **Sync Performance**: 5-10 seconds per source
- **API Response Time**: < 500ms for dashboard endpoints
- **AI Processing**: 2-5 seconds per analysis
- **Database Queries**: < 100ms for typical operations

## 🔄 Continuous Testing

For ongoing testing, you can:

1. **Schedule Regular Tests**: Run scripts on a schedule
2. **Monitor Dashboard**: Check for new issues appearing
3. **Verify Sync Health**: Monitor sync success rates
4. **Test AI Accuracy**: Review clustering quality
5. **Performance Tracking**: Monitor response times

This comprehensive testing suite ensures your dashboard integration is robust, reliable, and ready for production use!

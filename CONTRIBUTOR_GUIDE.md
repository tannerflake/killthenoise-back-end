# KillTheNoise Backend - Contributor Guide

## What is KillTheNoise?

KillTheNoise is a multi-tenant SaaS platform that aggregates issues from multiple sources (HubSpot, Jira, etc.) into a centralized dashboard. It helps organizations identify, prioritize, and resolve customer issues efficiently.

## 🏗️ Architecture Overview

### Core Components
- **API Layer** (`app/api/`): REST endpoints for frontend integration
- **Services** (`app/services/`): Business logic for data processing
- **Models** (`app/models/`): Database structure for issues and integrations
- **Scheduler** (`app/services/scheduler_service.py`): Background sync operations

### Data Flow
1. **External Systems** → Webhooks/API calls → **KillTheNoise**
2. **KillTheNoise** → Processes & calculates metrics → **Database**
3. **Frontend** → API calls → **KillTheNoise** → **Dashboard**

## 🔄 How It Works

### Multi-Tenant Design
Each organization (tenant) has isolated data and integrations:
- Separate HubSpot/Jira connections per tenant
- Tenant-specific issue tracking and analytics
- Isolated sync operations and calculations

### Issue Aggregation
1. **Sync Process**: Background jobs pull issues from external systems
2. **Data Transformation**: Convert external formats to internal issue model
3. **Calculation Engine**: Generate metrics, trends, and insights
4. **Real-time Updates**: Webhooks provide immediate data changes

### Key Features
- **Issue Prioritization**: Severity-based ranking system
- **Cross-Source Analysis**: Compare issues across HubSpot, Jira, etc.
- **Trend Analysis**: Track issue patterns over time
- **Sync Health Monitoring**: Track integration performance

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Poetry (package manager)

### Quick Start
```bash
# Clone and setup
git clone <repository>
cd killthenoise-back-end
python scripts/setup_dev_environment.py

# Start development server
poetry install
poetry run uvicorn app.main:app --reload
```

### Environment Variables
```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
HUBSPOT_ACCESS_TOKEN=your_token

# Optional
FRONTEND_ORIGIN=http://localhost:3000
SUPABASE_URL=your_supabase_url
```

## 📁 Project Structure

```
app/
├── api/              # REST endpoints
│   ├── analytics.py  # Dashboard metrics
│   ├── sync.py       # Sync management
│   └── webhooks.py   # Real-time updates
├── models/           # Database models
│   ├── issue.py      # Issue data structure
│   └── tenant_integration.py  # Integration configs
├── services/         # Business logic
│   ├── hubspot_service.py     # HubSpot integration
│   ├── calculation_service.py # Analytics engine
│   └── scheduler_service.py   # Background jobs
└── main.py          # Application entry point
```

## 🔧 Key Concepts

### Issue Model
```python
# Core issue structure
{
    "id": "uuid",
    "tenant_id": "uuid",        # Multi-tenant isolation
    "title": "Issue title",
    "severity": 1-5,            # Priority ranking
    "source": "hubspot|jira",   # Origin system
    "status": "open|resolved",
    "created_at": "timestamp"
}
```

### Sync Operations
- **Incremental Sync**: Only fetch changes since last sync
- **Webhook Processing**: Real-time updates from external systems
- **Error Handling**: Automatic retry and failure tracking
- **Performance Monitoring**: Track sync success rates and timing

### Analytics Engine
- **Issue Metrics**: Count, severity distribution, trends
- **Source Comparison**: Compare HubSpot vs Jira vs other sources
- **Velocity Tracking**: How quickly issues are created/resolved
- **Health Monitoring**: Sync performance and error rates

## 🚀 Adding New Features

### 1. New Integration (e.g., Zendesk)
```python
# Create service
app/services/zendesk_service.py
# Add API endpoints
app/api/zendesk.py
# Update models
app/models/tenant_integration.py
```

### 2. New Analytics
```python
# Add calculation method
app/services/calculation_service.py
# Add API endpoint
app/api/analytics.py
```

### 3. New API Endpoint
```python
# Follow existing patterns
app/api/your_feature.py
# Register in main.py
```

## 📊 API Endpoints

### Core Endpoints
- `GET /api/analytics/dashboard/{tenant_id}` - Main dashboard data
- `GET /api/sync/status` - Sync operation status
- `POST /api/sync/trigger` - Manual sync trigger
- `POST /api/webhooks/hubspot/{tenant_id}` - Real-time updates

### Response Format
```json
{
    "success": true,
    "data": {...},
    "message": "Operation completed"
}
```

## 🧪 Testing

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_hubspot_service.py

# With coverage
pytest --cov=app
```

### Test Structure
- **Unit Tests**: Test individual functions
- **Integration Tests**: Test API endpoints
- **Service Tests**: Test business logic
- **Mock External APIs**: Don't call real services

## 📝 Code Standards

### Line Limits
- **Files**: Maximum 200 lines
- **Functions**: Maximum 50 lines
- **Classes**: Maximum 150 lines

### Quality Checks
```bash
# Automatic checks on commit
pre-commit run --all-files

# Manual checks
black app/
isort app/
flake8 app/
mypy app/
```

### Architecture Patterns
- **Service Layer**: Business logic in services, not API endpoints
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: Use FastAPI's DI system
- **Async/Await**: All I/O operations are async

## 🔍 Debugging

### Common Issues
1. **Database Connection**: Check `DATABASE_URL` environment variable
2. **Sync Failures**: Check integration credentials and API limits
3. **Performance Issues**: Monitor database queries and external API calls

### Logs
```bash
# Application logs
tail -f logs/app.log

# Sync operation logs
tail -f logs/sync.log
```

## 🚀 Deployment

### Environment Setup
```bash
# Production
DATABASE_URL=postgresql+asyncpg://prod_user:pass@prod_host/db
HUBSPOT_ACCESS_TOKEN=prod_token
FRONTEND_ORIGIN=https://yourdomain.com
```

### Health Checks
- `GET /health` - Application health
- `GET /api/sync/status` - Sync operations health
- Database connectivity checks

## 📞 Getting Help

### Resources
- **Architecture Decisions**: Check `DEVELOPMENT_STANDARDS.md`
- **API Documentation**: Visit `/docs` when server is running
- **Code Examples**: See existing services for patterns

### Team Support
- Ask questions in team chat
- Request code reviews for complex changes
- Document architectural decisions

---

**Remember**: This is a multi-tenant system - always consider tenant isolation in your changes! 
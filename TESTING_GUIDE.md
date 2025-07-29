# KillTheNoise Backend - Testing Guide

## 🧪 Testing Strategy Overview

This guide covers the best approach to start testing the KillTheNoise backend, from initial setup to comprehensive test coverage.

## 🚀 Quick Start Testing

### 1. Environment Setup
```bash
# Install project dependencies
poetry install

# Or if using pip
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov aiosqlite
```

### 2. Run Basic Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_api_endpoints.py -v
python -m pytest tests/test_services.py -v
python -m pytest tests/test_models.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

## 📋 Test Categories

### 1. **API Endpoint Tests** (`tests/test_api_endpoints.py`)
**Purpose**: Test all REST API endpoints
**Coverage**: 
- ✅ Analytics endpoints (metrics, trends, distributions)
- ✅ Sync management endpoints
- ✅ Webhook endpoints (HubSpot, Jira)
- ✅ Issues endpoints
- ✅ Integration health checks

**Example Test**:
```python
def test_get_issue_metrics(self, client: TestClient, sample_tenant_id: str):
    """Test getting issue metrics for a tenant."""
    response = client.get(f"/api/analytics/metrics/{sample_tenant_id}")
    assert response.status_code == 200
    data = response.json()
    assert "total_issues" in data
    assert "avg_severity" in data
```

### 2. **Service Layer Tests** (`tests/test_services.py`)
**Purpose**: Test business logic in services
**Coverage**:
- ✅ Calculation service (metrics, trends, analytics)
- ✅ HubSpot service (sync, transformations)
- ✅ Scheduler service (background operations)

**Example Test**:
```python
async def test_calculate_issue_metrics_with_data(self, db_session: AsyncSession):
    """Test metrics calculation with sample issues."""
    tenant_id = uuid.uuid4()
    calc_service = CalculationService(tenant_id)
    result = await calc_service.calculate_issue_metrics(time_range_days=30)
    assert result["total_issues"] == 2
    assert result["avg_severity"] == 4.0
```

### 3. **Database Model Tests** (`tests/test_models.py`)
**Purpose**: Test database models and relationships
**Coverage**:
- ✅ Issue model (CRUD operations, tenant isolation)
- ✅ TenantIntegration model (config storage, sync tracking)
- ✅ SyncEvent model (performance metrics, error tracking)

**Example Test**:
```python
async def test_issue_tenant_isolation(self, db_session: AsyncSession):
    """Test that issues are properly isolated by tenant."""
    tenant_1 = uuid.uuid4()
    tenant_2 = uuid.uuid4()
    # Create issues for different tenants
    # Verify isolation
```

## 🔧 Test Infrastructure

### Test Database
- **In-Memory SQLite**: Fast, isolated tests
- **Async Support**: Full async/await testing
- **Automatic Cleanup**: Each test gets fresh database

### Test Fixtures
```python
@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database session."""
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)

@pytest.fixture
def sample_tenant_id() -> str:
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())
```

### Mocking Strategy
- **External APIs**: Mock HubSpot/Jira API calls
- **Database**: Use test database with fixtures
- **Time**: Mock datetime for consistent testing

## 🎯 Testing Priorities

### Phase 1: Core Functionality (Start Here)
1. **Database Models**: Test CRUD operations
2. **API Endpoints**: Test all endpoints return correct responses
3. **Service Logic**: Test business calculations

### Phase 2: Integration Testing
1. **Multi-tenant Isolation**: Ensure tenant data separation
2. **Sync Operations**: Test background sync processes
3. **Error Handling**: Test failure scenarios

### Phase 3: Performance & Edge Cases
1. **Load Testing**: High-volume data processing
2. **Error Recovery**: Network failures, API limits
3. **Security Testing**: Input validation, authentication

## 🛠️ Testing Tools

### Automated Test Runner
```bash
# Run comprehensive test suite
python scripts/run_tests.py

# This script runs:
# - All unit and integration tests
# - Code quality checks (black, isort, flake8, mypy)
# - Coverage reporting
# - Performance metrics
```

### Manual Testing
```bash
# Start development server
poetry run uvicorn app.main:app --reload

# Test endpoints manually
curl http://localhost:8000/api/analytics/dashboard/test-tenant-id
curl http://localhost:8000/api/sync/status
```

## 📊 Test Coverage Goals

### Current Coverage Targets
- **API Endpoints**: 100% endpoint coverage
- **Service Layer**: 90% business logic coverage
- **Database Models**: 100% model coverage
- **Error Handling**: 80% error path coverage

### Coverage Commands
```bash
# Generate coverage report
python -m pytest tests/ --cov=app --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Coverage summary
python -m pytest tests/ --cov=app --cov-report=term-missing
```

## 🔍 Debugging Tests

### Common Issues
1. **Import Errors**: Ensure all dependencies installed
2. **Database Errors**: Check test database configuration
3. **Async Issues**: Use `@pytest.mark.asyncio` for async tests

### Debug Commands
```bash
# Run single test with verbose output
python -m pytest tests/test_models.py::TestIssueModel::test_issue_creation -v -s

# Run with debugger
python -m pytest tests/ --pdb

# Run with print statements
python -m pytest tests/ -s
```

## 🚀 Continuous Integration

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files

# Hooks include:
# - Code formatting (black)
# - Import sorting (isort)
# - Linting (flake8)
# - Type checking (mypy)
# - Custom line limit checks
```

### CI/CD Pipeline
```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    python -m pytest tests/ --cov=app --cov-report=xml
    python scripts/run_tests.py

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## 📈 Performance Testing

### Load Testing
```python
# Test sync performance
async def test_sync_performance():
    start_time = time.time()
    await hubspot_service.sync_incremental()
    duration = time.time() - start_time
    assert duration < 30  # Should complete within 30 seconds
```

### Memory Testing
```python
# Test memory usage with large datasets
async def test_memory_usage():
    # Create 1000 issues
    issues = [create_test_issue() for _ in range(1000)]
    # Verify memory usage doesn't exceed limits
```

## 🎯 Best Practices

### Test Organization
- **Arrange**: Set up test data
- **Act**: Execute the function being tested
- **Assert**: Verify the expected outcome

### Test Naming
```python
# Good test names
def test_create_user_with_valid_data_returns_user():
def test_create_user_with_invalid_email_raises_validation_error():
def test_sync_incremental_updates_existing_issues():
```

### Test Data
- **Use factories**: Create test data consistently
- **Isolate tests**: Each test should be independent
- **Clean up**: Remove test data after each test

## 🚨 Testing Checklist

### Before Running Tests
- [ ] All dependencies installed
- [ ] Test database configured
- [ ] Environment variables set
- [ ] Pre-commit hooks installed

### After Running Tests
- [ ] All tests pass
- [ ] Coverage meets targets
- [ ] No new warnings
- [ ] Performance benchmarks met

### Before Deploying
- [ ] Integration tests pass
- [ ] Load tests completed
- [ ] Security tests passed
- [ ] Documentation updated

---

**Remember**: Good tests are the foundation of reliable software. Start with the basics and build up to comprehensive coverage! 
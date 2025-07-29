# KillTheNoise Development Standards

This document outlines the enterprise-level coding standards and architectural patterns used in the KillTheNoise backend project.

## 🚀 Quick Start

### Setup Development Environment
```bash
# Install pre-commit hooks and development tools
python scripts/setup_dev_environment.py

# Run pre-commit on all files
pre-commit run --all-files

# Run tests
python -m pytest tests/
```

## 📏 Code Quality Standards

### Line Limits
- **Files**: Maximum 200 lines
- **Functions**: Maximum 50 lines  
- **Classes**: Maximum 150 lines
- **Methods**: Maximum 50 lines

### Style Guidelines
- Follow PEP 8 strictly
- Use Black for code formatting (88 character line length)
- Use isort for import sorting
- Use type hints for all functions and variables
- Use f-strings for string formatting

## 🏗️ Architectural Patterns

### Service Layer Pattern
Business logic should be in service classes, not in API endpoints:

```python
# ✅ Good
class UserService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_user(self, user_data: UserCreate) -> User:
        # Business logic here
        pass

# ❌ Bad
@router.post("/users")
async def create_user(user_data: dict):
    # Don't put business logic here
    pass
```

### Repository Pattern
Data access should be abstracted through repository classes:

```python
# ✅ Good
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        # Data access logic here
        pass
```

### Dependency Injection
Use FastAPI's dependency injection system:

```python
# ✅ Good
async def get_user_service() -> UserService:
    session = await get_db()
    return UserService(session)

@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user(user_id)
```

## 🗄️ Database Standards

### Model Design
- Use SQLAlchemy declarative base
- Include `__tablename__` for all models
- Use appropriate column types and constraints
- Add indexes for frequently queried columns
- Include audit fields (created_at, updated_at)

### Migration Strategy
- Use Alembic for database migrations
- Version control all schema changes
- Test migrations on staging before production
- Include rollback strategies

## 🔌 API Design Standards

### RESTful Endpoints
- Use proper HTTP methods (GET, POST, PUT, DELETE)
- Return appropriate HTTP status codes
- Use consistent URL patterns
- Implement proper pagination for list endpoints

### Response Format
```python
# ✅ Good: Consistent response format
{
    "success": True,
    "data": {...},
    "message": "Operation completed successfully"
}
```

### Validation
- Use Pydantic for request/response validation
- Implement comprehensive input validation
- Return detailed error messages for validation failures

## ⚡ Async Programming Standards

### Async/Await Patterns
- Use `async def` for all I/O operations
- Use `await` for all async calls
- Don't mix sync and async code
- Use `asyncio.gather()` for concurrent operations

### Database Operations
- Use async SQLAlchemy
- Implement proper connection pooling
- Use transactions for multi-step operations
- Handle database errors gracefully

## 🧪 Testing Standards

### Test Structure
- Unit tests for all business logic
- Integration tests for API endpoints
- Use pytest for testing framework
- Mock external dependencies

### Test Naming
```python
# ✅ Good: Descriptive test names
def test_create_user_with_valid_data_returns_user():
    pass

def test_create_user_with_invalid_email_raises_validation_error():
    pass
```

## 🔒 Security Standards

### Authentication & Authorization
- Implement proper JWT token handling
- Use role-based access control (RBAC)
- Validate all user inputs
- Implement rate limiting

### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement proper session management
- Log security events

## 📊 Performance Standards

### Database Optimization
- Use database indexes appropriately
- Implement query optimization
- Use connection pooling
- Monitor query performance

### Caching Strategy
- Implement Redis for caching
- Cache frequently accessed data
- Use appropriate cache invalidation
- Monitor cache hit rates

## 📝 Logging Standards

### Log Levels
- **ERROR**: System errors that need immediate attention
- **WARN**: Unexpected situations that don't break functionality
- **INFO**: General application flow
- **DEBUG**: Detailed information for debugging

### Log Format
```python
# ✅ Good: Structured logging
logger.info("User created", extra={
    "user_id": str(user.id),
    "email": user.email,
    "tenant_id": str(user.tenant_id)
})
```

## 🔍 Monitoring & Observability

### Metrics
- Track API response times
- Monitor database query performance
- Track error rates
- Monitor resource usage

### Health Checks
- Implement `/health` endpoint
- Check database connectivity
- Monitor external service dependencies
- Track application uptime

## 🚀 Deployment Standards

### Environment Configuration
- Use environment variables for configuration
- Implement different configs for dev/staging/prod
- Use secrets management for sensitive data
- Implement proper logging configuration

### Container Standards
- Use multi-stage Docker builds
- Implement health checks in containers
- Use appropriate base images
- Implement proper resource limits

## 📋 Code Review Checklist

### Before Submitting
- [ ] Code follows PEP 8
- [ ] All functions under 50 lines
- [ ] All files under 200 lines
- [ ] Type hints included
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Logging added where appropriate

### Review Criteria
- [ ] Architecture patterns followed
- [ ] Security considerations addressed
- [ ] Performance implications considered
- [ ] Error handling comprehensive
- [ ] Code is maintainable and readable
- [ ] Tests cover edge cases
- [ ] Documentation is clear and complete

## 🛠️ Development Tools

### Pre-commit Hooks
The project uses pre-commit hooks to automatically enforce standards:

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

### Code Quality Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning

### Testing Tools
- **pytest**: Testing framework
- **pytest-asyncio**: Async testing support
- **pytest-cov**: Coverage reporting

## 📚 Documentation Standards

### Code Documentation
- Use docstrings for all public functions and classes
- Follow Google docstring format
- Include type hints in docstrings
- Document exceptions and edge cases

### API Documentation
- Use FastAPI's automatic documentation
- Include example requests and responses
- Document error codes and messages
- Keep documentation up to date

## 🔄 CI/CD Standards

### Automated Checks
- Code formatting and linting
- Type checking
- Security scanning
- Test execution
- Coverage reporting

### Quality Gates
- All tests must pass
- Coverage must meet minimum threshold
- No security vulnerabilities
- Code review approval required

## 🚨 Exception Handling

### When to Break Rules
- Complex business logic that cannot be simplified
- Third-party integrations with specific requirements
- Performance-critical code that requires optimization
- Legacy code migration (temporary exceptions)

### Documentation Required
- Justify any exceptions in code comments
- Document architectural decisions (ADRs)
- Update team on any rule changes
- Maintain exception tracking and review process

## 📞 Getting Help

### Resources
- [Python Style Guide (PEP 8)](https://peps.python.org/pep-0008/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)

### Team Support
- Ask questions in team chat
- Schedule code review sessions
- Request architecture guidance
- Report issues promptly

---

**Remember**: These standards are designed to ensure code quality, maintainability, and team productivity. When in doubt, prioritize readability and maintainability over cleverness. 
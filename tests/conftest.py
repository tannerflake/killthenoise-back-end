from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app

# Test database URL (use test Supabase database)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

# Create test session factory
TestingSessionLocal = sessionmaker(
    test_engine, expire_on_commit=False, class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_setup() -> AsyncGenerator[None, None]:
    """Set up test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_db_setup) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database session."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant_id() -> str:
    """Generate a sample tenant ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_integration_id() -> str:
    """Generate a sample integration ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_hubspot_service() -> AsyncMock:
    """Create a mock HubSpot service for testing."""
    mock_service = AsyncMock()
    mock_service.status.return_value = True
    mock_service.sync_incremental.return_value = {
        "success": True,
        "processed": 5,
        "updated": 3,
        "duration_seconds": 2,
    }
    return mock_service


@pytest.fixture
def sample_issue_data() -> dict:
    """Sample issue data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "title": "Test Issue",
        "description": "This is a test issue",
        "source": "hubspot",
        "severity": 3,
        "frequency": None,
        "status": "open",
        "type": "bug",
        "tags": "medium",
        "jira_issue_key": None,
        "hubspot_ticket_id": "12345",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_tenant_integration_data() -> dict:
    """Sample tenant integration data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "integration_type": "hubspot",
        "is_active": True,
        "config": {"access_token": "test_token", "domain": "test.hubapi.com"},
        "last_synced_at": "2024-01-01T00:00:00Z",
        "last_sync_status": "success",
        "sync_error_message": None,
        "webhook_url": "https://test.com/webhooks/hubspot",
        "webhook_secret": "test_secret",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient


class TestAnalyticsEndpoints:
    """Test analytics API endpoints."""

    def test_get_issue_metrics(self, client: TestClient, sample_tenant_id: str):
        """Test getting issue metrics for a tenant."""
        response = client.get(f"/api/analytics/metrics/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "total_issues" in data
        assert "avg_severity" in data
        assert "status_distribution" in data

    def test_get_source_comparison(self, client: TestClient, sample_tenant_id: str):
        """Test getting source comparison data."""
        response = client.get(f"/api/analytics/source-comparison/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert "total_issues" in data

    def test_get_trends(self, client: TestClient, sample_tenant_id: str):
        """Test getting trend data."""
        response = client.get(f"/api/analytics/trends/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        assert "total_days" in data

    def test_get_severity_distribution(self, client: TestClient, sample_tenant_id: str):
        """Test getting severity distribution."""
        response = client.get(
            f"/api/analytics/severity-distribution/{sample_tenant_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "distribution" in data
        assert "total" in data

    def test_get_status_distribution(self, client: TestClient, sample_tenant_id: str):
        """Test getting status distribution."""
        response = client.get(f"/api/analytics/status-distribution/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "distribution" in data
        assert "total" in data

    def test_get_top_issues(self, client: TestClient, sample_tenant_id: str):
        """Test getting top issues."""
        response = client.get(f"/api/analytics/top-issues/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_change_velocity(self, client: TestClient, sample_tenant_id: str):
        """Test getting change velocity metrics."""
        response = client.get(f"/api/analytics/change-velocity/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "creation_rate" in data
        assert "resolution_rate" in data

    def test_get_dashboard_data(self, client: TestClient, sample_tenant_id: str):
        """Test getting comprehensive dashboard data."""
        response = client.get(f"/api/analytics/dashboard/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "source_comparison" in data
        assert "trends" in data
        assert "severity_distribution" in data
        assert "status_distribution" in data
        assert "top_issues" in data
        assert "change_velocity" in data


class TestSyncEndpoints:
    """Test sync management endpoints."""

    def test_get_sync_status(self, client: TestClient):
        """Test getting sync status."""
        response = client.get("/api/sync/status")
        assert response.status_code == 200
        data = response.json()
        assert "running_tasks" in data
        assert "integrations" in data

    def test_get_sync_status_with_tenant(
        self, client: TestClient, sample_tenant_id: str
    ):
        """Test getting sync status for specific tenant."""
        response = client.get(f"/api/sync/status?tenant_id={sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "running_tasks" in data
        assert "integrations" in data

    def test_trigger_sync(self, client: TestClient, sample_tenant_id: str):
        """Test triggering a manual sync."""
        sync_data = {
            "tenant_id": sample_tenant_id,
            "integration_type": "hubspot",
            "sync_type": "incremental",
        }
        response = client.post("/api/sync/trigger", json=sync_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    def test_get_sync_metrics(self, client: TestClient, sample_tenant_id: str):
        """Test getting sync performance metrics."""
        response = client.get(f"/api/sync/metrics/{sample_tenant_id}")
        assert response.status_code == 200
        data = response.json()
        assert "total_syncs" in data
        assert "success_rate" in data

    def test_start_scheduler(self, client: TestClient):
        """Test starting the scheduler."""
        response = client.post("/api/sync/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_scheduler(self, client: TestClient):
        """Test stopping the scheduler."""
        response = client.post("/api/sync/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWebhookEndpoints:
    """Test webhook endpoints."""

    def test_hubspot_webhook(self, client: TestClient, sample_tenant_id: str):
        """Test HubSpot webhook endpoint."""
        webhook_data = {
            "subscriptionType": "ticket.propertyChange",
            "objectId": "12345",
            "propertyName": "hs_ticket_priority",
            "propertyValue": "high",
        }
        response = client.post(
            f"/api/webhooks/hubspot/{sample_tenant_id}", json=webhook_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_jira_webhook(self, client: TestClient, sample_tenant_id: str):
        """Test Jira webhook endpoint."""
        webhook_data = {
            "issue": {
                "id": "12345",
                "key": "TEST-123",
                "fields": {"summary": "Test Issue", "priority": "High"},
            }
        }
        response = client.post(
            f"/api/webhooks/jira/{sample_tenant_id}", json=webhook_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_webhook_health(self, client: TestClient):
        """Test webhook health endpoint."""
        response = client.get("/api/webhooks/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "endpoints" in data


class TestIssuesEndpoints:
    """Test issues endpoints."""

    def test_get_top_issues(self, client: TestClient):
        """Test getting top issues."""
        response = client.get("/api/issues/top")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "count" in data

    def test_list_issues(self, client: TestClient):
        """Test listing issues."""
        response = client.get("/api/issues/")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "count" in data

    def test_list_issues_with_source_filter(self, client: TestClient):
        """Test listing issues with source filter."""
        response = client.get("/api/issues/?source=hubspot")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data

    def test_list_issues_with_limit(self, client: TestClient):
        """Test listing issues with limit parameter."""
        response = client.get("/api/issues/?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data


class TestHubSpotEndpoints:
    """Test HubSpot integration endpoints."""

    def test_hubspot_status(self, client: TestClient):
        """Test HubSpot connection status."""
        response = client.get("/api/hubspot/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data

    def test_hubspot_sync(self, client: TestClient):
        """Test triggering HubSpot sync."""
        response = client.post("/api/hubspot/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestIntegrationsEndpoints:
    """Test general integrations endpoints."""

    def test_integrations_test(self, client: TestClient):
        """Test integrations health check."""
        response = client.post("/api/integrations/test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestJiraEndpoints:
    """Test Jira integration endpoints."""

    def test_jira_match_all(self, client: TestClient):
        """Test Jira issue matching."""
        response = client.post("/api/jira/match-all")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "matched" in data

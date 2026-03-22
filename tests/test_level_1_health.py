"""
LEVEL 1: Health Check & Basic Connectivity Tests
These tests verify that the API is running and accessible.
"""
import pytest
from httpx import AsyncClient


class TestLevel1Health:
    """Basic health and connectivity tests"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns service information"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["version"] == "2.0.0"
        print(f"✓ Root endpoint: {data}")

    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: AsyncClient):
        """Test liveness probe endpoint"""
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "mocktest-auth"
        print(f"✓ Liveness probe: {data}")

    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: AsyncClient):
        """Test readiness probe endpoint"""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        print(f"✓ Readiness probe: {data}")

    @pytest.mark.asyncio
    async def test_openapi_schema(self, client: AsyncClient):
        """Test OpenAPI schema is accessible"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        print(f"✓ OpenAPI schema version: {data['openapi']}")

    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client: AsyncClient):
        """Test API documentation is accessible"""
        response = await client.get("/docs")
        assert response.status_code == 200
        print("✓ API documentation accessible")

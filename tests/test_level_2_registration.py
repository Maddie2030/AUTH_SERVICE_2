"""
LEVEL 2: User Registration Tests
These tests verify user registration functionality for students and teachers.
"""
import pytest
from httpx import AsyncClient


class TestLevel2Registration:
    """User registration tests"""

    @pytest.mark.asyncio
    async def test_register_student_success(self, client: AsyncClient):
        """Test successful student registration"""
        payload = {
            "mobile_number": "+1234567890",
            "password": "Test@123456",
            "full_name": "John Doe",
            "role": "student"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert "access_token" in data
        assert "refresh_token" in data
        assert "session_id" in data
        assert data["user"]["mobile_number"] == payload["mobile_number"]
        assert data["user"]["role"] == "student"
        assert data["user"]["status"] == "active"

        print(f"✓ Student registered: {data['user']['id']}")
        print(f"  Access token: {data['access_token'][:20]}...")
        print(f"  Session ID: {data['session_id']}")

    @pytest.mark.asyncio
    async def test_register_teacher_success(self, client: AsyncClient):
        """Test successful teacher registration"""
        payload = {
            "mobile_number": "+9876543210",
            "password": "Secure@Pass123",
            "full_name": "Jane Teacher",
            "role": "teacher"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()

        assert data["user"]["role"] == "teacher"
        print(f"✓ Teacher registered: {data['user']['id']}")

    @pytest.mark.asyncio
    async def test_register_duplicate_mobile(self, client: AsyncClient):
        """Test registration fails with duplicate mobile number"""
        payload = {
            "mobile_number": "+1111111111",
            "password": "Test@123456",
            "full_name": "First User",
            "role": "student"
        }

        response1 = await client.post("/api/v1/auth/register", json=payload)
        assert response1.status_code == 201

        response2 = await client.post("/api/v1/auth/register", json=payload)
        assert response2.status_code == 409
        error = response2.json()
        assert error["error"]["code"] == "AUTH_001"
        print(f"✓ Duplicate mobile rejected: {error['error']['message']}")

    @pytest.mark.asyncio
    async def test_register_invalid_password(self, client: AsyncClient):
        """Test registration fails with weak password"""
        payload = {
            "mobile_number": "+2222222222",
            "password": "weak",
            "full_name": "Test User",
            "role": "student"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422
        print(f"✓ Weak password rejected")

    @pytest.mark.asyncio
    async def test_register_invalid_mobile(self, client: AsyncClient):
        """Test registration fails with invalid mobile number"""
        payload = {
            "mobile_number": "invalid",
            "password": "Test@123456",
            "full_name": "Test User",
            "role": "student"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422
        print(f"✓ Invalid mobile rejected")

    @pytest.mark.asyncio
    async def test_register_admin_role_rejected(self, client: AsyncClient):
        """Test registration fails when trying to register as admin"""
        payload = {
            "mobile_number": "+3333333333",
            "password": "Test@123456",
            "full_name": "Test Admin",
            "role": "admin"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422
        print(f"✓ Admin role registration blocked")

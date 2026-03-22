"""
LEVEL 3: Authentication & Login Tests
These tests verify login, logout, and token management.
"""
import pytest
from httpx import AsyncClient


class TestLevel3Authentication:
    """Authentication flow tests"""

    async def _create_user(self, client: AsyncClient, mobile: str, role: str = "student"):
        """Helper to create a test user"""
        payload = {
            "mobile_number": mobile,
            "password": "Test@123456",
            "full_name": "Test User",
            "role": role
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        return response.json()

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Test successful login"""
        mobile = "+1234567890"
        await self._create_user(client, mobile)

        login_payload = {
            "mobile_number": mobile,
            "password": "Test@123456"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["mobile_number"] == mobile
        print(f"✓ Login successful for: {mobile}")
        print(f"  Session ID: {data['session_id']}")

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login fails with wrong password"""
        mobile = "+1111111111"
        await self._create_user(client, mobile)

        login_payload = {
            "mobile_number": mobile,
            "password": "WrongPassword@123"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 401
        error = response.json()
        assert error["error"]["code"] == "AUTH_010"
        print(f"✓ Invalid credentials rejected")

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for non-existent user"""
        login_payload = {
            "mobile_number": "+9999999999",
            "password": "Test@123456"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 401
        print(f"✓ Non-existent user login rejected")

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user profile"""
        mobile = "+2222222222"
        reg_data = await self._create_user(client, mobile)

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["mobile_number"] == mobile
        assert "id" in data
        print(f"✓ User profile retrieved: {data['id']}")

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test accessing protected endpoint without token"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
        print(f"✓ Unauthorized access blocked")

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        """Test logout functionality"""
        mobile = "+3333333333"
        reg_data = await self._create_user(client, mobile)

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        response = await client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 204

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        print(f"✓ Logout successful, token invalidated")

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient):
        """Test token refresh functionality"""
        mobile = "+4444444444"
        reg_data = await self._create_user(client, mobile)

        refresh_payload = {"refresh_token": reg_data["refresh_token"]}
        response = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != reg_data["access_token"]
        print(f"✓ Token refreshed successfully")

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        """Test refresh fails with invalid token"""
        refresh_payload = {"refresh_token": "invalid_token_here"}
        response = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert response.status_code == 401
        print(f"✓ Invalid refresh token rejected")

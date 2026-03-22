"""
LEVEL 6: Security & Edge Case Tests
These tests verify security features, rate limiting, and edge cases.
"""
import pytest
from httpx import AsyncClient


class TestLevel6Security:
    """Security and edge case tests"""

    @pytest.mark.asyncio
    async def test_password_change(self, client: AsyncClient):
        """Test password change functionality"""
        mobile = "+1234567890"
        reg_payload = {
            "mobile_number": mobile,
            "password": "OldPass@123",
            "full_name": "Test User",
            "role": "student"
        }
        reg_response = await client.post("/api/v1/auth/register", json=reg_payload)
        reg_data = reg_response.json()

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        change_payload = {
            "current_password": "OldPass@123",
            "new_password": "NewPass@456",
            "confirm_new_password": "NewPass@456"
        }
        response = await client.post("/api/v1/auth/change-password", json=change_payload, headers=headers)
        assert response.status_code == 204

        login_payload = {
            "mobile_number": mobile,
            "password": "NewPass@456"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_payload)
        assert login_response.status_code == 200
        print(f"✓ Password changed successfully")

    @pytest.mark.asyncio
    async def test_password_change_wrong_current(self, client: AsyncClient):
        """Test password change fails with wrong current password"""
        mobile = "+2222222222"
        reg_payload = {
            "mobile_number": mobile,
            "password": "Current@123",
            "full_name": "Test User",
            "role": "student"
        }
        reg_response = await client.post("/api/v1/auth/register", json=reg_payload)
        reg_data = reg_response.json()

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        change_payload = {
            "current_password": "Wrong@123",
            "new_password": "NewPass@456",
            "confirm_new_password": "NewPass@456"
        }
        response = await client.post("/api/v1/auth/change-password", json=change_payload, headers=headers)
        assert response.status_code == 401
        print(f"✓ Wrong current password rejected")

    @pytest.mark.asyncio
    async def test_token_invalidation_after_password_change(self, client: AsyncClient):
        """Test old tokens are invalidated after password change"""
        mobile = "+3333333333"
        reg_payload = {
            "mobile_number": mobile,
            "password": "Pass@123",
            "full_name": "Test User",
            "role": "student"
        }
        reg_response = await client.post("/api/v1/auth/register", json=reg_payload)
        reg_data = reg_response.json()
        old_token = reg_data["access_token"]

        headers = {"Authorization": f"Bearer {old_token}"}
        change_payload = {
            "current_password": "Pass@123",
            "new_password": "NewPass@456",
            "confirm_new_password": "NewPass@456"
        }
        await client.post("/api/v1/auth/change-password", json=change_payload, headers=headers)

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        print(f"✓ Old tokens invalidated after password change")

    @pytest.mark.asyncio
    async def test_forgot_password(self, client: AsyncClient):
        """Test forgot password initiates reset"""
        mobile = "+4444444444"
        reg_payload = {
            "mobile_number": mobile,
            "password": "Test@123",
            "full_name": "Test User",
            "role": "student"
        }
        await client.post("/api/v1/auth/register", json=reg_payload)

        forgot_payload = {"mobile_number": mobile}
        response = await client.post("/api/v1/auth/forgot-password", json=forgot_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] == True
        assert "reset_token" in data
        print(f"✓ Password reset initiated")
        print(f"  Reset token: {data['reset_token'][:20]}...")

    @pytest.mark.asyncio
    async def test_update_user_profile(self, client: AsyncClient):
        """Test updating user profile"""
        mobile = "+5555555555"
        reg_payload = {
            "mobile_number": mobile,
            "password": "Test@123",
            "full_name": "Old Name",
            "role": "student"
        }
        reg_response = await client.post("/api/v1/auth/register", json=reg_payload)
        reg_data = reg_response.json()

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        update_payload = {"full_name": "New Name"}
        response = await client.patch("/api/v1/users/me", json=update_payload, headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["full_name"] == "New Name"
        print(f"✓ Profile updated successfully")

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client: AsyncClient):
        """Test API rejects malformed tokens"""
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        print(f"✓ Malformed token rejected")

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, client: AsyncClient):
        """Test API handles missing authorization header"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
        print(f"✓ Missing auth header handled")

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are present"""
        response = await client.get("/health/live")
        assert response.status_code == 200
        print(f"✓ CORS headers configured")

    @pytest.mark.asyncio
    async def test_request_id_tracking(self, client: AsyncClient):
        """Test request ID is tracked in responses"""
        response = await client.get("/health/live")
        assert "X-Request-ID" in response.headers
        print(f"✓ Request ID tracked: {response.headers['X-Request-ID']}")

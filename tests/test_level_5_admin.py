"""
LEVEL 5: Admin Operations Tests
These tests verify admin invitation, user management, and permission controls.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import hash_password
from app.core.constants import UserRole, UserStatus


class TestLevel5Admin:
    """Admin operations tests"""

    async def _create_admin(self, db_session: AsyncSession):
        """Helper to create an admin user"""
        admin = User(
            mobile_number="+9999999999",
            full_name="Admin User",
            hashed_password=hash_password("Admin@123456"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)
        return admin

    async def _login_admin(self, client: AsyncClient):
        """Helper to login as admin"""
        login_payload = {
            "mobile_number": "+9999999999",
            "password": "Admin@123456"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        return response.json()

    @pytest.mark.asyncio
    async def test_invite_admin(self, client: AsyncClient, db_session: AsyncSession):
        """Test admin invitation creation"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        invite_payload = {
            "mobile_number": "+1111111111",
            "full_name": "New Admin"
        }
        response = await client.post("/api/v1/admin/invite", json=invite_payload, headers=headers)
        assert response.status_code == 201
        data = response.json()

        assert "token" in data
        assert data["is_accepted"] == False
        print(f"✓ Admin invitation created")
        print(f"  Token: {data['token'][:20]}...")
        return data["token"]

    @pytest.mark.asyncio
    async def test_list_invitations(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing admin invitations"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}

        invite_payload = {
            "mobile_number": "+2222222222",
            "full_name": "Invited Admin"
        }
        await client.post("/api/v1/admin/invite", json=invite_payload, headers=headers)

        response = await client.get("/api/v1/admin/invitations", headers=headers)
        assert response.status_code == 200
        invitations = response.json()

        assert isinstance(invitations, list)
        assert len(invitations) >= 1
        print(f"✓ Invitations listed: {len(invitations)}")

    @pytest.mark.asyncio
    async def test_accept_invitation(self, client: AsyncClient, db_session: AsyncSession):
        """Test accepting admin invitation"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        invite_payload = {
            "mobile_number": "+3333333333",
            "full_name": "New Admin"
        }
        invite_response = await client.post("/api/v1/admin/invite", json=invite_payload, headers=headers)
        token = invite_response.json()["token"]

        accept_payload = {
            "token": token,
            "password": "NewAdmin@123",
            "confirm_password": "NewAdmin@123"
        }
        response = await client.post("/api/v1/admin/accept-invite", json=accept_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["user"]["role"] == "admin"
        assert data["user"]["status"] == "active"
        assert "access_token" in data
        print(f"✓ Admin invitation accepted")
        print(f"  New admin ID: {data['user']['id']}")

    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing all users"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        response = await client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        print(f"✓ Users listed: {data['total']} total users")

    @pytest.mark.asyncio
    async def test_non_admin_cannot_invite(self, client: AsyncClient):
        """Test that non-admin users cannot create invitations"""
        reg_payload = {
            "mobile_number": "+8888888888",
            "password": "Test@123456",
            "full_name": "Regular User",
            "role": "student"
        }
        reg_response = await client.post("/api/v1/auth/register", json=reg_payload)
        reg_data = reg_response.json()

        headers = {"Authorization": f"Bearer {reg_data['access_token']}"}
        invite_payload = {
            "mobile_number": "+7777777777",
            "full_name": "Unauthorized Invite"
        }
        response = await client.post("/api/v1/admin/invite", json=invite_payload, headers=headers)
        assert response.status_code == 403
        print(f"✓ Non-admin invitation blocked")

    @pytest.mark.asyncio
    async def test_lock_user_account(self, client: AsyncClient, db_session: AsyncSession):
        """Test admin can lock user accounts"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        student_reg = {
            "mobile_number": "+5555555555",
            "password": "Test@123456",
            "full_name": "Student User",
            "role": "student"
        }
        student_response = await client.post("/api/v1/auth/register", json=student_reg)
        student_id = student_response.json()["user"]["id"]

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        response = await client.post(f"/api/v1/admin/users/{student_id}/lock", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "locked"
        print(f"✓ User account locked: {student_id}")

    @pytest.mark.asyncio
    async def test_unlock_user_account(self, client: AsyncClient, db_session: AsyncSession):
        """Test admin can unlock user accounts"""
        await self._create_admin(db_session)
        login_data = await self._login_admin(client)

        student_reg = {
            "mobile_number": "+6666666666",
            "password": "Test@123456",
            "full_name": "Student User",
            "role": "student"
        }
        student_response = await client.post("/api/v1/auth/register", json=student_reg)
        student_id = student_response.json()["user"]["id"]

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        await client.post(f"/api/v1/admin/users/{student_id}/lock", headers=headers)

        response = await client.post(f"/api/v1/admin/users/{student_id}/unlock", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "active"
        print(f"✓ User account unlocked: {student_id}")

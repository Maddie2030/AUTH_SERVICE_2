"""
LEVEL 4: Session Management Tests
These tests verify session listing, exam sessions, and multi-device handling.
"""
import pytest
from httpx import AsyncClient


class TestLevel4Sessions:
    """Session management tests"""

    async def _create_and_login(self, client: AsyncClient, mobile: str):
        """Helper to create and login a user"""
        reg_payload = {
            "mobile_number": mobile,
            "password": "Test@123456",
            "full_name": "Test User",
            "role": "student"
        }
        await client.post("/api/v1/auth/register", json=reg_payload)

        login_payload = {
            "mobile_number": mobile,
            "password": "Test@123456"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        return response.json()

    @pytest.mark.asyncio
    async def test_list_sessions(self, client: AsyncClient):
        """Test listing active sessions"""
        mobile = "+1234567890"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        response = await client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == 200
        sessions = response.json()

        assert isinstance(sessions, list)
        assert len(sessions) >= 1
        print(f"✓ Sessions listed: {len(sessions)} active session(s)")

    @pytest.mark.asyncio
    async def test_get_current_session(self, client: AsyncClient):
        """Test getting current session details"""
        mobile = "+2222222222"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        response = await client.get("/api/v1/sessions/current", headers=headers)
        assert response.status_code == 200
        session = response.json()

        assert session["id"] == str(login_data["session_id"])
        assert session["is_active"] == True
        assert session["is_exam_active"] == False
        print(f"✓ Current session retrieved: {session['id']}")

    @pytest.mark.asyncio
    async def test_start_exam_session(self, client: AsyncClient):
        """Test starting an exam session"""
        mobile = "+3333333333"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        exam_payload = {"exam_id": "EXAM_001"}
        response = await client.post("/api/v1/sessions/exam/start", json=exam_payload, headers=headers)
        assert response.status_code == 200
        session = response.json()

        assert session["is_exam_active"] == True
        assert session["exam_id"] == "EXAM_001"
        assert "exam_started_at" in session
        print(f"✓ Exam session started: {session['exam_id']}")

    @pytest.mark.asyncio
    async def test_end_exam_session(self, client: AsyncClient):
        """Test ending an exam session"""
        mobile = "+4444444444"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}

        start_payload = {"exam_id": "EXAM_002"}
        await client.post("/api/v1/sessions/exam/start", json=start_payload, headers=headers)

        end_payload = {"exam_id": "EXAM_002", "reason": "submitted"}
        response = await client.post("/api/v1/sessions/exam/end", json=end_payload, headers=headers)
        assert response.status_code == 200
        session = response.json()

        assert session["is_exam_active"] == False
        assert session["exam_id"] == None
        print(f"✓ Exam session ended")

    @pytest.mark.asyncio
    async def test_prevent_multiple_exam_sessions(self, client: AsyncClient):
        """Test that only one exam session can be active"""
        mobile = "+5555555555"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}

        payload1 = {"exam_id": "EXAM_003"}
        response1 = await client.post("/api/v1/sessions/exam/start", json=payload1, headers=headers)
        assert response1.status_code == 200

        payload2 = {"exam_id": "EXAM_004"}
        response2 = await client.post("/api/v1/sessions/exam/start", json=payload2, headers=headers)
        assert response2.status_code == 409
        error = response2.json()
        assert error["error"]["code"] == "AUTH_051"
        print(f"✓ Multiple exam sessions prevented")

    @pytest.mark.asyncio
    async def test_terminate_session(self, client: AsyncClient):
        """Test terminating a specific session"""
        mobile = "+6666666666"
        login_data = await self._create_and_login(client, mobile)

        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        session_id = login_data["session_id"]

        response = await client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
        assert response.status_code == 204

        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        print(f"✓ Session terminated successfully")

    @pytest.mark.asyncio
    async def test_logout_all_devices(self, client: AsyncClient):
        """Test logging out from all devices"""
        mobile = "+7777777777"
        login_data1 = await self._create_and_login(client, mobile)
        login_data2 = await self._create_and_login(client, mobile)

        headers1 = {"Authorization": f"Bearer {login_data1['access_token']}"}
        headers2 = {"Authorization": f"Bearer {login_data2['access_token']}"}

        response = await client.post("/api/v1/auth/logout-all", headers=headers1)
        assert response.status_code == 204

        response1 = await client.get("/api/v1/users/me", headers=headers1)
        response2 = await client.get("/api/v1/users/me", headers=headers2)
        assert response1.status_code == 401
        assert response2.status_code == 401
        print(f"✓ All sessions terminated")

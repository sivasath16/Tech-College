from app.core.security import create_access_token
from tests.conftest import PASSWORD, auth, login, register_recruiter, register_student, student_payload, verify_mobile


def test_student_register_requires_otp(client):
    res = client.post("/api/v1/auth/register/student", json=student_payload())
    assert res.status_code == 400
    assert "OTP" in res.json()["detail"]


def test_otp_wrong_code_rejected(client):
    client.post("/api/v1/auth/otp/send", json={"mobile": "9876543210"})
    res = client.post("/api/v1/auth/otp/verify", json={"mobile": "9876543210", "code": "000000"})
    assert res.status_code == 400


def test_otp_locks_after_max_attempts(client):
    otp = client.post("/api/v1/auth/otp/send", json={"mobile": "9876543210"}).json()["dev_otp"]
    wrong = "000000" if otp != "000000" else "111111"
    for _ in range(5):
        client.post("/api/v1/auth/otp/verify", json={"mobile": "9876543210", "code": wrong})
    res = client.post("/api/v1/auth/otp/verify", json={"mobile": "9876543210", "code": otp})
    assert res.status_code == 429


def test_student_register_and_login(client):
    res = register_student(client)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "STUDENT"
    assert body["student"]["college_id"] == "CS2026001"
    assert "password" not in res.text
    token = login(client, "asha@college.edu")
    assert token.status_code == 200 and token.json()["role"] == "STUDENT"
    me = client.get("/api/v1/auth/me", headers=auth(client, "asha@college.edu"))
    assert me.json()["student"]["degree_cgpa"] == 8.4


def test_student_otp_cannot_be_reused(client):
    assert register_student(client).status_code == 201
    res = client.post("/api/v1/auth/register/student",
                      json=student_payload(email="other@college.edu", college_id="CS2026002"))
    assert res.status_code == 400


def test_duplicate_email_and_college_id(client):
    register_student(client)
    verify_mobile(client)
    dup_email = client.post("/api/v1/auth/register/student", json=student_payload(college_id="CS2026009"))
    assert dup_email.status_code == 409
    verify_mobile(client)
    dup_id = client.post("/api/v1/auth/register/student", json=student_payload(email="new@college.edu"))
    assert dup_id.status_code == 409


def test_student_validation(client):
    verify_mobile(client)
    for bad in ({"password": "weak"}, {"mobile": "12345"}, {"degree_cgpa": 11}, {"email": "not-an-email"}):
        res = client.post("/api/v1/auth/register/student", json=student_payload(**bad))
        assert res.status_code == 422, bad


def test_login_wrong_password_and_unknown_user(client):
    register_student(client)
    assert login(client, "asha@college.edu", "WrongPass1").status_code == 401
    assert login(client, "nobody@college.edu").status_code == 401


def test_protected_endpoint_requires_valid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {create_access_token(9999, 'ADMIN')}"}
                      ).status_code == 401


def test_recruiter_register_pending_blocked_then_approved(client):
    res = register_recruiter(client)
    assert res.status_code == 201, res.text
    rid = res.json()["recruiter"]["id"]
    assert res.json()["recruiter"]["verification_status"] == "PENDING"

    blocked = login(client, "hr@acme.com")
    assert blocked.status_code == 403 and "pending" in blocked.json()["detail"]

    approve = client.post(f"/api/v1/admin/recruiters/{rid}/approve", headers=auth(client, "admin@college.edu", "Admin@12345"))
    assert approve.status_code == 200 and approve.json()["verification_status"] == "APPROVED"
    assert login(client, "hr@acme.com").status_code == 200


def test_recruiter_rejected_cannot_login(client):
    rid = register_recruiter(client).json()["recruiter"]["id"]
    admin = auth(client, "admin@college.edu", "Admin@12345")
    res = client.post(f"/api/v1/admin/recruiters/{rid}/reject", json={"reason": "Unverified company"}, headers=admin)
    assert res.status_code == 200
    blocked = login(client, "hr@acme.com")
    assert blocked.status_code == 403 and "Unverified company" in blocked.json()["detail"]
    again = client.post(f"/api/v1/admin/recruiters/{rid}/approve", headers=admin)
    assert again.status_code == 409


def test_recruiter_logo_validation(client):
    assert register_recruiter(client, ctype="application/pdf").status_code == 422
    assert register_recruiter(client, logo=b"not really a png", ctype="image/png").status_code == 422
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)
    assert register_recruiter(client, logo=big).status_code == 413
    assert register_recruiter(client, password="weak").status_code == 422
    assert register_recruiter(client, email="bad-email").status_code == 422
    assert register_recruiter(client, phone="123").status_code == 422

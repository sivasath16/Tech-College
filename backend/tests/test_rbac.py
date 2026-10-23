from tests.conftest import auth, register_recruiter, register_student


def _approved_recruiter(client):
    rid = register_recruiter(client).json()["recruiter"]["id"]
    client.post(f"/api/v1/admin/recruiters/{rid}/approve", headers=auth(client, "admin@college.edu", "Admin@12345"))
    return rid


def test_admin_endpoints_reject_anonymous(client):
    assert client.get("/api/v1/admin/recruiters").status_code == 401
    assert client.post("/api/v1/admin/recruiters/1/approve").status_code == 401


def test_student_and_recruiter_forbidden_from_admin(client):
    register_student(client)
    _approved_recruiter(client)
    for email in ("asha@college.edu", "hr@acme.com"):
        h = auth(client, email)
        assert client.get("/api/v1/admin/recruiters", headers=h).status_code == 403
        assert client.get("/api/v1/admin/students", headers=h).status_code == 403
        assert client.post("/api/v1/admin/recruiters/1/approve", headers=h).status_code == 403
        assert client.post("/api/v1/announcements", json={"title": "Hello", "body": "World"}, headers=h
                           ).status_code == 403


def test_admin_lists_and_filters(client):
    register_student(client)
    register_recruiter(client)
    admin = auth(client, "admin@college.edu", "Admin@12345")
    assert len(client.get("/api/v1/admin/recruiters", headers=admin).json()) == 1
    assert client.get("/api/v1/admin/recruiters?status_filter=APPROVED", headers=admin).json() == []
    students = client.get("/api/v1/admin/students", headers=admin).json()
    assert students[0]["email"] == "asha@college.edu"


def test_approval_writes_audit_log(client):
    from app.core.database import SessionLocal
    from app.models import AuditLog

    _approved_recruiter(client)
    with SessionLocal() as db:
        logs = db.query(AuditLog).all()
    assert len(logs) == 1 and logs[0].action == "RECRUITER_APPROVED"


def test_unknown_recruiter_404(client):
    admin = auth(client, "admin@college.edu", "Admin@12345")
    assert client.post("/api/v1/admin/recruiters/999/approve", headers=admin).status_code == 404


def test_announcements_public_read_admin_write(client):
    admin = auth(client, "admin@college.edu", "Admin@12345")
    res = client.post("/api/v1/announcements", json={"title": "Drive", "body": "TCS drive on Monday"}, headers=admin)
    assert res.status_code == 201
    items = client.get("/api/v1/announcements").json()
    assert items[0]["title"] == "Drive"

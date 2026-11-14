from datetime import date, datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import Application, ApplicationStatus, AuditLog, Recruiter, Student
from tests.conftest import auth, register_recruiter, register_student
from tests.test_recruiter import JOB, _applied, _future, _job, _recruiter, _student

A = "/api/v1/admin"
ADMIN = ("admin@college.edu", "Admin@12345")


def _admin(client):
    return auth(client, *ADMIN)


def _student_id(email="asha@college.edu"):
    with SessionLocal() as db:
        return db.query(Student).filter(Student.user.has(email=email)).one().id


def _drive(**over):
    return {"title": "Acme Campus Drive", "company_name": "Acme Corp", "description": "Written test and two interviews.",
            "venue": "Main Auditorium", "drive_date": _future(5), "min_cgpa": 7, "departments": ["Computer Science"], **over}


def _actions():
    with SessionLocal() as db:
        return [a.action for a in db.query(AuditLog).order_by(AuditLog.id)]


# ---------- access control ----------

ADMIN_GETS = ("summary", "students", "jobs", "drives", "announcements", "applications", "audit-logs", "recruiters")


def test_admin_endpoints_reject_anonymous_student_and_recruiter(client):
    s = _student(client)
    r = _recruiter(client)
    for path in ADMIN_GETS:
        assert client.get(f"{A}/{path}").status_code == 401, path
        assert client.get(f"{A}/{path}", headers=s).status_code == 403, path
        assert client.get(f"{A}/{path}", headers=r).status_code == 403, path
    for h in (s, r):
        assert client.post(f"{A}/jobs/1/approve", headers=h).status_code == 403
        assert client.post(f"{A}/drives", json=_drive(), headers=h).status_code == 403
        assert client.put(f"{A}/students/1/placement-status", json={"placement_status": "PLACED"}, headers=h).status_code == 403
        assert client.post(f"{A}/applications/1/confirm-placement", headers=h).status_code == 403


# ---------- summary ----------

def test_summary_counts(client):
    h = _recruiter(client)
    s = _student(client)
    jid = _job(client, h)
    _job(client, h, publish=False, title="Pending role")
    _applied(client, s, jid)
    body = client.get(f"{A}/summary", headers=_admin(client)).json()
    assert body["students"] == 1 and body["placed"] == 0 and body["placement_percent"] == 0
    assert body["recruiters_approved"] == 1 and body["recruiters_pending"] == 0
    assert body["jobs_published"] == 1 and body["jobs_pending"] == 1
    assert body["applications"] == 1 and body["applications_by_status"]["APPLIED"] == 1


# ---------- student database ----------

def _three_students(client):
    _student(client)
    _student(client, email="ben@college.edu", college_id="ME2026002", mobile="9876500002", full_name="Ben Joseph",
             department="Mechanical", degree_cgpa=6.8)
    _student(client, email="cara@college.edu", college_id="CS2026003", mobile="9876500003", full_name="Cara Das", degree_cgpa=9.2)


def test_student_search_filters(client):
    _three_students(client)
    ids = lambda **p: sorted(s["college_id"] for s in client.get(f"{A}/students", params=p, headers=_admin(client)).json())
    assert ids() == ["CS2026001", "CS2026003", "ME2026002"]
    assert ids(q="joseph") == ["ME2026002"]
    assert ids(q="cara@college") == ["CS2026003"]
    assert ids(department="mechanical") == ["ME2026002"]
    assert ids(min_cgpa=9) == ["CS2026003"]
    assert ids(placement_status="PLACED") == []
    assert ids(is_active=False) == []


def test_student_detail_with_applications_and_certificates(client):
    h = _recruiter(client)
    s = _student(client)
    _applied(client, s, _job(client, h))
    client.post("/api/v1/student/certificates", data={"title": "AWS CP"},
                files={"file": ("c.pdf", b"%PDF-1.4\n" + b"0" * 32, "application/pdf")}, headers=s)
    d = client.get(f"{A}/students/{_student_id()}", headers=_admin(client)).json()
    assert d["email"] == "asha@college.edu" and d["has_resume"] is True and d["is_active"] is True
    assert d["applications"][0]["job_title"] == "Backend Engineer" and d["applications"][0]["status"] == "APPLIED"
    assert [c["title"] for c in d["certificates"]] == ["AWS CP"]
    assert client.get(f"{A}/students/9999", headers=_admin(client)).status_code == 404


def test_admin_can_download_student_resume(client):
    _student(client)
    r = client.get(f"{A}/students/{_student_id()}/resume", headers=_admin(client))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    _student(client, resume=False, email="ben@college.edu", college_id="ME2026002", mobile="9876500002")
    assert client.get(f"{A}/students/{_student_id('ben@college.edu')}/resume", headers=_admin(client)).status_code == 404


def test_deactivate_student_blocks_login_and_token(client):
    h = _student(client)
    sid = _student_id()
    r = client.patch(f"{A}/students/{sid}/active", json={"is_active": False}, headers=_admin(client))
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get("/api/v1/student/profile", headers=h).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "asha@college.edu", "password": "Passw0rdOK"}).status_code == 403
    client.patch(f"{A}/students/{sid}/active", json={"is_active": True}, headers=_admin(client))
    assert client.get("/api/v1/student/profile", headers=auth(client, "asha@college.edu")).status_code == 200
    assert _actions() == ["STUDENT_DEACTIVATED", "STUDENT_ACTIVATED"]


def test_manual_placement_status_change_is_audited(client):
    _student(client)
    sid = _student_id()
    r = client.put(f"{A}/students/{sid}/placement-status", json={"placement_status": "PLACED"}, headers=_admin(client))
    assert r.json()["placement_status"] == "PLACED"
    assert client.put(f"{A}/students/{sid}/placement-status", json={"placement_status": "MAYBE"}, headers=_admin(client)).status_code == 422
    logs = client.get(f"{A}/audit-logs", headers=_admin(client)).json()
    assert logs[0]["action"] == "PLACEMENT_STATUS_CHANGED" and logs[0]["details"]["current"] == "PLACED"
    assert logs[0]["admin_email"] == "admin@college.edu"


# ---------- job verification and publishing ----------

def test_new_job_is_pending_and_hidden_until_approved(client):
    h = _recruiter(client)
    s = _student(client)
    jid = _job(client, h, publish=False)
    assert client.get("/api/v1/student/jobs", headers=s).json() == []
    assert client.post("/api/v1/student/applications", json={"job_id": jid}, headers=s).status_code == 404
    pending = client.get(f"{A}/jobs", params={"status_filter": "PENDING"}, headers=_admin(client)).json()
    assert [j["id"] for j in pending] == [jid] and pending[0]["company_name"] == "Acme Corp"
    ok = client.post(f"{A}/jobs/{jid}/approve", headers=_admin(client))
    assert ok.status_code == 200 and ok.json()["verification_status"] == "APPROVED"
    assert [j["id"] for j in client.get("/api/v1/student/jobs", headers=s).json()] == [jid]
    assert "JOB_APPROVED" in _actions()


def test_reject_job_needs_reason_and_recruiter_sees_it(client):
    h = _recruiter(client)
    jid = _job(client, h, publish=False)
    assert client.post(f"{A}/jobs/{jid}/reject", json={"reason": "no"}, headers=_admin(client)).status_code == 422
    r = client.post(f"{A}/jobs/{jid}/reject", json={"reason": "Salary missing from posting"}, headers=_admin(client))
    assert r.status_code == 200 and r.json()["verification_status"] == "REJECTED"
    mine = client.get(f"/api/v1/recruiter/jobs/{jid}", headers=h).json()
    assert mine["verification_status"] == "REJECTED" and mine["rejection_reason"] == "Salary missing from posting"


def test_job_decision_only_once_and_404(client):
    h = _recruiter(client)
    jid = _job(client, h, publish=False)
    client.post(f"{A}/jobs/{jid}/approve", headers=_admin(client))
    assert client.post(f"{A}/jobs/{jid}/approve", headers=_admin(client)).status_code == 409
    assert client.post(f"{A}/jobs/{jid}/reject", json={"reason": "changed my mind"}, headers=_admin(client)).status_code == 409
    assert client.post(f"{A}/jobs/999/approve", headers=_admin(client)).status_code == 404


def test_editing_a_published_job_sends_it_back_for_verification(client):
    h = _recruiter(client)
    s = _student(client)
    jid = _job(client, h)
    assert len(client.get("/api/v1/student/jobs", headers=s).json()) == 1
    r = client.put(f"/api/v1/recruiter/jobs/{jid}", json={**JOB, "salary": "20 LPA"}, headers=h)
    assert r.json()["verification_status"] == "PENDING"
    assert client.get("/api/v1/student/jobs", headers=s).json() == []
    client.post(f"{A}/jobs/{jid}/approve", headers=_admin(client))
    assert client.get("/api/v1/student/jobs", headers=s).json()[0]["salary"] == "20 LPA"


def test_rejected_job_can_be_fixed_and_resubmitted(client):
    h = _recruiter(client)
    jid = _job(client, h, publish=False)
    client.post(f"{A}/jobs/{jid}/reject", json={"reason": "Description too vague"}, headers=_admin(client))
    r = client.put(f"/api/v1/recruiter/jobs/{jid}", json=JOB, headers=h)
    assert r.json()["verification_status"] == "PENDING" and r.json()["rejection_reason"] is None
    assert client.post(f"{A}/jobs/{jid}/approve", headers=_admin(client)).status_code == 200


# ---------- placement drives ----------

def test_drive_crud_and_student_visibility(client):
    admin = _admin(client)
    s = _student(client)
    r = client.post(f"{A}/drives", json=_drive(), headers=admin)
    assert r.status_code == 201, r.text
    did = r.json()["id"]
    assert r.json()["upcoming"] is True
    assert [d["id"] for d in client.get(f"{A}/drives", headers=admin).json()] == [did]
    assert client.get("/api/v1/student/drives", headers=s).json()[0]["title"] == "Acme Campus Drive"
    u = client.put(f"{A}/drives/{did}", json=_drive(venue="Seminar Hall 2", min_cgpa=9.5), headers=admin)
    assert u.json()["venue"] == "Seminar Hall 2"
    student_view = client.get("/api/v1/student/drives", headers=s).json()[0]
    assert student_view["eligible"] is False and "9.5" in student_view["ineligible_reason"]
    assert client.delete(f"{A}/drives/{did}", headers=admin).status_code == 204
    assert client.get("/api/v1/student/drives", headers=s).json() == []
    assert client.delete(f"{A}/drives/{did}", headers=admin).status_code == 404
    assert _actions() == ["DRIVE_CREATED", "DRIVE_UPDATED", "DRIVE_DELETED"]


def test_drive_validation(client):
    admin = _admin(client)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert client.post(f"{A}/drives", json=_drive(drive_date=past), headers=admin).status_code == 422
    for bad in ({"title": "ab"}, {"min_cgpa": 11}, {"description": "short"}, {"venue": "x"}):
        assert client.post(f"{A}/drives", json=_drive(**bad), headers=admin).status_code == 422, bad
    assert client.put(f"{A}/drives/999", json=_drive(), headers=admin).status_code == 404


def test_drive_can_publish_announcement(client):
    admin = _admin(client)
    assert client.post(f"{A}/drives", json=_drive(announce=False), headers=admin).status_code == 201
    assert client.get("/api/v1/announcements").json() == []
    client.post(f"{A}/drives", json=_drive(title="Globex Drive", announce=True), headers=admin)
    ann = client.get("/api/v1/announcements").json()
    assert len(ann) == 1 and ann[0]["title"] == "Placement drive: Globex Drive" and "Main Auditorium" in ann[0]["body"]


# ---------- announcements ----------

def test_announcement_edit_and_delete(client):
    admin = _admin(client)
    new = client.post("/api/v1/announcements", json={"title": "Orientation", "body": "Friday 10 AM"}, headers=admin).json()
    r = client.put(f"{A}/announcements/{new['id']}", json={"title": "Orientation moved", "body": "Monday 10 AM"}, headers=admin)
    assert r.status_code == 200 and r.json()["title"] == "Orientation moved"
    assert client.put(f"{A}/announcements/{new['id']}", json={"title": "x", "body": "y"}, headers=admin).status_code == 422
    assert [a["id"] for a in client.get(f"{A}/announcements", headers=admin).json()] == [new["id"]]
    assert client.delete(f"{A}/announcements/{new['id']}", headers=admin).status_code == 204
    assert client.get("/api/v1/announcements").json() == []
    assert client.delete(f"{A}/announcements/{new['id']}", headers=admin).status_code == 404


# ---------- application tracking and selection management ----------

def _selected_application(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    R = "/api/v1/recruiter"
    client.patch(f"{R}/applications/{aid}/status", json={"status": "SHORTLISTED"}, headers=h)
    client.post(f"{R}/applications/{aid}/interviews", headers=h,
                json={"scheduled_at": _future(), "mode": "Online", "location": "https://meet.test/x"})
    client.patch(f"{R}/applications/{aid}/status", json={"status": "INTERVIEWED"}, headers=h)
    client.patch(f"{R}/applications/{aid}/status", json={"status": "SELECTED"}, headers=h)
    return aid, s


def test_admin_application_tracking_filters(client):
    aid, _ = _selected_application(client)
    admin = _admin(client)
    rows = client.get(f"{A}/applications", headers=admin).json()
    assert len(rows) == 1 and rows[0]["student_name"] == "Asha Rao" and rows[0]["company_name"] == "Acme Corp"
    assert rows[0]["status"] == "SELECTED" and rows[0]["interviews"] == 1
    q = lambda **p: client.get(f"{A}/applications", params=p, headers=admin).json()
    assert len(q(status_filter="SELECTED")) == 1 and q(status_filter="APPLIED") == []
    assert len(q(company="acme")) == 1 and q(company="globex") == []
    assert len(q(department="computer science")) == 1 and q(department="mechanical") == []
    assert len(q(job_id=rows[0]["job_id"])) == 1 and q(job_id=999) == []


def test_confirm_placement_marks_student_placed(client):
    aid, s = _selected_application(client)
    admin = _admin(client)
    r = client.post(f"{A}/applications/{aid}/confirm-placement", headers=admin)
    assert r.status_code == 200 and r.json()["placement_status"] == "PLACED"
    assert client.get("/api/v1/auth/me", headers=s).json()["student"]["placement_status"] == "PLACED"
    assert client.post(f"{A}/applications/{aid}/confirm-placement", headers=admin).status_code == 409
    summary = client.get(f"{A}/summary", headers=admin).json()
    assert summary["placed"] == 1 and summary["placement_percent"] == 100
    assert "PLACEMENT_CONFIRMED" in _actions()


def test_confirm_placement_requires_selected_status(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    admin = _admin(client)
    assert client.post(f"{A}/applications/{aid}/confirm-placement", headers=admin).status_code == 409
    assert client.post(f"{A}/applications/999/confirm-placement", headers=admin).status_code == 404


# ---------- recruiter approval (Phase 2 flow, now with filters in the dashboard) ----------

def test_recruiter_approval_still_logged(client):
    register_recruiter(client)
    with SessionLocal() as db:
        rid = db.query(Recruiter).one().id
    client.post(f"{A}/recruiters/{rid}/approve", headers=_admin(client))
    logs = client.get(f"{A}/audit-logs", headers=_admin(client)).json()
    assert logs[0]["action"] == "RECRUITER_APPROVED" and logs[0]["details"]["company"] == "Acme Corp"

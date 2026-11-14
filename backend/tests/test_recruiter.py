from datetime import date, datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import Application, ApplicationStatus, Job, JobType, Recruiter
from tests.conftest import PNG, auth, register_recruiter, register_student

PDF = b"%PDF-1.4\n" + b"0" * 64
R = "/api/v1/recruiter"
ADMIN = ("admin@college.edu", "Admin@12345")

JOB = {"title": "Backend Engineer", "job_type": "JOB", "description": "Build and run REST APIs at scale.",
       "location": "Pune", "salary": "8 LPA", "required_skills": ["Python", " python ", "SQL"], "min_cgpa": 7.5,
       "eligible_departments": ["Computer Science"], "deadline": str(date.today() + timedelta(days=14))}


def _recruiter(client, email="hr@acme.com", approve=True, **over):
    register_recruiter(client, email=email, **over)
    with SessionLocal() as db:
        rid = db.query(Recruiter).filter(Recruiter.user.has(email=email)).one().id
    if approve:
        client.post(f"/api/v1/admin/recruiters/{rid}/approve", headers=auth(client, *ADMIN))
    return auth(client, email) if approve else None


def _student(client, resume=True, **over):
    register_student(client, **over)
    h = auth(client, over.get("email", "asha@college.edu"))
    if resume:
        client.post("/api/v1/student/resume", files={"file": ("cv.pdf", PDF, "application/pdf")}, headers=h)
    return h


def _job(client, h, publish=True, **over):
    r = client.post(f"{R}/jobs", json={**JOB, **over}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["verification_status"] == "PENDING"
    if publish:  # the placement cell verifies the posting before students can see it
        approved = client.post(f"/api/v1/admin/jobs/{r.json()['id']}/approve", headers=auth(client, *ADMIN))
        assert approved.status_code == 200, approved.text
    return r.json()["id"]


def _applied(client, student_h, job_id):
    r = client.post("/api/v1/student/applications", json={"job_id": job_id}, headers=student_h)
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        return db.query(Application).filter_by(job_id=job_id).order_by(Application.id.desc()).first().id


def _future(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


# ---------- access control ----------

def test_recruiter_endpoints_require_recruiter_role(client):
    assert client.get(f"{R}/jobs").status_code == 401
    student = _student(client)
    admin = auth(client, *ADMIN)
    for h in (student, admin):
        for path in ("jobs", "candidates", "applications", "summary"):
            assert client.get(f"{R}/{path}", headers=h).status_code == 403
        assert client.post(f"{R}/jobs", json=JOB, headers=h).status_code == 403


def test_unapproved_recruiter_cannot_use_token(client):
    h = _recruiter(client)
    with SessionLocal() as db:
        rec = db.query(Recruiter).one()
        rec.verification_status = "REJECTED"
        db.commit()
    assert client.get(f"{R}/jobs", headers=h).status_code == 403


# ---------- company profile ----------

def test_update_company_profile(client):
    h = _recruiter(client)
    body = {"company_name": "Acme Labs", "contact_person": "Ravi K", "phone": "9000000001",
            "company_profile": "Acme Labs builds developer tools."}
    r = client.put(f"{R}/profile", json=body, headers=h)
    assert r.status_code == 200 and r.json()["company_name"] == "Acme Labs"
    assert client.get("/api/v1/auth/me", headers=h).json()["recruiter"]["phone"] == "9000000001"


def test_company_profile_validation(client):
    h = _recruiter(client)
    good = {"company_name": "Acme Labs", "contact_person": "Ravi K", "phone": "9000000001",
            "company_profile": "Acme Labs builds developer tools."}
    for bad in ({"phone": "123"}, {"company_name": "A"}, {"company_profile": "short"}):
        assert client.put(f"{R}/profile", json={**good, **bad}, headers=h).status_code == 422


def test_replace_logo_validates_and_swaps_file(client):
    h = _recruiter(client)
    before = client.get("/api/v1/auth/me", headers=h).json()["recruiter"]["logo_path"]
    ok = client.post(f"{R}/logo", files={"logo": ("n.png", PNG, "image/png")}, headers=h)
    assert ok.status_code == 200 and ok.json()["logo_path"] != before
    assert client.post(f"{R}/logo", files={"logo": ("n.pdf", PDF, "application/pdf")}, headers=h).status_code == 422
    assert client.post(f"{R}/logo", files={"logo": ("n.png", b"junk", "image/png")}, headers=h).status_code == 422


# ---------- job postings ----------

def test_create_and_list_job(client):
    h = _recruiter(client)
    r = client.post(f"{R}/jobs", json=JOB, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["required_skills"] == ["Python", "SQL"] and body["is_active"] and body["applicants"] == 0
    assert [j["id"] for j in client.get(f"{R}/jobs", headers=h).json()] == [body["id"]]
    assert client.get(f"{R}/jobs/{body['id']}", headers=h).json()["title"] == "Backend Engineer"


def test_job_validation(client):
    h = _recruiter(client)
    yesterday = str(date.today() - timedelta(days=1))
    for bad in ({"deadline": yesterday}, {"min_cgpa": 11}, {"title": "ab"}, {"description": "short"},
                {"job_type": "FULLTIME"}):
        assert client.post(f"{R}/jobs", json={**JOB, **bad}, headers=h).status_code == 422, bad


def test_update_job(client):
    h = _recruiter(client)
    jid = _job(client, h)
    r = client.put(f"{R}/jobs/{jid}", json={**JOB, "title": "Senior Backend Engineer", "min_cgpa": 8}, headers=h)
    assert r.status_code == 200 and r.json()["title"] == "Senior Backend Engineer" and r.json()["min_cgpa"] == 8


def test_recruiter_cannot_touch_other_recruiters_job(client):
    h1 = _recruiter(client)
    jid = _job(client, h1)
    h2 = _recruiter(client, email="hr@globex.com")
    assert client.get(f"{R}/jobs/{jid}", headers=h2).status_code == 404
    assert client.put(f"{R}/jobs/{jid}", json=JOB, headers=h2).status_code == 404
    assert client.post(f"{R}/jobs/{jid}/close", headers=h2).status_code == 404
    assert client.get(f"{R}/jobs", headers=h2).json() == []


def test_close_hides_job_from_students_and_reopen_restores(client):
    h = _recruiter(client)
    jid = _job(client, h)
    s = _student(client)
    assert [j["id"] for j in client.get("/api/v1/student/jobs", headers=s).json()] == [jid]
    assert client.post(f"{R}/jobs/{jid}/close", headers=h).json()["is_active"] is False
    assert client.get("/api/v1/student/jobs", headers=s).json() == []
    assert client.post("/api/v1/student/applications", json={"job_id": jid}, headers=s).status_code == 404
    assert client.post(f"{R}/jobs/{jid}/reopen", headers=h).json()["is_active"] is True
    assert len(client.get("/api/v1/student/jobs", headers=s).json()) == 1


def test_reopen_expired_job_rejected(client):
    h = _recruiter(client)
    jid = _job(client, h)
    with SessionLocal() as db:
        db.get(Job, jid).deadline = date.today() - timedelta(days=1)
        db.commit()
    assert client.get(f"{R}/jobs/{jid}", headers=h).json()["expired"] is True
    assert client.post(f"{R}/jobs/{jid}/reopen", headers=h).status_code == 409


def test_department_eligibility_enforced_for_students(client):
    h = _recruiter(client)
    jid = _job(client, h, min_cgpa=0, eligible_departments=["Mechanical"])
    s = _student(client)
    listed = client.get("/api/v1/student/jobs", headers=s).json()[0]
    assert listed["eligible"] is False and "Mechanical" in listed["ineligible_reason"]
    assert client.post("/api/v1/student/applications", json={"job_id": jid}, headers=s).status_code == 403


# ---------- candidate search ----------

def _seed_students(client):
    _student(client, resume=False)
    _student(client, email="ben@college.edu", college_id="ME2026002", mobile="9876500002", full_name="Ben Joseph",
             department="Mechanical", degree_cgpa=6.8, skills=["CAD", "Python"])
    _student(client, email="cara@college.edu", college_id="CS2026003", mobile="9876500003", full_name="Cara Das",
             degree_cgpa=9.2, skills=["python", "React", "SQL"])


def test_candidate_search_filters(client):
    h = _recruiter(client)
    _seed_students(client)
    ids = lambda **params: sorted(c["college_id"] for c in client.get(f"{R}/candidates", params=params, headers=h).json())
    assert ids() == ["CS2026001", "CS2026003", "ME2026002"]
    assert ids(skills="python") == ["CS2026001", "CS2026003", "ME2026002"]
    assert ids(skills="Python, SQL") == ["CS2026001", "CS2026003"]
    assert ids(skills="react,sql,python") == ["CS2026003"]
    assert ids(skills="pyth") == []
    assert ids(department="mechanical") == ["ME2026002"]
    assert ids(min_cgpa=8.5) == ["CS2026003"]
    assert ids(q="joseph") == ["ME2026002"]
    assert ids(q="cs2026003") == ["CS2026003"]


def test_candidate_search_sorted_by_cgpa_and_hides_contact_details(client):
    h = _recruiter(client)
    _seed_students(client)
    rows = client.get(f"{R}/candidates", headers=h).json()
    assert [r["degree_cgpa"] for r in rows] == sorted((r["degree_cgpa"] for r in rows), reverse=True)
    assert all("email" not in r and "mobile" not in r for r in rows)
    assert {r["college_id"]: r["has_resume"] for r in rows} == {"CS2026001": False, "ME2026002": True, "CS2026003": True}


def test_candidate_search_eligible_for_job(client):
    h = _recruiter(client)
    _seed_students(client)
    jid = _job(client, h, min_cgpa=8.0, eligible_departments=["Computer Science"])
    rows = client.get(f"{R}/candidates", params={"eligible_for": jid}, headers=h).json()
    assert [r["college_id"] for r in rows] == ["CS2026003", "CS2026001"]
    assert client.get(f"{R}/candidates", params={"eligible_for": 999}, headers=h).status_code == 404


def test_skill_filter_treats_wildcards_literally(client):
    h = _recruiter(client)
    _student(client)
    assert client.get(f"{R}/candidates", params={"skills": "%"}, headers=h).json() == []
    assert client.get(f"{R}/candidates", params={"skills": "_ython"}, headers=h).json() == []


# ---------- application review ----------

def test_list_and_filter_applications(client):
    h = _recruiter(client)
    j1, j2 = _job(client, h), _job(client, h, title="Data Analyst", min_cgpa=0, eligible_departments=[])
    s = _student(client)
    a1 = _applied(client, s, j1)
    _applied(client, s, j2)
    rows = client.get(f"{R}/applications", headers=h).json()
    assert len(rows) == 2 and rows[0]["email"] == "asha@college.edu" and rows[0]["student"]["has_resume"]
    assert [r["id"] for r in client.get(f"{R}/applications", params={"job_id": j1}, headers=h).json()] == [a1]
    assert client.get(f"{R}/applications", params={"status_filter": "SHORTLISTED"}, headers=h).json() == []
    assert rows[1]["skills_match"] == ["Python", "SQL"]


def test_applications_isolated_between_recruiters(client):
    h1 = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h1))
    h2 = _recruiter(client, email="hr@globex.com")
    assert client.get(f"{R}/applications", headers=h2).json() == []
    assert client.patch(f"{R}/applications/{aid}/status", json={"status": "SHORTLISTED"}, headers=h2).status_code == 404
    assert client.get(f"{R}/applications/{aid}/resume", headers=h2).status_code == 404


def test_resume_download_for_applicant(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    r = client.get(f"{R}/applications/{aid}/resume", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_full_selection_flow(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    patch = lambda st: client.patch(f"{R}/applications/{aid}/status", json={"status": st}, headers=h)

    assert patch("SHORTLISTED").json()["status"] == "SHORTLISTED"
    iv = client.post(f"{R}/applications/{aid}/interviews", headers=h,
                     json={"scheduled_at": _future(), "mode": "Online", "location": "https://meet.test/abc", "notes": "Bring ID"})
    assert iv.status_code == 201
    assert iv.json()["status"] == "INTERVIEW_SCHEDULED" and iv.json()["interviews"][0]["mode"] == "Online"
    assert patch("INTERVIEWED").json()["status"] == "INTERVIEWED"
    assert patch("SELECTED").json()["status"] == "SELECTED"

    # the student sees every update on their own dashboard
    mine = client.get("/api/v1/student/applications", headers=s).json()[0]
    assert mine["status"] == "SELECTED" and mine["interviews"][0]["location"] == "https://meet.test/abc"
    assert len(client.get("/api/v1/student/interviews", headers=s).json()) == 1
    assert client.get(f"{R}/summary", headers=h).json()["selected"] == 1


def test_invalid_status_transitions_rejected(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    patch = lambda st: client.patch(f"{R}/applications/{aid}/status", json={"status": st}, headers=h)
    assert patch("SELECTED").status_code == 409
    assert patch("INTERVIEWED").status_code == 409
    assert patch("INTERVIEW_SCHEDULED").status_code == 422
    assert patch("APPLIED").status_code == 422
    assert patch("REJECTED").status_code == 200
    assert patch("SHORTLISTED").status_code == 409
    assert client.get("/api/v1/student/applications", headers=s).json()[0]["status"] == "REJECTED"


def test_interview_rules(client):
    h = _recruiter(client)
    s = _student(client)
    aid = _applied(client, s, _job(client, h))
    url = f"{R}/applications/{aid}/interviews"
    body = {"scheduled_at": _future(), "mode": "Offline", "location": "Room 4, Block B"}
    assert client.post(url, json=body, headers=h).status_code == 409  # not shortlisted yet
    client.patch(f"{R}/applications/{aid}/status", json={"status": "SHORTLISTED"}, headers=h)
    past = {**body, "scheduled_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
    assert client.post(url, json=past, headers=h).status_code == 422
    assert client.post(url, json={**body, "mode": "Phone"}, headers=h).status_code == 422
    assert client.post(url, json={**body, "location": "x"}, headers=h).status_code == 422
    assert client.post(url, json=body, headers=h).status_code == 201
    second = client.post(url, json={**body, "scheduled_at": _future(4)}, headers=h)  # extra round
    assert second.status_code == 201 and len(second.json()["interviews"]) == 2


def test_summary_counts(client):
    h = _recruiter(client)
    j1 = _job(client, h)
    _job(client, h, title="Closed role")
    s = _student(client)
    aid = _applied(client, s, j1)
    client.post(f"{R}/jobs/{j1 + 1}/close", headers=h)
    client.patch(f"{R}/applications/{aid}/status", json={"status": "SHORTLISTED"}, headers=h)
    client.post(f"{R}/applications/{aid}/interviews", headers=h,
                json={"scheduled_at": _future(), "mode": "Online", "location": "https://meet.test/x"})
    assert client.get(f"{R}/summary", headers=h).json() == {
        "active_jobs": 1, "total_jobs": 2, "applicants": 1, "shortlisted": 0, "interviews_upcoming": 1, "selected": 0}

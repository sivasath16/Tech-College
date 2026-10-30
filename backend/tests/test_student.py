from datetime import date, datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import (
    Application, ApplicationStatus, Interview, Job, JobType, OfferLetter, OfferStatus, PlacementDrive, Recruiter,
)
from tests.conftest import PNG, auth, register_recruiter, register_student

PDF = b"%PDF-1.4\n" + b"0" * 64
DOCX = b"PK\x03\x04" + b"0" * 64
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
S = "/api/v1/student"
SECOND = {"email": "ben@college.edu", "college_id": "cs2026002", "mobile": "9876500000"}


def _student(client, **over):
    register_student(client, **over)
    return auth(client, over.get("email", "asha@college.edu"))


def _make_job(client, min_cgpa=7.0, deadline=None, active=True, approve=True):
    register_recruiter(client)
    with SessionLocal() as db:
        rid = db.query(Recruiter).first().id
    if approve:
        client.post(f"/api/v1/admin/recruiters/{rid}/approve", headers=auth(client, "admin@college.edu", "Admin@12345"))
    with SessionLocal() as db:
        job = Job(recruiter_id=rid, title="Backend Engineer", job_type=JobType.JOB, description="Build APIs",
                  location="Pune", salary="8 LPA", required_skills=["Python"], min_cgpa=min_cgpa,
                  deadline=deadline or date.today() + timedelta(days=10), is_active=active)
        db.add(job)
        db.commit()
        return job.id


def _upload_resume(client, h, content=PDF, ctype="application/pdf", name="cv.pdf"):
    return client.post(f"{S}/resume", files={"file": (name, content, ctype)}, headers=h)


# ---------- profile ----------

PROFILE = {"full_name": "Asha R", "department": "IT", "tenth_percent": 90, "twelfth_percent": 85,
           "degree_cgpa": 9.1, "skills": ["Python", " Python ", "", "React"], "certifications": "AWS"}


def test_profile_get_and_update(client):
    h = _student(client)
    assert client.get(f"{S}/profile", headers=h).json()["college_id"] == "CS2026001"
    r = client.put(f"{S}/profile", json=PROFILE, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["degree_cgpa"] == 9.1 and body["department"] == "IT"
    assert body["skills"] == ["Python", "React"]


def test_profile_validation(client):
    h = _student(client)
    for bad in ({"degree_cgpa": 11}, {"tenth_percent": -1}, {"twelfth_percent": 101}, {"full_name": "A"}):
        assert client.put(f"{S}/profile", json={**PROFILE, **bad}, headers=h).status_code == 422


def test_student_endpoints_need_student_role(client):
    assert client.get(f"{S}/jobs").status_code == 401
    admin = auth(client, "admin@college.edu", "Admin@12345")
    for path in ("profile", "jobs", "applications", "drives", "interviews", "offers", "summary", "documents"):
        assert client.get(f"{S}/{path}", headers=admin).status_code == 403


# ---------- uploads ----------

def test_resume_upload_replace_and_download(client):
    h = _student(client)
    assert client.get(f"{S}/resume", headers=h).status_code == 404
    r = _upload_resume(client, h)
    assert r.status_code == 200 and r.json()["resume_name"] == "resume.pdf"
    assert client.get(f"{S}/resume", headers=h).content == PDF
    r = _upload_resume(client, h, DOCX, DOCX_TYPE, "cv.docx")
    assert r.json()["resume_name"] == "resume.docx"
    assert client.get(f"{S}/resume", headers=h).content == DOCX


def test_resume_rejects_bad_files(client):
    h = _student(client)
    assert _upload_resume(client, h, PNG, "image/png", "a.png").status_code == 422
    assert _upload_resume(client, h, b"not a pdf at all").status_code == 422
    assert _upload_resume(client, h, b"").status_code == 422
    assert _upload_resume(client, h, PDF + b"0" * (5 * 1024 * 1024)).status_code == 413
    assert client.get(f"{S}/resume", headers=h).status_code == 404


def test_certificates_upload_list_download_delete(client):
    h = _student(client)
    r = client.post(f"{S}/certificates", data={"title": "AWS Cloud Practitioner"},
                    files={"file": ("aws.png", PNG, "image/png")}, headers=h)
    assert r.status_code == 201
    cert = r.json()["certificates"][0]
    assert cert["title"] == "AWS Cloud Practitioner" and cert["original_name"] == "aws.png"
    assert client.get(f"{S}/certificates/{cert['id']}", headers=h).content == PNG
    assert client.get(f"{S}/documents", headers=h).json()["certificates"][0]["id"] == cert["id"]
    assert client.delete(f"{S}/certificates/{cert['id']}", headers=h).json()["certificates"] == []
    assert client.get(f"{S}/certificates/{cert['id']}", headers=h).status_code == 404


def test_certificate_validation_and_limit(client):
    h = _student(client)
    post = lambda title, files: client.post(f"{S}/certificates", data={"title": title}, files={"file": files}, headers=h)
    assert post("Bad", ("c.docx", DOCX, DOCX_TYPE)).status_code == 422
    assert post("Bad", ("c.pdf", b"nope", "application/pdf")).status_code == 422
    for i in range(10):
        assert post(f"Cert {i}", ("c.pdf", PDF, "application/pdf")).status_code == 201
    assert post("Eleven", ("c.pdf", PDF, "application/pdf")).status_code == 409


def test_certificates_are_private_between_students(client):
    h1 = _student(client)
    cert = client.post(f"{S}/certificates", data={"title": "Mine"},
                       files={"file": ("c.pdf", PDF, "application/pdf")}, headers=h1).json()["certificates"][0]
    h2 = _student(client, **SECOND)
    assert client.get(f"{S}/certificates/{cert['id']}", headers=h2).status_code == 404
    assert client.delete(f"{S}/certificates/{cert['id']}", headers=h2).status_code == 404
    assert client.get(f"{S}/certificates/{cert['id']}", headers=h1).status_code == 200


# ---------- jobs & applications ----------

def test_job_listing_filters_and_eligibility(client):
    h = _student(client)
    _make_job(client, min_cgpa=9.5)
    jobs = client.get(f"{S}/jobs", headers=h).json()
    assert len(jobs) == 1 and jobs[0]["company_name"] == "Acme Corp"
    assert jobs[0]["eligible"] is False and "9.5" in jobs[0]["ineligible_reason"]
    assert client.get(f"{S}/jobs?job_type=INTERNSHIP", headers=h).json() == []
    assert len(client.get(f"{S}/jobs?q=acme", headers=h).json()) == 1
    assert client.get(f"{S}/jobs?q=zzz", headers=h).json() == []


def test_jobs_hidden_when_expired_inactive_or_unapproved(client):
    h = _student(client)
    _make_job(client, deadline=date.today() - timedelta(days=1))
    assert client.get(f"{S}/jobs", headers=h).json() == []


def test_jobs_of_unapproved_recruiter_hidden(client):
    h = _student(client)
    _make_job(client, approve=False)
    assert client.get(f"{S}/jobs", headers=h).json() == []


def test_inactive_job_hidden(client):
    h = _student(client)
    _make_job(client, active=False)
    assert client.get(f"{S}/jobs", headers=h).json() == []


def test_apply_flow_and_tracking(client):
    h = _student(client)
    job_id = _make_job(client)
    assert client.post(f"{S}/applications", json={"job_id": job_id}, headers=h).status_code == 409  # no resume
    _upload_resume(client, h)
    r = client.post(f"{S}/applications", json={"job_id": job_id}, headers=h)
    assert r.status_code == 201 and r.json()["status"] == "APPLIED"
    assert client.post(f"{S}/applications", json={"job_id": job_id}, headers=h).status_code == 409  # duplicate
    apps = client.get(f"{S}/applications", headers=h).json()
    assert len(apps) == 1 and apps[0]["job_title"] == "Backend Engineer" and apps[0]["company_name"] == "Acme Corp"
    assert client.get(f"{S}/jobs", headers=h).json()[0]["application_status"] == "APPLIED"
    assert client.get(f"{S}/summary", headers=h).json()["applications"] == 1


def test_apply_blocked_for_ineligible_expired_and_missing(client):
    h = _student(client)
    _upload_resume(client, h)
    job_id = _make_job(client, min_cgpa=9.9)
    assert client.post(f"{S}/applications", json={"job_id": job_id}, headers=h).status_code == 403
    assert client.post(f"{S}/applications", json={"job_id": 9999}, headers=h).status_code == 404
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.min_cgpa, job.deadline = 0, date.today() - timedelta(days=1)
        db.commit()
    assert client.post(f"{S}/applications", json={"job_id": job_id}, headers=h).status_code == 409


def test_applications_are_private_between_students(client):
    h1 = _student(client)
    _upload_resume(client, h1)
    job_id = _make_job(client)
    client.post(f"{S}/applications", json={"job_id": job_id}, headers=h1)
    h2 = _student(client, **SECOND)
    assert client.get(f"{S}/applications", headers=h2).json() == []


# ---------- drives, interviews, offers ----------

def test_drives_filtered_by_time_and_eligibility(client):
    h = _student(client)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add_all([
            PlacementDrive(title="Past", company_name="Old", description="x", venue="Hall",
                           drive_date=now - timedelta(days=2)),
            PlacementDrive(title="Open", company_name="Acme", description="x", venue="Hall",
                           drive_date=now + timedelta(days=2), min_cgpa=7, departments=["Computer Science"]),
            PlacementDrive(title="Mech only", company_name="Gear", description="x", venue="Lab",
                           drive_date=now + timedelta(days=3), departments=["Mechanical"]),
            PlacementDrive(title="High bar", company_name="Elite", description="x", venue="Hall",
                           drive_date=now + timedelta(days=4), min_cgpa=9.5),
        ])
        db.commit()
    drives = client.get(f"{S}/drives", headers=h).json()
    assert [d["title"] for d in drives] == ["Open", "Mech only", "High bar"]
    assert [d["eligible"] for d in drives] == [True, False, False]
    assert "Mechanical" in drives[1]["ineligible_reason"] and "9.5" in drives[2]["ineligible_reason"]


def test_interviews_and_offers_visible_to_owner_only(client):
    h = _student(client)
    _upload_resume(client, h)
    job_id = _make_job(client)
    app_id = client.post(f"{S}/applications", json={"job_id": job_id}, headers=h).json()["id"]
    when = datetime.now(timezone.utc) + timedelta(days=3)
    with SessionLocal() as db:
        db.add(Interview(application_id=app_id, scheduled_at=when, mode="Online", location="Meet link", notes="Bring ID"))
        db.add(OfferLetter(application_id=app_id, status=OfferStatus.ISSUED, package="9 LPA"))
        db.get(Application, app_id).status = ApplicationStatus.SELECTED
        db.commit()
    interviews = client.get(f"{S}/interviews", headers=h).json()
    assert len(interviews) == 1 and interviews[0]["mode"] == "Online" and interviews[0]["company_name"] == "Acme Corp"
    offers = client.get(f"{S}/offers", headers=h).json()
    assert offers[0]["status"] == "ISSUED" and offers[0]["package"] == "9 LPA"
    assert client.get(f"{S}/applications", headers=h).json()[0]["status"] == "SELECTED"
    summary = client.get(f"{S}/summary", headers=h).json()
    assert summary["interviews_upcoming"] == 1 and summary["offers"] == 1
    h2 = _student(client, **SECOND)
    assert client.get(f"{S}/interviews", headers=h2).json() == [] and client.get(f"{S}/offers", headers=h2).json() == []


def test_profile_completion(client):
    h = _student(client)
    assert client.get(f"{S}/summary", headers=h).json()["profile_completion"] == 60  # base + skills
    _upload_resume(client, h)
    client.post(f"{S}/certificates", data={"title": "AWS"}, files={"file": ("a.pdf", PDF, "application/pdf")}, headers=h)
    assert client.get(f"{S}/summary", headers=h).json()["profile_completion"] == 100

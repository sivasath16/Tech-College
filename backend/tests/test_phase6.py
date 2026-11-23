from datetime import date, datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import DriveRegistration, PlacementDrive
from tests.conftest import auth
from tests.test_recruiter import ADMIN, _job, _recruiter, _student

R = "/api/v1/recruiter"
S = "/api/v1/student"
A = "/api/v1/admin"
PDF = b"%PDF-1.4\n" + b"0" * 64
SECOND = {"email": "ben@college.edu", "college_id": "cs2026002", "mobile": "9876500000"}


def _apply(client, student, job_id):
    r = client.post(f"{S}/applications", json={"job_id": job_id}, headers=student)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _move(client, hr, app_id, status):
    return client.patch(f"{R}/applications/{app_id}/status", json={"status": status}, headers=hr)


def _interview(client, hr, app_id):
    when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    return client.post(f"{R}/applications/{app_id}/interviews", headers=hr,
                       json={"scheduled_at": when, "mode": "Online", "location": "https://meet.example.com/x"})


def _select(client, hr, student, job_id):
    app_id = _apply(client, student, job_id)
    assert _move(client, hr, app_id, "SHORTLISTED").status_code == 200
    assert _interview(client, hr, app_id).status_code == 201
    assert _move(client, hr, app_id, "INTERVIEWED").status_code == 200
    assert _move(client, hr, app_id, "SELECTED").status_code == 200
    return app_id


def _offer(client, hr, app_id, name="offer.pdf", content=PDF, ctype="application/pdf", **form):
    data = {"package": "9 LPA", **form}
    return client.post(f"{R}/applications/{app_id}/offer", data=data, files={"file": (name, content, ctype)}, headers=hr)


def _drive(title="Acme Drive", days=3, **over):
    with SessionLocal() as db:
        d = PlacementDrive(title=title, company_name="Acme", description="Rounds: test and interview", venue="Hall",
                           drive_date=datetime.now(timezone.utc) + timedelta(days=days), **over)
        db.add(d)
        db.commit()
        return d.id


# ---------- end-to-end: post -> approve -> apply -> interview -> select -> offer -> placed ----------

def test_full_placement_lifecycle(client):
    hr = _recruiter(client)
    student = _student(client)
    admin = auth(client, *ADMIN)

    created = client.post(f"{R}/jobs", headers=hr, json={
        "title": "Backend Engineer", "job_type": "JOB", "description": "Build and run REST APIs at scale.",
        "location": "Pune", "min_cgpa": 7, "deadline": str(date.today() + timedelta(days=10))})
    job_id = created.json()["id"]
    assert created.json()["verification_status"] == "PENDING"
    assert client.get(f"{S}/jobs", headers=student).json() == []  # not visible before verification
    assert client.post(f"{S}/applications", json={"job_id": job_id}, headers=student).status_code == 404

    assert client.post(f"{A}/jobs/{job_id}/approve", headers=admin).status_code == 200
    assert [j["id"] for j in client.get(f"{S}/jobs", headers=student).json()] == [job_id]

    app_id = _apply(client, student, job_id)
    assert [a["id"] for a in client.get(f"{R}/applications", headers=hr).json()] == [app_id]  # reaches recruiter
    assert [a["id"] for a in client.get(f"{A}/applications", headers=admin).json()] == [app_id]

    assert _move(client, hr, app_id, "SHORTLISTED").status_code == 200
    assert _interview(client, hr, app_id).status_code == 201
    assert _move(client, hr, app_id, "INTERVIEWED").status_code == 200
    assert _move(client, hr, app_id, "SELECTED").status_code == 200
    assert _offer(client, hr, app_id, joining_date=str(date.today() + timedelta(days=90))).status_code == 200

    offers = client.get(f"{S}/offers", headers=student).json()
    assert offers[0]["status"] == "ISSUED" and offers[0]["has_file"] is True
    assert client.get(f"{S}/offers/{app_id}/file", headers=student).content == PDF
    accepted = client.post(f"{S}/offers/{app_id}/respond", json={"decision": "ACCEPT"}, headers=student)
    assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"

    assert client.get(f"{S}/profile", headers=student).json()["placement_status"] == "PLACED"
    summary = client.get(f"{A}/summary", headers=admin).json()
    assert summary["placed"] == 1 and summary["applications_by_status"]["SELECTED"] == 1
    assert client.get(f"{R}/applications", headers=hr).json()[0]["offer_status"] == "ACCEPTED"

    timeline = client.get(f"{S}/applications", headers=student).json()[0]["timeline"]
    assert [e["to_status"] for e in timeline] == ["APPLIED", "SHORTLISTED", "INTERVIEW_SCHEDULED", "INTERVIEWED",
                                                  "SELECTED"]
    assert [e["actor"] for e in timeline] == ["STUDENT"] + ["RECRUITER"] * 4
    assert timeline[0]["from_status"] is None and timeline[1]["from_status"] == "APPLIED"
    assert [e["to_status"] for e in client.get(f"{R}/applications", headers=hr).json()[0]["timeline"]] == \
           [e["to_status"] for e in timeline]


# ---------- status transitions ----------

def test_invalid_transitions_rejected_and_not_logged(client):
    hr = _recruiter(client)
    student = _student(client)
    job_id = _job(client, hr)
    app_id = _apply(client, student, job_id)
    for bad in ("INTERVIEWED", "SELECTED"):
        assert _move(client, hr, app_id, bad).status_code == 409
    assert _interview(client, hr, app_id).status_code == 409  # must be shortlisted first
    assert _move(client, hr, app_id, "REJECTED").status_code == 200
    assert _move(client, hr, app_id, "SHORTLISTED").status_code == 409  # rejected is final
    timeline = client.get(f"{S}/applications", headers=student).json()[0]["timeline"]
    assert [e["to_status"] for e in timeline] == ["APPLIED", "REJECTED"]


def test_other_recruiter_cannot_change_status_or_issue_offer(client):
    hr = _recruiter(client)
    other = _recruiter(client, email="hr@globex.com", company_name="Globex")
    student = _student(client)
    app_id = _select(client, hr, student, _job(client, hr))
    assert _move(client, other, app_id, "REJECTED").status_code == 404
    assert _offer(client, other, app_id).status_code == 404
    assert client.get(f"{R}/applications/{app_id}/offer/file", headers=other).status_code == 404


# ---------- offer letters ----------

def test_offer_requires_selection_and_valid_pdf(client):
    hr = _recruiter(client)
    student = _student(client)
    job_id = _job(client, hr)
    app_id = _apply(client, student, job_id)
    assert _offer(client, hr, app_id).status_code == 409  # not selected yet
    _move(client, hr, app_id, "SHORTLISTED")
    _interview(client, hr, app_id)
    _move(client, hr, app_id, "INTERVIEWED")
    _move(client, hr, app_id, "SELECTED")
    assert _offer(client, hr, app_id, "offer.png", b"\x89PNG\r\n\x1a\n0000", "image/png").status_code == 422
    assert _offer(client, hr, app_id, content=b"not a pdf").status_code == 422
    assert _offer(client, hr, app_id, content=b"").status_code == 422
    assert _offer(client, hr, app_id, content=PDF + b"0" * (5 * 1024 * 1024)).status_code == 413
    assert _offer(client, hr, app_id, joining_date=str(date.today() - timedelta(days=1))).status_code == 422
    assert client.get(f"{S}/offers", headers=student).json() == []  # nothing issued by failed attempts
    ok = _offer(client, hr, app_id, package="12 LPA")
    assert ok.status_code == 200 and ok.json()["offer_package"] == "12 LPA" and ok.json()["offer_has_file"] is True
    assert client.get(f"{R}/applications/{app_id}/offer/file", headers=hr).content == PDF


def test_student_decline_then_recruiter_reissues(client):
    hr = _recruiter(client)
    student = _student(client)
    app_id = _select(client, hr, student, _job(client, hr))
    _offer(client, hr, app_id)
    declined = client.post(f"{S}/offers/{app_id}/respond", json={"decision": "DECLINE"}, headers=student)
    assert declined.json()["status"] == "DECLINED"
    assert client.get(f"{S}/profile", headers=student).json()["placement_status"] == "NOT_PLACED"
    assert client.post(f"{S}/offers/{app_id}/respond", json={"decision": "ACCEPT"}, headers=student).status_code == 409
    new_pdf = b"%PDF-1.4\nrevised" + b"0" * 32
    assert _offer(client, hr, app_id, content=new_pdf, package="10 LPA").status_code == 200
    assert client.get(f"{S}/offers/{app_id}/file", headers=student).content == new_pdf
    assert client.get(f"{S}/offers", headers=student).json()[0]["status"] == "ISSUED"


def test_accepted_offer_is_final_and_only_one_can_be_accepted(client):
    hr = _recruiter(client)
    student = _student(client)
    first = _select(client, hr, student, _job(client, hr))
    second = _select(client, hr, student, _job(client, hr, title="Data Engineer"))
    _offer(client, hr, first)
    _offer(client, hr, second)
    assert client.post(f"{S}/offers/{first}/respond", json={"decision": "ACCEPT"}, headers=student).status_code == 200
    assert client.post(f"{S}/offers/{second}/respond", json={"decision": "ACCEPT"}, headers=student).status_code == 409
    assert _offer(client, hr, first).status_code == 409  # cannot replace an accepted offer
    assert client.post(f"{S}/offers/{first}/respond", json={"decision": "DECLINE"}, headers=student).status_code == 409


def test_offer_letters_are_private_to_the_student(client):
    hr = _recruiter(client)
    student = _student(client)
    other = _student(client, **SECOND)
    app_id = _select(client, hr, student, _job(client, hr))
    assert client.get(f"{S}/offers/{app_id}/file", headers=student).status_code == 404  # none issued yet
    _offer(client, hr, app_id)
    assert client.get(f"{S}/offers/{app_id}/file", headers=other).status_code == 404
    assert client.post(f"{S}/offers/{app_id}/respond", json={"decision": "ACCEPT"}, headers=other).status_code == 404
    assert client.get(f"{S}/offers/{app_id}/file", headers=hr).status_code == 403
    assert client.get(f"{S}/offers/{app_id}/file").status_code == 401


# ---------- placement drive registration and eligibility ----------

def test_drive_registration_and_cancellation(client):
    student = _student(client)
    drive_id = _drive(min_cgpa=7, departments=["Computer Science"])
    assert client.get(f"{S}/drives", headers=student).json()[0]["registration_status"] is None
    r = client.post(f"{S}/drives/{drive_id}/register", headers=student)
    assert r.status_code == 201 and r.json()["registration_status"] == "REGISTERED"
    assert client.post(f"{S}/drives/{drive_id}/register", headers=student).status_code == 409
    assert client.get(f"{S}/drives", headers=student).json()[0]["registration_status"] == "REGISTERED"
    assert client.get(f"{A}/drives", headers=auth(client, *ADMIN)).json()[0]["registered"] == 1
    cancelled = client.delete(f"{S}/drives/{drive_id}/register", headers=student)
    assert cancelled.status_code == 200 and cancelled.json()["registration_status"] is None
    assert client.delete(f"{S}/drives/{drive_id}/register", headers=student).status_code == 404


def test_drive_registration_blocked_for_ineligible_student(client):
    student = _student(client)  # Computer Science, CGPA 8.4
    high_bar = _drive("High bar", min_cgpa=9.5)
    mech = _drive("Mech only", departments=["Mechanical"])
    for drive_id in (high_bar, mech):
        assert client.post(f"{S}/drives/{drive_id}/register", headers=student).status_code == 403
    assert client.get(f"{S}/attendance", headers=student).json() == []


def test_drive_registration_closed_after_start_or_missing(client):
    student = _student(client)
    started = _drive("Started", days=-1)
    assert client.post(f"{S}/drives/{started}/register", headers=student).status_code == 409
    assert client.post(f"{S}/drives/9999/register", headers=student).status_code == 404
    assert client.post(f"{S}/drives/{started}/register").status_code == 401
    hr = _recruiter(client)
    assert client.post(f"{S}/drives/{started}/register", headers=hr).status_code == 403


# ---------- attendance and participation ----------

def _registered_drive(client, past=True):
    """Two students register for a drive; returns (drive_id, [registration ids], students)."""
    s1, s2 = _student(client), _student(client, **SECOND)
    drive_id = _drive(days=3)
    for s in (s1, s2):
        assert client.post(f"{S}/drives/{drive_id}/register", headers=s).status_code == 201
    if past:  # the drive has now started
        with SessionLocal() as db:
            db.get(PlacementDrive, drive_id).drive_date = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
    with SessionLocal() as db:
        regs = [r.id for r in db.query(DriveRegistration).order_by(DriveRegistration.id)]
    return drive_id, regs, (s1, s2)


def test_attendance_cannot_be_marked_before_drive_starts(client):
    drive_id, regs, _ = _registered_drive(client, past=False)
    admin = auth(client, *ADMIN)
    r = client.patch(f"{A}/drives/{drive_id}/registrations/{regs[0]}/attendance", json={"status": "PRESENT"},
                     headers=admin)
    assert r.status_code == 409
    assert client.get(f"{A}/drives/{drive_id}/participation", headers=admin).json()["started"] is False


def test_attendance_marking_and_participation_report(client):
    drive_id, regs, (s1, s2) = _registered_drive(client)
    admin = auth(client, *ADMIN)
    mark = lambda reg, status: client.patch(f"{A}/drives/{drive_id}/registrations/{reg}/attendance",
                                            json={"status": status}, headers=admin)
    assert mark(regs[0], "PRESENT").json()["status"] == "PRESENT"
    p = client.get(f"{A}/drives/{drive_id}/participation", headers=admin).json()
    assert (p["registered"], p["present"], p["absent"], p["pending"]) == (2, 1, 0, 1)
    assert p["attendance_percent"] == 100 and p["started"] is True
    assert mark(regs[1], "ABSENT").status_code == 200
    assert mark(regs[0], "ABSENT").status_code == 200  # correction is allowed
    p = client.get(f"{A}/drives/{drive_id}/participation", headers=admin).json()
    assert (p["present"], p["absent"], p["pending"], p["attendance_percent"]) == (0, 2, 0, 0)
    assert {r["college_id"] for r in p["registrations"]} == {"CS2026001", "CS2026002"}
    row = next(d for d in client.get(f"{A}/drives", headers=admin).json() if d["id"] == drive_id)
    assert (row["registered"], row["present"], row["absent"]) == (2, 0, 2)
    assert mark(regs[0], "PRESENT").json()["marked_at"] is not None
    logs = client.get(f"{A}/audit-logs", headers=admin).json()
    assert {"ATTENDANCE_PRESENT", "ATTENDANCE_ABSENT"} <= {entry["action"] for entry in logs}
    mine = client.get(f"{S}/attendance", headers=s1).json()
    assert mine[0]["status"] == "PRESENT" and mine[0]["title"] == "Acme Drive"
    assert client.get(f"{S}/attendance", headers=s2).json()[0]["status"] == "ABSENT"


def test_attendance_validation_and_rbac(client):
    drive_id, regs, (s1, _) = _registered_drive(client)
    admin = auth(client, *ADMIN)
    url = f"{A}/drives/{drive_id}/registrations/{regs[0]}/attendance"
    assert client.patch(url, json={"status": "REGISTERED"}, headers=admin).status_code == 422
    assert client.patch(f"{A}/drives/{drive_id}/registrations/9999/attendance", json={"status": "PRESENT"},
                        headers=admin).status_code == 404
    other_drive = _drive("Other")
    assert client.patch(f"{A}/drives/{other_drive}/registrations/{regs[0]}/attendance", json={"status": "PRESENT"},
                        headers=admin).status_code == 404  # registration belongs to a different drive
    hr = _recruiter(client)
    for h in (s1, hr):
        assert client.patch(url, json={"status": "PRESENT"}, headers=h).status_code == 403
        assert client.get(f"{A}/drives/{drive_id}/participation", headers=h).status_code == 403
    assert client.patch(url, json={"status": "PRESENT"}).status_code == 401


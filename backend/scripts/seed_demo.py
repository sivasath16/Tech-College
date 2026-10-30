"""Demo data for Phase 3: approved recruiters, jobs, drives, and a student with applications at every stage.

Recruiters and job posting arrive in Phase 4/5, so this script stands in for them. Idempotent.
Demo student login: asha@college.edu / Passw0rdOK
"""
import struct
import zlib
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Application, ApplicationStatus, Interview, Job, JobType, OfferLetter, OfferStatus, PlacementDrive, Recruiter, Role,
    Student, User, VerificationStatus,
)

PASSWORD = "Passw0rdOK"


def _logo(name: str, rgb: tuple[int, int, int]) -> str:
    """Write a small solid-colour PNG as a placeholder company logo."""
    size = 64
    row = b"\x00" + bytes(rgb) * size
    raw = zlib.compress(row * size)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", raw) + chunk(b"IEND", b""))
    folder = settings.upload_dir / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.png").write_bytes(png)
    return f"logos/{name}.png"


def _recruiter(db, email, company, person, profile, rgb) -> Recruiter:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user.recruiter
    user = User(email=email, password_hash=hash_password(PASSWORD), role=Role.RECRUITER, is_active=True)
    user.recruiter = Recruiter(company_name=company, contact_person=person, phone="9123456780",
                               company_profile=profile, logo_path=_logo(company.split()[0].lower(), rgb),
                               verification_status=VerificationStatus.APPROVED)
    db.add(user)
    db.flush()
    return user.recruiter


def main() -> None:
    today, now = date.today(), datetime.now(timezone.utc)
    with SessionLocal() as db:
        if db.scalar(select(Job.id).limit(1)):
            print("Demo data already present")
            return
        acme = _recruiter(db, "hr@acme.com", "Acme Technologies", "Ravi Kumar",
                          "Enterprise software and cloud services company.", (31, 78, 95))
        globex = _recruiter(db, "hr@globex.com", "Globex Analytics", "Meera Nair",
                            "Data and AI consulting for global retail brands.", (192, 100, 40))
        nimbus = _recruiter(db, "hr@nimbus.com", "Nimbus Cloud", "Arjun Mehta",
                            "Cloud-native infrastructure start-up.", (60, 130, 90))

        def job(rec, title, kind, location, salary, skills, cgpa, days, desc):
            j = Job(recruiter_id=rec.id, title=title, job_type=kind, description=desc, location=location,
                    salary=salary, required_skills=skills, min_cgpa=cgpa, deadline=today + timedelta(days=days))
            db.add(j)
            return j

        j_backend = job(acme, "Backend Engineer", JobType.JOB, "Pune", "8 - 10 LPA", ["Python", "FastAPI", "SQL"], 7,
                        14, "Design and build REST APIs for the Acme cloud platform.")
        j_intern = job(acme, "Software Engineering Intern", JobType.INTERNSHIP, "Remote", "25,000 / month",
                       ["Python", "Git"], 6.5, 10, "Six-month internship with the platform team.")
        j_data = job(globex, "Data Analyst", JobType.JOB, "Bengaluru", "7 - 9 LPA", ["SQL", "Python", "Tableau"], 7.5,
                     12, "Build dashboards and analyse retail sales data.")
        j_ml = job(globex, "Machine Learning Engineer", JobType.JOB, "Hyderabad", "12 - 15 LPA",
                   ["Python", "TensorFlow", "Statistics"], 9.5, 20, "Productionise forecasting models.")
        j_front = job(nimbus, "Frontend Developer", JobType.JOB, "Mumbai", "6 - 8 LPA", ["React", "JavaScript", "CSS"],
                      7, 9, "Build the Nimbus console UI.")
        j_devops = job(nimbus, "DevOps Intern", JobType.INTERNSHIP, "Pune", "20,000 / month", ["Linux", "Docker"], 6,
                       7, "Help automate CI/CD pipelines.")
        j_qa = job(acme, "QA Automation Engineer", JobType.JOB, "Pune", "5 - 7 LPA", ["Selenium", "Java"], 6.5, 15,
                   "Own the automated regression suite.")

        asha = db.scalar(select(User).where(User.email == "asha@college.edu"))
        if asha is None:
            asha = User(email="asha@college.edu", password_hash=hash_password(PASSWORD), role=Role.STUDENT,
                        is_active=True)
            asha.student = Student(
                college_id="CS2026001", full_name="Asha Rao", mobile="9876543210", department="Computer Science",
                tenth_percent=91.5, twelfth_percent=88, degree_cgpa=8.4, skills=["Python", "SQL", "React"],
                certifications="AWS Cloud Practitioner", is_verified=True)
            db.add(asha)
        db.flush()
        sid = asha.student.id

        def application(j, status, days_ago):
            a = Application(student_id=sid, job_id=j.id, status=status, applied_at=now - timedelta(days=days_ago))
            db.add(a)
            db.flush()
            return a

        application(j_front, ApplicationStatus.APPLIED, 1)
        application(j_data, ApplicationStatus.SHORTLISTED, 3)
        a_int = application(j_intern, ApplicationStatus.INTERVIEW_SCHEDULED, 5)
        db.add(Interview(application_id=a_int.id, scheduled_at=now + timedelta(days=2, hours=3), mode="Online",
                         location="https://meet.example.com/acme-intern", notes="Technical round, 45 minutes."))
        application(j_qa, ApplicationStatus.REJECTED, 8)
        a_sel = application(j_backend, ApplicationStatus.SELECTED, 12)
        db.add(Interview(application_id=a_sel.id, scheduled_at=now - timedelta(days=4), mode="On campus",
                         location="Placement Cell, Block C", notes="Completed - HR round."))
        db.add(OfferLetter(application_id=a_sel.id, status=OfferStatus.ISSUED, package="9 LPA",
                           joining_date=today + timedelta(days=120)))

        db.add_all([
            PlacementDrive(title="Acme Technologies Campus Drive", company_name="Acme Technologies",
                           description="Aptitude test, technical and HR rounds for 2026 graduates.",
                           venue="Main Auditorium", drive_date=now + timedelta(days=6), min_cgpa=7,
                           departments=["Computer Science", "Information Technology"]),
            PlacementDrive(title="Globex Analytics Pool Drive", company_name="Globex Analytics",
                           description="Open to all branches. Bring two printed resumes.", venue="Seminar Hall 2",
                           drive_date=now + timedelta(days=9), min_cgpa=7.5, departments=[]),
            PlacementDrive(title="Nimbus Cloud Hackathon Hiring", company_name="Nimbus Cloud",
                           description="Hackathon-based shortlisting for DevOps roles.", venue="Computer Lab 3",
                           drive_date=now + timedelta(days=13), min_cgpa=0, departments=["Mechanical"]),
        ])
        db.commit()
        print("Seeded demo recruiters, jobs, drives and student asha@college.edu")


if __name__ == "__main__":
    main()

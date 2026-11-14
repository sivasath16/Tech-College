from datetime import date, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.models import (
    Announcement, Application, ApplicationStatus, AuditLog, Job, PlacementDrive, PlacementStatus, Recruiter, Role,
    Student, StudentDocument, User, VerificationStatus,
)
from app.schemas.admin import (
    ActiveUpdate, AdminApplicationOut, AdminJobOut, AdminSummary, AuditLogOut, DriveIn, DriveOut, PlacementUpdate,
    StudentApplicationBrief, StudentDetail, StudentRow,
)
from app.schemas.auth import AnnouncementCreate, AnnouncementOut, RecruiterAdminOut, RejectRequest
from app.services import utcnow

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_only = require_roles(Role.ADMIN)


def _recruiter_out(r: Recruiter) -> RecruiterAdminOut:
    return RecruiterAdminOut.model_validate({**r.__dict__, "email": r.user.email})


@router.get("/recruiters", response_model=list[RecruiterAdminOut])
def list_recruiters(status_filter: VerificationStatus | None = None, db: Session = Depends(get_db),
                    _: User = Depends(admin_only)):
    query = select(Recruiter).order_by(Recruiter.id.desc())
    if status_filter:
        query = query.where(Recruiter.verification_status == status_filter)
    return [_recruiter_out(r) for r in db.scalars(query)]


def _decide(db: Session, recruiter_id: int, admin: User, decision: VerificationStatus, reason: str | None):
    recruiter = db.get(Recruiter, recruiter_id)
    if recruiter is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recruiter not found")
    if recruiter.verification_status != VerificationStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Recruiter already {recruiter.verification_status.value}")
    recruiter.verification_status = decision
    recruiter.rejection_reason = reason
    recruiter.verified_by = admin.id
    db.add(AuditLog(admin_id=admin.id, action=f"RECRUITER_{decision.value}", entity_type="recruiter",
                    entity_id=recruiter.id, details={"company": recruiter.company_name, "reason": reason}))
    db.commit()
    return _recruiter_out(recruiter)


@router.post("/recruiters/{recruiter_id}/approve", response_model=RecruiterAdminOut)
def approve_recruiter(recruiter_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    return _decide(db, recruiter_id, admin, VerificationStatus.APPROVED, None)


@router.post("/recruiters/{recruiter_id}/reject", response_model=RecruiterAdminOut)
def reject_recruiter(recruiter_id: int, body: RejectRequest, db: Session = Depends(get_db),
                     admin: User = Depends(admin_only)):
    return _decide(db, recruiter_id, admin, VerificationStatus.REJECTED, body.reason)


def _audit(db: Session, admin: User, action: str, entity_type: str, entity_id: int | None, **details) -> None:
    db.add(AuditLog(admin_id=admin.id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


# ---------- dashboard summary ----------

@router.get("/summary", response_model=AdminSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    count = lambda q: db.scalar(q) or 0
    students = count(select(func.count()).select_from(Student))
    placed = count(select(func.count()).select_from(Student).where(Student.placement_status == PlacementStatus.PLACED))
    by_status = {s.value: 0 for s in ApplicationStatus}
    by_status.update({k.value: v for k, v in db.execute(
        select(Application.status, func.count()).group_by(Application.status)).all()})
    return AdminSummary(
        students=students, placed=placed, placement_percent=round(100 * placed / students, 1) if students else 0,
        recruiters_pending=count(select(func.count()).select_from(Recruiter).where(
            Recruiter.verification_status == VerificationStatus.PENDING)),
        recruiters_approved=count(select(func.count()).select_from(Recruiter).where(
            Recruiter.verification_status == VerificationStatus.APPROVED)),
        jobs_pending=count(select(func.count()).select_from(Job).where(
            Job.verification_status == VerificationStatus.PENDING)),
        jobs_published=count(select(func.count()).select_from(Job).where(
            Job.verification_status == VerificationStatus.APPROVED, Job.is_active.is_(True),
            Job.deadline >= date.today())),
        drives_upcoming=count(select(func.count()).select_from(PlacementDrive).where(
            PlacementDrive.drive_date >= utcnow())),
        applications=sum(by_status.values()), applications_by_status=by_status,
    )


# ---------- student database ----------

def _student_row(s: Student) -> dict:
    return {**s.__dict__, "email": s.user.email, "is_active": s.user.is_active, "has_resume": bool(s.resume_path)}


def _get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student


@router.get("/students", response_model=list[StudentRow])
def list_students(q: str | None = None, department: str | None = None, min_cgpa: float | None = None,
                  placement_status: PlacementStatus | None = None, is_active: bool | None = None,
                  db: Session = Depends(get_db), _: User = Depends(admin_only)):
    query = select(Student).join(User, Student.user_id == User.id).order_by(Student.id.desc())
    if q:
        like = f"%{q.strip()}%"
        query = query.where(Student.full_name.ilike(like) | Student.college_id.ilike(like) | User.email.ilike(like))
    if department:
        query = query.where(func.lower(Student.department) == department.strip().lower())
    if min_cgpa is not None:
        query = query.where(Student.degree_cgpa >= min_cgpa)
    if placement_status:
        query = query.where(Student.placement_status == placement_status)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    return [StudentRow.model_validate(_student_row(s)) for s in db.scalars(query)]


@router.get("/students/{student_id}", response_model=StudentDetail)
def student_detail(student_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    s = _get_student(db, student_id)
    apps = db.scalars(select(Application).where(Application.student_id == s.id).order_by(Application.id.desc())
                      .options(joinedload(Application.job).joinedload(Job.recruiter))).unique()
    certs = db.scalars(select(StudentDocument).where(StudentDocument.student_id == s.id).order_by(StudentDocument.id))
    return StudentDetail.model_validate({
        **_student_row(s), "certificates": list(certs),
        "applications": [StudentApplicationBrief(id=a.id, job_title=a.job.title, company_name=a.job.recruiter.company_name,
                                                 status=a.status, applied_at=a.applied_at) for a in apps],
    })


@router.get("/students/{student_id}/resume")
def student_resume(student_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    s = _get_student(db, student_id)
    if not s.resume_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student has no resume")
    path = settings.upload_dir / s.resume_path
    return FileResponse(path, filename=f"{s.college_id}_resume{path.suffix}")


@router.patch("/students/{student_id}/active", response_model=StudentRow)
def set_student_active(student_id: int, body: ActiveUpdate, db: Session = Depends(get_db),
                       admin: User = Depends(admin_only)):
    s = _get_student(db, student_id)
    s.user.is_active = body.is_active
    _audit(db, admin, "STUDENT_ACTIVATED" if body.is_active else "STUDENT_DEACTIVATED", "student", s.id,
           college_id=s.college_id)
    db.commit()
    return StudentRow.model_validate(_student_row(s))


@router.put("/students/{student_id}/placement-status", response_model=StudentRow)
def set_placement_status(student_id: int, body: PlacementUpdate, db: Session = Depends(get_db),
                         admin: User = Depends(admin_only)):
    s = _get_student(db, student_id)
    previous, s.placement_status = s.placement_status, body.placement_status
    _audit(db, admin, "PLACEMENT_STATUS_CHANGED", "student", s.id, college_id=s.college_id,
           previous=previous.value, current=body.placement_status.value)
    db.commit()
    return StudentRow.model_validate(_student_row(s))


# ---------- job posting verification ----------

def _job_out(db: Session, job: Job) -> AdminJobOut:
    applicants = db.scalar(select(func.count()).select_from(Application).where(Application.job_id == job.id)) or 0
    return AdminJobOut(
        id=job.id, title=job.title, job_type=job.job_type, company_name=job.recruiter.company_name,
        description=job.description, location=job.location, salary=job.salary, required_skills=job.required_skills,
        min_cgpa=float(job.min_cgpa), eligible_departments=job.eligible_departments, deadline=job.deadline,
        is_active=job.is_active, verification_status=job.verification_status, rejection_reason=job.rejection_reason,
        created_at=job.created_at, applicants=applicants,
    )


@router.get("/jobs", response_model=list[AdminJobOut])
def list_jobs(status_filter: VerificationStatus | None = None, db: Session = Depends(get_db),
              _: User = Depends(admin_only)):
    query = select(Job).options(joinedload(Job.recruiter)).order_by(Job.id.desc())
    if status_filter:
        query = query.where(Job.verification_status == status_filter)
    return [_job_out(db, j) for j in db.scalars(query)]


def _decide_job(db: Session, job_id: int, admin: User, decision: VerificationStatus, reason: str | None):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.verification_status != VerificationStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Job already {job.verification_status.value}")
    job.verification_status, job.rejection_reason, job.verified_by = decision, reason, admin.id
    _audit(db, admin, f"JOB_{decision.value}", "job", job.id, title=job.title,
           company=job.recruiter.company_name, reason=reason)
    db.commit()
    return _job_out(db, job)


@router.post("/jobs/{job_id}/approve", response_model=AdminJobOut)
def approve_job(job_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    return _decide_job(db, job_id, admin, VerificationStatus.APPROVED, None)


@router.post("/jobs/{job_id}/reject", response_model=AdminJobOut)
def reject_job(job_id: int, body: RejectRequest, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    return _decide_job(db, job_id, admin, VerificationStatus.REJECTED, body.reason)


# ---------- placement drives ----------

def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _drive_out(d: PlacementDrive) -> DriveOut:
    return DriveOut.model_validate({**d.__dict__, "min_cgpa": float(d.min_cgpa), "upcoming": d.drive_date >= utcnow()})


def _get_drive(db: Session, drive_id: int) -> PlacementDrive:
    drive = db.get(PlacementDrive, drive_id)
    if drive is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drive not found")
    return drive


@router.get("/drives", response_model=list[DriveOut])
def list_drives(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [_drive_out(d) for d in db.scalars(select(PlacementDrive).order_by(PlacementDrive.drive_date.desc()))]


@router.post("/drives", response_model=DriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(body: DriveIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    when = _aware(body.drive_date)
    if when <= utcnow():
        raise HTTPException(422, "Drive date must be in the future")
    fields = body.model_dump(exclude={"announce"})
    drive = PlacementDrive(**{**fields, "drive_date": when})
    db.add(drive)
    db.flush()
    if body.announce:
        db.add(Announcement(
            title=f"Placement drive: {drive.title}", created_by=admin.id,
            body=f"{drive.company_name} on {when:%d %b %Y, %H:%M} UTC at {drive.venue}. {drive.description}"))
    _audit(db, admin, "DRIVE_CREATED", "drive", drive.id, title=drive.title, announced=body.announce)
    db.commit()
    return _drive_out(drive)


@router.put("/drives/{drive_id}", response_model=DriveOut)
def update_drive(drive_id: int, body: DriveIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    drive = _get_drive(db, drive_id)
    for field, value in body.model_dump(exclude={"announce"}).items():
        setattr(drive, field, _aware(value) if field == "drive_date" else value)
    _audit(db, admin, "DRIVE_UPDATED", "drive", drive.id, title=drive.title)
    db.commit()
    return _drive_out(drive)


@router.delete("/drives/{drive_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drive(drive_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    drive = _get_drive(db, drive_id)
    _audit(db, admin, "DRIVE_DELETED", "drive", drive.id, title=drive.title)
    db.delete(drive)
    db.commit()


# ---------- announcements ----------

@router.get("/announcements", response_model=list[AnnouncementOut])
def list_all_announcements(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(Announcement).order_by(Announcement.id.desc())).all()


def _get_announcement(db: Session, item_id: int) -> Announcement:
    item = db.get(Announcement, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Announcement not found")
    return item


@router.put("/announcements/{item_id}", response_model=AnnouncementOut)
def update_announcement(item_id: int, body: AnnouncementCreate, db: Session = Depends(get_db),
                        admin: User = Depends(admin_only)):
    item = _get_announcement(db, item_id)
    item.title, item.body = body.title, body.body
    _audit(db, admin, "ANNOUNCEMENT_UPDATED", "announcement", item.id, title=item.title)
    db.commit()
    return item


@router.delete("/announcements/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(item_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    item = _get_announcement(db, item_id)
    _audit(db, admin, "ANNOUNCEMENT_DELETED", "announcement", item.id, title=item.title)
    db.delete(item)
    db.commit()


# ---------- application tracking and selection management ----------

def _application_row(a: Application) -> AdminApplicationOut:
    s = a.student
    return AdminApplicationOut(
        id=a.id, student_id=s.id, college_id=s.college_id, student_name=s.full_name, department=s.department,
        degree_cgpa=float(s.degree_cgpa), placement_status=s.placement_status, job_id=a.job_id, job_title=a.job.title,
        company_name=a.job.recruiter.company_name, status=a.status, applied_at=a.applied_at, updated_at=a.updated_at,
        interviews=len(a.interviews),
    )


@router.get("/applications", response_model=list[AdminApplicationOut])
def list_applications(status_filter: ApplicationStatus | None = None, job_id: int | None = None,
                      company: str | None = None, department: str | None = None, db: Session = Depends(get_db),
                      _: User = Depends(admin_only)):
    query = (select(Application).join(Job).join(Recruiter, Job.recruiter_id == Recruiter.id)
             .join(Student, Application.student_id == Student.id)
             .options(joinedload(Application.job).joinedload(Job.recruiter), joinedload(Application.student),
                      joinedload(Application.interviews))
             .order_by(Application.updated_at.desc(), Application.id.desc()))
    if status_filter:
        query = query.where(Application.status == status_filter)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    if company:
        query = query.where(Recruiter.company_name.ilike(f"%{company.strip()}%"))
    if department:
        query = query.where(func.lower(Student.department) == department.strip().lower())
    return [_application_row(a) for a in db.scalars(query).unique()]


@router.post("/applications/{application_id}/confirm-placement", response_model=AdminApplicationOut)
def confirm_placement(application_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Placement cell confirms a recruiter's selection: the student becomes PLACED."""
    a = db.scalar(select(Application).where(Application.id == application_id).options(
        joinedload(Application.job).joinedload(Job.recruiter), joinedload(Application.student),
        joinedload(Application.interviews)))
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if a.status != ApplicationStatus.SELECTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a selected candidate can be confirmed as placed")
    if a.student.placement_status == PlacementStatus.PLACED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Student is already marked as placed")
    a.student.placement_status = PlacementStatus.PLACED
    _audit(db, admin, "PLACEMENT_CONFIRMED", "application", a.id, college_id=a.student.college_id,
           job=a.job.title, company=a.job.recruiter.company_name)
    db.commit()
    return _application_row(a)


# ---------- audit trail ----------

@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(limit: int = 50, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    rows = db.scalars(select(AuditLog).options(joinedload(AuditLog.admin)).order_by(AuditLog.id.desc())
                      .limit(max(1, min(limit, 200))))
    return [AuditLogOut.model_validate({**r.__dict__, "admin_email": r.admin.email}) for r in rows]

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.models import (
    Application, ApplicationStatus, Job, JobType, PlacementDrive, Recruiter, Role, Student,
    StudentDocument, User, VerificationStatus,
)
from app.schemas.auth import StudentOut
from app.schemas.student import (
    ApplicationOut, ApplyRequest, DashboardSummary, DocumentOut, DocumentsOut, DriveOut, InterviewUpdateOut, JobOut,
    OfferUpdateOut, ProfileUpdate,
)
from app.services import CERTIFICATE_EXTS, RESUME_EXTS, delete_file, save_document, utcnow

router = APIRouter(prefix="/student", tags=["Student"])


def current_student(user: User = Depends(require_roles(Role.STUDENT))) -> Student:
    return user.student


def _ineligible_reason(student: Student, min_cgpa: float, departments: list[str] | None = None) -> str | None:
    if float(student.degree_cgpa) < float(min_cgpa):
        return f"Minimum CGPA {float(min_cgpa):g} required (yours is {float(student.degree_cgpa):g})"
    if departments and student.department.lower() not in {d.lower() for d in departments}:
        return f"Open to {', '.join(departments)} only"
    return None


# ---------- profile ----------

@router.get("/profile", response_model=StudentOut)
def get_profile(student: Student = Depends(current_student)):
    return student


@router.put("/profile", response_model=StudentOut)
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db), student: Student = Depends(current_student)):
    for field, value in body.model_dump().items():
        setattr(student, field, value)
    db.add(student)
    db.commit()
    return student


# ---------- documents (private: served only to the owner through an authenticated endpoint) ----------

def _documents_out(db: Session, student: Student) -> DocumentsOut:
    docs = db.scalars(select(StudentDocument).where(StudentDocument.student_id == student.id)
                      .order_by(StudentDocument.id.desc())).all()
    resume_name = f"resume{student.resume_path[student.resume_path.rfind('.'):]}" if student.resume_path else None
    return DocumentsOut(resume_name=resume_name, certificates=[DocumentOut.model_validate(d) for d in docs])


@router.get("/documents", response_model=DocumentsOut)
def list_documents(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    return _documents_out(db, student)


@router.post("/resume", response_model=DocumentsOut)
async def upload_resume(file: UploadFile = File(), db: Session = Depends(get_db),
                        student: Student = Depends(current_student)):
    new_path = await save_document(file, "resumes", RESUME_EXTS)
    old_path, student.resume_path = student.resume_path, new_path
    db.add(student)
    db.commit()
    delete_file(old_path)
    return _documents_out(db, student)


@router.get("/resume")
def download_resume(student: Student = Depends(current_student)):
    if not student.resume_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded")
    path = settings.upload_dir / student.resume_path
    return FileResponse(path, filename=f"{student.college_id}_resume{path.suffix}")


@router.post("/certificates", response_model=DocumentsOut, status_code=status.HTTP_201_CREATED)
async def upload_certificate(title: str = Form(min_length=2, max_length=150), file: UploadFile = File(),
                             db: Session = Depends(get_db), student: Student = Depends(current_student)):
    count = db.scalar(select(func.count()).select_from(StudentDocument).where(StudentDocument.student_id == student.id))
    if count >= settings.max_certificates:
        raise HTTPException(status.HTTP_409_CONFLICT, f"At most {settings.max_certificates} certificates allowed")
    path = await save_document(file, "certificates", CERTIFICATE_EXTS)
    db.add(StudentDocument(student_id=student.id, title=title.strip(), original_name=(file.filename or "file")[:255],
                           path=path))
    db.commit()
    return _documents_out(db, student)


def _own_certificate(db: Session, student: Student, doc_id: int) -> StudentDocument:
    doc = db.get(StudentDocument, doc_id)
    if doc is None or doc.student_id != student.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    return doc


@router.get("/certificates/{doc_id}")
def download_certificate(doc_id: int, db: Session = Depends(get_db), student: Student = Depends(current_student)):
    doc = _own_certificate(db, student, doc_id)
    return FileResponse(settings.upload_dir / doc.path, filename=doc.original_name)


@router.delete("/certificates/{doc_id}", response_model=DocumentsOut)
def delete_certificate(doc_id: int, db: Session = Depends(get_db), student: Student = Depends(current_student)):
    doc = _own_certificate(db, student, doc_id)
    db.delete(doc)
    db.commit()
    delete_file(doc.path)
    return _documents_out(db, student)


# ---------- jobs & internships ----------

def _job_out(job: Job, student: Student, applied: dict[int, ApplicationStatus]) -> JobOut:
    reason = _ineligible_reason(student, job.min_cgpa)
    return JobOut(
        id=job.id, title=job.title, job_type=job.job_type, company_name=job.recruiter.company_name,
        company_logo=job.recruiter.logo_path, description=job.description, location=job.location,
        salary=job.salary, required_skills=job.required_skills, min_cgpa=float(job.min_cgpa),
        deadline=job.deadline, eligible=reason is None, ineligible_reason=reason,
        application_status=applied.get(job.id),
    )


def _applied_map(db: Session, student: Student) -> dict[int, ApplicationStatus]:
    rows = db.execute(select(Application.job_id, Application.status).where(Application.student_id == student.id))
    return {job_id: st for job_id, st in rows}


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(job_type: JobType | None = None, q: str | None = None, db: Session = Depends(get_db),
              student: Student = Depends(current_student)):
    query = (select(Job).join(Recruiter).options(joinedload(Job.recruiter))
             .where(Job.is_active.is_(True), Job.deadline >= date.today(),
                    Recruiter.verification_status == VerificationStatus.APPROVED)
             .order_by(Job.deadline, Job.id))
    if job_type:
        query = query.where(Job.job_type == job_type)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Job.title.ilike(like), Recruiter.company_name.ilike(like), Job.location.ilike(like)))
    applied = _applied_map(db, student)
    return [_job_out(j, student, applied) for j in db.scalars(query)]


# ---------- applications ----------

def _application_out(a: Application) -> ApplicationOut:
    return ApplicationOut(
        id=a.id, job_id=a.job_id, job_title=a.job.title, job_type=a.job.job_type,
        company_name=a.job.recruiter.company_name, status=a.status, applied_at=a.applied_at,
        updated_at=a.updated_at, interviews=a.interviews, offer=a.offer,
    )


def _applications(db: Session, student: Student) -> list[Application]:
    return list(db.scalars(
        select(Application).where(Application.student_id == student.id).order_by(Application.id.desc())
        .options(joinedload(Application.job).joinedload(Job.recruiter), joinedload(Application.offer),
                 joinedload(Application.interviews))
    ).unique())


@router.post("/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_to_job(body: ApplyRequest, db: Session = Depends(get_db), student: Student = Depends(current_student)):
    job = db.get(Job, body.job_id)
    if (job is None or not job.is_active
            or job.recruiter.verification_status != VerificationStatus.APPROVED):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.deadline < date.today():
        raise HTTPException(status.HTTP_409_CONFLICT, "Application deadline has passed")
    if (reason := _ineligible_reason(student, job.min_cgpa)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Not eligible: {reason}")
    if not student.resume_path:
        raise HTTPException(status.HTTP_409_CONFLICT, "Upload your resume before applying")
    if db.scalar(select(Application.id).where(Application.student_id == student.id, Application.job_id == job.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this job")
    application = Application(student_id=student.id, job_id=job.id, status=ApplicationStatus.APPLIED)
    db.add(application)
    db.commit()
    db.refresh(application)
    return _application_out(application)


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    return [_application_out(a) for a in _applications(db, student)]


# ---------- placement drives, interviews, offers ----------

@router.get("/drives", response_model=list[DriveOut])
def list_drives(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    drives = db.scalars(select(PlacementDrive).where(PlacementDrive.drive_date >= utcnow())
                        .order_by(PlacementDrive.drive_date))
    out = []
    for d in drives:
        reason = _ineligible_reason(student, d.min_cgpa, d.departments)
        out.append(DriveOut(id=d.id, title=d.title, company_name=d.company_name, description=d.description,
                            venue=d.venue, drive_date=d.drive_date, min_cgpa=float(d.min_cgpa),
                            departments=d.departments, eligible=reason is None, ineligible_reason=reason))
    return out


@router.get("/interviews", response_model=list[InterviewUpdateOut])
def list_interviews(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    rows = [(a, i) for a in _applications(db, student) for i in a.interviews]
    rows.sort(key=lambda r: r[1].scheduled_at)
    return [InterviewUpdateOut(application_id=a.id, job_title=a.job.title, company_name=a.job.recruiter.company_name,
                               scheduled_at=i.scheduled_at, mode=i.mode, location=i.location, notes=i.notes)
            for a, i in rows]


@router.get("/offers", response_model=list[OfferUpdateOut])
def list_offers(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    return [OfferUpdateOut(application_id=a.id, job_title=a.job.title, company_name=a.job.recruiter.company_name,
                           status=a.offer.status, package=a.offer.package, joining_date=a.offer.joining_date)
            for a in _applications(db, student) if a.offer]


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), student: Student = Depends(current_student)):
    apps = _applications(db, student)
    now = utcnow()
    certs = db.scalar(select(func.count()).select_from(StudentDocument).where(StudentDocument.student_id == student.id))
    completion = 40 + 20 * bool(student.skills) + 20 * bool(student.resume_path) + 20 * bool(certs)
    return DashboardSummary(
        applications=len(apps),
        shortlisted=sum(a.status == ApplicationStatus.SHORTLISTED for a in apps),
        interviews_upcoming=sum(i.scheduled_at >= now for a in apps for i in a.interviews),
        offers=sum(a.offer is not None for a in apps),
        profile_completion=completion,
    )

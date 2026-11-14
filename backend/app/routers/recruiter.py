from datetime import date, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.models import (
    Application, ApplicationStatus, Interview, Job, PlacementStatus, Recruiter, Role, Student, User,
    VerificationStatus,
)
from app.schemas.auth import RecruiterOut
from app.schemas.recruiter import (
    ApplicantOut, CandidateOut, CompanyProfileUpdate, InterviewIn, JobIn, RecruiterJobOut, RecruiterSummary,
    StatusUpdate,
)
from app.services import delete_file, save_logo, utcnow

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

# Statuses a recruiter may move an application to from the current one.
# Interview scheduling (-> INTERVIEW_SCHEDULED) has its own endpoint because it needs date, mode and venue.
TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.APPLIED: {ApplicationStatus.SHORTLISTED, ApplicationStatus.REJECTED},
    ApplicationStatus.SHORTLISTED: {ApplicationStatus.REJECTED},
    ApplicationStatus.INTERVIEW_SCHEDULED: {ApplicationStatus.INTERVIEWED, ApplicationStatus.REJECTED},
    ApplicationStatus.INTERVIEWED: {ApplicationStatus.SELECTED, ApplicationStatus.REJECTED},
}
CAN_SCHEDULE = {ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.INTERVIEWED}


def current_recruiter(user: User = Depends(require_roles(Role.RECRUITER))) -> Recruiter:
    recruiter = user.recruiter
    if recruiter.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Recruiter account is not verified")
    return recruiter


# ---------- company profile ----------

@router.put("/profile", response_model=RecruiterOut)
def update_profile(body: CompanyProfileUpdate, db: Session = Depends(get_db),
                   recruiter: Recruiter = Depends(current_recruiter)):
    for field, value in body.model_dump().items():
        setattr(recruiter, field, value.strip())
    db.add(recruiter)
    db.commit()
    return recruiter


@router.post("/logo", response_model=RecruiterOut)
async def replace_logo(logo: UploadFile = File(), db: Session = Depends(get_db),
                       recruiter: Recruiter = Depends(current_recruiter)):
    new_path = await save_logo(logo)
    old_path, recruiter.logo_path = recruiter.logo_path, new_path
    db.add(recruiter)
    db.commit()
    delete_file(old_path)
    return recruiter


# ---------- job postings ----------

def _job_out(db: Session, job: Job) -> RecruiterJobOut:
    counts = dict(db.execute(
        select(Application.status, func.count()).where(Application.job_id == job.id).group_by(Application.status)
    ).all())
    return RecruiterJobOut(
        id=job.id, title=job.title, job_type=job.job_type, description=job.description, location=job.location,
        salary=job.salary, required_skills=job.required_skills, min_cgpa=float(job.min_cgpa),
        eligible_departments=job.eligible_departments, deadline=job.deadline, is_active=job.is_active,
        verification_status=job.verification_status, rejection_reason=job.rejection_reason,
        expired=job.deadline < date.today(), created_at=job.created_at,
        applicants=sum(counts.values()), shortlisted=counts.get(ApplicationStatus.SHORTLISTED, 0),
        selected=counts.get(ApplicationStatus.SELECTED, 0),
    )


def _own_job(db: Session, recruiter: Recruiter, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.recruiter_id != recruiter.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("/jobs", response_model=RecruiterJobOut, status_code=status.HTTP_201_CREATED)
def create_job(body: JobIn, db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    job = Job(recruiter_id=recruiter.id, **body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_out(db, job)


@router.get("/jobs", response_model=list[RecruiterJobOut])
def list_jobs(db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    jobs = db.scalars(select(Job).where(Job.recruiter_id == recruiter.id).order_by(Job.id.desc()))
    return [_job_out(db, j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=RecruiterJobOut)
def get_job(job_id: int, db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    return _job_out(db, _own_job(db, recruiter, job_id))


@router.put("/jobs/{job_id}", response_model=RecruiterJobOut)
def update_job(job_id: int, body: JobIn, db: Session = Depends(get_db),
               recruiter: Recruiter = Depends(current_recruiter)):
    job = _own_job(db, recruiter, job_id)
    for field, value in body.model_dump().items():
        setattr(job, field, value)
    # Any edit sends the posting back to the placement cell, so students never see unverified content.
    job.verification_status = VerificationStatus.PENDING
    job.rejection_reason = None
    db.commit()
    return _job_out(db, job)


@router.post("/jobs/{job_id}/close", response_model=RecruiterJobOut)
def close_job(job_id: int, db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    job = _own_job(db, recruiter, job_id)
    job.is_active = False
    db.commit()
    return _job_out(db, job)


@router.post("/jobs/{job_id}/reopen", response_model=RecruiterJobOut)
def reopen_job(job_id: int, db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    job = _own_job(db, recruiter, job_id)
    if job.deadline < date.today():
        raise HTTPException(status.HTTP_409_CONFLICT, "Deadline has passed: edit the job and set a new deadline")
    job.is_active = True
    db.commit()
    return _job_out(db, job)


# ---------- candidate search ----------

def _skill_filter(skill: str):
    """Case-insensitive exact-token match against the student's skills array."""
    token = skill.strip().lower().replace("|", "").replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    padded = func.lower(literal("|").concat(func.array_to_string(Student.skills, "|")).concat("|"))
    return padded.like(f"%|{token}|%", escape="\\")


@router.get("/candidates", response_model=list[CandidateOut])
def search_candidates(
    skills: str | None = None, department: str | None = None, min_cgpa: float | None = None, q: str | None = None,
    eligible_for: int | None = None, placed: bool | None = None, limit: int = 100,
    db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter),
):
    """Search verified students. `skills` is a comma separated list; every skill must match.
    `eligible_for` (a job id of this recruiter) applies that job's CGPA and department criteria."""
    query = select(Student).where(Student.is_verified.is_(True))
    for skill in filter(None, (s.strip() for s in (skills or "").split(","))):
        query = query.where(_skill_filter(skill))
    if department:
        query = query.where(func.lower(Student.department) == department.strip().lower())
    if min_cgpa is not None:
        query = query.where(Student.degree_cgpa >= min_cgpa)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(Student.full_name.ilike(like) | Student.college_id.ilike(like))
    if placed is not None:
        is_placed = Student.placement_status == PlacementStatus.PLACED
        query = query.where(is_placed if placed else ~is_placed)
    if eligible_for is not None:
        job = _own_job(db, recruiter, eligible_for)
        query = query.where(Student.degree_cgpa >= job.min_cgpa)
        if job.eligible_departments:
            query = query.where(func.lower(Student.department).in_([d.lower() for d in job.eligible_departments]))
    rows = db.scalars(query.order_by(Student.degree_cgpa.desc(), Student.id).limit(max(1, min(limit, 200))))
    return [CandidateOut.model_validate({**s.__dict__, "has_resume": bool(s.resume_path)}) for s in rows]


# ---------- applications: review, shortlist, interview, selection ----------

def _applicant_out(a: Application) -> ApplicantOut:
    wanted = {s.lower() for s in a.job.required_skills}
    return ApplicantOut(
        id=a.id, job_id=a.job_id, job_title=a.job.title, status=a.status, applied_at=a.applied_at,
        updated_at=a.updated_at, email=a.student.user.email, mobile=a.student.mobile,
        student=CandidateOut.model_validate({**a.student.__dict__, "has_resume": bool(a.student.resume_path)}),
        skills_match=[s for s in a.student.skills if s.lower() in wanted], interviews=a.interviews,
        offer_status=a.offer.status if a.offer else None,
    )


def _own_application(db: Session, recruiter: Recruiter, application_id: int) -> Application:
    a = db.scalar(select(Application).where(Application.id == application_id).options(
        joinedload(Application.job), joinedload(Application.student).joinedload(Student.user),
        joinedload(Application.interviews), joinedload(Application.offer)))
    if a is None or a.job.recruiter_id != recruiter.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return a


@router.get("/applications", response_model=list[ApplicantOut])
def list_applications(job_id: int | None = None, status_filter: ApplicationStatus | None = None,
                      db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    query = (select(Application).join(Job).where(Job.recruiter_id == recruiter.id)
             .options(joinedload(Application.job), joinedload(Application.student).joinedload(Student.user),
                      joinedload(Application.interviews), joinedload(Application.offer))
             .order_by(Application.id.desc()))
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    if status_filter:
        query = query.where(Application.status == status_filter)
    return [_applicant_out(a) for a in db.scalars(query).unique()]


@router.patch("/applications/{application_id}/status", response_model=ApplicantOut)
def update_status(application_id: int, body: StatusUpdate, db: Session = Depends(get_db),
                  recruiter: Recruiter = Depends(current_recruiter)):
    a = _own_application(db, recruiter, application_id)
    target = ApplicationStatus(body.status)
    if target not in TRANSITIONS.get(a.status, set()):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot change status from {a.status.value} to {target.value}")
    a.status = target
    db.commit()
    return _applicant_out(a)


@router.post("/applications/{application_id}/interviews", response_model=ApplicantOut,
             status_code=status.HTTP_201_CREATED)
def schedule_interview(application_id: int, body: InterviewIn, db: Session = Depends(get_db),
                       recruiter: Recruiter = Depends(current_recruiter)):
    a = _own_application(db, recruiter, application_id)
    if a.status not in CAN_SCHEDULE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Shortlist the candidate before scheduling an interview")
    when = body.scheduled_at if body.scheduled_at.tzinfo else body.scheduled_at.replace(tzinfo=timezone.utc)
    if when <= utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Interview must be scheduled in the future")
    a.interviews.append(Interview(scheduled_at=when, mode=body.mode, location=body.location.strip(), notes=body.notes))
    a.status = ApplicationStatus.INTERVIEW_SCHEDULED
    db.commit()
    db.refresh(a)
    return _applicant_out(a)


@router.get("/applications/{application_id}/resume")
def download_resume(application_id: int, db: Session = Depends(get_db),
                    recruiter: Recruiter = Depends(current_recruiter)):
    a = _own_application(db, recruiter, application_id)
    if not a.student.resume_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate has no resume")
    path = settings.upload_dir / a.student.resume_path
    return FileResponse(path, filename=f"{a.student.college_id}_resume{path.suffix}")


# ---------- dashboard summary ----------

@router.get("/summary", response_model=RecruiterSummary)
def summary(db: Session = Depends(get_db), recruiter: Recruiter = Depends(current_recruiter)):
    jobs = db.scalars(select(Job).where(Job.recruiter_id == recruiter.id)).all()
    apps = list(db.scalars(select(Application).join(Job).where(Job.recruiter_id == recruiter.id)
                           .options(joinedload(Application.interviews))).unique())
    now = utcnow()
    return RecruiterSummary(
        active_jobs=sum(j.is_active and j.deadline >= date.today() for j in jobs), total_jobs=len(jobs),
        applicants=len(apps), shortlisted=sum(a.status == ApplicationStatus.SHORTLISTED for a in apps),
        interviews_upcoming=sum(i.scheduled_at >= now for a in apps for i in a.interviews),
        selected=sum(a.status == ApplicationStatus.SELECTED for a in apps),
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import AuditLog, Recruiter, Role, Student, User, VerificationStatus
from app.schemas.auth import RecruiterAdminOut, RejectRequest, StudentAdminOut

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


@router.get("/students", response_model=list[StudentAdminOut])
def list_students(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    rows = db.scalars(select(Student).order_by(Student.id.desc()))
    return [StudentAdminOut.model_validate({**s.__dict__, "email": s.user.email}) for s in rows]

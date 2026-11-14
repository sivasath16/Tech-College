from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus, JobType, PlacementStatus, VerificationStatus
from app.schemas.auth import StudentAdminOut
from app.schemas.student import DocumentOut


def _clean(values: list[str], limit: int) -> list[str]:
    unique = {v.strip().lower(): v.strip() for v in reversed(values) if v.strip()}
    return list(reversed(unique.values()))[:limit]


class AdminSummary(BaseModel):
    students: int
    placed: int
    placement_percent: float
    recruiters_pending: int
    recruiters_approved: int
    jobs_pending: int
    jobs_published: int
    drives_upcoming: int
    applications: int
    applications_by_status: dict[str, int]


class StudentRow(StudentAdminOut):
    is_active: bool
    has_resume: bool


class StudentApplicationBrief(BaseModel):
    id: int
    job_title: str
    company_name: str
    status: ApplicationStatus
    applied_at: datetime


class StudentDetail(StudentRow):
    certificates: list[DocumentOut]
    applications: list[StudentApplicationBrief]


class ActiveUpdate(BaseModel):
    is_active: bool


class PlacementUpdate(BaseModel):
    placement_status: PlacementStatus


class AdminJobOut(BaseModel):
    id: int
    title: str
    job_type: JobType
    company_name: str
    description: str
    location: str
    salary: str | None
    required_skills: list[str]
    min_cgpa: float
    eligible_departments: list[str]
    deadline: date
    is_active: bool
    verification_status: VerificationStatus
    rejection_reason: str | None
    created_at: datetime
    applicants: int


class DriveIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    company_name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    venue: str = Field(min_length=2, max_length=200)
    drive_date: datetime
    min_cgpa: float = Field(default=0, ge=0, le=10)
    departments: list[str] = []
    announce: bool = Field(default=False, description="Also publish an announcement on the landing page (create only)")

    @field_validator("departments")
    @classmethod
    def clean_departments(cls, v: list[str]) -> list[str]:
        return _clean(v, 20)


class DriveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_name: str
    description: str
    venue: str
    drive_date: datetime
    min_cgpa: float
    departments: list[str]
    upcoming: bool = True


class AdminApplicationOut(BaseModel):
    id: int
    student_id: int
    college_id: str
    student_name: str
    department: str
    degree_cgpa: float
    placement_status: PlacementStatus
    job_id: int
    job_title: str
    company_name: str
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    interviews: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int | None
    details: dict | None
    created_at: datetime
    admin_email: str

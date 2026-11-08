from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus, JobType, OfferStatus, PlacementStatus
from app.schemas.student import InterviewOut


def _clean_list(values: list[str], limit: int) -> list[str]:
    unique = {v.strip().lower(): v.strip() for v in reversed(values) if v.strip()}  # case-insensitive, keep first spelling
    return list(reversed(unique.values()))[:limit]


class CompanyProfileUpdate(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    contact_person: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^[6-9]\d{9}$")
    company_profile: str = Field(min_length=10, max_length=5000)


class JobIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    job_type: JobType
    description: str = Field(min_length=10, max_length=5000)
    location: str = Field(min_length=2, max_length=150)
    salary: str | None = Field(default=None, max_length=100)
    required_skills: list[str] = []
    min_cgpa: float = Field(default=0, ge=0, le=10)
    eligible_departments: list[str] = []
    deadline: date

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        return _clean_list(v, 30)

    @field_validator("eligible_departments")
    @classmethod
    def clean_departments(cls, v: list[str]) -> list[str]:
        return _clean_list(v, 20)

    @field_validator("deadline")
    @classmethod
    def deadline_not_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Deadline cannot be in the past")
        return v


class RecruiterJobOut(BaseModel):
    id: int
    title: str
    job_type: JobType
    description: str
    location: str
    salary: str | None
    required_skills: list[str]
    min_cgpa: float
    eligible_departments: list[str]
    deadline: date
    is_active: bool
    expired: bool
    created_at: datetime
    applicants: int
    shortlisted: int
    selected: int


class CandidateOut(BaseModel):
    """Search result: academic data only, no contact details until the student applies."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: str
    full_name: str
    department: str
    tenth_percent: float
    twelfth_percent: float
    degree_cgpa: float
    skills: list[str]
    certifications: str | None
    placement_status: PlacementStatus
    has_resume: bool = False


class ApplicantOut(BaseModel):
    id: int
    job_id: int
    job_title: str
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    student: CandidateOut
    email: str
    mobile: str
    skills_match: list[str]
    interviews: list[InterviewOut]
    offer_status: OfferStatus | None


class StatusUpdate(BaseModel):
    status: Literal["SHORTLISTED", "INTERVIEWED", "SELECTED", "REJECTED"]


class InterviewIn(BaseModel):
    scheduled_at: datetime
    mode: Literal["Online", "Offline"]
    location: str = Field(min_length=2, max_length=200, description="Meeting link or venue")
    notes: str | None = Field(default=None, max_length=1000)


class RecruiterSummary(BaseModel):
    active_jobs: int
    total_jobs: int
    applicants: int
    shortlisted: int
    interviews_upcoming: int
    selected: int

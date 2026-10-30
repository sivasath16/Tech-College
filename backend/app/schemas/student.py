from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus, JobType, OfferStatus


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    department: str = Field(min_length=2, max_length=100)
    tenth_percent: float = Field(ge=0, le=100)
    twelfth_percent: float = Field(ge=0, le=100)
    degree_cgpa: float = Field(ge=0, le=10)
    skills: list[str] = []
    certifications: str | None = Field(default=None, max_length=2000)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(s.strip() for s in v if s.strip()))[:30]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_name: str
    created_at: datetime


class DocumentsOut(BaseModel):
    resume_name: str | None
    certificates: list[DocumentOut]


class JobOut(BaseModel):
    id: int
    title: str
    job_type: JobType
    company_name: str
    company_logo: str | None
    description: str
    location: str
    salary: str | None
    required_skills: list[str]
    min_cgpa: float
    deadline: date
    eligible: bool
    ineligible_reason: str | None
    application_status: ApplicationStatus | None


class ApplyRequest(BaseModel):
    job_id: int


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_at: datetime
    mode: str
    location: str
    notes: str | None


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: OfferStatus
    package: str | None
    joining_date: date | None


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    job_title: str
    job_type: JobType
    company_name: str
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    interviews: list[InterviewOut]
    offer: OfferOut | None


class DriveOut(BaseModel):
    id: int
    title: str
    company_name: str
    description: str
    venue: str
    drive_date: datetime
    min_cgpa: float
    departments: list[str]
    eligible: bool
    ineligible_reason: str | None


class InterviewUpdateOut(BaseModel):
    application_id: int
    job_title: str
    company_name: str
    scheduled_at: datetime
    mode: str
    location: str
    notes: str | None


class OfferUpdateOut(BaseModel):
    application_id: int
    job_title: str
    company_name: str
    status: OfferStatus
    package: str | None
    joining_date: date | None


class DashboardSummary(BaseModel):
    applications: int
    shortlisted: int
    interviews_upcoming: int
    offers: int
    profile_completion: int

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import is_strong_password
from app.models.enums import PlacementStatus, Role, VerificationStatus

MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def _check_mobile(v: str) -> str:
    v = v.strip()
    if not MOBILE_RE.match(v):
        raise ValueError("Mobile must be a valid 10-digit number")
    return v


def _check_password(v: str) -> str:
    if not is_strong_password(v):
        raise ValueError("Password must be 8-64 chars with upper, lower case and a digit")
    return v


class OtpSendRequest(BaseModel):
    mobile: str

    _mobile = field_validator("mobile")(_check_mobile)


class OtpSendResponse(BaseModel):
    message: str
    expires_in_minutes: int
    dev_otp: str | None = None


class OtpVerifyRequest(BaseModel):
    mobile: str
    code: str = Field(pattern=r"^\d{6}$")

    _mobile = field_validator("mobile")(_check_mobile)


class StudentRegister(BaseModel):
    college_id: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    mobile: str
    password: str
    department: str = Field(min_length=2, max_length=100)
    tenth_percent: float = Field(ge=0, le=100)
    twelfth_percent: float = Field(ge=0, le=100)
    degree_cgpa: float = Field(ge=0, le=10)
    skills: list[str] = []
    certifications: str | None = None

    _mobile = field_validator("mobile")(_check_mobile)
    _password = field_validator("password")(_check_password)

    @field_validator("college_id")
    @classmethod
    def clean_college_id(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v if s.strip()][:30]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    college_id: str
    full_name: str
    mobile: str
    department: str
    tenth_percent: float
    twelfth_percent: float
    degree_cgpa: float
    skills: list[str]
    certifications: str | None
    placement_status: PlacementStatus
    is_verified: bool


class RecruiterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    contact_person: str
    phone: str
    company_profile: str
    logo_path: str | None
    verification_status: VerificationStatus
    rejection_reason: str | None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    student: StudentOut | None = None
    recruiter: RecruiterOut | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RecruiterAdminOut(RecruiterOut):
    email: EmailStr


class StudentAdminOut(StudentOut):
    id: int
    email: EmailStr


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3)


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    created_at: datetime

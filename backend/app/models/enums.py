import enum


class Role(str, enum.Enum):
    STUDENT = "STUDENT"
    RECRUITER = "RECRUITER"
    ADMIN = "ADMIN"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PlacementStatus(str, enum.Enum):
    PLACED = "PLACED"
    NOT_PLACED = "NOT_PLACED"


class JobType(str, enum.Enum):
    JOB = "JOB"
    INTERNSHIP = "INTERNSHIP"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEWED = "INTERVIEWED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class OfferStatus(str, enum.Enum):
    PENDING = "PENDING"
    ISSUED = "ISSUED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"

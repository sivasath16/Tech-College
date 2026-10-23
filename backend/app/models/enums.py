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

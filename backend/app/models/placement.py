from datetime import date, datetime

from sqlalchemy import ARRAY, Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApplicationStatus, JobType, OfferStatus
from app.models.user import Recruiter, Student


class StudentDocument(Base):
    """Certificate uploaded by a student (the resume lives on `students.resume_path`)."""

    __tablename__ = "student_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    original_name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("recruiters.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    job_type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), default=JobType.JOB)
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(150))
    salary: Mapped[str | None] = mapped_column(String(100))
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_cgpa: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    deadline: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recruiter: Mapped[Recruiter] = relationship()


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("student_id", "job_id", name="uq_application_student_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.APPLIED
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student: Mapped[Student] = relationship()
    job: Mapped[Job] = relationship()
    interviews: Mapped[list["Interview"]] = relationship(back_populates="application", order_by="Interview.scheduled_at")
    offer: Mapped["OfferLetter | None"] = relationship(back_populates="application", uselist=False)


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(30))
    location: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="interviews")


class OfferLetter(Base):
    __tablename__ = "offer_letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus, name="offer_status"), default=OfferStatus.PENDING)
    package: Mapped[str | None] = mapped_column(String(100))
    joining_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    application: Mapped[Application] = relationship(back_populates="offer")


class PlacementDrive(Base):
    __tablename__ = "placement_drives"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    venue: Mapped[str] = mapped_column(String(200))
    drive_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    min_cgpa: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    departments: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

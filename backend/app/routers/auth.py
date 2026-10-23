from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token, generate_otp, hash_otp, hash_password, is_strong_password, verify_password,
)
from app.models import OtpVerification, Recruiter, Role, Student, User, VerificationStatus
from app.schemas.auth import (
    LoginRequest, OtpSendRequest, OtpSendResponse, OtpVerifyRequest, StudentRegister, TokenResponse, UserOut,
)
from app.services import log, otp_expiry, save_logo, utcnow

router = APIRouter(prefix="/auth", tags=["Authentication"])

OTP_VALID_FOR_REGISTRATION = timedelta(minutes=30)
email_adapter = TypeAdapter(EmailStr)


def _email_taken(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email.lower())) is not None


@router.post("/otp/send", response_model=OtpSendResponse)
def send_otp(body: OtpSendRequest, db: Session = Depends(get_db)):
    code = generate_otp()
    db.add(OtpVerification(mobile=body.mobile, code_hash=hash_otp(body.mobile, code), expires_at=otp_expiry()))
    db.commit()
    log.warning("MOCK SMS -> %s : your placement portal OTP is %s", body.mobile, code)
    return OtpSendResponse(
        message="OTP sent to mobile number",
        expires_in_minutes=settings.otp_expire_minutes,
        dev_otp=code if settings.environment != "production" else None,
    )


@router.post("/otp/verify")
def verify_otp(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    otp = db.scalar(
        select(OtpVerification)
        .where(OtpVerification.mobile == body.mobile, OtpVerification.verified.is_(False))
        .order_by(OtpVerification.id.desc())
    )
    if otp is None or otp.expires_at < utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP expired or not requested")
    if otp.attempts >= settings.otp_max_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, request a new OTP")
    otp.attempts += 1
    if otp.code_hash != hash_otp(body.mobile, body.code):
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect OTP")
    otp.verified = True
    db.commit()
    return {"message": "Mobile number verified"}


@router.post("/register/student", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_student(body: StudentRegister, db: Session = Depends(get_db)):
    otp = db.scalar(
        select(OtpVerification)
        .where(OtpVerification.mobile == body.mobile, OtpVerification.verified.is_(True),
               OtpVerification.consumed.is_(False))
        .order_by(OtpVerification.id.desc())
    )
    if otp is None or utcnow() - otp.expires_at > OTP_VALID_FOR_REGISTRATION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verify your mobile number with OTP first")
    if _email_taken(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if db.scalar(select(Student.id).where(Student.college_id == body.college_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "College ID already registered")

    user = User(email=body.email.lower(), password_hash=hash_password(body.password), role=Role.STUDENT, is_active=True)
    user.student = Student(
        college_id=body.college_id, full_name=body.full_name, mobile=body.mobile, department=body.department,
        tenth_percent=body.tenth_percent, twelfth_percent=body.twelfth_percent, degree_cgpa=body.degree_cgpa,
        skills=body.skills, certifications=body.certifications, is_verified=True,
    )
    otp.consumed = True
    db.add(user)
    db.commit()
    return user


@router.post("/register/recruiter", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_recruiter(
    company_name: str = Form(min_length=2, max_length=200),
    contact_person: str = Form(min_length=2, max_length=150),
    email: str = Form(),
    phone: str = Form(pattern=r"^[6-9]\d{9}$"),
    company_profile: str = Form(min_length=10),
    password: str = Form(),
    logo: UploadFile = File(),
    db: Session = Depends(get_db),
):
    try:
        email = str(email_adapter.validate_python(email)).lower()
    except ValidationError:
        raise HTTPException(422, "Invalid email address")
    if not is_strong_password(password):
        raise HTTPException(422,
                            "Password must be 8-64 chars with upper, lower case and a digit")
    if _email_taken(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    logo_path = await save_logo(logo)

    user = User(email=email, password_hash=hash_password(password), role=Role.RECRUITER, is_active=True)
    user.recruiter = Recruiter(
        company_name=company_name, contact_person=contact_person, phone=phone,
        company_profile=company_profile, logo_path=logo_path,
    )
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    if user.role == Role.RECRUITER:
        state = user.recruiter.verification_status
        if state == VerificationStatus.PENDING:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Recruiter account is pending Admin verification")
        if state == VerificationStatus.REJECTED:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Recruiter registration was rejected: {user.recruiter.rejection_reason}")
    return TokenResponse(access_token=create_access_token(user.id, user.role.value), role=user.role)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

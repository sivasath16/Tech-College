import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://localhost/placement_portal_test"
os.environ["UPLOAD_DIR"] = "/tmp/placement_test_uploads"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PASSWORD = "Passw0rdOK"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(email="admin@college.edu", password_hash=hash_password("Admin@12345"),
                    role=Role.ADMIN, is_active=True))
        db.commit()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def student_payload(**over):
    data = {
        "college_id": "cs2026001", "full_name": "Asha Rao", "email": "asha@college.edu", "mobile": "9876543210",
        "password": PASSWORD, "department": "Computer Science", "tenth_percent": 91.5, "twelfth_percent": 88,
        "degree_cgpa": 8.4, "skills": ["Python", "SQL"], "certifications": "AWS Cloud Practitioner",
    }
    data.update(over)
    return data


def verify_mobile(client, mobile="9876543210"):
    otp = client.post("/api/v1/auth/otp/send", json={"mobile": mobile}).json()["dev_otp"]
    return client.post("/api/v1/auth/otp/verify", json={"mobile": mobile, "code": otp})


def register_student(client, **over):
    payload = student_payload(**over)
    verify_mobile(client, payload["mobile"])
    return client.post("/api/v1/auth/register/student", json=payload)


def register_recruiter(client, email="hr@acme.com", logo=PNG, ctype="image/png", **over):
    form = {"company_name": "Acme Corp", "contact_person": "Ravi Kumar", "email": email, "phone": "9123456789",
            "company_profile": "Acme builds enterprise software.", "password": PASSWORD}
    form.update(over)
    return client.post("/api/v1/auth/register/recruiter", data=form, files={"logo": ("logo.png", logo, ctype)})


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth(client, email, password=PASSWORD):
    token = login(client, email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

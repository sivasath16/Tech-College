"""Create the default Admin account and sample announcements (idempotent)."""
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Announcement, Role, User

ANNOUNCEMENTS = [
    ("Campus Placement Season 2026 begins", "Registration for the 2026 placement season is now open for all final-year students."),
    ("Pre-placement talks next week", "Recruiters will conduct pre-placement talks in the main auditorium. Watch this space for the schedule."),
]


def main() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.admin_email))
        if admin is None:
            admin = User(email=settings.admin_email, password_hash=hash_password(settings.admin_password),
                         role=Role.ADMIN, is_active=True)
            db.add(admin)
            db.flush()
            print(f"Created admin {settings.admin_email}")
        if db.scalar(select(Announcement.id).limit(1)) is None:
            for title, body in ANNOUNCEMENTS:
                db.add(Announcement(title=title, body=body, created_by=admin.id))
            print("Seeded announcements")
        db.commit()


if __name__ == "__main__":
    main()

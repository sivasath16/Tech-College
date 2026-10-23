from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Announcement, Role, User
from app.schemas.auth import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(db: Session = Depends(get_db)):
    return db.scalars(select(Announcement).order_by(Announcement.id.desc()).limit(10)).all()


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(body: AnnouncementCreate, db: Session = Depends(get_db),
                        admin: User = Depends(require_roles(Role.ADMIN))):
    item = Announcement(title=body.title, body=body.body, created_by=admin.id)
    db.add(item)
    db.commit()
    return item

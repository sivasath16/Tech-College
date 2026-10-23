from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import admin, announcements, auth

app = FastAPI(title="College Placement Management Portal API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(admin.router, prefix=API)
app.include_router(announcements.router, prefix=API)

(settings.upload_dir / "logos").mkdir(parents=True, exist_ok=True)
app.mount("/media/logos", StaticFiles(directory=settings.upload_dir / "logos"), name="logos")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}

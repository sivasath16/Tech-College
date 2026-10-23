# College Placement Management Portal

React (Vite) + FastAPI + PostgreSQL. Phase 2: landing page, authentication, user management.

## Backend
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # set SECRET_KEY, DATABASE_URL
createdb placement_portal
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed  # default admin + sample announcements
.venv/bin/uvicorn app.main:app --reload --port 8000   # Swagger: http://localhost:8000/docs
```
Tests (needs a `placement_portal_test` database): `createdb placement_portal_test && .venv/bin/python -m pytest -q`

## Frontend
```bash
cd frontend && npm install && cp .env.example .env && npm run dev   # http://localhost:5173
```

## Key behaviour
- Student: register with college ID, email, mobile (mock OTP, logged to server console), academic profile.
- Recruiter: register with company details and logo; account is `PENDING` until an Admin approves it.
- Roles (STUDENT / RECRUITER / ADMIN) enforced by `require_roles` on the API and `ProtectedRoute` in the UI.
- Default admin (change in `.env`): `admin@college.edu` / `Admin@12345`.

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings, get_rules
from app.core.database import Base, engine, SessionLocal
from app.api.deps import limiter
from app.api.v1.router import api_v1_router
from app.models.entities import Institution, User, UserRole
from app.core.security import hash_password

settings = get_settings()


def seed_initial_data():
    """Seed initial fictional institutions and default test users if not present.

    Demo credentials (matching README quick-fill buttons):
      admin@aicte.gov.in        / AdminSecret2026!   (Administrator)
      official@aicte.gov.in     / OfficialSecret2026! (AICTE Official)
      institution1@aicte.gov.in / InstSecret2026!    (Institution)
    """
    db = SessionLocal()
    try:
        # ── Step 1: seed institutions FIRST and commit ──────────────────────────
        # Must commit before users so the FK institution_id constraint is satisfied.
        rules = get_rules()
        institutions_config = rules.get("fictional_institutions", [])
        for inst_cfg in institutions_config:
            existing = db.query(Institution).filter(Institution.id == inst_cfg["id"]).first()
            if not existing:
                inst = Institution(
                    id=inst_cfg["id"],
                    name=inst_cfg["name"],
                    code=inst_cfg["code"],
                    region=inst_cfg["region"],
                    city=inst_cfg["city"],
                    state=inst_cfg["state"],
                    contact_email=f"registrar@{inst_cfg['code'].lower()}.edu.in",
                    phone="+91-11-23456789"
                )
                db.add(inst)
        db.commit()  # commit institutions before inserting users with institution_id FK

        # ── Step 2: seed demo users (credentials match README quick-fill buttons) ─
        demo_users = [
            {
                "email": "admin@aicte.gov.in",
                "password": "AdminSecret2026!",
                "full_name": "AICTE Central Admin",
                "role": UserRole.ADMIN,
                "institution_id": None
            },
            {
                "email": "official@aicte.gov.in",
                "password": "OfficialSecret2026!",
                "full_name": "Regional Verification Officer",
                "role": UserRole.OFFICIAL,
                "institution_id": None
            },
            {
                "email": "institution1@aicte.gov.in",
                "password": "InstSecret2026!",
                "full_name": "Zenith Tech Registrar",
                "role": UserRole.INSTITUTION,
                "institution_id": "INST-001"
            }
        ]

        for u_data in demo_users:
            existing_user = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing_user:
                if u_data.get("institution_id"):
                    inst_exists = db.query(Institution).filter(Institution.id == u_data["institution_id"]).first()
                    if not inst_exists:
                        inst = Institution(
                            id=u_data["institution_id"],
                            name="Zenith Institute of Technology",
                            code="ZIT-N01",
                            region="Northern",
                            city="Greater Noida",
                            state="Uttar Pradesh",
                            contact_email="registrar@zit-n01.edu.in",
                            phone="+91-11-23456789"
                        )
                        db.add(inst)
                        db.commit()
                user = User(
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    institution_id=u_data["institution_id"],
                    is_active=True,
                    totp_enabled=False
                )
                db.add(user)
                db.commit()

    except Exception as e:
        db.rollback()
        import traceback
        print(f"Initial seeding notice: {e}")
        traceback.print_exc()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FDR-Sentinel: AICTE Security Deposit & FDR Forensic Verification Portal (SIH26265)",
    lifespan=lifespan
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers_and_banner(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Sentinel-Notice"] = settings.SYNTHETIC_BANNER
    return response


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "banner": settings.SYNTHETIC_BANNER,
        "database": "CONNECTED",
        "clock_offset_days": settings.DEMO_CLOCK_OFFSET_DAYS
    }


# Include API v1 router
app.include_router(api_v1_router, prefix="/api")

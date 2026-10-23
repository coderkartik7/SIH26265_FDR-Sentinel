from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.audit import router as audit_router
from app.api.v1.fdr import router as fdr_router
from app.api.v1.trust_and_risk import router as trust_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.ask_sentinel import router as ask_sentinel_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(fdr_router)
api_v1_router.include_router(trust_router)
api_v1_router.include_router(monitoring_router)
api_v1_router.include_router(ask_sentinel_router)

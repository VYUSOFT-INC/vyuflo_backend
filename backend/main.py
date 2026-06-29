"""
VisaFlow FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, Base, get_db
from app.core.middleware import  RateLimitMiddleware,RequestLoggingMiddleware
from app.core.exceptions import register_exception_handlers

# ✅ IMPORTANT: ensure all models are loaded
from app.models.visamodels import *

from app.routes import auth, onboarding
from app.routes.document import document_router
from app.routes.application import application_router,application_task_router,application_history_router
from app.services.seeddata_service import  seed_document_types, seed_fee_templates, seed_rbac, seed_subscription_plans, seed_support_articles, seed_system_settings, seed_visa_types
from app.routes.visa_types import visa_type_router
from app.routes.dashboard import dashboard_router
from app.routes.user_profile import user_profile_router
from app.routes.login_history import login_history_router
from app.routes.admin.admin_dashboard import admin_dashboard_router
from app.routes.ocr_service import ocr_router
from app.routes.roles import roles_router
from app.routes.payment_routes import payment_router
from app.routes.attorney.attorney_routes import attorney_router
from app.routes.consultation_routes import consultation_router
from app.routes.notification_routes import notification_router
from app.routes.admin.roles import roles_router
from app.routes.admin.custom_roles import custom_roles_router
# from app.routes.user_management import user_management_router
from app.routes.admin.system_settings import system_settings_router
from app.routes.admin.notification_templates import notification_templates_router
from app.routes.admin.admin_visa_types_router import admin_visa_types_router
from app.routes.admin.subscription import subscription_router
from app.routes.admin.revenue_dashboard import revenue_dashboard_router
from app.routes.admin.system_audit import system_audit_router
from app.routes.admin.workspace import workspace_router
from app.routes.admin.admin_support import admin_support_router
from app.routes.attorney.intake import intake_router
from app.routes.attorney.analytics import analytics_router
from app.routes.attorney.calendar import calendar_router





from fastapi.staticfiles import StaticFiles


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")

    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Run seed safely
    async with AsyncSessionLocal() as db:
        await seed_rbac(db)                  # roles, permissions, role_permissions
        await seed_visa_types(db)            # visa_types
        await seed_document_types(db)        # document_types
        await seed_subscription_plans(db)    # subscription_plans + plan_features
        await seed_fee_templates(db)         # fee_templates
        await seed_system_settings(db)       # system_settings
        await seed_support_articles(db)      # support_articles
        
    yield
    print("🛑 Shutting down...")
    await engine.dispose()

# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="VisaFlow Immigration Management Platform API",
    docs_url="/docs",                # Swagger
    redoc_url="/redoc",              # ReDoc
    lifespan=lifespan,
)



# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173','https://helper-sheep-imminent.ngrok-free.dev'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# app.add_middleware(RateLimitMiddleware)
# app.add_middleware(RequestLoggingMiddleware)


# ─────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────
register_exception_handlers(app)


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="uploads"), name="static")
app.include_router(auth.router,                prefix="/api/v1/auth",       tags=["Authentication"])
app.include_router(onboarding.router,          prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(document_router,            prefix="/api/v1", tags=["Documents"])
app.include_router(application_router,         prefix="/api/v1", tags=["Applications"])
app.include_router(application_history_router, prefix="/api/v1", tags=["Application History"])
app.include_router(application_task_router,    prefix="/api/v1", tags=["Application Tasks"])
app.include_router(visa_type_router,           prefix="/api/v1", tags=["Visa Types"])
app.include_router(dashboard_router,           prefix="/api/v1", tags=["Dashboard"])
app.include_router(user_profile_router,        prefix="/api/v1", tags=["User Profile"])
app.include_router(login_history_router,       prefix="/api/v1", tags=["Login History"])
app.include_router(admin_dashboard_router,     prefix="/api/v1", tags=["Admin cards"])
app.include_router(roles_router,               prefix="/api/v1", tags=["Roles"])
app.include_router(ocr_router,                 prefix="/api/v1", tags=["Ocr"])
app.include_router(payment_router,             prefix="/api/v1", tags=["Payments "])
app.include_router(consultation_router, prefix="/api/v1", tags=["consultations"])
app.include_router(notification_router, prefix="/api/v1", tags=["notifications"])
app.include_router(attorney_router, prefix="/api/v1", tags=["attorneys"])
app.include_router(roles_router,       prefix="/api/v1")
# app.include_router(user_roles_router,  prefix="/api/v1", tags=["User Roles"])
app.include_router(custom_roles_router,prefix="/api/v1",tags=["Custom Roles"])
app.include_router(system_settings_router, prefix="/api/v1",tags=["System Settings"])
app.include_router(notification_templates_router, prefix="/api/v1",tags=["Notification Templates"])
app.include_router(admin_visa_types_router, prefix="/api/v1", tags=["Admin — Visa Types"])
app.include_router(subscription_router, prefix="/api/v1", tags=["Admin — Subscriptions"])
app.include_router(revenue_dashboard_router,prefix="/api/v1",tags=["Admin — Revenue Dashboard"])
app.include_router(system_audit_router,prefix="/api/v1",tags=["System Audit"])
app.include_router(workspace_router,prefix="/api/v1")
app.include_router(admin_support_router, prefix="/api/v1")
app.include_router(intake_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")





# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
    }


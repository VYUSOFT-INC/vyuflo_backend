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

from app.routes.employee import auth, onboarding
from app.routes.employee.document import document_router
from app.routes.employee.message import message_router
from app.routes.employee.application import application_router,application_task_router,application_history_router
from app.services.employee.seeddata_service import  seed_document_types, seed_fee_templates, seed_rbac, seed_subscription_plans, seed_support_articles, seed_system_settings, seed_visa_types
from app.routes.employee.visa_types import visa_type_router
from app.routes.employee.dashboard import dashboard_router
from app.routes.employee.user_profile import user_profile_router
from app.routes.employee.login_history import login_history_router
from app.routes.admin.admin_dashboard import admin_dashboard_router
from app.routes.employee.ocr_service import ocr_router
from app.routes.employee.roles import roles_router
from app.routes.employee.payment_routes import payment_router
from app.routes.attorney.attorney_routes import attorney_router
from app.routes.employee.consultation_routes import consultation_router
from app.routes.employee.notification_routes import notification_router
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
from app.routes.attorney.document_extra import document_extra_router
from app.routes.attorney.application_extra import application_extra_router
from app.routes.attorney.help import help_router
from app.routes.attorney.billing import billing_router
from app.routes.attorney.secure_messages import secure_messages_router
from app.routes.attorney.profile_settings import profile_settings_router
from app.routes.attorney.invoice_detail import invoice_detail_router
from app.routes.attorney.template_library import template_library_router
from app.routes.attorney.notifications_reminders import notifications_reminders_router
from app.routes.attorney.lawyer_dashboard import lawyer_dashboard_router
# hr routes
from app.routes.hr.invitation_routes import invitation_router
from app.routes.hr.hr_case_routes import hr_case_router
from app.routes.hr.hr_task_routes import hr_task_router
from app.routes.hr.hr_document_routes import hr_document_router
from app.routes.hr.hr_deadline_routes  import hr_deadline_router
from app.routes.hr.hr_approval_routes  import hr_approval_router




from fastapi.staticfiles import StaticFiles


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────

# create_all does not alter existing Postgres enums — add new values explicitly
_VISA_CATEGORY_ENUM_VALUES = ("dependent", "family_based")


async def _ensure_pg_enum_values(enum_name: str, values: tuple[str, ...]) -> None:
    """Idempotently add values to an existing Postgres enum (autocommit; PG < 12 safe)."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        for value in values:
            await conn.execute(
                text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")

    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1b. Sync enum values added to the model after the DB was first created
    await _ensure_pg_enum_values("visa_category_enum", _VISA_CATEGORY_ENUM_VALUES)

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
    allow_origins=settings.CORS_ORIGINS,
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
app.mount("/api/v1/static", StaticFiles(directory="uploads"), name="static")
app.include_router(auth.router,                prefix="/api/v1/auth",       tags=["Authentication"])
app.include_router(onboarding.router,          prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(document_router,            prefix="/api/v1", tags=["Documents"])
app.include_router(message_router,            prefix="/api/v1", tags=["Message"])
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
# app.include_router(roles_router,       prefix="/api/v1")
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
app.include_router(document_extra_router, prefix="/api/v1", tags=["Attroney-Documents"])
app.include_router(application_extra_router, prefix="/api/v1", tags=["Attroney-Applications"])
app.include_router(help_router, prefix="/api/v1", tags=["Attroney-Help"])
app.include_router(billing_router,prefix="/api/v1")
app.include_router(secure_messages_router, prefix="/api/v1", tags=["Secure Messages"])
app.include_router(profile_settings_router,prefix="/api/v1", tags=["Profile Settings"] )
app.include_router(invoice_detail_router, prefix="/api/v1", tags=["Invoice Detail"])
app.include_router(template_library_router, prefix="/api/v1", tags=["Template Library"])
app.include_router(notifications_reminders_router, prefix="/api/v1", tags=["Notification Reminders"])
app.include_router(lawyer_dashboard_router, prefix="/api/v1", tags=["Lawyer Dashboard"])
# Hr Routes
app.include_router(invitation_router, prefix="/api/v1",tags=["HR Invitation"])
app.include_router(hr_case_router, prefix="/api/v1/hr", tags=["HR Cases"])
app.include_router(hr_task_router, prefix="/api/v1/hr", tags=["HR Tasks"])
app.include_router(hr_document_router, prefix="/api/v1/hr", tags=["HR Documents"])
app.include_router(hr_deadline_router, prefix="/api/v1/hr", tags=["HR Deadlines"])
app.include_router(hr_approval_router, prefix="/api/v1/hr", tags=["HR Approvals"])









# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
    }


"""
VisaFlow FastAPI Application Entry Point
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, Base, get_db
from app.core.middleware import  RateLimitMiddleware,RequestLoggingMiddleware
from app.core.exceptions import register_exception_handlers

# ✅ IMPORTANT: ensure all models are loaded
from app.models.visamodels import *

from app.routes.attorney.attorney_profile_router import attorney_profile_router
from app.routes.employee import auth, onboarding
from app.routes.employee.document import document_router
from app.routes.employee.message import message_router
from app.routes.employee.application import application_router,application_task_router,application_history_router
from app.routes.employee.employee_forms import employee_forms_router          
from app.services.employee.expiry_reminder_service import activate_pending_document_replacements, check_and_send_expiry_reminders, mark_expired_documents
from app.services.employee.seeddata_service import  seed_document_types, seed_fee_templates, seed_notification_templates, seed_rbac, seed_subscription_plans, seed_support_articles, seed_system_settings, seed_visa_types,seed_document_field_configurations
from app.routes.employee.visa_types import visa_type_router
from app.routes.employee.dashboard import dashboard_router
from app.routes.employee.user_profile import user_profile_router
from app.routes.employee.login_history import login_history_router
from app.routes.admin.admin_dashboard import admin_dashboard_router
from app.routes.employee.roles import roles_router
from app.routes.employee.payment_routes import payment_router
from app.routes.attorney.attorney_routes import attorney_router
from app.routes.employee.consultation_routes import consultation_router
from app.routes.attorney.new_case_routes import new_case_router   # NEW
from app.routes.employee.notification_routes import notification_router
from app.routes.admin.roles import roles_router
from app.routes.admin.custom_roles import custom_roles_router
from app.routes.admin.user_management import user_management_router
from app.routes.admin.notifications_reminders import admin_notifications_router
from app.routes.admin.system_settings import system_settings_router
from app.routes.admin.notification_templates import notification_templates_router
from app.routes.admin.admin_visa_types_router import admin_visa_types_router
from app.routes.admin.subscription import subscription_router
from app.routes.admin.revenue_dashboard import revenue_dashboard_router
from app.routes.admin.system_audit import system_audit_router
from app.routes.admin.workspace import workspace_router
from app.routes.admin.document_field_config import document_field_config_router
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
from app.routes.attorney.employee_forms_review_routes import employee_forms_review_router 
# hr routes
from app.routes.hr.invitation_routes import invitation_router
from app.routes.hr.hr_case_routes import hr_case_router
from app.routes.hr.hr_task_routes import hr_task_router
from app.routes.hr.hr_document_routes import hr_document_router
from app.routes.hr.hr_deadline_routes  import hr_deadline_router
from app.routes.hr.hr_approval_routes  import hr_approval_router
from app.routes.employee.security import employee_security_router
from app.routes.hr.hr_document_request_routes import hr_document_request_router
from app.routes.hr.hr_case_overview_routes import hr_case_overview_router
from app.routes.hr.hr_case_letters_routes import hr_case_letters_router
from app.routes.hr.hr_employee_forms_routes import hr_employee_forms_router
from app.routes.hr.hr_employee_forms_review_routes import hr_employee_forms_review_router     
from app.routes.hr.company_profile_router import company_profile_router

from app.ocr.ocr_service_router import ocr_router
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
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for value in values:
            await conn.execute(
                text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")
            )

async def _ensure_notif_template_unique_constraint() -> None:
    """
    create_all does not alter indexes on existing tables.

    Seed data has one row per (event_key, channel). Older DBs may still have a
    unique index on event_key alone (ix_notification_templates_event_key), which
    blocks multi-channel templates. Drop that unique index and ensure the
    composite unique constraint exists.
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Drop leftover unique-on-event_key index if present (unique or not —
        # model only needs a non-unique index, which create_all / Index below cover)
        await conn.execute(text("""
            DROP INDEX IF EXISTS ix_notification_templates_event_key;
        """))

        # Recreate as a non-unique index (matches Column(..., index=True))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_notification_templates_event_key
            ON notification_templates (event_key);
        """))

        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_notif_template_event_channel'
                ) THEN
                    -- Drop duplicate (event_key, channel) rows, keep oldest
                    DELETE FROM notification_templates
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT DISTINCT ON (event_key, channel) id
                            FROM notification_templates
                            ORDER BY event_key, channel, created_at ASC NULLS LAST, id ASC
                        ) keepers
                    );

                    ALTER TABLE notification_templates
                        ADD CONSTRAINT uq_notif_template_event_channel
                        UNIQUE (event_key, channel);
                END IF;
            END $$;
        """))


async def _run_expiry_reminder_check():
    """
    The actual job APScheduler calls. Creates its own DB session since
    scheduled jobs run outside any request context — same pattern as the
    old asyncio loop, just triggered by the scheduler now instead of a
    manual sleep().
    """
    print("cron job is working ")
    try:
        async with AsyncSessionLocal() as db:
            sent = await check_and_send_expiry_reminders(db)
            if sent:
                print(f"✅ Sent {sent} document expiry reminder(s)")
    except Exception as e:
        print(f"⚠️  Expiry reminder check failed: {type(e).__name__}: {e}")
        
async def _run_mark_expired_documents():
    """
    Flips documents whose expiry_date has passed to status='expired' and
    fires the 'document has expired, please re-upload' notification.
    Separate job from the reminder check above — that one only WARNS as
    the date approaches; this one is what actually marks the document
    expired once the date has passed.
    """
    print("cron job (mark_expired_documents) is working")
    try:
        async with AsyncSessionLocal() as db:
            expired_count = await mark_expired_documents(db)
            if expired_count:
                print(f"✅ Marked {expired_count} document(s) as expired")
    except Exception as e:
        print(f"⚠️  Mark-expired-documents check failed: {type(e).__name__}: {e}")


async def _run_activate_pending_document_replacements():
    """
    Performs the old→'superseded' handoff for documents that were
    proactively replaced before their predecessor actually expired, once
    that predecessor's expiry date has arrived.
    """
    print("cron job (activate_pending_document_replacements) is working")
    try:
        async with AsyncSessionLocal() as db:
            activated_count = await activate_pending_document_replacements(db)
            if activated_count:
                print(f"✅ Activated {activated_count} pending document replacement(s)")
    except Exception as e:
        print(f"⚠️  Activate-pending-replacements check failed: {type(e).__name__}: {e}")

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")

    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1b. Sync enum values added to the model after the DB was first created
    await _ensure_pg_enum_values("visa_category_enum", _VISA_CATEGORY_ENUM_VALUES)
    # 1c. Sync unique constraint needed by notification template seed
    await _ensure_notif_template_unique_constraint()


    # 2. Run seed safely
    async with AsyncSessionLocal() as db:
        await seed_rbac(db)                  # roles, permissions, role_permissions
        await seed_visa_types(db)            # visa_types
        await seed_document_types(db)        # document_types
        await seed_subscription_plans(db)    # subscription_plans + plan_features
        await seed_fee_templates(db)         # fee_templates
        await seed_system_settings(db)       # system_settings
        await seed_support_articles(db)      # support_articles
        await seed_notification_templates(db)
        await seed_document_field_configurations(db)
    job = scheduler.add_job(
        _run_expiry_reminder_check,
        trigger=CronTrigger(hour=19, minute=18, timezone=ZoneInfo("Asia/Kolkata")),
        id="expiry_reminder_check",
        misfire_grace_time=3600,
        replace_existing=True,
    )

    expired_job = scheduler.add_job(
        _run_mark_expired_documents,
        trigger=CronTrigger(hour=19, minute=18, timezone=ZoneInfo("Asia/Kolkata")),
        id="mark_expired_documents_check",
        misfire_grace_time=3600,
        replace_existing=True,
    )

    activation_job = scheduler.add_job(
        _run_activate_pending_document_replacements,
        trigger=CronTrigger(hour=19, minute=18, timezone=ZoneInfo("Asia/Kolkata")),
        id="activate_pending_document_replacements_check",
        misfire_grace_time=3600,
        replace_existing=True,
    )

    scheduler.start()
    print(f"⏰ Scheduler started — expiry_reminder_check next run at: {job.next_run_time}")
    print(f"⏰ Scheduler started — mark_expired_documents_check next run at: {expired_job.next_run_time}")
    print(f"⏰ Scheduler started — activate_pending_document_replacements_check next run at: {activation_job.next_run_time}")
    yield
    print("🛑 Shutting down...")
    scheduler.shutdown(wait=False)
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
    allow_origins=['http://localhost:5174','https://designate-donated-subsoil.ngrok-free.dev'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# ─────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────
register_exception_handlers(app)


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.include_router(ocr_router,prefix="/api/v1", tags=["Ocr"]) 
app.include_router(auth.router,                prefix="/api/v1/auth",       tags=["Authentication"])
app.include_router(onboarding.router,          prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(document_extra_router, prefix="/api/v1/attorney", tags=["Attroney-Documents"])
app.include_router(message_router,            prefix="/api/v1", tags=["Message"])
app.include_router(application_router,         prefix="/api/v1", tags=["Applications"])
app.include_router(employee_forms_router,      prefix="/api/v1", tags=["Employee Forms"])        
app.include_router(application_history_router, prefix="/api/v1", tags=["Application History"])
app.include_router(application_task_router,    prefix="/api/v1", tags=["Application Tasks"])
app.include_router(visa_type_router,           prefix="/api/v1", tags=["Visa Types"])
app.include_router(dashboard_router,           prefix="/api/v1", tags=["Dashboard"])
app.include_router(user_profile_router,        prefix="/api/v1", tags=["User Profile"])
app.include_router(login_history_router,       prefix="/api/v1", tags=["Login History"])
app.include_router(admin_dashboard_router,     prefix="/api/v1", tags=["Admin cards"])
app.include_router(roles_router,               prefix="/api/v1", tags=["Roles"])
app.include_router(payment_router,             prefix="/api/v1", tags=["Payments "])
app.include_router(consultation_router, prefix="/api/v1", tags=["consultations"])
app.include_router(notification_router, prefix="/api/v1", tags=["notifications"])
app.include_router(attorney_router, prefix="/api/v1", tags=["attorneys"])
app.include_router(new_case_router, prefix="/api/v1", tags=["Lawyer Cases"])   # NEW
app.include_router(attorney_profile_router, prefix="/api/v1/attorney", tags=["attorney-profile"])
# app.include_router(roles_router,       prefix="/api/v1")
# app.include_router(user_roles_router,  prefix="/api/v1", tags=["User Roles"])

app.include_router(document_field_config_router, prefix="/api/v1",tags=["Admin — Document Field Config"])
app.include_router(user_management_router, prefix="/api/v1",tags=["User Management"])
app.include_router(admin_notifications_router, prefix="/api/v1/admin")
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
app.include_router(document_router,            prefix="/api/v1", tags=["Documents"])
app.include_router(application_extra_router, prefix="/api/v1", tags=["Attroney-Applications"])
app.include_router(help_router, prefix="/api/v1/attorney", tags=["Attroney-Help"])
app.include_router(billing_router,prefix="/api/v1")
app.include_router(secure_messages_router, prefix="/api/v1", tags=["Secure Messages"])
app.include_router(profile_settings_router,prefix="/api/v1/attorney", tags=["Profile Settings"] )
app.include_router(invoice_detail_router, prefix="/api/v1", tags=["Invoice Detail"])
app.include_router(template_library_router, prefix="/api/v1", tags=["Template Library"])
app.include_router(notifications_reminders_router, prefix="/api/v1", tags=["Notification Reminders"])
app.include_router(lawyer_dashboard_router, prefix="/api/v1", tags=["Lawyer Dashboard"])
app.include_router(employee_forms_review_router, prefix="/api/v1/attorney", tags=["Attorney Form Review"])  
# Hr Routes
app.include_router(invitation_router, prefix="/api/v1",tags=["HR Invitation"])
app.include_router(hr_case_router, prefix="/api/v1/hr", tags=["HR Cases"])
app.include_router(hr_task_router, prefix="/api/v1/hr", tags=["HR Tasks"])
app.include_router(hr_document_router, prefix="/api/v1/hr", tags=["HR Documents"])
app.include_router(hr_deadline_router, prefix="/api/v1/hr", tags=["HR Deadlines"])
app.include_router(hr_approval_router, prefix="/api/v1/hr", tags=["HR Approvals"])
app.include_router(employee_security_router,prefix="/api/v1/hr", tags=["Login_History"] )
app.include_router(hr_case_overview_router,prefix="/api/v1/hr", tags=["Case Overview"] )
app.include_router(hr_document_request_router, prefix="/api/v1/hr", tags=["HR Document Request"])
app.include_router(hr_case_letters_router,prefix="/api/v1/hr", tags=["Case Generated Letters"] )
app.include_router(hr_employee_forms_router,prefix="/api/v1/hr", tags=["HR Employee Forms"] ) 
app.include_router(hr_employee_forms_review_router, prefix="/api/v1/hr", tags=["HR Form Review"])   
app.include_router(company_profile_router, prefix="/api/v1", tags=["company-profile"])







# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
    }


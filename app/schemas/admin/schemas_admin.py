# # =============================================================================
# #  schemas_admin.py — Pydantic v2 Schemas for Admin Role
# #  VisaFlow — Admin Role
# # =============================================================================

# from __future__ import annotations
# import uuid
# from datetime import datetime, date
# from decimal import Decimal
# from typing import Optional, List, Any, Dict
# from pydantic import BaseModel, Field, ConfigDict
# from enum import Enum


# # ─── Enums ────────────────────────────────────────────────────────────────────

# class AdminLevelEnum(str, Enum):
#     super_admin   = "super_admin"
#     admin         = "admin"
#     support_admin = "support_admin"
#     billing_admin = "billing_admin"

# class AuditSeverityEnum(str, Enum):
#     info     = "info"
#     warning  = "warning"
#     critical = "critical"

# class SettingValueTypeEnum(str, Enum):
#     string  = "string"
#     boolean = "boolean"
#     integer = "integer"
#     json    = "json"
#     secret  = "secret"

# class NotifChannelEnum(str, Enum):
#     email  = "email"
#     sms    = "sms"
#     push   = "push"
#     in_app = "in_app"

# class SubscriptionStatusEnum(str, Enum):
#     trialing = "trialing"
#     active   = "active"
#     past_due = "past_due"
#     canceled = "canceled"
#     paused   = "paused"

# class BillingCycleEnum(str, Enum):
#     monthly = "monthly"
#     yearly  = "yearly"

# class InvoiceStatusEnum(str, Enum):
#     draft         = "draft"
#     open          = "open"
#     paid          = "paid"
#     void          = "void"
#     uncollectible = "uncollectible"

# class OnboardingStepTypeEnum(str, Enum):
#     info      = "info"
#     form      = "form"
#     upload    = "upload"
#     video     = "video"
#     checklist = "checklist"
#     redirect  = "redirect"

# class OnboardingStatusEnum(str, Enum):
#     not_started = "not_started"
#     in_progress = "in_progress"
#     completed   = "completed"
#     skipped     = "skipped"

# class BroadcastTypeEnum(str, Enum):
#     info        = "info"
#     warning     = "warning"
#     critical    = "critical"
#     maintenance = "maintenance"

# class BroadcastAudienceEnum(str, Enum):
#     all_users    = "all_users"
#     all_admins   = "all_admins"
#     attorneys    = "attorneys"
#     clients      = "clients"
#     specific_plan = "specific_plan"

# # Matches your EXISTING ticket_priority_enum / ticket_status_enum in models.py
# class TicketPriorityEnum(str, Enum):
#     urgent = "urgent"
#     high   = "high"
#     medium = "medium"
#     low    = "low"

# class TicketStatusEnum(str, Enum):
#     open         = "open"
#     in_progress  = "in_progress"
#     waiting_user = "waiting_user"
#     resolved     = "resolved"
#     closed       = "closed"


# # ─── Pagination ───────────────────────────────────────────────────────────────

# class PaginatedOut(BaseModel):
#     items      : List[Any]
#     total      : int
#     page       : int
#     page_size  : int
#     total_pages: int


# # ─── Admin Profile ────────────────────────────────────────────────────────────

# class AdminProfileCreate(BaseModel):
#     user_id             : uuid.UUID
#     admin_level         : AdminLevelEnum = AdminLevelEnum.admin
#     can_manage_users    : bool = True
#     can_manage_billing  : bool = False
#     can_manage_settings : bool = False
#     can_view_audit_logs : bool = True
#     mfa_enabled         : bool = False

# class AdminProfileUpdate(BaseModel):
#     admin_level         : Optional[AdminLevelEnum] = None
#     can_manage_users    : Optional[bool] = None
#     can_manage_billing  : Optional[bool] = None
#     can_manage_settings : Optional[bool] = None
#     can_view_audit_logs : Optional[bool] = None
#     mfa_enabled         : Optional[bool] = None

# class AdminProfileOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id                  : uuid.UUID
#     user_id             : uuid.UUID
#     admin_level         : str
#     can_manage_users    : bool
#     can_manage_billing  : bool
#     can_manage_settings : bool
#     can_view_audit_logs : bool
#     mfa_enabled         : bool
#     created_at          : datetime
#     updated_at          : datetime


# # ─── Audit Log ────────────────────────────────────────────────────────────────

# class AuditLogOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id            : uuid.UUID
#     admin_user_id : uuid.UUID
#     action_type   : str
#     entity_type   : Optional[str] = None
#     entity_id     : Optional[uuid.UUID] = None
#     old_value     : Optional[Dict[str, Any]] = None
#     new_value     : Optional[Dict[str, Any]] = None
#     description   : Optional[str] = None
#     ip_address    : Optional[str] = None
#     severity      : str
#     created_at    : datetime

# class AuditLogFilter(BaseModel):
#     action_type   : Optional[str] = None
#     entity_type   : Optional[str] = None
#     severity      : Optional[AuditSeverityEnum] = None
#     admin_user_id : Optional[uuid.UUID] = None
#     date_from     : Optional[datetime] = None
#     date_to       : Optional[datetime] = None
#     search        : Optional[str] = None
#     page          : int = Field(1, ge=1)
#     page_size     : int = Field(20, ge=1, le=100)


# # ─── Platform Settings ────────────────────────────────────────────────────────

# class PlatformSettingUpdate(BaseModel):
#     setting_value : str
#     description   : Optional[str] = None

# class PlatformSettingOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id            : uuid.UUID
#     setting_key   : str
#     setting_value : Optional[str] = None
#     value_type    : str
#     category      : str
#     description   : Optional[str] = None
#     is_sensitive  : bool
#     updated_at    : datetime


# # ─── Visa Type (admin view — extends existing visa_types) ────────────────────

# class VisaTypeAdminUpdate(BaseModel):
#     """Only the fields the admin can change via Admin-06 screen."""
#     name                      : Optional[str] = None
#     description               : Optional[str] = None
#     processing_time_min       : Optional[int] = None
#     processing_time_max       : Optional[int] = None
#     government_fee_usd        : Optional[int] = None
#     max_stay_days             : Optional[int] = None
#     is_renewable              : Optional[bool] = None
#     is_active                 : Optional[bool] = None
#     requires_employer_sponsor : Optional[bool] = None

# class VisaTypeAdminOut(BaseModel):
#     """Full admin view of a visa type — includes all fields from existing + new."""
#     model_config = ConfigDict(from_attributes=True)
#     id                        : uuid.UUID
#     code                      : str
#     name                      : str
#     category                  : str
#     description               : Optional[str] = None
#     processing_time_min       : Optional[int] = None
#     processing_time_max       : Optional[int] = None
#     typical_processing_days   : Optional[int] = None   # existing field
#     government_fee_usd        : Optional[int] = None
#     max_stay_days             : Optional[int] = None
#     is_renewable              : bool = False
#     is_active                 : bool
#     requires_employer_sponsor : bool
#     display_order             : int
#     updated_at                : datetime


# # ─── Visa Type Document Rules ─────────────────────────────────────────────────

# class DocumentRuleCreate(BaseModel):
#     visa_type_id  : uuid.UUID
#     document_name : str = Field(..., max_length=200)
#     is_mandatory  : bool = True
#     who_provides  : Optional[str] = None
#     who_signs     : Optional[str] = None
#     notes         : Optional[str] = None
#     sort_order    : int = 0

# class DocumentRuleUpdate(BaseModel):
#     document_name : Optional[str] = None
#     is_mandatory  : Optional[bool] = None
#     who_provides  : Optional[str] = None
#     who_signs     : Optional[str] = None
#     notes         : Optional[str] = None
#     sort_order    : Optional[int] = None

# class DocumentRuleOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id            : uuid.UUID
#     visa_type_id  : uuid.UUID
#     document_name : str
#     is_mandatory  : bool
#     who_provides  : Optional[str] = None
#     who_signs     : Optional[str] = None
#     notes         : Optional[str] = None
#     sort_order    : int
#     created_at    : datetime


# # ─── Subscription Plans ───────────────────────────────────────────────────────

# class SubscriptionPlanCreate(BaseModel):
#     name              : str
#     slug              : str
#     description       : Optional[str] = None
#     price_monthly_usd : Decimal
#     price_yearly_usd  : Optional[Decimal] = None
#     max_cases         : Optional[int] = None
#     max_users         : Optional[int] = None
#     max_storage_gb    : Optional[int] = None
#     features          : Optional[List[str]] = None
#     trial_days        : int = 0
#     sort_order        : int = 0

# class SubscriptionPlanUpdate(BaseModel):
#     name              : Optional[str] = None
#     description       : Optional[str] = None
#     price_monthly_usd : Optional[Decimal] = None
#     price_yearly_usd  : Optional[Decimal] = None
#     max_cases         : Optional[int] = None
#     max_users         : Optional[int] = None
#     features          : Optional[List[str]] = None
#     is_active         : Optional[bool] = None
#     is_featured       : Optional[bool] = None
#     trial_days        : Optional[int] = None

# class SubscriptionPlanOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id                : uuid.UUID
#     name              : str
#     slug              : str
#     description       : Optional[str] = None
#     price_monthly_usd : Decimal
#     price_yearly_usd  : Optional[Decimal] = None
#     max_cases         : Optional[int] = None
#     max_users         : Optional[int] = None
#     max_storage_gb    : Optional[int] = None
#     features          : Optional[Any] = None
#     is_active         : bool
#     is_featured       : bool
#     trial_days        : int
#     sort_order        : int
#     created_at        : datetime
#     updated_at        : datetime


# # ─── Invoice ──────────────────────────────────────────────────────────────────

# class InvoiceOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id             : uuid.UUID
#     invoice_number : str
#     user_id        : Optional[uuid.UUID] = None
#     amount_usd     : Decimal
#     tax_usd        : Decimal
#     total_usd      : Decimal
#     status         : str
#     due_date       : Optional[date] = None
#     paid_at        : Optional[datetime] = None
#     created_at     : datetime


# # ─── Notification Template ────────────────────────────────────────────────────

# class NotificationTemplateCreate(BaseModel):
#     template_key : str = Field(..., max_length=120)
#     name         : str
#     channel      : NotifChannelEnum = NotifChannelEnum.email
#     subject      : Optional[str] = None
#     body_html    : Optional[str] = None
#     body_text    : Optional[str] = None
#     variables    : Optional[List[str]] = None
#     category     : Optional[str] = None

# class NotificationTemplateUpdate(BaseModel):
#     name      : Optional[str] = None
#     subject   : Optional[str] = None
#     body_html : Optional[str] = None
#     body_text : Optional[str] = None
#     variables : Optional[List[str]] = None
#     is_active : Optional[bool] = None

# class NotificationTemplateOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id           : uuid.UUID
#     template_key : str
#     name         : str
#     channel      : str
#     subject      : Optional[str] = None
#     body_html    : Optional[str] = None
#     variables    : Optional[Any] = None
#     category     : Optional[str] = None
#     is_active    : bool
#     updated_at   : datetime


# # ─── Broadcast ────────────────────────────────────────────────────────────────

# class BroadcastCreate(BaseModel):
#     title             : str = Field(..., max_length=250)
#     message           : str
#     notification_type : BroadcastTypeEnum = BroadcastTypeEnum.info
#     target_audience   : BroadcastAudienceEnum = BroadcastAudienceEnum.all_users
#     target_plan_id    : Optional[uuid.UUID] = None
#     channels          : List[str] = ["in_app"]
#     scheduled_at      : Optional[datetime] = None

# class BroadcastOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id                : uuid.UUID
#     title             : str
#     message           : str
#     notification_type : str
#     target_audience   : str
#     channels          : Optional[Any] = None
#     sent_at           : Optional[datetime] = None
#     total_recipients  : int
#     created_at        : datetime


# # ─── Support Tickets (admin view of existing table) ───────────────────────────

# class SupportTicketAdminUpdate(BaseModel):
#     """Admin can update these fields on existing support_tickets table."""
#     status              : Optional[TicketStatusEnum] = None
#     priority            : Optional[TicketPriorityEnum] = None
#     assigned_to         : Optional[uuid.UUID] = None
#     satisfaction_rating : Optional[int] = Field(None, ge=1, le=5)

# class SupportTicketAdminOut(BaseModel):
#     """Full admin view — mirrors your existing SupportTicket model + new columns."""
#     model_config = ConfigDict(from_attributes=True)
#     id                  : uuid.UUID
#     ticket_number       : str
#     subject             : str
#     category            : Optional[str] = None
#     priority            : str
#     status              : str
#     user_id             : Optional[uuid.UUID] = None
#     assigned_to         : Optional[uuid.UUID] = None
#     first_response_at   : Optional[datetime] = None
#     resolved_at         : Optional[datetime] = None
#     closed_at           : Optional[datetime] = None     # new column added by migration
#     satisfaction_rating : Optional[int] = None          # new column added by migration
#     created_at          : datetime
#     updated_at          : datetime

# class TicketReplyCreate(BaseModel):
#     """Uses your existing support_ticket_replies table."""
#     body        : str
#     is_internal : bool = False   # admin can post internal notes

# class TicketReplyOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id          : uuid.UUID
#     ticket_id   : uuid.UUID
#     sender_id   : Optional[uuid.UUID] = None
#     sender_type : str
#     body        : str
#     is_read     : bool
#     created_at  : datetime


# # ─── User Management (admin view of existing users table) ─────────────────────

# class UserAdminOut(BaseModel):
#     """Admin view of a user — uses your existing User model fields."""
#     model_config = ConfigDict(from_attributes=True)
#     id            : uuid.UUID
#     first_name    : str
#     last_name     : str
#     email         : str
#     phone         : Optional[str] = None
#     is_active     : bool
#     is_verified   : bool
#     auth_provider : str
#     last_login_at : Optional[datetime] = None
#     last_login_ip : Optional[str] = None   # new column added by migration
#     created_at    : datetime

# class UserSuspendRequest(BaseModel):
#     reason: str = Field(..., min_length=5)


# # ─── Onboarding Flow ──────────────────────────────────────────────────────────

# class OnboardingFlowCreate(BaseModel):
#     name        : str
#     target_role : str   # 'employee' | 'attorney' | 'hr' | 'app_admin'
#     description : Optional[str] = None
#     is_default  : bool = False

# class OnboardingFlowUpdate(BaseModel):
#     name        : Optional[str] = None
#     description : Optional[str] = None
#     is_active   : Optional[bool] = None
#     is_default  : Optional[bool] = None

# class OnboardingStepCreate(BaseModel):
#     flow_id      : uuid.UUID
#     step_number  : int
#     title        : str
#     description  : Optional[str] = None
#     step_type    : OnboardingStepTypeEnum = OnboardingStepTypeEnum.info
#     content      : Optional[Dict[str, Any]] = None
#     is_skippable : bool = False
#     is_mandatory : bool = True

# class OnboardingStepOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id           : uuid.UUID
#     flow_id      : uuid.UUID
#     step_number  : int
#     title        : str
#     description  : Optional[str] = None
#     step_type    : str
#     content      : Optional[Any] = None
#     is_skippable : bool
#     is_mandatory : bool

# class OnboardingFlowOut(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     id          : uuid.UUID
#     name        : str
#     target_role : str
#     description : Optional[str] = None
#     is_active   : bool
#     is_default  : bool
#     total_steps : int
#     created_at  : datetime
#     updated_at  : datetime
#     steps       : List[OnboardingStepOut] = []


# # ─── Dashboard Stats ──────────────────────────────────────────────────────────

# class AdminDashboardStats(BaseModel):
#     total_users         : int
#     active_cases        : int
#     document_types_count: int
#     ai_accuracy_pct     : float
#     open_tickets        : int
#     system_uptime_pct   : float
#     monthly_revenue_usd : Decimal
#     new_signups_30d     : int

# class RevenueMetrics(BaseModel):
#     total_revenue_usd    : Decimal
#     monthly_revenue_usd  : Decimal
#     active_subscriptions : int
#     mrr_usd              : Decimal
#     arr_usd              : Decimal
#     revenue_by_plan      : List[Dict[str, Any]] = []
#     revenue_by_month     : List[Dict[str, Any]] = []

# class SystemStatusOut(BaseModel):
#     overall_status    : str
#     uptime_pct        : float
#     api_latency_ms    : int
#     db_status         : str
#     storage_status    : str
#     email_status      : str
#     ai_service_status : str

# =============================================================================
# new_models.py — VisaFlow Complete SQLAlchemy Models
# Production-ready — 70 tables covering all 4 roles
# Roles: employee · attorney · hr · app_admin
# =============================================================================

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Time,
    Integer, Enum, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =============================================================================
# TABLE 01 — users
# =============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    first_name   = Column(String(100), nullable=False)
    last_name    = Column(String(100), nullable=False)
    email        = Column(String(255), nullable=False, unique=True, index=True)
    phone        = Column(String(20),  nullable=True)
    country_code = Column(String(10),  nullable=True)

    password_hash    = Column(String(255), nullable=True)
    auth_provider    = Column(
        Enum("email", "google", "microsoft", "apple",
             name="auth_provider_enum"),
        nullable=False, default="email"
    )
    auth_provider_id = Column(String(255), nullable=True)

    is_active   = Column(Boolean, default=True,  nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    terms_accepted    = Column(Boolean,  nullable=False, default=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    marketing_opt_in  = Column(Boolean,  default=False, nullable=False)
    newsletter_opt_in = Column(Boolean,  default=False, nullable=False)
    referral_source   = Column(String(100), nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    otp_records          = relationship("UserOTP",
                                        foreign_keys="UserOTP.user_id",
                                        back_populates="user")
    login_history        = relationship("UserLoginHistory",
                                        foreign_keys="UserLoginHistory.user_id",
                                        back_populates="user",
                                        order_by="UserLoginHistory.created_at.desc()")
    reset_tokens         = relationship("PasswordResetToken",
                                        foreign_keys="PasswordResetToken.user_id",
                                        back_populates="user")
    profile              = relationship("UserProfile",
                                        foreign_keys="UserProfile.user_id",
                                        back_populates="user", uselist=False)
    visa_targets         = relationship("UserVisaTarget",
                                        foreign_keys="UserVisaTarget.user_id",
                                        back_populates="user")
    user_roles           = relationship("UserRole",
                                        foreign_keys="UserRole.user_id",
                                        back_populates="user")
    applications         = relationship("Application",
                                        foreign_keys="Application.user_id",
                                        back_populates="user")
    attorney_cases       = relationship("Application",
                                        foreign_keys="Application.assigned_attorney_id",
                                        back_populates="assigned_attorney")
    hr_cases             = relationship("Application",
                                        foreign_keys="Application.assigned_hr_id",
                                        back_populates="assigned_hr")
    documents            = relationship("Document",
                                        foreign_keys="Document.user_id",
                                        back_populates="user")
    verified_documents   = relationship("Document",
                                        foreign_keys="Document.verified_by",
                                        back_populates="verified_by_user")
    message_threads      = relationship("MessageThreadParticipant",
                                        foreign_keys="MessageThreadParticipant.user_id",
                                        back_populates="user")
    sent_messages        = relationship("Message",
                                        foreign_keys="Message.sender_id",
                                        back_populates="sender")
    notifications        = relationship("Notification",
                                        foreign_keys="Notification.user_id",
                                        back_populates="user")
    triggered_notifications = relationship("Notification",
                                           foreign_keys="Notification.actor_id",
                                           back_populates="actor")
    notification_prefs   = relationship("NotificationPreferences",
                                        foreign_keys="NotificationPreferences.user_id",
                                        back_populates="user", uselist=False)
    deadlines            = relationship("Deadline",
                                        foreign_keys="Deadline.user_id",
                                        back_populates="user")
    news_bookmarks       = relationship("NewsArticleBookmark",
                                        foreign_keys="NewsArticleBookmark.user_id",
                                        back_populates="user")
    feed_preferences     = relationship("NewsFeedPreference",
                                        foreign_keys="NewsFeedPreference.user_id",
                                        back_populates="user")
    interview_sessions   = relationship("InterviewSession",
                                        foreign_keys="InterviewSession.user_id",
                                        back_populates="user")
    support_tickets      = relationship("SupportTicket",
                                        foreign_keys="SupportTicket.user_id",
                                        back_populates="user")
    assigned_tickets     = relationship("SupportTicket",
                                        foreign_keys="SupportTicket.assigned_to",
                                        back_populates="assigned_agent")
    chat_sessions_user   = relationship("SupportChatSession",
                                        foreign_keys="SupportChatSession.user_id",
                                        back_populates="user")
    chat_sessions_agent  = relationship("SupportChatSession",
                                        foreign_keys="SupportChatSession.agent_id",
                                        back_populates="agent")
    fees                 = relationship("Fee",
                                        foreign_keys="Fee.user_id",
                                        back_populates="user")
    waived_fees          = relationship("Fee",
                                        foreign_keys="Fee.waived_by",
                                        back_populates="waived_by_user")
    payment_methods      = relationship("PaymentMethod",
                                        foreign_keys="PaymentMethod.user_id",
                                        back_populates="user")
    payments             = relationship("Payment",
                                        foreign_keys="Payment.user_id",
                                        back_populates="user")
    payment_invoices     = relationship("PaymentInvoice",
                                        foreign_keys="PaymentInvoice.user_id",
                                        back_populates="user")
    requested_refunds    = relationship("PaymentRefund",
                                        foreign_keys="PaymentRefund.requested_by",
                                        back_populates="requested_by_user")
    approved_refunds     = relationship("PaymentRefund",
                                        foreign_keys="PaymentRefund.approved_by",
                                        back_populates="approved_by_user")
    subscriptions        = relationship("UserSubscription",
                                        foreign_keys="UserSubscription.user_id",
                                        back_populates="user")
    application_comments = relationship("ApplicationComment",
                                        foreign_keys="ApplicationComment.author_id",
                                        back_populates="author")
    employer_profile     = relationship("EmployerProfile",
                                        foreign_keys="EmployerProfile.user_id",
                                        back_populates="user", uselist=False)
    attorney_profile     = relationship("AttorneyProfile",
                                        foreign_keys="AttorneyProfile.user_id",
                                        back_populates="user", uselist=False)

    # ── Invitation relationships (merged in from the 66-table version) ───────
    sent_invitations     = relationship("EmployerInvitation",
                                        foreign_keys="EmployerInvitation.created_by",
                                        back_populates="creator")
    accepted_invitations = relationship("EmployerInvitation",
                                        foreign_keys="EmployerInvitation.accepted_by",
                                        back_populates="acceptor")
    my_employees         = relationship("EmployerEmployee",
                                        foreign_keys="EmployerEmployee.employer_id",
                                        back_populates="employer")
    my_employer_link     = relationship("EmployerEmployee",
                                        foreign_keys="EmployerEmployee.employee_id",
                                        back_populates="employee",
                                        uselist=False)
    push_subscriptions   = relationship("PushSubscription",
                                        foreign_keys="PushSubscription.user_id",
                                        back_populates="user")

    __table_args__ = (
        Index("ix_users_email_active",  "email",         "is_active"),
        Index("ix_users_auth_provider", "auth_provider", "auth_provider_id"),
    )


# =============================================================================
# TABLE 02 — roles
# =============================================================================

class Role(Base):
    __tablename__ = "roles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_system   = Column(Boolean, default=False, nullable=False)
    is_active   = Column(Boolean, default=True,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    role_permissions = relationship("RolePermission", back_populates="role",
                                    cascade="all, delete-orphan")
    user_roles       = relationship("UserRole", back_populates="role")


# =============================================================================
# TABLE 03 — permissions
# =============================================================================

class Permission(Base):
    __tablename__ = "permissions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code        = Column(String(100), nullable=False, unique=True)
    module      = Column(String(50),  nullable=False)
    description = Column(String(255), nullable=True)
    is_system   = Column(Boolean, default=False, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    role_permissions = relationship("RolePermission", back_populates="permission",
                                    cascade="all, delete-orphan")


# =============================================================================
# TABLE 04 — role_permissions
# =============================================================================

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id       = Column(UUID(as_uuid=True), ForeignKey("roles.id"),
                           nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"),
                           nullable=False, index=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role       = relationship("Role",       back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


# =============================================================================
# TABLE 05 — user_roles
# =============================================================================

class UserRole(Base):
    __tablename__ = "user_roles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                         nullable=False, index=True)
    role_id     = Column(UUID(as_uuid=True), ForeignKey("roles.id"),
                         nullable=False, index=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


# =============================================================================
# TABLE 06 — user_otp
# =============================================================================

class UserOTP(Base):
    __tablename__ = "user_otp"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    otp_code   = Column(String(10), nullable=False)
    otp_type   = Column(
        Enum("email_verification", "phone_verification",
             "password_reset", "two_factor_auth",
             name="otp_type_enum"),
        nullable=False
    )
    is_used    = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id], back_populates="otp_records")


# =============================================================================
# TABLE 07 — user_profiles
# Merged: includes employer link + theme_color from the 66-table version.
# =============================================================================

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, unique=True)

    full_legal_name      = Column(String(200), nullable=True)
    nationality          = Column(String(100), nullable=True)
    country_of_residence = Column(String(100), nullable=True)
    date_of_birth        = Column(Date,        nullable=True)
    gender               = Column(String(20),  nullable=True)
    profile_picture_url  = Column(String(2000), nullable=True)
    timezone             = Column(String(100), nullable=True)
    preferred_language   = Column(String(50),  nullable=True, default="en")
    phone_number         = Column(String(20),  nullable=True)
    country_code         = Column(String(10),  nullable=True)
    onboarding_step      = Column(Integer, default=1,     nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    theme_color = Column(String(7), nullable=True, default="#4f46e5")

    # ── Employer Link (set when employee accepts HR invitation) ───────────────
    employer_id = Column(UUID(as_uuid=True), ForeignKey("employer_profiles.id"),
                         nullable=True, index=True)
    invited_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user     = relationship("User", foreign_keys=[user_id], back_populates="profile")
    employer = relationship("EmployerProfile", foreign_keys=[employer_id])


# =============================================================================
# TABLE 08 — user_visa_targets
# =============================================================================

class UserVisaTarget(Base):
    __tablename__ = "user_visa_targets"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visa_type_code = Column(String, ForeignKey("visa_types.code"), nullable=False)
    is_primary     = Column(Boolean, default=False, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    user      = relationship("User",     foreign_keys=[user_id],
                             back_populates="visa_targets")
    visa_type = relationship("VisaType", back_populates="user_visa_targets")


# =============================================================================
# TABLE 09 — user_login_history
# =============================================================================

class UserLoginHistory(Base):
    __tablename__ = "user_login_history"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)

    status = Column(
        Enum("success", "failed", "blocked", name="login_status_enum"),
        nullable=False
    )
    auth_method = Column(
        Enum("email_password", "google", "microsoft", "apple", "otp",
             name="auth_method_enum"),
        nullable=False
    )
    ip_address  = Column(String(45),  nullable=True)
    city        = Column(String(100), nullable=True)
    country     = Column(String(100), nullable=True)
    browser     = Column(String(100), nullable=True)
    os          = Column(String(100), nullable=True)
    device_type = Column(
        Enum("desktop", "mobile", "tablet", "unknown",
             name="device_type_enum"),
        nullable=False, default="unknown"
    )
    user_agent         = Column(String(500), nullable=True)
    failure_reason     = Column(String(255), nullable=True)
    failed_attempts    = Column(Integer, default=0, nullable=False)
    is_suspicious      = Column(Boolean, default=False, nullable=False)
    is_current_session = Column(Boolean, default=False, nullable=False)
    session_token      = Column(String(500), nullable=True)
    logged_out_at      = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="login_history")


# =============================================================================
# TABLE 10 — password_reset_tokens
# =============================================================================

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)

    requested_email    = Column(String(255), nullable=False)
    request_ip         = Column(String(45),  nullable=True)
    request_user_agent = Column(String(500), nullable=True)
    otp_code           = Column(String(10),  nullable=False)
    otp_code_hash      = Column(String(255), nullable=True)
    expires_at         = Column(DateTime(timezone=True), nullable=False)
    resend_count       = Column(Integer,  default=0,     nullable=False)
    last_resent_at     = Column(DateTime(timezone=True), nullable=True)
    otp_verified       = Column(Boolean,  default=False, nullable=False)
    otp_verified_at    = Column(DateTime(timezone=True), nullable=True)
    failed_attempts    = Column(Integer,  default=0,     nullable=False)
    password_reset_completed    = Column(Boolean,  default=False, nullable=False)
    password_reset_completed_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        Enum("pending", "verified", "completed", "expired", "locked", "cancelled",
             name="reset_token_status_enum"),
        nullable=False, default="pending"
    )

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="reset_tokens")


# =============================================================================
# TABLE 11 — visa_types
# =============================================================================

class VisaType(Base):
    __tablename__ = "visa_types"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code        = Column(String(50),  nullable=False, unique=True)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # category = Column(
        # Enum("employment", "student", "visitor", "permanent_resident", "exchange",
            #  name="visa_category_enum"),
        # nullable=False
    # )
    category = Column(
    Enum("employment", "student", "visitor", "permanent_resident", "exchange",
         "dependent", "family_based",
         name="visa_category_enum"),
    nullable=False
    )
    requires_employer_sponsor = Column(Boolean, default=False, nullable=False)
    required_documents        = Column(Text,    nullable=True)
    typical_processing_days   = Column(Integer, nullable=True)
    government_fee_usd        = Column(Integer, nullable=True)
    lca_required              = Column(Boolean, nullable=False, default=False)
    uscis_url                 = Column(String(1000), nullable=True)
    short_label               = Column(String(30),   nullable=True)
    display_order             = Column(Integer, default=0,    nullable=False)
    is_active                 = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    applications      = relationship("Application",        back_populates="visa_type")
    user_visa_targets = relationship("UserVisaTarget",     back_populates="visa_type")
    news_tags         = relationship("NewsArticleVisaTag", back_populates="visa_type")
    feed_preferences  = relationship("NewsFeedPreference", back_populates="visa_type")
    letter_templates  = relationship("LetterTemplate",     back_populates="visa_type")


# =============================================================================
# TABLE 12 — applications
# Merged: keeps application_number auto-default + hr_approval fields.
# =============================================================================

class Application(Base):
    __tablename__ = "applications"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_number = Column(String(50), nullable=False, unique=True, index=True,
                              default=lambda: f"VF-{uuid.uuid4().hex[:8].upper()}")

    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                          nullable=False, index=True)
    visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                          nullable=False)

    sponsor_employer = Column(String(200), nullable=True)

    status = Column(
        Enum("draft", "in_progress", "action_needed", "rfe_response",
             "submitted", "approved", "rejected", "withdrawn",
             name="application_status_enum"),
        nullable=False, default="draft"
    )
    current_stage = Column(
        Enum("profile_eligibility", "documentation",
             "lca_filing", "uscis_submission",
             name="application_stage_enum"),
        nullable=True
    )

    progress_percent     = Column(Integer, default=0,     nullable=False)
    start_date           = Column(Date,    nullable=True)
    due_date             = Column(Date,    nullable=True)
    submission_date      = Column(DateTime(timezone=True), nullable=True)
    is_draft             = Column(Boolean, default=True,  nullable=False)
    has_action_required  = Column(Boolean, default=False, nullable=False)
    action_required_note = Column(String(500), nullable=True)

    assigned_attorney_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                  nullable=True)
    assigned_hr_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                  nullable=True)
    notes = Column(Text, nullable=True)

    # ── HR Approval Fields ────────────────────────────────────────────────────
    hr_approval_status = Column(
        Enum("pending", "approved", "rejected", "changes_requested",
             name="hr_approval_enum"),
        nullable=True
    )
    hr_notes       = Column(Text, nullable=True)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    hr_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("uq_one_draft_per_user_per_visa", "user_id", "visa_type_id",
              unique=True,
              postgresql_where=text("status = 'draft'")),
    )

    user              = relationship("User", foreign_keys=[user_id],
                                     back_populates="applications")
    visa_type         = relationship("VisaType", back_populates="applications")
    assigned_attorney = relationship("User", foreign_keys=[assigned_attorney_id],
                                     back_populates="attorney_cases")
    assigned_hr       = relationship("User", foreign_keys=[assigned_hr_id],
                                     back_populates="hr_cases")
    status_history    = relationship("ApplicationStatusHistory",
                                     back_populates="application")
    tasks             = relationship("ApplicationTask",
                                     back_populates="application",
                                     order_by="ApplicationTask.sort_order")
    comments          = relationship("ApplicationComment",
                                     back_populates="application",
                                     order_by="ApplicationComment.created_at.desc()")
    fees              = relationship("Fee", back_populates="application")


# =============================================================================
# TABLE 13 — application_status_history
# =============================================================================

class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=False, index=True)

    stage = Column(
        Enum("profile_eligibility", "documentation",
             "lca_filing", "uscis_submission",
             name="history_stage_enum"),
        nullable=False
    )
    status = Column(
        Enum("draft", "in_progress", "action_needed", "rfe_response",
             "submitted", "approved", "rejected", "withdrawn",
             name="history_status_enum"),
        nullable=False
    )

    note         = Column(String(500), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    changed_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="status_history")


# =============================================================================
# TABLE 14 — application_tasks
# =============================================================================

class ApplicationTask(Base):
    __tablename__ = "application_tasks"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=False, index=True)

    task_name    = Column(String(200), nullable=False)
    description  = Column(String(500), nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    is_required  = Column(Boolean, default=True,  nullable=False)
    sort_order   = Column(Integer, default=0,     nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="tasks")
    document    = relationship("Document", foreign_keys=[document_id])


# =============================================================================
# TABLE 15 — application_comments
# =============================================================================

class ApplicationComment(Base):
    __tablename__ = "application_comments"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=False, index=True)
    author_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)

    body = Column(Text, nullable=False)

    visible_to = Column(
        Enum("all_staff", "attorney_only", "hr_only", "admin_only",
             name="comment_visibility_enum"),
        nullable=False, default="all_staff"
    )

    is_pinned  = Column(Boolean, default=False, nullable=False)
    pinned_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    pinned_at  = Column(DateTime(timezone=True), nullable=True)
    is_edited  = Column(Boolean, default=False, nullable=False)
    edited_at  = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_app_comments_application", "application_id", "created_at"),
    )

    application    = relationship("Application",  foreign_keys=[application_id],
                                  back_populates="comments")
    author         = relationship("User", foreign_keys=[author_id],
                                  back_populates="application_comments")
    pinned_by_user = relationship("User", foreign_keys=[pinned_by])


# =============================================================================
# TABLE 16 — document_types
# =============================================================================

class DocumentType(Base):
    __tablename__ = "document_types"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(200), nullable=False, unique=True)
    category    = Column(
        Enum("identity", "employment", "education", "legal", "personal", "other",
             name="doc_category_enum"),
        nullable=False
    )
    description      = Column(String(500), nullable=True)
    is_optional      = Column(Boolean, default=False, nullable=False)
    accepted_formats = Column(String(100), nullable=True, default="PDF,JPG,PNG")
    max_file_size_mb = Column(Integer, default=10, nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))


# =============================================================================
# TABLE 17 — documents
# =============================================================================

class Document(Base):
    __tablename__ = "documents"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                              nullable=False, index=True)
    application_id   = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                              nullable=True, index=True)
    document_type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id"),
                              nullable=False)

    file_name        = Column(String(255), nullable=False)
    file_path        = Column(String(1000), nullable=False)
    file_size_kb     = Column(Integer, nullable=False)
    file_format      = Column(
                          Enum("pdf", "jpg", "png", "docx", "jpeg", "gif",
                               name="file_format_enum"),
                          nullable=False
                       )
    total_pages      = Column(Integer, nullable=True)

    status           = Column(
                          Enum("required", "uploaded", "pending_review",
                               "verified", "rejected", "missing",
                               name="document_status_enum"),
                          nullable=False, default="uploaded"
                       )

    verified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at      = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)

    version          = Column(Integer, default=1, nullable=False)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                                nullable=True)

    ocr_status       = Column(
                          Enum("not_started", "processing", "completed",
                               "review_needed", "confirmed",
                               name="ocr_status_enum"),
                          nullable=False, default="not_started"
                       )
    ocr_confidence   = Column(Integer, nullable=True)

    is_draft         = Column(Boolean, default=False, nullable=False)

    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user             = relationship("User",         foreign_keys=[user_id],
                                    back_populates="documents")
    application      = relationship("Application")
    document_type    = relationship("DocumentType")
    verified_by_user = relationship("User",         foreign_keys=[verified_by],
                                    back_populates="verified_documents")
    parent           = relationship("Document",     foreign_keys=[parent_document_id],
                                    remote_side="Document.id")
    pages            = relationship("DocumentPage", back_populates="document")
    activity_log     = relationship("DocumentActivity", back_populates="document")


# =============================================================================
# TABLE 18 — document_pages
# =============================================================================

class DocumentPage(Base):
    __tablename__ = "document_pages"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                         nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    image_url   = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    ocr_raw_text  = Column(Text, nullable=True)
    ocr_confidence = Column(Integer, nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    document   = relationship("Document", back_populates="pages")
    ocr_fields = relationship("DocumentOCRField", back_populates="page")


# =============================================================================
# TABLE 19 — document_ocr_fields
# =============================================================================

class DocumentOCRField(Base):
    __tablename__ = "document_ocr_fields"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                          nullable=False, index=True)
    page_id      = Column(UUID(as_uuid=True), ForeignKey("document_pages.id"),
                          nullable=True)

    field_name   = Column(String(100), nullable=False)
    extracted_value = Column(String(500), nullable=True)
    confidence_score = Column(Integer, nullable=True)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    page = relationship("DocumentPage", back_populates="ocr_fields")


# =============================================================================
# TABLE 20 — document_activity
# =============================================================================

class DocumentActivity(Base):
    __tablename__ = "document_activity"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                         nullable=False, index=True)

    action = Column(
        Enum("uploaded", "status_changed", "verified", "rejected",
             "downloaded", "viewed", "version_updated", "ocr_completed",
             "document_requested",     
             "request_fulfilled",  
             name="doc_activity_enum"),
        nullable=False
    )
    actor_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_type = Column(
        Enum("user", "system", "hr_admin", "attorney",
             name="actor_type_enum"),
        nullable=False, default="user"
    )
    note = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="activity_log")


# =============================================================================
# TABLE 21 — deadlines
# Merged: includes DeadlineExtensionRequest from the 66-table version.
# =============================================================================

class Deadline(Base):
    __tablename__ = "deadlines"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True, index=True)

    title       = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    due_date    = Column(DateTime(timezone=True), nullable=False)

    urgency = Column(
        Enum("critical", "high", "medium", "low",
             name="deadline_urgency_enum"),
        nullable=False, default="medium"
    )
    deadline_type = Column(
        Enum("document_submission", "government_filing", "attorney_review",
             "hr_approval", "interview", "other",
             name="deadline_type_enum"),
        nullable=False, default="other"
    )

    is_completed  = Column(Boolean, default=False, nullable=False)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    completed_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_dismissed  = Column(Boolean, default=False, nullable=False)
    dismissed_at  = Column(DateTime(timezone=True), nullable=True)
    reminder_sent = Column(Boolean, default=False, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_deadlines_user_due",   "user_id",  "due_date"),
        Index("ix_deadlines_urgency",    "urgency",  "is_completed"),
    )

    user        = relationship("User", foreign_keys=[user_id],
                               back_populates="deadlines")
    application = relationship("Application", foreign_keys=[application_id])


class DeadlineExtensionRequest(Base):
    """
    Stores HR extension requests against an existing Deadline row.
    """
    __tablename__ = "deadline_extension_requests"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deadline_id = Column(UUID(as_uuid=True), ForeignKey("deadlines.id"),
                         nullable=False, index=True)
    hr_user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                         nullable=False, index=True)

    request_number = Column(String(50), nullable=False)
    extension_days = Column(Integer, nullable=False)
    reason = Column(String(1000), nullable=False)

    original_deadline  = Column(DateTime(timezone=True), nullable=False)
    proposed_deadline  = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        Enum("pending", "approved", "denied",
             name="extension_status_enum"),
        nullable=False, default="pending"
    )

    requested_by_name = Column(String(200), nullable=False)
    reviewed_by_name  = Column(String(200), nullable=True)
    reviewed_at       = Column(DateTime(timezone=True), nullable=True)
    review_note       = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ext_req_deadline",  "deadline_id"),
        Index("ix_ext_req_hr_user",   "hr_user_id", "status"),
    )

    deadline = relationship("Deadline",  foreign_keys=[deadline_id])
    hr_user  = relationship("User",      foreign_keys=[hr_user_id])


# =============================================================================
# TABLE 22 — message_threads
# Merged: adds action_required + thread_status from the 70-table version.
# =============================================================================

class MessageThread(Base):
    __tablename__ = "message_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    thread_type = Column(
        Enum("direct", "group", name="thread_type_enum"),
        nullable=False, default="direct"
    )
    title          = Column(String(200), nullable=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True, index=True)

    last_message_preview = Column(String(200), nullable=True)
    last_message_at      = Column(DateTime(timezone=True), nullable=True)
    is_archived          = Column(Boolean, default=False, nullable=False)
    is_active            = Column(Boolean, default=True,  nullable=False)

    action_required = Column(Boolean, default=False, nullable=False)
    # True → attorney flagged this thread as needing client action
    thread_status = Column(
        Enum("active", "pending", "resolved", name="thread_status_enum"),
        nullable=False,
        default="active",
        index=True,
    )

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    participants = relationship("MessageThreadParticipant", back_populates="thread")
    messages     = relationship("Message", back_populates="thread",
                                order_by="Message.created_at")


# =============================================================================
# TABLE 23 — message_thread_participants
# =============================================================================

class MessageThreadParticipant(Base):
    __tablename__ = "message_thread_participants"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("message_threads.id"),
                       nullable=False, index=True)
    user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                       nullable=False, index=True)

    participant_role = Column(
        Enum("employee", "attorney", "hr", "support", "admin",
             name="participant_role_enum"),
        nullable=False
    )
    is_online    = Column(Boolean, default=False, nullable=False)
    unread_count = Column(Integer, default=0,     nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    is_muted     = Column(Boolean, default=False, nullable=False)
    is_archived  = Column(Boolean, default=False, nullable=False)
    joined_at    = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc), nullable=False)
    left_at      = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_thread_participant"),
    )

    thread = relationship("MessageThread", back_populates="participants")
    user   = relationship("User", foreign_keys=[user_id],
                          back_populates="message_threads")


# =============================================================================
# TABLE 24 — messages
# =============================================================================

class Message(Base):
    __tablename__ = "messages"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("message_threads.id"),
                       nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                       nullable=False, index=True)

    body         = Column(Text, nullable=True)
    message_type = Column(
        Enum("text", "file_attachment", "call_event", "system_notification",
             name="message_type_enum"),
        nullable=False, default="text"
    )
    document_id           = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                                   nullable=True)
    call_duration_seconds = Column(Integer, nullable=True)
    call_status = Column(
        Enum("incoming", "outgoing", "missed", "declined",
             name="call_status_enum"),
        nullable=True
    )

    is_read    = Column(Boolean, default=False, nullable=False)
    read_at    = Column(DateTime(timezone=True), nullable=True)
    is_edited  = Column(Boolean, default=False, nullable=False)
    edited_at  = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    thread     = relationship("MessageThread", back_populates="messages")
    sender     = relationship("User", foreign_keys=[sender_id],
                              back_populates="sent_messages")
    attachment = relationship("Document", foreign_keys=[document_id])


# =============================================================================
# TABLE 25 — notifications
# Merged: union of notification_type values from both versions.
# =============================================================================

class Notification(Base):
    __tablename__ = "notifications"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)

    notification_type = Column(
        Enum("missing_document", "deadline_approaching", "policy_update",
             "document_approved", "case_status_updated", "participant_added",
             "document_comment", "weekly_summary", "security_alert",
             "payment_receipt", "immigration_news",
             "approval_pending", "approval_resolved", "compliance_alert",
             "employee_onboarded", "employee_profile_updated",
             "task_assigned","new_device_login", "failed_login_alert",
             "password_changed", "unusual_activity",
             "document_requested",              
             "document_request_fulfilled",       
             "document_uploaded_by_staff",
             "document_uploaded",
             "chat_message_received",
             "deadline_missed",
             "calendar_event_reminder",      
             name="notification_type_enum"),
        nullable=False
    )
    category = Column(
        Enum("case_update", "deadline", "news", "security", "billing",
             "approval", "compliance", "employee",
             name="notification_category_enum"),
        nullable=False
    )
    priority = Column(
        Enum("urgent", "high", "medium", "low",
             name="notification_priority_enum"),
        nullable=False, default="low"
    )

    title          = Column(String(300), nullable=False)
    body           = Column(Text,        nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True)
    document_id    = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                            nullable=True)
    case_reference = Column(String(100), nullable=True)
    actor_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_label    = Column(String(150), nullable=True)

    cta_primary_label   = Column(String(50),  nullable=True)
    cta_primary_url     = Column(String(500), nullable=True)
    cta_secondary_label = Column(String(50),  nullable=True)
    cta_secondary_url   = Column(String(500), nullable=True)

    is_read      = Column(Boolean, default=False, nullable=False)
    read_at      = Column(DateTime(timezone=True), nullable=True)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    sent_via_email = Column(Boolean, default=False, nullable=False)
    sent_via_push  = Column(Boolean, default=False, nullable=False)
    sent_via_sms   = Column(Boolean, default=False, nullable=False)
    expires_at     = Column(DateTime(timezone=True), nullable=True)
    dedup_key = Column(String(255), nullable=True, unique=True, index=True)


    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_notifications_user_read",     "user_id", "is_read"),
        Index("ix_notifications_user_category", "user_id", "category"),
    )

    user  = relationship("User", foreign_keys=[user_id],
                         back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id],
                         back_populates="triggered_notifications")


# =============================================================================
# TABLE 26 — notification_preferences
# Merged: keeps notify_compliance_alerts from the 66-table version.
# =============================================================================

class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, unique=True)

    email_enabled = Column(Boolean, default=True,  nullable=False)
    push_enabled  = Column(Boolean, default=True,  nullable=False)
    sms_enabled   = Column(Boolean, default=False, nullable=False)

    notify_case_updates     = Column(Boolean, default=True, nullable=False)
    notify_deadlines        = Column(Boolean, default=True, nullable=False)
    notify_document_updates = Column(Boolean, default=True, nullable=False)
    notify_news             = Column(Boolean, default=True, nullable=False)
    notify_security_alerts  = Column(Boolean, default=True, nullable=False)
    notify_billing          = Column(Boolean, default=True, nullable=False)
    notify_weekly_summary   = Column(Boolean, default=True, nullable=False)
    notify_compliance_alerts = Column(Boolean, default=True, nullable=False)

    notify_new_device_login_email = Column(Boolean, default=True,  nullable=False)
    notify_new_device_login_sms   = Column(Boolean, default=True,  nullable=False)
    notify_failed_login_email     = Column(Boolean, default=True,  nullable=False)
    notify_failed_login_sms       = Column(Boolean, default=False, nullable=False)
    notify_password_changed_email = Column(Boolean, default=True,  nullable=False)
    notify_password_changed_sms   = Column(Boolean, default=False, nullable=False)
    notify_unusual_activity_email = Column(Boolean, default=True,  nullable=False)
    notify_unusual_activity_sms   = Column(Boolean, default=True,  nullable=False)


    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id],
                        back_populates="notification_prefs")
# =============================================================================
# TABLE 26.5 — push_subscriptions
# =============================================================================

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
 
    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                      nullable=False, index=True)
    endpoint = Column(Text, nullable=False)
    p256dh   = Column(Text, nullable=False)
    auth     = Column(Text, nullable=False)
 
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc), nullable=False)
 
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_push_sub_user_endpoint"),
    )
 
    user = relationship("User", foreign_keys=[user_id],
                        back_populates="push_subscriptions")

# =============================================================================
# TABLE 27 — notification_templates
# =============================================================================

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key = Column(String(100), nullable=False,index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    channel = Column(
        Enum("email", "sms", "in_app", "push",
             name="notification_channel_enum"),
        nullable=False
    )

    subject   = Column(String(500), nullable=True)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=False)
    available_placeholders = Column(Text, nullable=True)

    category = Column(
        Enum("case_update", "deadline", "news", "security", "billing",
              "approval", "compliance", "employee",
             name="notification_category_enum",
             create_type=False),
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # __table_args__ = (
        # Index("ix_notif_templates_event_channel", "event_key", "channel"),
    # )
    __table_args__ = (
    UniqueConstraint("event_key", "channel", name="uq_notif_template_event_channel"),
    Index("ix_notif_templates_event_channel", "event_key", "channel"),
    )


# =============================================================================
# TABLE 28 — news_articles
# =============================================================================

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title   = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    body    = Column(Text, nullable=False)
    source  = Column(String(200), nullable=False)
    source_url = Column(String(1000), nullable=True)

    read_time_minutes = Column(Integer, nullable=True)
    view_count        = Column(Integer, default=0, nullable=False)

    priority = Column(
        Enum("critical", "important", "normal", name="news_priority_enum"),
        nullable=False, default="normal"
    )
    update_type = Column(
        Enum("policy_change", "fee_update", "processing_time",
             "form_change", "court_decision", "general",
             name="news_update_type_enum"),
        nullable=False, default="general"
    )

    has_case_impact  = Column(Boolean, default=False, nullable=False)
    case_impact_note = Column(Text, nullable=True)
    cta_label        = Column(String(100),  nullable=True)
    cta_url          = Column(String(1000), nullable=True)

    published_at = Column(DateTime(timezone=True), nullable=False)
    is_published = Column(Boolean, default=True,  nullable=False)
    is_active    = Column(Boolean, default=True,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_news_published_at", "published_at", "is_published"),
    )

    visa_tags = relationship("NewsArticleVisaTag",  back_populates="article",
                             cascade="all, delete-orphan")
    bookmarks = relationship("NewsArticleBookmark", back_populates="article")


# =============================================================================
# TABLE 29 — news_article_visa_tags
# =============================================================================

class NewsArticleVisaTag(Base):
    __tablename__ = "news_article_visa_tags"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id   = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"),
                          nullable=False, index=True)
    visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                          nullable=False, index=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("article_id", "visa_type_id", name="uq_article_visa_tag"),
    )

    article   = relationship("NewsArticle", back_populates="visa_tags")
    visa_type = relationship("VisaType",    back_populates="news_tags")


# =============================================================================
# TABLE 30 — news_article_bookmarks
# =============================================================================

class NewsArticleBookmark(Base):
    __tablename__ = "news_article_bookmarks"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                        nullable=False, index=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"),
                        nullable=False, index=True)
    note       = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_bookmark"),
    )

    user    = relationship("User",        foreign_keys=[user_id],
                           back_populates="news_bookmarks")
    article = relationship("NewsArticle", back_populates="bookmarks")


# =============================================================================
# TABLE 31 — news_feed_preferences
# =============================================================================

class NewsFeedPreference(Base):
    __tablename__ = "news_feed_preferences"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                          nullable=False, index=True)
    visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                          nullable=False)

    include_policy_changes   = Column(Boolean, default=True,  nullable=False)
    include_fee_updates      = Column(Boolean, default=True,  nullable=False)
    include_processing_times = Column(Boolean, default=True,  nullable=False)
    include_form_changes     = Column(Boolean, default=True,  nullable=False)
    include_court_decisions  = Column(Boolean, default=False, nullable=False)
    is_active                = Column(Boolean, default=True,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "visa_type_id",
                         name="uq_user_visa_feed_preference"),
    )

    user      = relationship("User",     foreign_keys=[user_id],
                             back_populates="feed_preferences")
    visa_type = relationship("VisaType", back_populates="feed_preferences")


# =============================================================================
# TABLE 32 — interview_sessions
# Merged: keeps HR approval fields from the 66-table version.
# =============================================================================

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True, index=True)
    visa_type_id   = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                            nullable=False)

    status = Column(
        Enum("upcoming", "completed", "cancelled", "rescheduled",
             name="interview_status_enum"),
        nullable=False, default="upcoming"
    )

    interview_date   = Column(Date,        nullable=False)
    interview_time   = Column(String(20),  nullable=True)
    timezone         = Column(String(100), nullable=True)
    location_name    = Column(String(300), nullable=True)
    location_address = Column(String(500), nullable=True)
    location_city    = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=True)
    preparation_progress = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)

    # ── HR Approval Fields ────────────────────────────────────────────────────
    hr_approval_status = Column(
        Enum("pending", "approved", "rejected", "changes_requested",
             name="hr_approval_enum"),
        nullable=True
    )
    hr_notes       = Column(Text, nullable=True)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    hr_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user            = relationship("User", foreign_keys=[user_id],
                                   back_populates="interview_sessions")
    application     = relationship("Application", foreign_keys=[application_id])
    visa_type       = relationship("VisaType",    foreign_keys=[visa_type_id])
    checklist_items = relationship("InterviewChecklistItem",
                                   back_populates="session",
                                   order_by="InterviewChecklistItem.sort_order")
    questions       = relationship("InterviewQuestion", back_populates="session")
    tips            = relationship("InterviewTip",      back_populates="session")


# =============================================================================
# TABLE 33 — interview_checklist_items
# =============================================================================

class InterviewChecklistItem(Base):
    __tablename__ = "interview_checklist_items"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
                        nullable=False, index=True)

    title        = Column(String(300), nullable=False)
    description  = Column(Text, nullable=True)
    is_required  = Column(Boolean, default=True,  nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    sort_order   = Column(Integer, default=0, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    session  = relationship("InterviewSession", back_populates="checklist_items")
    document = relationship("Document", foreign_keys=[document_id])


# =============================================================================
# TABLE 34 — interview_questions
# =============================================================================

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
                          nullable=True, index=True)
    visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                          nullable=True)

    question    = Column(Text, nullable=False)
    guidance    = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    sort_order  = Column(Integer, default=0,    nullable=False)
    is_active   = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    session   = relationship("InterviewSession", back_populates="questions")
    visa_type = relationship("VisaType", foreign_keys=[visa_type_id])


# =============================================================================
# TABLE 35 — interview_tips
# =============================================================================

class InterviewTip(Base):
    __tablename__ = "interview_tips"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
                          nullable=True, index=True)
    visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                          nullable=True)

    tip_group = Column(
        Enum("day_of_interview", "what_to_wear", "general",
             name="tip_group_enum"),
        nullable=False, default="day_of_interview"
    )
    title       = Column(String(300), nullable=False)
    body        = Column(Text, nullable=True)
    disclaimer  = Column(Text, nullable=True)
    sort_order  = Column(Integer, default=0,    nullable=False)
    is_active   = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    session   = relationship("InterviewSession", back_populates="tips")
    visa_type = relationship("VisaType", foreign_keys=[visa_type_id])


# =============================================================================
# TABLE 36 — support_articles
# =============================================================================

class SupportArticle(Base):
    __tablename__ = "support_articles"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title    = Column(String(500), nullable=False)
    body     = Column(Text, nullable=False)
    summary  = Column(String(500), nullable=True)

    article_type = Column(
        Enum("faq", "guide", "video_tutorial", "policy",
             name="article_type_enum"),
        nullable=False, default="faq"
    )
    category = Column(
        Enum("all", "account_profile", "active_cases", "documents",
             "billing_payments", "visa_types", "getting_started",
             name="support_category_enum"),
        nullable=False, default="all"
    )

    tag                    = Column(String(100), nullable=True)
    video_url              = Column(String(1000), nullable=True)
    video_duration_seconds = Column(Integer,      nullable=True)
    search_keywords        = Column(Text,         nullable=True)
    view_count             = Column(Integer, default=0,     nullable=False)
    helpful_count          = Column(Integer, default=0,     nullable=False)
    not_helpful_count      = Column(Integer, default=0,     nullable=False)
    sort_order             = Column(Integer, default=0,     nullable=False)
    is_published           = Column(Boolean, default=False, nullable=False)
    is_active              = Column(Boolean, default=True,  nullable=False)
    is_featured            = Column(Boolean, default=False, nullable=False)

    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at   = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_support_articles_cat", "category", "is_published", "sort_order"),
    )


# =============================================================================
# TABLE 37 — support_tickets
# =============================================================================

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(50), nullable=False, unique=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                           nullable=True, index=True)
    guest_name    = Column(String(200), nullable=True)
    guest_email   = Column(String(255), nullable=True)

    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True)
    document_id    = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                            nullable=True)

    subject  = Column(String(500), nullable=False)
    body     = Column(Text, nullable=False)
    category = Column(
        Enum("account_profile", "active_cases", "documents",
             "billing_payments", "visa_types", "technical", "other",
             name="ticket_category_enum"),
        nullable=False, default="other"
    )
    priority = Column(
        Enum("urgent", "high", "medium", "low", name="ticket_priority_enum"),
        nullable=False, default="medium"
    )
    status = Column(
        Enum("open", "in_progress", "waiting_user", "resolved", "closed",
             name="ticket_status_enum"),
        nullable=False, default="open"
    )

    assigned_to       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sla_due_at        = Column(DateTime(timezone=True), nullable=True)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at       = Column(DateTime(timezone=True), nullable=True)

    channel = Column(
        Enum("web_form", "live_chat", "email", name="ticket_channel_enum"),
        nullable=False, default="web_form"
    )
    chat_session_id = Column(UUID(as_uuid=True),
                             ForeignKey("support_chat_sessions.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_tickets_status_priority", "status",      "priority"),
        Index("ix_tickets_assigned_status", "assigned_to", "status"),
    )

    user           = relationship("User", foreign_keys=[user_id],
                                  back_populates="support_tickets")
    assigned_agent = relationship("User", foreign_keys=[assigned_to],
                                  back_populates="assigned_tickets")
    application    = relationship("Application", foreign_keys=[application_id])
    replies        = relationship("SupportTicketReply", back_populates="ticket",
                                  order_by="SupportTicketReply.created_at",
                                  cascade="all, delete-orphan")


# =============================================================================
# TABLE 38 — support_ticket_replies
# =============================================================================

class SupportTicketReply(Base):
    __tablename__ = "support_ticket_replies"

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"),
                       nullable=False, index=True)

    sender_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sender_type = Column(
        Enum("user", "agent", "system", name="reply_sender_type_enum"),
        nullable=False, default="user"
    )
    body             = Column(Text, nullable=False)
    document_id      = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
                              nullable=True)
    is_read          = Column(Boolean, default=False, nullable=False)
    read_at          = Column(DateTime(timezone=True), nullable=True)
    is_internal_note = Column(Boolean, default=False, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    ticket     = relationship("SupportTicket", back_populates="replies")
    sender     = relationship("User", foreign_keys=[sender_id])
    attachment = relationship("Document", foreign_keys=[document_id])


# =============================================================================
# TABLE 39 — support_chat_sessions
# =============================================================================

class SupportChatSession(Base):
    __tablename__ = "support_chat_sessions"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    guest_name  = Column(String(200), nullable=True)
    guest_email = Column(String(255), nullable=True)

    status = Column(
        Enum("queued", "active", "ended", "escalated", "abandoned",
             name="chat_session_status_enum"),
        nullable=False, default="queued"
    )

    ticket_id    = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"),
                          nullable=True)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    ended_at     = Column(DateTime(timezone=True), nullable=True)
    wait_seconds = Column(Integer, nullable=True)
    rating       = Column(Integer, nullable=True)
    rating_note  = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    user     = relationship("User", foreign_keys=[user_id],
                            back_populates="chat_sessions_user")
    agent    = relationship("User", foreign_keys=[agent_id],
                            back_populates="chat_sessions_agent")
    ticket   = relationship("SupportTicket", foreign_keys=[ticket_id])
    messages = relationship("SupportChatMessage", back_populates="session",
                            order_by="SupportChatMessage.created_at",
                            cascade="all, delete-orphan")


# =============================================================================
# TABLE 40 — support_chat_messages
# =============================================================================

class SupportChatMessage(Base):
    __tablename__ = "support_chat_messages"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("support_chat_sessions.id"),
                        nullable=False, index=True)

    sender_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sender_type = Column(
        Enum("user", "agent", "system", name="chat_sender_type_enum"),
        nullable=False, default="user"
    )
    body         = Column(Text, nullable=False)
    message_type = Column(
        Enum("text", "file", "system_event", name="chat_message_type_enum"),
        nullable=False, default="text"
    )
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    is_read     = Column(Boolean, default=False, nullable=False)
    read_at     = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    session    = relationship("SupportChatSession", back_populates="messages")
    sender     = relationship("User",     foreign_keys=[sender_id])
    attachment = relationship("Document", foreign_keys=[document_id])


# =============================================================================
# TABLE 41 — employer_profiles
# Merged: keeps invitations/employees relationships from the 66-table version.
# =============================================================================

class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, unique=True)

    company_name  = Column(String(300), nullable=False)
    company_size  = Column(
        Enum("1_10", "11_50", "51_200", "201_500", "501_1000", "1000_plus",
             name="company_size_enum"),
        nullable=True
    )
    industry       = Column(String(100),  nullable=True)
    website        = Column(String(500),  nullable=True)
    ein            = Column(String(20),   nullable=True)
    address_line1  = Column(String(300),  nullable=True)
    address_line2  = Column(String(300),  nullable=True)
    city           = Column(String(100),  nullable=True)
    state          = Column(String(100),  nullable=True)
    zip_code       = Column(String(20),   nullable=True)
    country        = Column(String(2),    nullable=True, default="US")
    contact_name   = Column(String(200),  nullable=True)
    contact_email  = Column(String(255),  nullable=True)
    contact_phone  = Column(String(30),   nullable=True)
    logo_url       = Column(String(1000), nullable=True)
    is_verified    = Column(Boolean, default=False, nullable=False)
    is_active      = Column(Boolean, default=True,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user        = relationship("User", foreign_keys=[user_id],
                             back_populates="employer_profile")
    invitations = relationship("EmployerInvitation",
                               foreign_keys="EmployerInvitation.employer_profile_id",
                               back_populates="employer_profile")
    employees   = relationship("EmployerEmployee",
                               foreign_keys="EmployerEmployee.employer_profile_id",
                               back_populates="employer_profile")


# =============================================================================
# TABLE 42 — attorney_profiles
# Merged: adds hourly_rate_cents + monthly_billing_target_cents (70-table).
# =============================================================================

class AttorneyProfile(Base):
    __tablename__ = "attorney_profiles"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, unique=True)

    bar_number         = Column(String(50),  nullable=True)
    bar_state          = Column(String(50),  nullable=True)
    years_experience   = Column(Integer,     nullable=True)
    law_firm_name      = Column(String(300), nullable=True)
    specialisations    = Column(Text, nullable=True)
    languages          = Column(Text, nullable=True)
    availability_note  = Column(String(300), nullable=True)
    max_active_cases   = Column(Integer,      nullable=True)
    bio                = Column(Text,         nullable=True)
    profile_photo_url  = Column(String(1000), nullable=True)
    is_accepting_cases = Column(Boolean, default=True,  nullable=False)
    is_verified        = Column(Boolean, default=False, nullable=False)
    is_active          = Column(Boolean, default=True,  nullable=False)

    hourly_rate_cents = Column(Integer, nullable=True)
    # Used as the default rate for attorney billing (TimeEntry / BillingClient).

    monthly_billing_target_cents = Column(Integer, nullable=True)
    # Attorney's self-set monthly billing revenue target in US cents.
    # NULL = no target set → dashboard hides the progress bar.

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id],
                        back_populates="attorney_profile")


# =============================================================================
# TABLE 43 — fee_templates
# =============================================================================

class FeeTemplate(Base):
    __tablename__ = "fee_templates"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code        = Column(String(100), nullable=False, unique=True)
    name        = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    category = Column(
        Enum("filing_fee", "premium_processing", "biometrics",
             "attorney_fee", "document_fee", "other",
             name="fee_category_enum"),
        nullable=False, default="other"
    )
    visa_type_id        = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
                                 nullable=True)
    default_amount_usd  = Column(Integer, nullable=False)
    is_government_fee   = Column(Boolean, default=False, nullable=False)
    is_optional         = Column(Boolean, default=False, nullable=False)
    due_days_after_creation = Column(Integer, nullable=True)
    sort_order          = Column(Integer, default=0,    nullable=False)
    is_active           = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    fees      = relationship("Fee",      back_populates="template")
    visa_type = relationship("VisaType", foreign_keys=[visa_type_id])


# =============================================================================
# TABLE 44 — fees
# =============================================================================

class Fee(Base):
    __tablename__ = "fees"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=False, index=True)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)
    fee_template_id = Column(UUID(as_uuid=True), ForeignKey("fee_templates.id"),
                             nullable=True)

    title    = Column(String(300), nullable=False)
    category = Column(
        Enum("filing_fee", "premium_processing", "biometrics",
             "attorney_fee", "document_fee", "other",
             name="fee_instance_category_enum"),
        nullable=False, default="filing_fee"
    )
    amount_usd = Column(Integer, nullable=False)

    status = Column(
        Enum("pending", "paid", "overdue", "waived", "refunded", "cancelled",
             name="fee_status_enum"),
        nullable=False, default="pending"
    )

    is_urgent  = Column(Boolean, default=False, nullable=False)
    due_date   = Column(DateTime(timezone=True), nullable=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    paid_at    = Column(DateTime(timezone=True), nullable=True)

    waived_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    waived_at     = Column(DateTime(timezone=True), nullable=True)
    waiver_reason = Column(String(500), nullable=True)
    notes         = Column(Text, nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_fees_user_status",        "user_id",        "status"),
        Index("ix_fees_application_status", "application_id", "status"),
        Index("ix_fees_due_date",           "due_date",       "status"),
    )

    application    = relationship("Application",  foreign_keys=[application_id],
                                  back_populates="fees")
    user           = relationship("User",         foreign_keys=[user_id],
                                  back_populates="fees")
    template       = relationship("FeeTemplate",  back_populates="fees")
    payment        = relationship("Payment",      foreign_keys=[payment_id],
                                  back_populates="fees")
    waived_by_user = relationship("User",         foreign_keys=[waived_by],
                                  back_populates="waived_fees")


# =============================================================================
# TABLE 45 — payment_methods
# =============================================================================

class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)

    method_type = Column(
        Enum("credit_card", "debit_card", "paypal",
             "apple_pay", "google_pay", "bank_transfer",
             name="payment_method_type_enum"),
        nullable=False
    )
    card_brand = Column(
        Enum("visa", "mastercard", "amex", "discover", "other",
             name="card_brand_enum"),
        nullable=True
    )
    card_last4               = Column(String(4),   nullable=True)
    card_exp_month           = Column(Integer,     nullable=True)
    card_exp_year            = Column(Integer,     nullable=True)
    card_holder_name         = Column(String(200), nullable=True)
    gateway_customer_id      = Column(String(255), nullable=True)
    gateway_payment_method_id = Column(String(255), nullable=True)
    paypal_email             = Column(String(255), nullable=True)
    wallet_device_id         = Column(String(255), nullable=True)

    billing_name    = Column(String(200), nullable=True)
    billing_line1   = Column(String(300), nullable=True)
    billing_line2   = Column(String(300), nullable=True)
    billing_city    = Column(String(100), nullable=True)
    billing_state   = Column(String(100), nullable=True)
    billing_zip     = Column(String(20),  nullable=True)
    billing_country = Column(String(2),   nullable=True)

    is_default  = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active   = Column(Boolean, default=True,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_payment_methods_user_active", "user_id", "is_active"),
    )

    user     = relationship("User",    foreign_keys=[user_id],
                            back_populates="payment_methods")
    payments = relationship("Payment", back_populates="payment_method")


# =============================================================================
# TABLE 46 — payments
# Merged: keeps both invoice_id (SaaS) and attorney_invoice_id (attorney billing).
# =============================================================================

class Payment(Base):
    __tablename__ = "payments"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                               nullable=False, index=True)
    payment_method_id = Column(UUID(as_uuid=True), ForeignKey("payment_methods.id"),
                               nullable=True)

    method_type_snapshot = Column(
        Enum("credit_card", "debit_card", "paypal",
             "apple_pay", "google_pay", "bank_transfer",
             name="payment_method_snapshot_enum"),
        nullable=False
    )
    card_last4_snapshot = Column(String(4), nullable=True)
    amount_usd          = Column(Integer,   nullable=False)

    gateway = Column(
        Enum("stripe", "braintree", "paypal", "apple_pay", "manual",
             name="payment_gateway_enum"),
        nullable=False, default="stripe"
    )
    gateway_payment_intent_id = Column(String(255), nullable=True, index=True)
    gateway_charge_id         = Column(String(255), nullable=True)
    gateway_receipt_url       = Column(String(1000), nullable=True)

    status = Column(
        Enum("pending", "processing", "completed", "failed",
             "cancelled", "refunded", "partially_refunded",
             name="payment_status_enum"),
        nullable=False, default="pending"
    )

    failure_code    = Column(String(100), nullable=True)
    failure_message = Column(String(500), nullable=True)
    initiated_at    = Column(DateTime(timezone=True), nullable=True)
    completed_at    = Column(DateTime(timezone=True), nullable=True)

    invoice_id      = Column(UUID(as_uuid=True), ForeignKey("payment_invoices.id",
                                                           use_alter=True,
                                                           name="fk_payments_invoice_id"),
                             nullable=True)
    attorney_invoice_id = Column(UUID(as_uuid=True),
                                ForeignKey("attorney_invoices.id"),
                                nullable=True, index=True)

    description     = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_payments_user_status",    "user_id", "status"),
        Index("ix_payments_gateway_intent", "gateway_payment_intent_id"),
        Index("ix_payments_completed_at",   "completed_at"),
        Index("ix_payments_attorney_invoice", "attorney_invoice_id",
              postgresql_where=text("attorney_invoice_id IS NOT NULL")),
    )

    user           = relationship("User",          foreign_keys=[user_id],
                                  back_populates="payments")
    payment_method = relationship("PaymentMethod", back_populates="payments")
    fees           = relationship("Fee",           foreign_keys="Fee.payment_id",
                                  back_populates="payment")
    invoice        = relationship("PaymentInvoice", foreign_keys=[invoice_id],
                                  back_populates="payment", uselist=False)
    attorney_invoice = relationship("AttorneyInvoice",
                                foreign_keys=[attorney_invoice_id])
    refunds        = relationship("PaymentRefund", back_populates="payment")


# =============================================================================
# TABLE 47 — payment_invoices
# =============================================================================

class PaymentInvoice(Base):
    __tablename__ = "payment_invoices"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), nullable=False, unique=True)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                            nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True)

    subtotal_usd = Column(Integer, nullable=False)
    tax_usd      = Column(Integer, nullable=False, default=0)
    total_usd    = Column(Integer, nullable=False)
    currency     = Column(String(3), nullable=False, default="USD")

    pdf_url          = Column(String(1000), nullable=True)
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        Enum("pending", "generated", "sent", "voided",
             name="invoice_status_enum"),
        nullable=False, default="pending"
    )
    sent_at     = Column(DateTime(timezone=True), nullable=True)
    voided_at   = Column(DateTime(timezone=True), nullable=True)
    void_reason = Column(String(300), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user        = relationship("User",        foreign_keys=[user_id],
                               back_populates="payment_invoices")
    application = relationship("Application", foreign_keys=[application_id])
    payment     = relationship("Payment",     foreign_keys="Payment.invoice_id",
                               back_populates="invoice", uselist=False)


# =============================================================================
# TABLE 48 — payment_refunds
# =============================================================================

class PaymentRefund(Base):
    __tablename__ = "payment_refunds"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"),
                        nullable=False, index=True)

    amount_usd = Column(Integer, nullable=False)
    reason = Column(
        Enum("duplicate_payment", "application_withdrawn", "fee_waived",
             "overpayment", "admin_adjustment", "other",
             name="refund_reason_enum"),
        nullable=False, default="other"
    )
    notes  = Column(Text, nullable=True)
    status = Column(
        Enum("pending", "processing", "completed", "failed",
             name="refund_status_enum"),
        nullable=False, default="pending"
    )

    gateway_refund_id = Column(String(255), nullable=True)
    requested_at      = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at      = Column(DateTime(timezone=True), nullable=True)
    requested_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    payment           = relationship("Payment",  back_populates="refunds")
    requested_by_user = relationship("User",     foreign_keys=[requested_by],
                                     back_populates="requested_refunds")
    approved_by_user  = relationship("User",     foreign_keys=[approved_by],
                                     back_populates="approved_refunds")


# =============================================================================
# TABLE 49 — subscription_plans
# =============================================================================

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False, unique=True)
    slug        = Column(String(50),  nullable=False, unique=True)
    description = Column(String(500), nullable=True)

    price_monthly_cents = Column(Integer, nullable=False, default=0)
    price_annual_cents  = Column(Integer, nullable=False, default=0)
    currency            = Column(String(3), nullable=False, default="USD")
    trial_days          = Column(Integer,   nullable=False, default=0)

    max_applications = Column(Integer, nullable=True)
    max_documents    = Column(Integer, nullable=True)
    max_messages     = Column(Integer, nullable=True)

    stripe_product_id       = Column(String(255), nullable=True)
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_annual  = Column(String(255), nullable=True)
    paypal_plan_id_monthly  = Column(String(255), nullable=True)
    paypal_plan_id_annual   = Column(String(255), nullable=True)

    is_active       = Column(Boolean, default=True,  nullable=False)
    is_public       = Column(Boolean, default=True,  nullable=False)
    is_featured     = Column(Boolean, default=False, nullable=False)
    display_order   = Column(Integer, default=0,     nullable=False)
    highlight_color = Column(String(7), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_subscription_plans_active_order", "is_active", "display_order"),
    )

    features      = relationship("PlanFeature",      back_populates="plan",
                                 cascade="all, delete-orphan",
                                 order_by="PlanFeature.sort_order")
    subscriptions = relationship("UserSubscription", back_populates="plan")


# =============================================================================
# TABLE 50 — plan_features
# =============================================================================

class PlanFeature(Base):
    __tablename__ = "plan_features"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"),
                     nullable=False, index=True)

    feature_text   = Column(String(300), nullable=False)
    is_included    = Column(Boolean, default=True,  nullable=False)
    is_highlighted = Column(Boolean, default=False, nullable=False)
    sort_order     = Column(Integer, default=0, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    plan = relationship("SubscriptionPlan", back_populates="features")


# =============================================================================
# TABLE 51 — subscription_coupons
# =============================================================================

class SubscriptionCoupon(Base):
    __tablename__ = "subscription_coupons"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code        = Column(String(50),  nullable=False, unique=True)
    name        = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    discount_type = Column(
        Enum("percentage", "fixed_amount", name="coupon_discount_type_enum"),
        nullable=False
    )
    discount_value = Column(Integer, nullable=False)

    valid_from  = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    max_uses    = Column(Integer, nullable=True)
    uses_count  = Column(Integer, default=0, nullable=False)

    applicable_plan_slugs = Column(Text, nullable=True)

    stripe_coupon_id     = Column(String(255), nullable=True)
    stripe_promo_code_id = Column(String(255), nullable=True)
    is_active            = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_coupons_code",      "code"),
        Index("ix_coupons_is_active", "is_active"),
    )


# =============================================================================
# TABLE 52 — user_subscriptions
# =============================================================================

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"),
                     nullable=False, index=True)

    status = Column(
        Enum("trialing", "active", "past_due", "cancelled",
             "paused", "expired", "unpaid",
             name="subscription_status_enum"),
        nullable=False, default="trialing"
    )
    billing_cycle = Column(
        Enum("monthly", "annual", "lifetime", name="billing_cycle_enum"),
        nullable=False, default="monthly"
    )

    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end   = Column(DateTime(timezone=True), nullable=True)
    trial_start          = Column(DateTime(timezone=True), nullable=True)
    trial_end            = Column(DateTime(timezone=True), nullable=True)

    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancelled_at         = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason  = Column(String(500), nullable=True)

    payment_processor = Column(
        Enum("stripe", "paypal", "manual", name="payment_processor_enum"),
        nullable=False, default="stripe"
    )
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_customer_id     = Column(String(255), nullable=True)
    paypal_subscription_id = Column(String(255), nullable=True, index=True)

    coupon_id             = Column(UUID(as_uuid=True),
                                   ForeignKey("subscription_coupons.id"), nullable=True)
    discount_percent      = Column(Integer, nullable=True)
    discount_amount_cents = Column(Integer, nullable=True)
    effective_mrr_cents   = Column(Integer, nullable=True)

    assigned_by_admin = Column(Boolean, default=False, nullable=False)
    admin_notes       = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_user_subs_user_status",   "user_id", "status"),
        Index("ix_user_subs_stripe_sub_id", "stripe_subscription_id"),
        Index("ix_user_subs_paypal_sub_id", "paypal_subscription_id"),
    )

    user     = relationship("User",             foreign_keys=[user_id],
                            back_populates="subscriptions")
    plan     = relationship("SubscriptionPlan", back_populates="subscriptions")
    coupon   = relationship("SubscriptionCoupon")
    invoices = relationship("SubscriptionInvoice", back_populates="subscription",
                            order_by="SubscriptionInvoice.created_at.desc()")


# =============================================================================
# TABLE 53 — subscription_invoices
# =============================================================================

class SubscriptionInvoice(Base):
    __tablename__ = "subscription_invoices"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("user_subscriptions.id"),
                             nullable=False, index=True)
    invoice_number  = Column(String(50), nullable=False, unique=True)

    subtotal_cents = Column(Integer, nullable=False, default=0)
    discount_cents = Column(Integer, nullable=False, default=0)
    tax_cents      = Column(Integer, nullable=False, default=0)
    total_cents    = Column(Integer, nullable=False, default=0)
    currency       = Column(String(3), nullable=False, default="USD")

    status = Column(
        Enum("draft", "open", "pending", "failed", "paid",
             "void", "uncollectible", "refunded",
             name="sub_invoice_status_enum"),
        nullable=False, default="open"
    )

    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    billing_period_end   = Column(DateTime(timezone=True), nullable=True)
    due_date             = Column(DateTime(timezone=True), nullable=True)
    paid_at              = Column(DateTime(timezone=True), nullable=True)

    payment_processor = Column(
        Enum("stripe", "paypal", "manual", name="sub_invoice_processor_enum"),
        nullable=False, default="stripe"
    )

    stripe_invoice_id        = Column(String(255), nullable=True, unique=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_charge_id         = Column(String(255), nullable=True)
    invoice_pdf_url          = Column(String(1000), nullable=True)
    paypal_order_id          = Column(String(255), nullable=True)
    paypal_capture_id        = Column(String(255), nullable=True)

    refunded_at         = Column(DateTime(timezone=True), nullable=True)
    refund_amount_cents = Column(Integer, nullable=True)
    refund_reason       = Column(String(500), nullable=True)
    stripe_refund_id    = Column(String(255), nullable=True)
    attempt_count       = Column(Integer, default=0, nullable=False)
    next_attempt_at     = Column(DateTime(timezone=True), nullable=True)

    failure_code = Column(
        Enum("card_expired", "insufficient_funds", "card_declined",
             "authentication_required", "do_not_honor",
             "lost_card", "stolen_card", "other",
             name="invoice_failure_code_enum"),
        nullable=True
    )

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False, index=True)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_sub_invoices_stripe_id",  "stripe_invoice_id"),
        Index("ix_sub_invoices_sub_status", "subscription_id", "status"),
    )

    subscription = relationship("UserSubscription", back_populates="invoices")


# =============================================================================
# TABLE 54 — revenue_snapshots
# =============================================================================

class RevenueSnapshot(Base):
    __tablename__ = "revenue_snapshots"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date = Column(Date, nullable=False, unique=True, index=True)

    mrr_cents = Column(Integer, nullable=False, default=0)
    arr_cents = Column(Integer, nullable=False, default=0)

    active_subscriber_count  = Column(Integer, nullable=False, default=0)
    new_subscriber_count     = Column(Integer, nullable=False, default=0)
    churned_subscriber_count = Column(Integer, nullable=False, default=0)

    net_revenue_churn_bps = Column(Integer, nullable=False, default=0)
    churned_mrr_cents     = Column(Integer, nullable=False, default=0)
    expansion_mrr_cents   = Column(Integer, nullable=False, default=0)

    mrr_by_plan              = Column(Text, nullable=True)
    subscriber_count_by_plan = Column(Text, nullable=True)

    new_trial_count       = Column(Integer, nullable=False, default=0)
    converted_trial_count = Column(Integer, nullable=False, default=0)
    churned_trial_count   = Column(Integer, nullable=False, default=0)

    failing_payment_count             = Column(Integer, nullable=False, default=0)
    failing_payment_mrr_at_risk_cents = Column(Integer, nullable=False, default=0)

    generated_at = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc), nullable=False)


# =============================================================================
# TABLE 55 — revenue_targets
# =============================================================================

class RevenueTarget(Base):
    __tablename__ = "revenue_targets"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_month     = Column(Date,    nullable=False, unique=True)
    target_mrr_cents = Column(Integer, nullable=False)
    notes            = Column(String(500), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_revenue_targets_month", "target_month"),
    )

    created_by_user  = relationship("User", foreign_keys=[created_by])
    modified_by_user = relationship("User", foreign_keys=[modified_by])


# =============================================================================
# TABLE 56 — system_settings
# =============================================================================

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key   = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)

    value_type = Column(
        Enum("string", "boolean", "integer", "json", "url",
             name="setting_value_type_enum"),
        nullable=False, default="string"
    )
    setting_group = Column(
        Enum("general", "security", "email", "sms",
             "notifications", "features", "maintenance",
             name="setting_group_enum"),
        nullable=False
    )

    label         = Column(String(255), nullable=False)
    description   = Column(Text, nullable=True)
    is_public     = Column(Boolean, default=False, nullable=False)
    is_readonly   = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_system_settings_group_order", "setting_group", "display_order"),
    )


# =============================================================================
# TABLE 57 — audit_logs
# =============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                        nullable=True, index=True)
    actor_type = Column(
        Enum("user", "system", "webhook", "admin_impersonation",
             name="audit_actor_type_enum"),
        nullable=False, default="user"
    )
    actor_email         = Column(String(255), nullable=True)
    actor_role_snapshot = Column(String(50),  nullable=True)

    action = Column(String(100), nullable=False, index=True)

    resource_type = Column(String(50),  nullable=True)
    resource_id   = Column(UUID(as_uuid=True), nullable=True, index=True)

    old_value   = Column(Text, nullable=True)
    new_value   = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)

    ip_address = Column(String(45),  nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)

    severity = Column(
        Enum("info", "warning", "critical", name="audit_severity_enum"),
        nullable=False, default="info"
    )

    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_logs_actor_created",    "actor_id",      "created_at"),
        Index("ix_audit_logs_resource",         "resource_type", "resource_id"),
        Index("ix_audit_logs_action_created",   "action",        "created_at"),
        Index("ix_audit_logs_severity_created", "severity",      "created_at"),
    )

    actor = relationship("User", foreign_keys=[actor_id])

# TABLE 57b — payment_gateway_configs
# =============================================================================
 
class PaymentGatewayConfig(Base):
    """
    Admin Subscription screen → "Payment Gateway Configuration" panel.
    One row per gateway (stripe / paypal / bank_transfer).
    Credentials are stored encrypted at the application layer — this column
    holds ciphertext only, never plaintext keys.
    """
    __tablename__ = "payment_gateway_configs"
 
    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # gateway  = Column(
        # Enum("stripe", "paypal", "bank_transfer", name="payment_gateway_enum"),
        # nullable=False, unique=True
    # )
    gateway = Column(
    Enum("stripe", "braintree", "paypal", "apple_pay", "manual",
         name="payment_gateway_enum"),
    nullable=False, default="stripe"
            )
    is_connected = Column(Boolean, default=False, nullable=False)
    is_enabled   = Column(Boolean, default=False, nullable=False)  # on/off toggle in UI
 
    # Ciphertext only — encrypt/decrypt in the service layer, never log this column.
    credentials_encrypted = Column(Text, nullable=True)
 
    transaction_fee_percent_bps = Column(Integer, nullable=True)  # 290 = 2.90%
    transaction_fee_fixed_cents = Column(Integer, nullable=True)  # 30 = $0.30
    settlement_days_min         = Column(Integer, nullable=True)
    settlement_days_max         = Column(Integer, nullable=True)
    supported_methods           = Column(String(255), nullable=True)  # "Card, ACH"
 
    connected_at = Column(DateTime(timezone=True), nullable=True)
 
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
    __table_args__ = (
        Index("ix_payment_gateway_configs_gateway", "gateway"),
    )
 
 

# =============================================================================
# TABLE 58 — appointment_types
# =============================================================================

class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title       = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    price_usd   = Column(Integer, nullable=False)
    is_active   = Column(Boolean, default=True, nullable=False)
    sort_order  = Column(Integer, default=0, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    bookings = relationship("ConsultationBooking", back_populates="appointment_type")


# =============================================================================
# TABLE 59 — attorney_availability
# =============================================================================

class AttorneyAvailability(Base):
    __tablename__ = "attorney_availability"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attorney_id = Column(UUID(as_uuid=True), ForeignKey("attorney_profiles.id"),
                         nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time  = Column(Time, nullable=False)
    end_time    = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    timezone    = Column(String(50), nullable=False, default="America/Los_Angeles")
    is_active   = Column(Boolean, default=True, nullable=False)

    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    attorney    = relationship("AttorneyProfile", foreign_keys=[attorney_id])

    __table_args__ = (
        Index("ix_attorney_availability_attorney_day", "attorney_id", "day_of_week"),
    )


# =============================================================================
# TABLE 60 — consultation_slots
# =============================================================================

class ConsultationSlot(Base):
    __tablename__ = "consultation_slots"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attorney_id = Column(UUID(as_uuid=True), ForeignKey("attorney_profiles.id"),
                         nullable=False, index=True)
    slot_date   = Column(Date, nullable=False)
    slot_time   = Column(Time, nullable=False)
    timezone    = Column(String(50), nullable=False, default="America/Los_Angeles")

    is_booked   = Column(Boolean, default=False, nullable=False)
    is_blocked  = Column(Boolean, default=False, nullable=False)

    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    attorney    = relationship("AttorneyProfile", foreign_keys=[attorney_id])
    booking     = relationship("ConsultationBooking", back_populates="slot",
                               uselist=False)

    __table_args__ = (
        UniqueConstraint("attorney_id", "slot_date", "slot_time",
                         name="uq_slot_attorney_date_time"),
        Index("ix_consultation_slots_attorney_date", "attorney_id", "slot_date"),
    )


# =============================================================================
# TABLE 61 — consultation_bookings
# =============================================================================

class ConsultationBooking(Base):
    __tablename__ = "consultation_bookings"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                  nullable=False, index=True)
    attorney_id          = Column(UUID(as_uuid=True), ForeignKey("attorney_profiles.id"),
                                  nullable=False, index=True)
    slot_id              = Column(UUID(as_uuid=True), ForeignKey("consultation_slots.id"),
                                  nullable=False, unique=True)
    appointment_type_id  = Column(UUID(as_uuid=True), ForeignKey("appointment_types.id"),
                                  nullable=False)

    consultation_format  = Column(
        Enum("virtual", "in_person", name="consultation_format_enum"),
        nullable=False, default="virtual"
    )

    status = Column(
        Enum("pending", "confirmed", "cancelled", "completed", "no_show",
             name="consultation_booking_status_enum"),
        nullable=False, default="pending"
    )

    amount_usd           = Column(Integer, nullable=True)
    payment_id           = Column(UUID(as_uuid=True), ForeignKey("payments.id"),
                                  nullable=True)
    is_paid              = Column(Boolean, default=False, nullable=False)

    meeting_link         = Column(String(1000), nullable=True)

    employee_notes       = Column(Text, nullable=True)
    attorney_notes       = Column(Text, nullable=True)
    cancellation_reason  = Column(String(500), nullable=True)
    cancelled_at         = Column(DateTime(timezone=True), nullable=True)
    cancelled_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at           = Column(DateTime(timezone=True),
                                  default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at           = Column(DateTime(timezone=True),
                                  default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    employee         = relationship("User", foreign_keys=[employee_id])
    attorney         = relationship("AttorneyProfile", foreign_keys=[attorney_id])
    slot             = relationship("ConsultationSlot", back_populates="booking")
    appointment_type = relationship("AppointmentType", back_populates="bookings")
    payment          = relationship("Payment", foreign_keys=[payment_id])

    __table_args__ = (
        Index("ix_consultation_bookings_employee", "employee_id", "status"),
        Index("ix_consultation_bookings_attorney", "attorney_id", "status"),
    )


# =============================================================================
# TABLE 62 — employer_invitations
# (restored from the 66-table version — missing entirely from the 70-table one)
# =============================================================================

class EmployerInvitation(Base):
    __tablename__ = "employer_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                 nullable=False)
    employer_profile_id = Column(UUID(as_uuid=True), ForeignKey("employer_profiles.id"),
                                 nullable=False)

    invite_method = Column(
        Enum("email", "link", "code", name="invite_method_enum"),
        nullable=False, default="email"
    )

    invited_email    = Column(String(255), nullable=True)
    invite_code      = Column(String(30),  nullable=True, unique=True)
    invite_token     = Column(String(128), nullable=True, unique=True)

    max_uses         = Column(Integer, nullable=True)
    used_count       = Column(Integer, default=0, nullable=False)

    status = Column(
        Enum("pending", "accepted", "expired", "revoked",
             name="invitation_status_enum"),
        nullable=False, default="pending"
    )

    expires_at       = Column(DateTime(timezone=True), nullable=True)
    accepted_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    accepted_at      = Column(DateTime(timezone=True), nullable=True)
    personal_message = Column(String(500), nullable=True)
    revoked_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    revoked_at       = Column(DateTime(timezone=True), nullable=True)
    modified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_employer_invitations_creator",  "created_by"),
        Index("ix_employer_invitations_employer",  "employer_profile_id"),
        Index("ix_employer_invitations_email",     "invited_email"),
        Index("ix_employer_invitations_code",      "invite_code"),
        Index("ix_employer_invitations_token",     "invite_token"),
        Index("ix_employer_invitations_status",    "status"),
    )

    creator          = relationship("User", foreign_keys=[created_by],
                                    back_populates="sent_invitations")
    employer_profile = relationship("EmployerProfile",
                                    foreign_keys=[employer_profile_id],
                                    back_populates="invitations")
    acceptor         = relationship("User", foreign_keys=[accepted_by],
                                    back_populates="accepted_invitations")
    revoker          = relationship("User", foreign_keys=[revoked_by])
    employment       = relationship("EmployerEmployee",
                                    back_populates="invitation", uselist=False)


# =============================================================================
# TABLE 63 — employer_employees
# (restored from the 66-table version — missing entirely from the 70-table one)
# =============================================================================

class EmployerEmployee(Base):
    __tablename__ = "employer_employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    employer_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                 nullable=False)
    employee_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                 nullable=False)
    employer_profile_id = Column(UUID(as_uuid=True), ForeignKey("employer_profiles.id"),
                                 nullable=False)
    invitation_id       = Column(UUID(as_uuid=True), ForeignKey("employer_invitations.id"),
                                 nullable=True)

    is_active    = Column(Boolean, default=True,  nullable=False)
    job_title    = Column(String(200), nullable=True)
    department   = Column(String(200), nullable=True)
    work_email   = Column(String(255), nullable=True)
    start_date   = Column(Date,        nullable=True)
    end_date     = Column(Date,        nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("employer_id", "employee_id", name="uq_employer_employee_pair"),
        Index("ix_employer_employees_employer",  "employer_id"),
        Index("ix_employer_employees_employee",  "employee_id"),
        Index("ix_employer_employees_active",    "employer_id", "is_active"),
    )

    employer         = relationship("User", foreign_keys=[employer_id],
                                    back_populates="my_employees")
    employee         = relationship("User", foreign_keys=[employee_id],
                                    back_populates="my_employer_link")
    employer_profile = relationship("EmployerProfile",
                                    foreign_keys=[employer_profile_id],
                                    back_populates="employees")
    invitation       = relationship("EmployerInvitation",
                                    back_populates="employment")


# =============================================================================
# TABLE 64 — calendar_events
# =============================================================================

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attorney_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                          nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=True, index=True)

    event_type = Column(
        Enum("consultation", "court_hearing", "doc_review",
             "internal_sync", "deadline",
             name="calendar_event_type_enum"),
        nullable=False, index=True,
    )

    title      = Column(String(300), nullable=False)
    event_date = Column(Date,        nullable=False, index=True)
    start_time = Column(Time,        nullable=True)
    end_time   = Column(Time,        nullable=True)
    is_all_day = Column(Boolean,     default=False, nullable=False)
    location   = Column(String(300), nullable=True)
    notes      = Column(Text,        nullable=True)

    status = Column(
        Enum("confirmed", "cancelled", "tentative",
             name="calendar_event_status_enum"),
        nullable=False, default="confirmed",
    )

    reminder_enabled = Column(Boolean, default=True,  nullable=False)
    reminder_minutes = Column(Integer, default=1440,  nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_calendar_events_attorney_date", "attorney_id", "event_date"),
        Index("ix_calendar_events_type_date",     "event_type",  "event_date"),
    )

    attorney         = relationship("User", foreign_keys=[attorney_id])
    application      = relationship("Application", foreign_keys=[application_id])
    created_by_user  = relationship("User", foreign_keys=[created_by])
    modified_by_user = relationship("User", foreign_keys=[modified_by])


# =============================================================================
# TABLE 65 — client_intake_sessions
# =============================================================================

class ClientIntakeSession(Base):
    __tablename__ = "client_intake_sessions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                            nullable=False, index=True)

    token              = Column(String(128), nullable=True, unique=True, index=True)
    token_expires_at   = Column(DateTime(timezone=True), nullable=True)
    token_generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    token_generated_at = Column(DateTime(timezone=True), nullable=True)

    current_step      = Column(Integer, default=1,     nullable=False)
    step_1_completed  = Column(Boolean, default=False, nullable=False)
    step_2_completed  = Column(Boolean, default=False, nullable=False)
    step_3_completed  = Column(Boolean, default=False, nullable=False)
    step_4_completed  = Column(Boolean, default=False, nullable=False)
    step_5_completed  = Column(Boolean, default=False, nullable=False)

    is_draft      = Column(Boolean, default=True,  nullable=False)
    last_saved_at = Column(DateTime(timezone=True), nullable=True)
    is_submitted  = Column(Boolean, default=False, nullable=False)
    submitted_at  = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("application_id", name="uq_one_session_per_application"),
        Index("ix_intake_sessions_token", "token"),
    )

    application = relationship("Application", foreign_keys=[application_id])
    intake_data = relationship("IntakeImmigrationHistory",
                               back_populates="session", uselist=False,
                               cascade="all, delete-orphan")


# =============================================================================
# TABLE 66 — intake_immigration_history
# Merged: union of fields from both versions (richer disclosure/overstay data
# from the 70-table version + passport_expiry_date from the 66-table one).
# =============================================================================

class IntakeImmigrationHistory(Base):
    __tablename__ = "intake_immigration_history"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_session_id = Column(UUID(as_uuid=True),
                               ForeignKey("client_intake_sessions.id"),
                               nullable=False, unique=True, index=True)

    first_name           = Column(String(100), nullable=True)
    last_name            = Column(String(100), nullable=True)
    date_of_birth        = Column(Date,        nullable=True)
    gender               = Column(String(20),  nullable=True)
    nationality          = Column(String(100), nullable=True)
    passport_number      = Column(String(50),  nullable=True)
    passport_expiry_date = Column(Date,        nullable=True)
    email                = Column(String(255), nullable=True)

    current_visa_status  = Column(String(50), nullable=True)
    visa_expiration_date = Column(Date,       nullable=True)

    has_visa_denial     = Column(Boolean, nullable=True)
    visa_denial_details = Column(Text,    nullable=True)
    has_overstay        = Column(Boolean, nullable=True)
    overstay_days        = Column(Integer, nullable=True)
    overstay_period      = Column(String(100), nullable=True)

    disclosures_acknowledged_at         = Column(DateTime(timezone=True), nullable=True)
    disclosures_verified_by_attorney_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    disclosures_verified_at = Column(DateTime(timezone=True), nullable=True)

    previous_visas = Column(Text, nullable=True, default="[]")

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("ClientIntakeSession", back_populates="intake_data")


# =============================================================================
# TABLE 67 — billing_clients
# =============================================================================

class BillingClient(Base):
    __tablename__ = "billing_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                                 nullable=True, index=True)
    employer_profile_id = Column(UUID(as_uuid=True),
                                 ForeignKey("employer_profiles.id"),
                                 nullable=True, index=True)

    display_name      = Column(String(300), nullable=False)
    client_type       = Column(
        Enum("corporate", "individual", name="billing_client_type_enum"),
        nullable=False, default="individual",
    )
    billing_email     = Column(String(255), nullable=True)
    billing_phone     = Column(String(30),  nullable=True)
    custom_rate_cents = Column(Integer, nullable=True)
    is_active         = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("uq_billing_clients_user",
              "user_id", unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        Index("uq_billing_clients_employer",
              "employer_profile_id", unique=True,
              postgresql_where=text("employer_profile_id IS NOT NULL")),
        Index("ix_billing_clients_type_active", "client_type", "is_active"),
    )

    user             = relationship("User",            foreign_keys=[user_id])
    employer_profile = relationship("EmployerProfile", foreign_keys=[employer_profile_id])
    created_by_user  = relationship("User",            foreign_keys=[created_by])
    time_entries     = relationship("TimeEntry",       back_populates="billing_client",
                                    order_by="TimeEntry.entry_date.desc()")
    invoices         = relationship("AttorneyInvoice", back_populates="billing_client",
                                    order_by="AttorneyInvoice.created_at.desc()")


# =============================================================================
# TABLE 68 — time_entries
# =============================================================================

class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    attorney_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                               nullable=False, index=True)
    billing_client_id = Column(UUID(as_uuid=True), ForeignKey("billing_clients.id"),
                               nullable=False, index=True)
    application_id    = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                               nullable=True, index=True)

    entry_date       = Column(Date, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False)
    description      = Column(Text, nullable=False)
    is_billable      = Column(Boolean, default=True, nullable=False)

    hourly_rate_cents = Column(Integer, nullable=False)
    amount_cents      = Column(Integer, nullable=False)

    status = Column(
        Enum("unbilled", "invoiced", "paid", "written_off",
             name="time_entry_status_enum"),
        nullable=False, default="unbilled", index=True,
    )

    invoice_id  = Column(UUID(as_uuid=True), ForeignKey("attorney_invoices.id"),
                         nullable=True, index=True)
    invoiced_at = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_time_entries_attorney_date", "attorney_id",       "entry_date"),
        Index("ix_time_entries_client_status", "billing_client_id", "status"),
        Index("ix_time_entries_application",   "application_id",    "status",
              postgresql_where=text("application_id IS NOT NULL")),
        Index("ix_time_entries_invoice",       "invoice_id",
              postgresql_where=text("invoice_id IS NOT NULL")),
    )

    attorney         = relationship("User",            foreign_keys=[attorney_id])
    billing_client   = relationship("BillingClient",   back_populates="time_entries")
    application      = relationship("Application",     foreign_keys=[application_id])
    invoice          = relationship("AttorneyInvoice", foreign_keys=[invoice_id],
                                    back_populates="time_entries")
    line_items       = relationship("InvoiceLineItem", back_populates="time_entry")
    created_by_user  = relationship("User",            foreign_keys=[created_by])
    modified_by_user = relationship("User",            foreign_keys=[modified_by])


# =============================================================================
# TABLE 69 — attorney_invoices
# NOT the same as payment_invoices (T47): that's SaaS employee receipts;
# this is attorney-to-client legal billing.
# =============================================================================

class AttorneyInvoice(Base):
    __tablename__ = "attorney_invoices"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)

    attorney_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                               nullable=False, index=True)
    billing_client_id = Column(UUID(as_uuid=True), ForeignKey("billing_clients.id"),
                               nullable=False, index=True)
    application_id    = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
                               nullable=True, index=True)

    issued_date = Column(Date, nullable=True)
    due_date    = Column(Date, nullable=True)

    subtotal_cents = Column(Integer, nullable=False, default=0)
    tax_cents      = Column(Integer, nullable=False, default=0)
    discount_cents = Column(Integer, nullable=False, default=0)
    total_cents    = Column(Integer, nullable=False, default=0)
    currency       = Column(String(3), nullable=False, default="USD")

    status = Column(
        Enum("draft", "open", "sent", "paid", "overdue", "void",
             name="attorney_invoice_status_enum"),
        nullable=False, default="draft", index=True,
    )

    sent_at   = Column(DateTime(timezone=True), nullable=True)
    paid_at   = Column(DateTime(timezone=True), nullable=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)

    void_reason = Column(String(300), nullable=True)
    voided_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    pdf_url          = Column(String(1000), nullable=True)
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)
    notes            = Column(Text, nullable=True)

    matter            = Column(String(200), nullable=True)
    tax_rate_percent  = Column(Integer, nullable=False, default=0)
    payment_terms     = Column(String(100), nullable=True)
    notes_to_client   = Column(Text, nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_attorney_invoices_attorney_status", "attorney_id",       "status"),
        Index("ix_attorney_invoices_client_status",   "billing_client_id", "status"),
        Index("ix_attorney_invoices_due_date_status", "due_date",          "status"),
    )

    attorney         = relationship("User",          foreign_keys=[attorney_id])
    billing_client   = relationship("BillingClient", back_populates="invoices")
    application      = relationship("Application",   foreign_keys=[application_id])
    voided_by_user   = relationship("User",          foreign_keys=[voided_by])
    created_by_user  = relationship("User",          foreign_keys=[created_by])
    modified_by_user = relationship("User",          foreign_keys=[modified_by])
    time_entries     = relationship("TimeEntry",     back_populates="invoice",
                                    foreign_keys="TimeEntry.invoice_id")
    line_items       = relationship("InvoiceLineItem", back_populates="invoice",
                                    order_by="InvoiceLineItem.sort_order",
                                    cascade="all, delete-orphan")


# =============================================================================
# TABLE 70 — invoice_line_items
# =============================================================================

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("attorney_invoices.id"),
                        nullable=False, index=True)

    time_entry_id = Column(UUID(as_uuid=True), ForeignKey("time_entries.id"),
                           nullable=True, index=True)

    description       = Column(String(500), nullable=False)
    quantity          = Column(Integer, nullable=False, default=1)
    unit_amount_cents = Column(Integer, nullable=False)
    total_cents       = Column(Integer, nullable=False)
    sort_order        = Column(Integer, nullable=False, default=0)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    invoice    = relationship("AttorneyInvoice", back_populates="line_items")
    time_entry = relationship("TimeEntry",       back_populates="line_items")
    created_by_user = relationship("User",       foreign_keys=[created_by])


# =============================================================================
# TABLE 71 — message_templates
# =============================================================================

class MessageTemplate(Base):
    """
    Canned reply-template chips shown in the message compose bar.
    """
    __tablename__ = "message_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_message_templates_active_order", "is_active", "sort_order"),
    )


# =============================================================================
# TABLE 72 — letter_templates
# =============================================================================

class LetterTemplate(Base):
    """
    Immigration letter/document templates for the Template Library.

    is_platform = False → "My Templates" (created by this attorney)
    is_platform = True  → "Platform Templates" (pre-seeded, visible to all)
    """
    __tablename__ = "letter_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title       = Column(String(300), nullable=False)
    description = Column(String(1000), nullable=True)
    body_content = Column(Text, nullable=False)

    template_type = Column(
        Enum(
            "cover_letter",
            "support_letter",
            "rfe_response",
            "petition_statement",
            name="letter_template_type_enum",
        ),
        nullable=False,
    )

    visa_type_code = Column(
        String(50),
        ForeignKey("visa_types.code"),
        nullable=True,
        index=True,
    )

    page_count = Column(Integer, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    is_platform = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_letter_templates_type_platform", "template_type", "is_platform", "is_active"),
        Index("ix_letter_templates_visa_code", "visa_type_code"),
        Index("ix_letter_templates_created_by", "created_by", "is_active"),
    )

    visa_type = relationship("VisaType", back_populates="letter_templates")

# =============================================================================
# TABLE 73 — document_requests
# =============================================================================

class DocumentRequest(Base):
    __tablename__ = "document_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    application_id  = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    requested_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)   # the attorney
    requested_from  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)   # the client

    document_name = Column(String(200), nullable=False)     # e.g. "Form W-2 (2024)"
    details       = Column(Text, nullable=False)             # "Details / Reason"

    priority = Column(
        Enum("low", "normal", "high", "urgent", name="doc_request_priority_enum"),
        nullable=False, default="normal"
    )
    due_date = Column(Date, nullable=True)

    status = Column(
        Enum("pending", "fulfilled", "cancelled", name="doc_request_status_enum"),
        nullable=False, default="pending"
    )

    document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)  # filled in once uploaded
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_doc_requests_application_status", "application_id", "status"),
        Index("ix_doc_requests_client_status", "requested_from", "status"),
    )

    application = relationship("Application")
    requester   = relationship("User", foreign_keys=[requested_by])
    client      = relationship("User", foreign_keys=[requested_from])
    document    = relationship("Document", foreign_keys=[document_id])
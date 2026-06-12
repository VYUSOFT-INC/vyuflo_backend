# # =============================================================================
# # models.py — SQLAlchemy Models
# # =============================================================================

# import uuid
# from datetime import datetime, timezone
# from sqlalchemy import (
#     Column, String, Boolean, DateTime, Date, Time,
#     Integer, Enum, Text, ForeignKey, UniqueConstraint, Index
# )
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import declarative_base, relationship

# Base = declarative_base()


# # =============================================================================
# # TABLE 1 — users
# # =============================================================================

# # class User(Base):
# #     __tablename__ = "users"

# #     # ── Primary Key ───────────────────────────────────────────────────────────
# #     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# #     # ── Basic Info (from Signup form) ─────────────────────────────────────────
# #     first_name   = Column(String(100), nullable=False)
# #     last_name    = Column(String(100), nullable=False)
# #     email        = Column(String(255), nullable=False, unique=True, index=True)
# #     phone        = Column(String(20),  nullable=True)
# #     country_code = Column(String(10),  nullable=True)   # e.g. "+1"

# #     # ── Authentication ────────────────────────────────────────────────────────
# #     password_hash    = Column(String(255), nullable=True)
# #     # nullable → SSO users (Google/Microsoft/Apple) have no password

# #     auth_provider    = Column(
# #                           Enum("email", "google", "microsoft", "apple",
# #                                name="auth_provider_enum"),
# #                           nullable=False, default="email"
# #                        )
# #     # "Continue with Google / Microsoft" — Login screen
# #     # "Sign in with Apple" — Profile & Security screen 28

# #     auth_provider_id = Column(String(255), nullable=True)
# #     # OAuth user ID returned by Google/Microsoft/Apple
# #     # null for email users

# #     # ── Status Flags ──────────────────────────────────────────────────────────
# #     is_active   = Column(Boolean, default=True,  nullable=False)
# #     # False → suspended account — cannot login
# #     is_verified = Column(Boolean, default=False, nullable=False)
# #     # True → email verified (Onboarding Step 3 "Verification — Confirm email")

# #     # ── Consent (from Signup form) ────────────────────────────────────────────
# #     terms_accepted     = Column(Boolean,  nullable=False, default=False)
# #     terms_accepted_at  = Column(DateTime(timezone=True), nullable=True)
# #     marketing_opt_in   = Column(Boolean,  default=False, nullable=False)
# #     # "I'd like to receive product updates..." checkbox
# #     newsletter_opt_in  = Column(Boolean,  default=False, nullable=False)
# #     # "Subscribe to monthly immigration insights newsletter" checkbox
# #     referral_source    = Column(String(100), nullable=True)
# #     # "How did you hear about us?" optional dropdown

# #     # ── Timestamps ────────────────────────────────────────────────────────────
# #     last_login_at = Column(DateTime(timezone=True), nullable=True)
# #     created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
# #     updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
# #                            onupdate=lambda: datetime.now(timezone.utc), nullable=False)

# #     # ── Audit — self-referencing FK ───────────────────────────────────────────
# #     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
# #     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
# #     # nullable → first admin has no creator above them

# #     # =========================================================
# #     # ALL RELATIONSHIPS — every table that FK's back to users
# #     # =========================================================

# #     # ── Auth & Security ───────────────────────────────────────────────────────
# #     otp_records    = relationship("UserOTP",
# #                                    foreign_keys="UserOTP.user_id",
# #                                    back_populates="user")
# #     # TABLE 3 — user_otp.user_id → users.id
# #     # 2FA codes, email verification, phone verification, password reset OTPs

# #     login_history  = relationship("UserLoginHistory",
# #                                    foreign_keys="UserLoginHistory.user_id",
# #                                    back_populates="user",
# #                                    order_by="UserLoginHistory.created_at.desc()")
# #     # TABLE 6 — user_login_history.user_id → users.id
# #     # "Login History" panel — Screen 28
# #     # Chrome on MacBook Pro, Safari on iPhone, Failed Login from Mumbai...

# #     reset_tokens   = relationship("PasswordResetToken",
# #                                    foreign_keys="PasswordResetToken.user_id",
# #                                    back_populates="user")
# #     # TABLE 32 — password_reset_tokens.user_id → users.id
# #     # Screens 07–10: Email → OTP → New Password → Success

# #     # ── Profile & Preferences ─────────────────────────────────────────────────
# #     profile        = relationship("UserProfile",
# #                                    foreign_keys="UserProfile.user_id",
# #                                    back_populates="user",
# #                                    uselist=False)
# #     # TABLE 4 — user_profiles.user_id → users.id  (1:1)
# #     # full_legal_name, nationality, DOB, profile_picture, timezone, language
# #     # onboarding_step, onboarding_completed

# #     visa_targets   = relationship("UserVisaTarget",
# #                                    foreign_keys="UserVisaTarget.user_id",
# #                                    back_populates="user")
# #     # TABLE 5 — user_visa_targets.user_id → users.id  (1:many)
# #     # Multi-select "Target Visa Types" — Onboarding Step 3
# #     # H-1B, O-1 Extraordinary, etc.

# #     # ── Roles & Permissions ───────────────────────────────────────────────────
# #     user_roles     = relationship("UserRole",
# #                                    foreign_keys="UserRole.user_id",
# #                                    back_populates="user")
# #     # TABLE 2 — user_roles.user_id → users.id  (1:many)
# #     # employee, student, dependent, employer_hr, attorney, admin
# #     # A user CAN have multiple roles simultaneously (confirmed)

# #     # ── Applications ──────────────────────────────────────────────────────────
# #     applications       = relationship("Application",
# #                                        foreign_keys="Application.user_id",
# #                                        back_populates="user")
# #     # TABLE 7 — applications.user_id → users.id  (1:many)
# #     # All visa applications filed by this user

# #     attorney_cases     = relationship("Application",
# #                                        foreign_keys="Application.assigned_attorney_id",
# #                                        back_populates="assigned_attorney")
# #     # TABLE 7 — applications.assigned_attorney_id → users.id
# #     # Cases where this user is the assigned attorney

# #     hr_cases           = relationship("Application",
# #                                        foreign_keys="Application.assigned_hr_id",
# #                                        back_populates="assigned_hr")
# #     # TABLE 7 — applications.assigned_hr_id → users.id
# #     # Cases where this user is the assigned HR manager
# #     # "TechCorp Inc. Sponsorship" — Screen 15

# #     # ── Documents ─────────────────────────────────────────────────────────────
# #     documents          = relationship("Document",
# #                                        foreign_keys="Document.user_id",
# #                                        back_populates="user")
# #     # TABLE 11 — documents.user_id → users.id  (1:many)
# #     # All documents uploaded by this user

# #     verified_documents = relationship("Document",
# #                                        foreign_keys="Document.verified_by",
# #                                        back_populates="verified_by_user")
# #     # TABLE 11 — documents.verified_by → users.id
# #     # Documents this user has verified (HR Admin / Attorney role)
# #     # "Passport_Scan_2023.pdf verified by HR Admin" — Screen 19

# #     # ── Messaging ─────────────────────────────────────────────────────────────
# #     message_threads    = relationship("MessageThreadParticipant",
# #                                        foreign_keys="MessageThreadParticipant.user_id",
# #                                        back_populates="user")
# #     # TABLE 16 — message_thread_participants.user_id → users.id
# #     # All conversation threads this user is part of — Screen 24

# #     sent_messages      = relationship("Message",
# #                                        foreign_keys="Message.sender_id",
# #                                        back_populates="sender")
# #     # TABLE 17 — messages.sender_id → users.id  (1:many)
# #     # All messages sent by this user

# #     # ── Notifications ─────────────────────────────────────────────────────────
# #     notifications      = relationship("Notification",
# #                                        foreign_keys="Notification.user_id",
# #                                        back_populates="user")
# #     # TABLE 20 — notifications.user_id → users.id  (1:many)
# #     # All notifications received by this user — Screen 25/26

# #     triggered_notifications = relationship("Notification",
# #                                             foreign_keys="Notification.actor_id",
# #                                             back_populates="actor")
# #     # TABLE 20 — notifications.actor_id → users.id
# #     # Notifications triggered BY this user
# #     # "David Martinez commented..." / "Michael Chen was added..."

# #     notification_prefs = relationship("NotificationPreferences",
# #                                        foreign_keys="NotificationPreferences.user_id",
# #                                        back_populates="user",
# #                                        uselist=False)
# #     # TABLE 21 — notification_preferences.user_id → users.id  (1:1)
# #     # Email / Push / SMS toggle preferences — Screen 25 sidebar

# #     deadlines          = relationship("Deadline",
# #                                        foreign_keys="Deadline.user_id",
# #                                        back_populates="user")
# #     # TABLE 22 — deadlines.user_id → users.id  (1:many)
# #     # "I-983 Signature Due — March 28 (3 days) — Critical" — Screen 25

# #     # ── News Feed ─────────────────────────────────────────────────────────────
# #     news_bookmarks     = relationship("NewsArticleBookmark",
# #                                        foreign_keys="NewsArticleBookmark.user_id",
# #                                        back_populates="user")
# #     # TABLE 25 — news_article_bookmarks.user_id → users.id  (1:many)
# #     # "Saved Articles: 18" — Screen 27

# #     feed_preferences   = relationship("NewsFeedPreference",
# #                                        foreign_keys="NewsFeedPreference.user_id",
# #                                        back_populates="user")
# #     # TABLE 26 — news_feed_preferences.user_id → users.id  (1:many)
# #     # "Active Filters: H-1B, OPT/STEM OPT" — Screen 27

# #     # ── Interview Prep ────────────────────────────────────────────────────────
# #     interview_sessions = relationship("InterviewSession",
# #                                        foreign_keys="InterviewSession.user_id",
# #                                        back_populates="user")
# #     # TABLE 28 — interview_sessions.user_id → users.id  (1:many)
# #     # "B1/B2 Visa Interview — Oct 15, 2023 — US Embassy London" — Screen 23

# #     # ── Help & Support ────────────────────────────────────────────────────────
# #     support_tickets    = relationship("SupportTicket",
# #                                        foreign_keys="SupportTicket.user_id",
# #                                        back_populates="user")
# #     # TABLE 34 — support_tickets.user_id → users.id  (1:many)
# #     # Tickets submitted by this user — "Submit a Ticket" — Screen 29

# #     assigned_tickets   = relationship("SupportTicket",
# #                                        foreign_keys="SupportTicket.assigned_to",
# #                                        back_populates="assigned_agent")
# #     # TABLE 34 — support_tickets.assigned_to → users.id
# #     # Tickets assigned TO this user (support agent role)
# #     # "Available Mon-Fri 9am-6pm EST" — Screen 29

# #     chat_sessions_user  = relationship("SupportChatSession",
# #                                         foreign_keys="SupportChatSession.user_id",
# #                                         back_populates="user")
# #     # TABLE 36 — support_chat_sessions.user_id → users.id
# #     # "Start Chat" live chat sessions started by this user

# #     chat_sessions_agent = relationship("SupportChatSession",
# #                                         foreign_keys="SupportChatSession.agent_id",
# #                                         back_populates="agent")
# #     # TABLE 36 — support_chat_sessions.agent_id → users.id
# #     # Live chat sessions where this user is the support agent

# #     # ── Table constraints ─────────────────────────────────────────────────────
# #     __table_args__ = (
# #         Index("ix_users_email_active", "email", "is_active"),
# #         # composite index — most queries filter by email + active status
# #         Index("ix_users_auth_provider", "auth_provider", "auth_provider_id"),
# #         # speeds up SSO login lookup
# #     )

# # =============================================================================
# # TABLE 1 — users  (COMPLETE — with payment relationships added)
# # Replace your existing User class entirely with this one.
# # Only addition vs original: the "── Payments & Billing ──" section
# # inserted after "── Help & Support ──".
# # =============================================================================

# class User(Base):
#     __tablename__ = "users"

#     # ── Primary Key ───────────────────────────────────────────────────────────
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # ── Basic Info (from Signup form) ─────────────────────────────────────────
#     first_name   = Column(String(100), nullable=False)
#     last_name    = Column(String(100), nullable=False)
#     email        = Column(String(255), nullable=False, unique=True, index=True)
#     phone        = Column(String(20),  nullable=True)
#     country_code = Column(String(10),  nullable=True)   # e.g. "+1"

#     # ── Authentication ────────────────────────────────────────────────────────
#     password_hash    = Column(String(255), nullable=True)
#     # nullable → SSO users (Google/Microsoft/Apple) have no password

#     auth_provider    = Column(
#                           Enum("email", "google", "microsoft", "apple",
#                                name="auth_provider_enum"),
#                           nullable=False, default="email"
#                        )
#     # "Continue with Google / Microsoft" — Login screen
#     # "Sign in with Apple" — Profile & Security screen 28

#     auth_provider_id = Column(String(255), nullable=True)
#     # OAuth user ID returned by Google/Microsoft/Apple
#     # null for email users

#     # ── Status Flags ──────────────────────────────────────────────────────────
#     is_active   = Column(Boolean, default=True,  nullable=False)
#     # False → suspended account — cannot login
#     is_verified = Column(Boolean, default=False, nullable=False)
#     # True → email verified (Onboarding Step 3 "Verification — Confirm email")

#     # ── Consent (from Signup form) ────────────────────────────────────────────
#     terms_accepted     = Column(Boolean,  nullable=False, default=False)
#     terms_accepted_at  = Column(DateTime(timezone=True), nullable=True)
#     marketing_opt_in   = Column(Boolean,  default=False, nullable=False)
#     # "I'd like to receive product updates..." checkbox
#     newsletter_opt_in  = Column(Boolean,  default=False, nullable=False)
#     # "Subscribe to monthly immigration insights newsletter" checkbox
#     referral_source    = Column(String(100), nullable=True)
#     # "How did you hear about us?" optional dropdown

#     # ── Timestamps ────────────────────────────────────────────────────────────
#     last_login_at = Column(DateTime(timezone=True), nullable=True)
#     created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                            onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # ── Audit — self-referencing FK ───────────────────────────────────────────
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     # nullable → first admin has no creator above them

#     # =========================================================================
#     # ALL RELATIONSHIPS — every table that FK's back to users
#     # =========================================================================

#     # ── Auth & Security ───────────────────────────────────────────────────────
#     otp_records    = relationship("UserOTP",
#                                    foreign_keys="UserOTP.user_id",
#                                    back_populates="user")
#     # TABLE 3 — user_otp.user_id → users.id
#     # 2FA codes, email verification, phone verification, password reset OTPs

#     login_history  = relationship("UserLoginHistory",
#                                    foreign_keys="UserLoginHistory.user_id",
#                                    back_populates="user",
#                                    order_by="UserLoginHistory.created_at.desc()")
#     # TABLE 6 — user_login_history.user_id → users.id
#     # "Login History" panel — Screen 28
#     # Chrome on MacBook Pro, Safari on iPhone, Failed Login from Mumbai...

#     reset_tokens   = relationship("PasswordResetToken",
#                                    foreign_keys="PasswordResetToken.user_id",
#                                    back_populates="user")
#     # TABLE 33 — password_reset_tokens.user_id → users.id
#     # Screens 07–10: Email → OTP → New Password → Success

#     # ── Profile & Preferences ─────────────────────────────────────────────────
#     profile        = relationship("UserProfile",
#                                    foreign_keys="UserProfile.user_id",
#                                    back_populates="user",
#                                    uselist=False)
#     # TABLE 7 — user_profiles.user_id → users.id  (1:1)
#     # full_legal_name, nationality, DOB, profile_picture, timezone, language
#     # onboarding_step, onboarding_completed

#     visa_targets   = relationship("UserVisaTarget",
#                                    foreign_keys="UserVisaTarget.user_id",
#                                    back_populates="user")
#     # TABLE 8 — user_visa_targets.user_id → users.id  (1:many)
#     # Multi-select "Target Visa Types" — Onboarding Step 3
#     # H-1B, O-1 Extraordinary, etc.

#     # ── Roles & Permissions ───────────────────────────────────────────────────
#     user_roles     = relationship("UserRole",
#                                    foreign_keys="UserRole.user_id",
#                                    back_populates="user")
#     # TABLE 5 — user_roles.user_id → users.id  (1:many)
#     # employee, student, dependent, employer_hr, attorney, admin
#     # A user CAN have multiple roles simultaneously (confirmed)

#     # ── Applications ──────────────────────────────────────────────────────────
#     applications       = relationship("Application",
#                                        foreign_keys="Application.user_id",
#                                        back_populates="user")
#     # TABLE 10 — applications.user_id → users.id  (1:many)
#     # All visa applications filed by this user

#     attorney_cases     = relationship("Application",
#                                        foreign_keys="Application.assigned_attorney_id",
#                                        back_populates="assigned_attorney")
#     # TABLE 10 — applications.assigned_attorney_id → users.id
#     # Cases where this user is the assigned attorney

#     hr_cases           = relationship("Application",
#                                        foreign_keys="Application.assigned_hr_id",
#                                        back_populates="assigned_hr")
#     # TABLE 10 — applications.assigned_hr_id → users.id
#     # Cases where this user is the assigned HR manager
#     # "TechCorp Inc. Sponsorship" — Screen 15

#     # ── Documents ─────────────────────────────────────────────────────────────
#     documents          = relationship("Document",
#                                        foreign_keys="Document.user_id",
#                                        back_populates="user")
#     # TABLE 13 — documents.user_id → users.id  (1:many)
#     # All documents uploaded by this user

#     verified_documents = relationship("Document",
#                                        foreign_keys="Document.verified_by",
#                                        back_populates="verified_by_user")
#     # TABLE 13 — documents.verified_by → users.id
#     # Documents this user has verified (HR Admin / Attorney role)
#     # "Passport_Scan_2023.pdf verified by HR Admin" — Screen 19

#     # ── Messaging ─────────────────────────────────────────────────────────────
#     message_threads    = relationship("MessageThreadParticipant",
#                                        foreign_keys="MessageThreadParticipant.user_id",
#                                        back_populates="user")
#     # TABLE 19 — message_thread_participants.user_id → users.id
#     # All conversation threads this user is part of — Screen 24

#     sent_messages      = relationship("Message",
#                                        foreign_keys="Message.sender_id",
#                                        back_populates="sender")
#     # TABLE 20 — messages.sender_id → users.id  (1:many)
#     # All messages sent by this user

#     # ── Notifications ─────────────────────────────────────────────────────────
#     notifications      = relationship("Notification",
#                                        foreign_keys="Notification.user_id",
#                                        back_populates="user")
#     # TABLE 20 — notifications.user_id → users.id  (1:many)
#     # All notifications received by this user — Screen 25/26

#     triggered_notifications = relationship("Notification",
#                                             foreign_keys="Notification.actor_id",
#                                             back_populates="actor")
#     # TABLE 20 — notifications.actor_id → users.id
#     # Notifications triggered BY this user
#     # "David Martinez commented..." / "Michael Chen was added..."

#     notification_prefs = relationship("NotificationPreferences",
#                                        foreign_keys="NotificationPreferences.user_id",
#                                        back_populates="user",
#                                        uselist=False)
#     # TABLE 21 — notification_preferences.user_id → users.id  (1:1)
#     # Email / Push / SMS toggle preferences — Screen 25 sidebar

#     deadlines          = relationship("Deadline",
#                                        foreign_keys="Deadline.user_id",
#                                        back_populates="user")
#     # TABLE 22 — deadlines.user_id → users.id  (1:many)
#     # "I-983 Signature Due — March 28 (3 days) — Critical" — Screen 25

#     # ── News Feed ─────────────────────────────────────────────────────────────
#     news_bookmarks     = relationship("NewsArticleBookmark",
#                                        foreign_keys="NewsArticleBookmark.user_id",
#                                        back_populates="user")
#     # TABLE 25 — news_article_bookmarks.user_id → users.id  (1:many)
#     # "Saved Articles: 18" — Screen 27

#     feed_preferences   = relationship("NewsFeedPreference",
#                                        foreign_keys="NewsFeedPreference.user_id",
#                                        back_populates="user")
#     # TABLE 26 — news_feed_preferences.user_id → users.id  (1:many)
#     # "Active Filters: H-1B, OPT/STEM OPT" — Screen 27

#     # ── Interview Prep ────────────────────────────────────────────────────────
#     interview_sessions = relationship("InterviewSession",
#                                        foreign_keys="InterviewSession.user_id",
#                                        back_populates="user")
#     # TABLE 29 — interview_sessions.user_id → users.id  (1:many)
#     # "B1/B2 Visa Interview — Oct 15, 2023 — US Embassy London" — Screen 23

#     # ── Help & Support ────────────────────────────────────────────────────────
#     support_tickets    = relationship("SupportTicket",
#                                        foreign_keys="SupportTicket.user_id",
#                                        back_populates="user")
#     # TABLE 35 — support_tickets.user_id → users.id  (1:many)
#     # Tickets submitted by this user — "Submit a Ticket" — Screen 29

#     assigned_tickets   = relationship("SupportTicket",
#                                        foreign_keys="SupportTicket.assigned_to",
#                                        back_populates="assigned_agent")
#     # TABLE 35 — support_tickets.assigned_to → users.id
#     # Tickets assigned TO this user (support agent role)
#     # "Available Mon-Fri 9am-6pm EST" — Screen 29

#     chat_sessions_user  = relationship("SupportChatSession",
#                                         foreign_keys="SupportChatSession.user_id",
#                                         back_populates="user")
#     # TABLE 37 — support_chat_sessions.user_id → users.id
#     # "Start Chat" live chat sessions started by this user

#     chat_sessions_agent = relationship("SupportChatSession",
#                                         foreign_keys="SupportChatSession.agent_id",
#                                         back_populates="agent")
#     # TABLE 37 — support_chat_sessions.agent_id → users.id
#     # Live chat sessions where this user is the support agent

#     # ── Payments & Billing  ── NEW ────────────────────────────────────────────
#     fees             = relationship("Fee",
#                                      foreign_keys="Fee.user_id",
#                                      back_populates="user")
#     # TABLE 39 — fees.user_id → users.id  (1:many)
#     # All fees owed by this user across all their applications
#     # "H-1B Premium Processing Fee $2,805", "I-129 Filing Fee $460" — Screen 18
#     # Query: user.fees filtered by status="pending" → outstanding fees panel

#     payment_methods  = relationship("PaymentMethod",
#                                      foreign_keys="PaymentMethod.user_id",
#                                      back_populates="user")
#     # TABLE 40 — payment_methods.user_id → users.id  (1:many)
#     # Saved payment instruments: Credit Card (Visa/MC), PayPal, Apple Pay
#     # "Payment Methods" tile — Screen 18
#     # One is marked is_default=True → the pre-selected ● radio button

#     payments         = relationship("Payment",
#                                      foreign_keys="Payment.user_id",
#                                      back_populates="user")
#     # TABLE 41 — payments.user_id → users.id  (1:many)
#     # All payment transactions made by this user
#     # "Payment History" tab — Screen 18
#     # Includes completed, failed, refunded transactions

#     payment_invoices = relationship("PaymentInvoice",
#                                      foreign_keys="PaymentInvoice.user_id",
#                                      back_populates="user")
#     # TABLE 42 — payment_invoices.user_id → users.id  (1:many)
#     # PDF invoices generated after each successful payment
#     # Downloadable by employee; also visible to HR/attorney for the case

#     # ── Waived fees (HR / Admin action) ──────────────────────────────────────
#     waived_fees      = relationship("Fee",
#                                      foreign_keys="Fee.waived_by",
#                                      back_populates="waived_by_user")
#     # TABLE 39 — fees.waived_by → users.id
#     # Fees this user has waived (HR or admin role)
#     # e.g. HR waives attorney_fee for a key employee

#     # ── Refunds processed (HR / Admin action) ─────────────────────────────────
#     requested_refunds = relationship("PaymentRefund",
#                                       foreign_keys="PaymentRefund.requested_by",
#                                       back_populates="requested_by_user")
#     # TABLE 43 — payment_refunds.requested_by → users.id
#     # Refund requests initiated BY this user (HR / admin billing dashboard)

#     approved_refunds  = relationship("PaymentRefund",
#                                       foreign_keys="PaymentRefund.approved_by",
#                                       back_populates="approved_by_user")
#     # TABLE 43 — payment_refunds.approved_by → users.id
#     # Refunds approved BY this user (admin only)

#     # ── Table constraints ─────────────────────────────────────────────────────
#     __table_args__ = (
#         Index("ix_users_email_active",    "email",         "is_active"),
#         # composite index — most queries filter by email + active status
#         Index("ix_users_auth_provider",   "auth_provider", "auth_provider_id"),
#         # speeds up SSO login lookup
#     )

# # =============================================================================
# # ENUM — UserRoleName
# # Four roles in VisaFlow. Stored as a typed Postgres enum — no free strings.
# #
# #   app_admin  → Full system access. Manages users, roles, visa types, news,
# #                support tickets, billing. One or more internal staff.
# #
# #   hr         → Employer HR manager. Creates/manages applications for their
# #                employees, uploads employer docs, assigns attorneys, views
# #                all cases under their company.
# #
# #   employee   → The visa applicant. Sees only their own applications,
# #                uploads their own documents, messages their attorney/HR,
# #                tracks deadlines and interview prep.
# #
# #   attorney   → Immigration lawyer. Manages assigned cases, verifies
# #                documents, updates application status, messages clients.
# # =============================================================================

# class UserRoleName(str):
#     APP_ADMIN = "app_admin"
#     HR        = "hr"
#     EMPLOYEE  = "employee"
#     ATTORNEY  = "attorney"

# # =============================================================================
# # TABLE 2 — roles
# # One row per role — seeded once, never inserted by users.
# # =============================================================================

# class Role(Base):
#     __tablename__ = "roles"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # ── Typed enum instead of free String ────────────────────────────────────
#     name        = Column(String(100), nullable=False, unique=True)
#     is_system   = Column(Boolean, default=False, nullable=False)

#     description = Column(String(255), nullable=True)
#     # Human-readable: "Employer HR Manager", "Immigration Attorney", etc.

#     is_active   = Column(Boolean, default=True, nullable=False)
#     # False → role is retired; existing UserRole rows kept for audit

#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable — seeded without a creator
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     role_permissions = relationship("RolePermission", back_populates="role",
#                                     cascade="all, delete-orphan")
#     user_roles       = relationship("UserRole", back_populates="role")


# # =============================================================================
# # ENUM — PermissionCode
# # Every permission that can be granted to a role.
# # Grouped by module. The Postgres enum guarantees no typos at DB level.
# #
# # MODULE: users
# #   users.manage          → create, suspend, delete any user          (admin only)
# #   users.view_all        → list / search all users                   (admin, hr)
# #
# # MODULE: applications
# #   applications.create          → start a new visa application       (all roles)
# #   applications.view_own        → see own applications only          (all roles)
# #   applications.view_all        → see ALL applications               (admin, hr, attorney)
# #   applications.update_status   → change status / stage              (admin, hr, attorney)
# #   applications.delete          → hard-delete a draft                (admin only)
# #
# # MODULE: documents
# #   documents.upload      → upload a file                             (all roles)
# #   documents.view_own    → download own documents                    (all roles)
# #   documents.view_all    → view any user's documents                 (admin, hr, attorney)
# #   documents.verify      → mark document verified / rejected         (admin, hr, attorney)
# #   documents.delete      → permanently delete a document             (admin, hr)
# #
# # MODULE: messages
# #   messages.send               → send a message in any thread        (all roles)
# #   messages.view_all_threads   → see every thread in the system      (admin, hr)
# #
# # MODULE: roles
# #   roles.manage          → create/edit/deactivate roles              (admin only)
# #   permissions.manage    → assign permissions to roles               (admin only)
# #
# # MODULE: support
# #   support.view_all_tickets  → see all support tickets               (admin, hr)
# #   support.manage_tickets    → reply, reassign, close tickets        (admin, hr)
# #
# # MODULE: content
# #   news.publish          → publish / unpublish news articles         (admin only)
# #   deadlines.manage      → create / edit / close deadlines           (admin, hr, attorney)
# #   visa_types.manage     → add / edit visa types in master list      (admin only)
# # =============================================================================


# class Permission(Base):
#     __tablename__ = "permissions"

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     #  Plain string instead of enum — allows custom permission codes
#     code        = Column(String(100), nullable=False, unique=True)
#     #  Plain string instead of enum — allows custom modules
#     module      = Column(String(50), nullable=False)
#     #  Flag to protect seeded permissions from deletion
#     is_system   = Column(Boolean, default=False, nullable=False)

#     description = Column(String(255), nullable=True)
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc))

#     role_permissions = relationship("RolePermission", back_populates="permission",
#                                     cascade="all, delete-orphan")


# # =============================================================================
# # TABLE 3 — permissions
# # Master list of every permission in the system. Seeded once by admin.
# # =============================================================================

# # class Permission(Base):
# #     __tablename__ = "permissions"

# #     id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# #     # ── Typed enum — the actual permission code ───────────────────────────────
# #     code = Column(
# #         _permission_code_enum,
# #         nullable=False,
# #         unique=True,
# #     )
# #     # e.g. "documents.verify", "applications.update_status"
# #     # unique=True → one row per code, no duplicates

# #     module = Column(
# #         Enum(
# #             "users", "applications", "documents",
# #             "messages", "roles", "support", "content",
# #             name="permission_module_enum"
# #         ),
# #         nullable=False,
# #     )
# #     # Groups permissions in the admin UI by module

# #     description = Column(String(255), nullable=True)
# #     # Human-readable: "Verify or reject any uploaded document"

# #     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable — seeded without a creator
# #     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
# #     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
# #     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# #     # Relationships
# #     role_permissions = relationship("RolePermission", back_populates="permission",
# #                                     cascade="all, delete-orphan")

# # =============================================================================
# # TABLE 4 — role_permissions (junction)
# # Which role has which permission.
# #
# # Seed data (matches the matrix above):
# #
# #  app_admin  → ALL 21 permissions
# #  hr         → users.view_all, applications.*, documents.*, messages.*,
# #               support.*, deadlines.manage
# #  attorney   → applications.create/view_own/view_all/update_status,
# #               documents.upload/view_own/view_all/verify,
# #               messages.send, deadlines.manage
# #  employee   → applications.create/view_own, documents.upload/view_own,
# #               messages.send
# # =============================================================================

# class RolePermission(Base):
#     __tablename__ = "role_permissions"

#     id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     role_id       = Column(UUID(as_uuid=True), ForeignKey("roles.id"),
#                            nullable=False, index=True)
#     permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"),
#                            nullable=False, index=True)

#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable — seeded without a creator
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Unique together — a role can't have the same permission twice
#     __table_args__ = (
#         UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
#     )

#     # Relationships
#     role       = relationship("Role",       back_populates="role_permissions")
#     permission = relationship("Permission", back_populates="role_permissions")


# # =============================================================================
# # TABLE 5 — user_roles (junction)
# # Which user has which role. A user CAN have multiple roles simultaneously
# # (e.g. an attorney who is also an app_admin).
# # =============================================================================

# class UserRole(Base):
#     __tablename__ = "user_roles"

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)
#     role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"),
#                      nullable=False, index=True)

#     assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable — first admin assigns themselves
#     # Who granted this role (app_admin or system on signup)

#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # nullable — seeded without a creator
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Unique together — a user can't have the same role twice
#     __table_args__ = (
#         UniqueConstraint("user_id", "role_id", name="uq_user_role"),
#     )

#     # Relationships
#     user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
#     role = relationship("Role", back_populates="user_roles")


# # =============================================================================
# # RBAC SEED DATA
# # Run once at DB init / Alembic seed migration.
# # Defines: the 4 roles + the 21 permissions + which role gets which.
# # =============================================================================


# # =============================================================================
# # TABLE 6 — user_otp
# # =============================================================================

# class UserOTP(Base):
#     __tablename__ = "user_otp"

#     id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

#     otp_code   = Column(String(10), nullable=False)     # the 4 or 6 digit code
#     otp_type   = Column(
#                     Enum("email_verification", "phone_verification",
#                          "password_reset", "two_factor_auth",
#                          name="otp_type_enum"),
#                     nullable=False
#                  )
#     is_used    = Column(Boolean, default=False, nullable=False)  # used = expired
#     expires_at = Column(DateTime(timezone=True), nullable=False)   # OTP has a short TTL (5-10 min)

#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     user = relationship("User", foreign_keys=[user_id], back_populates="otp_records")


# # =============================================================================
# # TABLE 7 — user_profiles
# # =============================================================================

# class UserProfile(Base):
#     __tablename__ = "user_profiles"

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, unique=True)  # unique → strict 1:1

#     # Personal Details (Onboarding Step 3)
#     full_legal_name      = Column(String(200), nullable=True)  # as on passport
#     nationality          = Column(String(100), nullable=True)  # e.g. "United Kingdom"
#     country_of_residence = Column(String(100), nullable=True)  # where they live now
#     date_of_birth        = Column(Date,        nullable=True)
#     gender               = Column(String(20),  nullable=True)

#     # Profile Picture (Screen 28)
#     profile_picture_url  = Column(String(500), nullable=True)  # stored path/S3 URL

#     # Preferences (Screen 28)
#     timezone             = Column(String(100), nullable=True)  # e.g. "America/Los_Angeles"
#     preferred_language   = Column(String(50),  nullable=True, default="en")

#     # Onboarding Progress — "Save my progress" button
#     onboarding_step      = Column(Integer, default=1,     nullable=False)  # 1 to 4
#     onboarding_completed = Column(Boolean, default=False, nullable=False)
#     phone_number = Column(String(20),  nullable=True)
#     country_code = Column(String(10),  nullable=True)  # e.g. "+91"
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user = relationship("User", foreign_keys=[user_id], back_populates="profile")


# # =============================================================================
# # TABLE 8 — user_visa_targets
# # =============================================================================

# class UserVisaTarget(Base):
#     __tablename__ = "user_visa_targets"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

#     # ✅ FIXED
#     visa_type_code = Column(String, ForeignKey("visa_types.code"), nullable=False)

#     is_primary = Column(Boolean, default=False, nullable=False)

#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # relationships
#     user = relationship("User", foreign_keys=[user_id], back_populates="visa_targets")

#     visa_type = relationship(
#         "VisaType",
#         back_populates="user_visa_targets"
#     )



# # =============================================================================
# # TABLE 9 — user_login_history
# # =============================================================================

# class UserLoginHistory(Base):
#     __tablename__ = "user_login_history"

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)

#     # Login Result — 3 states seen in Figma
#     status = Column(
#                 Enum("success", "failed", "blocked",
#                      name="login_status_enum"),
#                 nullable=False
#              )

#     # How they authenticated
#     auth_method = Column(
#                      Enum("email_password", "google", "microsoft",
#                           "apple", "otp",
#                           name="auth_method_enum"),
#                      nullable=False
#                   )

#     # Network Info
#     ip_address = Column(String(45),  nullable=True)   # supports IPv4 + IPv6
#     city       = Column(String(100), nullable=True)   # geo from IP
#     country    = Column(String(100), nullable=True)   # geo from IP

#     # Device Info (parsed from user_agent)
#     browser     = Column(String(100), nullable=True)  # e.g. "Chrome"
#     os          = Column(String(100), nullable=True)  # e.g. "MacBook Pro"
#     device_type = Column(
#                      Enum("desktop", "mobile", "tablet", "unknown",
#                           name="device_type_enum"),
#                      nullable=False, default="unknown"
#                   )
#     user_agent  = Column(String(500), nullable=True)  # full raw UA string

#     # Failure Tracking
#     failure_reason  = Column(String(255), nullable=True)  # null on success
#     failed_attempts = Column(Integer, default=0, nullable=False)
#     # e.g. 3 → triggers account lock

#     # Session State
#     is_suspicious      = Column(Boolean, default=False, nullable=False)
#     # → True when user clicks "Report" button
#     is_current_session = Column(Boolean, default=False, nullable=False)
#     # → True for "Active Now" entry
#     session_token      = Column(String(500), nullable=True)
#     # JWT/session token — used to force logout a specific session
#     logged_out_at      = Column(DateTime(timezone=True), nullable=True)
#     # null = session still active

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user = relationship("User", foreign_keys=[user_id], back_populates="login_history")


# # =============================================================================
# # TABLE 10 — applications
# # =============================================================================

# from sqlalchemy import text

# class Application(Base):
#     __tablename__ = "applications"

#     id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # Reference Number
#     application_number = Column(String(50), nullable=False, unique=True, index=True)

#     # Core FKs
#     user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                                 nullable=False, index=True)
#     visa_type_id       = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                                 nullable=False)

#     # Sponsor
#     sponsor_employer   = Column(String(200), nullable=True)

#     # Status
#     status = Column(
#         Enum("draft", "in_progress", "action_needed", "rfe_response",
#              "submitted", "approved", "rejected", "withdrawn",
#              name="application_status_enum"),
#         nullable=False, default="draft"
#     )

#     # Current Stage
#     current_stage = Column(
#         Enum("profile_eligibility", "documentation",
#              "lca_filing", "uscis_submission",
#              name="application_stage_enum"),
#         nullable=True
#     )

#     # Progress
#     progress_percent     = Column(Integer, default=0, nullable=False)

#     # Dates
#     start_date           = Column(Date,                  nullable=True)
#     due_date             = Column(Date,                  nullable=True)
#     submission_date      = Column(DateTime(timezone=True), nullable=True)

#     # Draft Flag
#     is_draft             = Column(Boolean, default=True,  nullable=False)

#     # Action Required
#     has_action_required  = Column(Boolean, default=False, nullable=False)
#     action_required_note = Column(String(500), nullable=True)

#     # Assigned Staff
#     assigned_attorney_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     assigned_hr_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

#     # Internal Notes
#     notes = Column(Text, nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # ── Unique constraint: only ONE draft per user per visa type ──────────
#     __table_args__ = (
#         Index(
#             "uq_one_draft_per_user_per_visa",
#             "user_id",
#             "visa_type_id",
#             unique=True,
#             postgresql_where=text("status = 'draft'"),
#         ),
#     )

#     # Relationships
#     user              = relationship("User", foreign_keys=[user_id],
#                                      back_populates="applications")
#     visa_type         = relationship("VisaType")
#     assigned_attorney = relationship("User", foreign_keys=[assigned_attorney_id],
#                                      back_populates="attorney_cases")
#     assigned_hr       = relationship("User", foreign_keys=[assigned_hr_id],
#                                      back_populates="hr_cases")
#     status_history    = relationship("ApplicationStatusHistory",
#                                      back_populates="application")


# # =============================================================================
# # TABLE 11 — application_status_history
# # =============================================================================

# class ApplicationStatusHistory(Base):
#     __tablename__ = "application_status_history"
#     # Immutable audit log — never update rows, only INSERT

#     id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=False, index=True)

#     # The stage that was reached
#     stage = Column(
#                Enum("profile_eligibility", "documentation",
#                     "lca_filing", "uscis_submission",
#                     name="history_stage_enum"),
#                nullable=False
#             )

#     # Status at this point in time
#     status = Column(
#                 Enum("draft", "in_progress", "action_needed", "rfe_response",
#                      "submitted", "approved", "rejected", "withdrawn",
#                      name="history_status_enum"),
#                 nullable=False
#              )

#     # e.g. "Completed on Oct 12, 2023" / "Pending HR review"
#     note          = Column(String(500), nullable=True)
#     completed_at  = Column(DateTime(timezone=True),   nullable=True)
#     # null = not yet completed

#     # Who triggered this status change
#     changed_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationship
#     application = relationship("Application", back_populates="status_history")


# # =============================================================================
# # TABLE 12 — application_tasks
# # =============================================================================

# class ApplicationTask(Base):
#     __tablename__ = "application_tasks"
#     # Checklist items inside an application

#     id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=False, index=True)

#     task_name        = Column(String(200), nullable=False)
#     # e.g. "Upload Passport Copy"
#     description      = Column(String(500), nullable=True)
#     # e.g. "Valid for at least 6 months"
#     is_completed     = Column(Boolean, default=False, nullable=False)
#     is_required      = Column(Boolean, default=True,  nullable=False)
#     # some tasks may be optional
#     sort_order       = Column(Integer,  default=0,     nullable=False)
#     # controls display order in the checklist
#     completed_at     = Column(DateTime(timezone=True), nullable=True)
#     completed_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     document_id    = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
#     document    = relationship("Document", foreign_keys=[document_id])

# # =============================================================================
# # TABLE 13 — document_types
# # =============================================================================

# class DocumentType(Base):
#     __tablename__ = "document_types"
#     # Master list of allowed document types — controlled by admin

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name        = Column(String(200), nullable=False, unique=True)
#     # e.g. "Valid Passport", "Offer Letter", "Degree Transcripts"

#     category    = Column(
#                      Enum("identity", "employment", "education",
#                           "legal", "personal", "other",
#                           name="doc_category_enum"),
#                      nullable=False
#                   )
#     # Screen 17/18 groups: Identity Documents, Employment Documents, Personal

#     description = Column(String(500), nullable=True)
#     # e.g. "Biographical page showing photo, details, and expiration date."

#     is_optional = Column(Boolean, default=False, nullable=False)
#     # "Previous I-797 (Optional) — If applicable" → Screen 19

#     accepted_formats = Column(String(100), nullable=True, default="PDF,JPG,PNG")
#     # "PDF, JPG, PNG (max. 10MB)" — Screen 18

#     max_file_size_mb = Column(Integer, default=10, nullable=False)
#     # "max. 10MB" — Screen 17/18, "Max 5MB" for profile pictures

#     is_active   = Column(Boolean, default=True, nullable=False)
#     # admin can deactivate a document type

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# # =============================================================================
# # TABLE 14 — documents
# # =============================================================================

# class Document(Base):
#     __tablename__ = "documents"

#     id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # Who uploaded it
#     user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                               nullable=False, index=True)

#     # Which application this document belongs to
#     # nullable because Screen 19 shows Personal documents NOT tied to any application
#     application_id   = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                               nullable=True, index=True)

#     # What type of document it is — FK to lookup table
#     document_type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id"),
#                               nullable=False)

#     # File Info — from Screen 19: "passport_scan_2023.pdf • 2.4 MB • Uploaded Oct 12"
#     file_name        = Column(String(255), nullable=False)
#     # original filename e.g. "passport_scan_2023.pdf"
#     file_path        = Column(String(1000), nullable=False)
#     # S3 / storage path — never expose this directly to frontend
#     file_size_kb     = Column(Integer, nullable=False)
#     # "2.4 MB" stored as KB for precise math
#     file_format      = Column(
#                           Enum("pdf", "jpg", "png", "docx", "jpeg", "gif",
#                                name="file_format_enum"),
#                           nullable=False
#                        )
#     # "PDF, JPG, PNG, DOCX" — seen across screens 17-20
#     total_pages      = Column(Integer, nullable=True)
#     # "5 pages" — Screen 20 sidebar thumbnails

#     # Document Status — all states seen across screens
#     status           = Column(
#                           Enum("required", "uploaded", "pending_review",
#                                "verified", "rejected", "missing",
#                                name="document_status_enum"),
#                           nullable=False, default="uploaded"
#                        )
#     # Screen 17/18/19: Required → Uploaded → Pending Review → Verified

#     # Verification details — "Passport_Scan_2023.pdf verified by HR Admin"
#     verified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     verified_at      = Column(DateTime(timezone=True), nullable=True)
#     rejection_reason = Column(String(500), nullable=True)
#     # filled when status = rejected — to show user why

#     # Version tracking — "Updated_Resume_v2.docx" — Screen 19
#     version          = Column(Integer, default=1, nullable=False)
#     # increments each re-upload: v1, v2, v3...
#     parent_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                                 nullable=True)
#     # self-referencing FK — links new version back to the original document
#     # null = this IS the original

#     # OCR Processing — Screen 20 shows OCR results with confidence scores
#     ocr_status       = Column(
#                           Enum("not_started", "processing", "completed",
#                                "review_needed", "confirmed",
#                                name="ocr_status_enum"),
#                           nullable=False, default="not_started"
#                        )
#     # "Processed / Processing / Review" — page statuses in Screen 20
#     ocr_confidence   = Column(Integer, nullable=True)
#     # "95% average confidence score" — Screen 20, stored as integer 0-100

#     # Flags
#     is_draft         = Column(Boolean, default=False, nullable=False)
#     # "Save Draft" button in Screen 18

#     # Audit
#     created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     user             = relationship("User",         foreign_keys=[user_id],
#                                     back_populates="documents")
#     application      = relationship("Application")
#     document_type    = relationship("DocumentType")
#     verified_by_user = relationship("User",         foreign_keys=[verified_by],
#                                     back_populates="verified_documents")
#     parent           = relationship("Document",     foreign_keys=[parent_document_id],
#                                     remote_side="Document.id")
#     pages            = relationship("DocumentPage", back_populates="document")
#     activity_log     = relationship("DocumentActivity", back_populates="document")


# # =============================================================================
# # TABLE 15 — document_pages
# # =============================================================================

# class DocumentPage(Base):
#     __tablename__ = "document_pages"
#     # Each page of a multi-page document — Screen 20 sidebar: Page 1,2,3,4,5

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                           nullable=False, index=True)

#     page_number  = Column(Integer, nullable=False)
#     # "Page 1 of 5" — Screen 20

#     thumbnail_url = Column(String(1000), nullable=True)
#     # thumbnail shown in sidebar — Screen 20

#     page_status  = Column(
#                       Enum("processing", "processed", "review_needed", "confirmed",
#                            name="page_status_enum"),
#                       nullable=False, default="processing"
#                    )
#     # "Processed / Review / Processing" — Screen 20 sidebar labels

#     ocr_confidence = Column(Integer, nullable=True)
#     # per-page confidence score — different pages can have different scores

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     document    = relationship("Document", back_populates="pages")
#     ocr_fields  = relationship("DocumentOCRField", back_populates="page")


# # =============================================================================
# # TABLE 16 — document_ocr_fields
# # =============================================================================

# class DocumentOCRField(Base):
#     __tablename__ = "document_ocr_fields"
#     # Each extracted field from OCR — Screen 20 "Extracted Data" panel

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                           nullable=False, index=True)
#     page_id      = Column(UUID(as_uuid=True), ForeignKey("document_pages.id"),
#                           nullable=True)

#     field_name   = Column(String(100), nullable=False)
#     # e.g. "Passport Number", "Date of Birth", "Nationality", "Surname"

#     extracted_value = Column(String(500), nullable=True)
#     # e.g. "542789634", "15 MAR 1995", "SHARMA"

#     confidence_score = Column(Integer, nullable=True)
#     # per-field % — "98%", "85%" — Screen 20 shows each field has own score

#     is_confirmed = Column(Boolean, default=False, nullable=False)
#     # "Confirmed" badge in Screen 20 — user clicked Confirm on this field

#     needs_review = Column(Boolean, default=False, nullable=False)
#     # "Please verify this date is correct" — flagged fields need user review

#     confirmed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     confirmed_at = Column(DateTime(timezone=True), nullable=True)
#     # "Confirm All & Continue" — Screen 20

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     page = relationship("DocumentPage", back_populates="ocr_fields")


# # =============================================================================
# # TABLE 17 — document_activity
# # =============================================================================

# class DocumentActivity(Base):
#     __tablename__ = "document_activity"
#     # Immutable audit log — INSERT only, never UPDATE

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                          nullable=False, index=True)

#     action      = Column(
#                      Enum("uploaded", "status_changed", "verified",
#                           "rejected", "downloaded", "viewed",
#                           "version_updated", "ocr_completed",
#                           name="doc_activity_enum"),
#                      nullable=False
#                   )
#     # All actions seen: uploaded, status changed, verified — Screen 19

#     actor_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     # null when actor is "System" (automated action) — Screen 19

#     actor_type  = Column(
#                      Enum("user", "system", "hr_admin", "attorney",
#                           name="actor_type_enum"),
#                      nullable=False, default="user"
#                   )
#     # "by Alexandra Smith", "by System", "by HR Admin" — Screen 19

#     note        = Column(String(500), nullable=True)
#     # e.g. "status changed to Pending Review", "Awaiting manager approval"

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationship
#     document    = relationship("Document", back_populates="activity_log")


# # =============================================================================
# # TABLE 18 — message_threads
# # =============================================================================

# class MessageThread(Base):
#     __tablename__ = "message_threads"
#     # One thread = one conversation row in the left panel of Screen 24

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # Thread type — "David Kovalev" is direct, "HR Department" is a group
#     thread_type = Column(
#                      Enum("direct", "group",
#                           name="thread_type_enum"),
#                      nullable=False, default="direct"
#                   )
#     # direct  → exactly 2 participants (employee ↔ attorney/HR/support)
#     # group   → "Support Team", "HR Department" — multiple participants

#     # Group-only fields — null for direct messages
#     title       = Column(String(200), nullable=True)
#     # "HR Department", "Support Team" — group name shown in left panel
#     # null for direct threads (name comes from the other participant)

#     # Linked to an application — most conversations are about a specific case
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=True, index=True)
#     # nullable — some threads may be general support, not case-specific

#     # Last message snapshot — powers the preview in conversation list
#     last_message_preview = Column(String(200), nullable=True)
#     # "I have reviewed your transcripts. Please check..."

#     last_message_at = Column(DateTime(timezone=True), nullable=True)
#     # "5 min ago", "10:11 AM", "Yesterday" — sort order + display

#     # Status
#     is_archived  = Column(Boolean, default=False, nullable=False)
#     # "Archived" filter tab in Screen 24

#     is_active    = Column(Boolean, default=True, nullable=False)
#     # soft delete — deactivate thread without deleting messages

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     participants = relationship("MessageThreadParticipant", back_populates="thread")
#     messages     = relationship("Message", back_populates="thread",
#                                 order_by="Message.created_at")


# # =============================================================================
# # TABLE 19 — message_thread_participants
# # =============================================================================

# class MessageThreadParticipant(Base):
#     __tablename__ = "message_thread_participants"
#     # Junction table — who belongs to which thread

#     id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     thread_id = Column(UUID(as_uuid=True), ForeignKey("message_threads.id"),
#                        nullable=False, index=True)
#     user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                        nullable=False, index=True)

#     # Role in this thread — from Screen 24: "Immigration Specialist" label
#     participant_role = Column(
#                           Enum("employee", "attorney", "hr",
#                                "support", "admin",
#                                name="participant_role_enum"),
#                           nullable=False
#                        )

#     # Online presence — "Online • Immigration Specialist" shown in chat header
#     is_online   = Column(Boolean, default=False, nullable=False)

#     # Unread count — "2" badge on Messages nav
#     unread_count = Column(Integer, default=0, nullable=False)
#     # per-participant unread count — resets when they open the thread

#     last_read_at = Column(DateTime(timezone=True), nullable=True)
#     # timestamp of when this participant last read the thread

#     # Mute/Archive per participant
#     is_muted     = Column(Boolean, default=False, nullable=False)
#     is_archived  = Column(Boolean, default=False, nullable=False)
#     # each participant can independently archive a thread

#     joined_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     left_at     = Column(DateTime(timezone=True), nullable=True)
#     # null = still in thread; filled when removed from group

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     thread = relationship("MessageThread", back_populates="participants")
#     user   = relationship("User", foreign_keys=[user_id],
#                           back_populates="message_threads")


# # =============================================================================
# # TABLE 20 — messages
# # =============================================================================

# class Message(Base):
#     __tablename__ = "messages"
#     # Each bubble in the chat window — timestamps: 08:32, 08:33, 08:35, 08:38, 08:42

#     id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     thread_id = Column(UUID(as_uuid=True), ForeignKey("message_threads.id"),
#                        nullable=False, index=True)
#     sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                        nullable=False, index=True)

#     # Message content
#     body      = Column(Text, nullable=True)
#     # nullable because some messages are attachment-only or call events

#     # Message type — different bubble styles in Screen 24
#     message_type = Column(
#                       Enum("text", "file_attachment", "call_event",
#                            "system_notification",
#                            name="message_type_enum"),
#                       nullable=False, default="text"
#                    )
#     # text              → normal chat bubble
#     # file_attachment   → "Updated_Resume_v2.docx • 1.2 MB" bubble
#     # call_event        → "Incoming Call • 12:45" shown as special bubble
#     # system_notification → automated messages e.g. "passport verified"

#     # File attachment — only filled when message_type = file_attachment
#     document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                           nullable=True)

#     # Call event — only filled when message_type = call_event
#     call_duration_seconds = Column(Integer, nullable=True)
#     # "12:45" = 765 seconds — shown in the Incoming Call bubble

#     call_status = Column(
#                      Enum("incoming", "outgoing", "missed", "declined",
#                           name="call_status_enum"),
#                      nullable=True
#                   )

#     # Read receipts
#     is_read     = Column(Boolean, default=False, nullable=False)
#     read_at     = Column(DateTime(timezone=True), nullable=True)

#     # Edit / Delete
#     is_edited   = Column(Boolean, default=False, nullable=False)
#     edited_at   = Column(DateTime(timezone=True), nullable=True)
#     is_deleted  = Column(Boolean, default=False, nullable=False)
#     # soft delete — message shows as "This message was deleted"
#     deleted_at  = Column(DateTime(timezone=True), nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     thread     = relationship("MessageThread", back_populates="messages")
#     sender     = relationship("User", foreign_keys=[sender_id],
#                               back_populates="sent_messages")
#     attachment = relationship("Document", foreign_keys=[document_id])


# # =============================================================================
# # TABLE 21 — notifications
# # =============================================================================

# class Notification(Base):
#     __tablename__ = "notifications"

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # Who receives this notification
#     user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                          nullable=False, index=True)

#     # ── Type ──────────────────────────────────────────────────────────────────
#     notification_type = Column(
#         Enum(
#             "missing_document",       # "Urgent: Missing Document Required"
#             "deadline_approaching",   # "Deadline Approaching: I-983 Signature Required"
#             "policy_update",          # "Immigration Policy Update Affects Your Case"
#             "document_approved",      # "Document Approved: Passport Copy"
#             "case_status_updated",    # "Case Status Updated: Under Review"
#             "participant_added",      # "New Participant Added to Your Case"
#             "document_comment",       # "New Comment on Your Document"
#             "weekly_summary",         # "Weekly Case Summary Available"
#             "security_alert",         # "Security Alert: New Login from New Device"
#             "payment_receipt",        # "Payment Receipt Available"
#             "immigration_news",       # news feed updates counted in KPI
#             name="notification_type_enum"
#         ),
#         nullable=False
#     )

#     # ── Category / Filter tab ─────────────────────────────────────────────────
#     category = Column(
#         Enum(
#             "case_update",   # Case Updates tab
#             "deadline",      # Deadlines tab
#             "news",          # News tab
#             "security",      # Security alerts (own group)
#             "billing",       # Payment/billing notices
#             name="notification_category_enum"
#         ),
#         nullable=False
#     )

#     # ── Priority / Urgency badge ──────────────────────────────────────────────
#     priority = Column(
#         Enum(
#             "urgent",    # red  "URGENT" badge — "within 48 hours"
#             "high",      # "3 DAYS" badge — deadline soon
#             "medium",    # "POLICY" badge — informational but important
#             "low",       # no badge — general updates
#             name="notification_priority_enum"
#         ),
#         nullable=False, default="low"
#     )

#     # ── Content ───────────────────────────────────────────────────────────────
#     title       = Column(String(300), nullable=False)
#     body        = Column(Text, nullable=False)

#     # ── Context links ─────────────────────────────────────────────────────────
#     application_id  = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                              nullable=True)
#     document_id     = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                              nullable=True)
#     case_reference  = Column(String(100), nullable=True)
#     # "H-1B Case #2024-1847", "STEM OPT Extension" — display label

#     # ── Actor — who triggered this notification ───────────────────────────────
#     actor_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     actor_label = Column(String(150), nullable=True)
#     # stored separately so it displays even if actor account is deleted

#     # ── CTA Buttons ───────────────────────────────────────────────────────────
#     cta_primary_label  = Column(String(50),  nullable=True)
#     cta_primary_url    = Column(String(500), nullable=True)
#     cta_secondary_label = Column(String(50),  nullable=True)
#     cta_secondary_url   = Column(String(500), nullable=True)

#     # ── Read / Dismiss state ──────────────────────────────────────────────────
#     is_read      = Column(Boolean, default=False, nullable=False)
#     read_at      = Column(DateTime(timezone=True), nullable=True)
#     is_dismissed = Column(Boolean, default=False, nullable=False)
#     dismissed_at = Column(DateTime(timezone=True), nullable=True)

#     # ── Delivery channels ─────────────────────────────────────────────────────
#     sent_via_email = Column(Boolean, default=False, nullable=False)
#     sent_via_push  = Column(Boolean, default=False, nullable=False)
#     sent_via_sms   = Column(Boolean, default=False, nullable=False)

#     # ── Expiry ────────────────────────────────────────────────────────────────
#     expires_at   = Column(DateTime(timezone=True), nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user        = relationship("User",        foreign_keys=[user_id],
#                                back_populates="notifications")
#     actor       = relationship("User",        foreign_keys=[actor_id],
#                                back_populates="triggered_notifications")
#     application = relationship("Application", foreign_keys=[application_id])
#     document    = relationship("Document",    foreign_keys=[document_id])


# # =============================================================================
# # TABLE 22 — notification_preferences
# # =============================================================================

# class NotificationPreferences(Base):
#     __tablename__ = "notification_preferences"
#     # One row per user — their channel preferences

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, unique=True)
#     # unique=True → strict 1 row per user

#     # ── Per-channel master toggles ────────────────────────────────────────────
#     email_enabled = Column(Boolean, default=True,  nullable=False)
#     push_enabled  = Column(Boolean, default=True,  nullable=False)
#     sms_enabled   = Column(Boolean, default=False, nullable=False)
#     # default False — user must opt-in to SMS

#     # ── Per-type granular toggles ─────────────────────────────────────────────
#     notify_case_updates     = Column(Boolean, default=True,  nullable=False)
#     notify_deadlines        = Column(Boolean, default=True,  nullable=False)
#     notify_document_updates = Column(Boolean, default=True,  nullable=False)
#     notify_news             = Column(Boolean, default=True,  nullable=False)
#     notify_security_alerts  = Column(Boolean, default=True,  nullable=False)
#     notify_billing          = Column(Boolean, default=True,  nullable=False)
#     notify_weekly_summary   = Column(Boolean, default=True,  nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationship
#     user = relationship("User", foreign_keys=[user_id],
#                         back_populates="notification_prefs")


# # =============================================================================
# # TABLE 23 — deadlines
# # =============================================================================

# class Deadline(Base):
#     __tablename__ = "deadlines"
#     # "I-983 Signature Due — March 28, 2024 (3 days) — Critical"

#     id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=False, index=True)
#     user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                             nullable=False, index=True)

#     title          = Column(String(300), nullable=False)
#     description    = Column(Text, nullable=True)
#     due_date       = Column(DateTime(timezone=True), nullable=False)

#     severity       = Column(
#                         Enum("critical", "high", "medium", "low",
#                              name="deadline_severity_enum"),
#                         nullable=False, default="medium"
#                      )
#     # "Critical" label shown in Screen 25 sidebar

#     deadline_type  = Column(
#                         Enum("document_upload", "form_signature",
#                              "government_filing", "review", "payment",
#                              name="deadline_type_enum"),
#                         nullable=False
#                      )

#     is_completed   = Column(Boolean, default=False, nullable=False)
#     completed_at   = Column(DateTime(timezone=True), nullable=True)

#     # Notification trigger — auto-create notification when X days before due
#     notify_days_before = Column(Integer, default=3, nullable=False)
#     notification_sent  = Column(Boolean, default=False, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     application = relationship("Application")
#     user        = relationship("User", foreign_keys=[user_id],
#                                back_populates="deadlines")


# # =============================================================================
# # TABLE 24 — news_articles
# # =============================================================================

# class NewsArticle(Base):
#     __tablename__ = "news_articles"

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     # ── Core Content ──────────────────────────────────────────────────────────
#     title   = Column(String(500), nullable=False)
#     summary = Column(Text, nullable=True)
#     body    = Column(Text, nullable=False)
#     source  = Column(String(200), nullable=False)
#     # "USCIS Official", "SEVP", "DOL", "DOS", "USCIS"
#     source_url = Column(String(1000), nullable=True)

#     # ── Read time & engagement ────────────────────────────────────────────────
#     read_time_minutes = Column(Integer, nullable=True)
#     view_count = Column(Integer, default=0, nullable=False)

#     # ── Priority / Urgency ────────────────────────────────────────────────────
#     priority = Column(
#                   Enum("critical", "important", "normal",
#                        name="news_priority_enum"),
#                   nullable=False, default="normal"
#                )

#     # ── Update type ───────────────────────────────────────────────────────────
#     update_type = Column(
#                      Enum("policy_change", "fee_update", "processing_time",
#                           "form_change", "court_decision", "general",
#                           name="news_update_type_enum"),
#                      nullable=False, default="general"
#                   )

#     # ── Case impact ───────────────────────────────────────────────────────────
#     has_case_impact  = Column(Boolean, default=False, nullable=False)
#     case_impact_note = Column(Text, nullable=True)

#     cta_label = Column(String(100), nullable=True)
#     cta_url   = Column(String(1000), nullable=True)

#     # ── Publication ───────────────────────────────────────────────────────────
#     published_at  = Column(DateTime(timezone=True), nullable=False)
#     is_published  = Column(Boolean, default=True, nullable=False)
#     is_active     = Column(Boolean, default=True, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     visa_tags   = relationship("NewsArticleVisaTag",  back_populates="article")
#     bookmarks   = relationship("NewsArticleBookmark", back_populates="article")


# # =============================================================================
# # TABLE 25 — news_article_visa_tags (junction)
# # =============================================================================

# class NewsArticleVisaTag(Base):
#     __tablename__ = "news_article_visa_tags"
#     # Junction table — which visa types an article applies to

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     article_id   = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"),
#                           nullable=False, index=True)
#     visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                           nullable=False, index=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     article   = relationship("NewsArticle",  back_populates="visa_tags")
#     visa_type = relationship("VisaType",     back_populates="news_tags")


# # =============================================================================
# # TABLE 26 — news_article_bookmarks
# # =============================================================================

# class NewsArticleBookmark(Base):
#     __tablename__ = "news_article_bookmarks"
#     # "Saved Articles: 18" — per user bookmarks of news articles

#     id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                         nullable=False, index=True)
#     article_id = Column(UUID(as_uuid=True), ForeignKey("news_articles.id"),
#                         nullable=False, index=True)

#     note       = Column(String(500), nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Unique constraint — one bookmark per user per article
#     __table_args__ = (
#         UniqueConstraint("user_id", "article_id",
#                          name="uq_user_article_bookmark"),
#     )

#     # Relationships
#     user    = relationship("User",        foreign_keys=[user_id],
#                            back_populates="news_bookmarks")
#     article = relationship("NewsArticle", back_populates="bookmarks")


# # =============================================================================
# # TABLE 27 — news_feed_preferences
# # =============================================================================

# class NewsFeedPreference(Base):
#     __tablename__ = "news_feed_preferences"
#     # Per-user feed personalisation — "Customize Feed" button
#     # One row per user per visa type they follow

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                           nullable=False, index=True)
#     visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                           nullable=False)
#     # "Active Filters: H-1B, OPT/STEM OPT" — each is one row

#     include_policy_changes   = Column(Boolean, default=True,  nullable=False)
#     include_fee_updates      = Column(Boolean, default=True,  nullable=False)
#     include_processing_times = Column(Boolean, default=True,  nullable=False)
#     include_form_changes     = Column(Boolean, default=True,  nullable=False)
#     include_court_decisions  = Column(Boolean, default=False, nullable=False)

#     is_active    = Column(Boolean, default=True, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Unique constraint — one preference row per user per visa type
#     __table_args__ = (
#         UniqueConstraint("user_id", "visa_type_id",
#                          name="uq_user_visa_feed_preference"),
#     )

#     user      = relationship("User",     foreign_keys=[user_id],
#                              back_populates="feed_preferences")
#     visa_type = relationship("VisaType", back_populates="feed_preferences")


# # =============================================================================
# # TABLE 28 — visa_types (master lookup)
# # =============================================================================

# class VisaType(Base):
#     __tablename__ = "visa_types"
#     # Master lookup — every visa type in the system
#     # Admin-managed — only admins can add/edit visa types

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     code        = Column(String(50), nullable=False, unique=True)
#     # e.g. "H-1B", "F-1", "O-1A", "L-1", "EB-2", "B-1/B-2"

#     name        = Column(String(200), nullable=False)
#     # e.g. "H-1B Specialty Occupation"

#     description = Column(Text, nullable=True)

#     # ── Category ──────────────────────────────────────────────────────────────
#     category    = Column(
#                      Enum(
#                          "employment",
#                          "student",
#                          "visitor",
#                          "permanent_resident",
#                          "exchange",
#                          name="visa_category_enum"
#                      ),
#                      nullable=False
#                   )

#     requires_employer_sponsor = Column(Boolean, default=False, nullable=False)

#     required_documents = Column(Text, nullable=True)
#     # JSON array: ["Passport Copy", "Educational Transcripts", ...]

#     typical_processing_days = Column(Integer, nullable=True)
#     government_fee_usd      = Column(Integer, nullable=True)
#     uscis_url               = Column(String(1000), nullable=True)

#     short_label   = Column(String(30), nullable=True)
#     display_order = Column(Integer, default=0, nullable=False)
#     is_active     = Column(Boolean, default=True, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     applications      = relationship("Application",        back_populates="visa_type")
#     # user_visa_targets = relationship("UserVisaTarget",     back_populates="visa_type_rel")
#     news_tags         = relationship("NewsArticleVisaTag", back_populates="visa_type")
#     feed_preferences  = relationship("NewsFeedPreference", back_populates="visa_type")
#     user_visa_targets = relationship("UserVisaTarget",back_populates="visa_type")


# # =============================================================================
# # TABLE 29 — interview_sessions
# # =============================================================================

# class InterviewSession(Base):
#     __tablename__ = "interview_sessions"
#     # One row = one scheduled visa interview for a user
#     # "B1/B2 Visa Interview · Oct 15, 2023 · 09:30 AM · US Embassy London"

#     id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                             nullable=False, index=True)
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=True, index=True)
#     visa_type_id   = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                             nullable=False)

#     # ── Interview Status ──────────────────────────────────────────────────────
#     status         = Column(
#                         Enum(
#                             "upcoming",
#                             "completed",
#                             "cancelled",
#                             "rescheduled",
#                             name="interview_status_enum"
#                         ),
#                         nullable=False, default="upcoming"
#                      )

#     # ── Schedule ──────────────────────────────────────────────────────────────
#     interview_date = Column(Date,       nullable=False)
#     interview_time = Column(String(20), nullable=True)
#     timezone       = Column(String(100), nullable=True)

#     # ── Location ──────────────────────────────────────────────────────────────
#     location_name    = Column(String(300), nullable=True)
#     location_address = Column(String(500), nullable=True)
#     location_city    = Column(String(100), nullable=True)
#     location_country = Column(String(100), nullable=True)

#     # ── Progress ──────────────────────────────────────────────────────────────
#     preparation_progress = Column(Integer, default=0, nullable=False)
#     # 0–100 percentage — calculated from completed checklist items

#     notes          = Column(Text, nullable=True)

#     # Audit
#     created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user            = relationship("User",        foreign_keys=[user_id],
#                                    back_populates="interview_sessions")
#     application     = relationship("Application", foreign_keys=[application_id])
#     visa_type       = relationship("VisaType",    foreign_keys=[visa_type_id])
#     checklist_items = relationship("InterviewChecklistItem",
#                                    back_populates="session",
#                                    order_by="InterviewChecklistItem.sort_order")
#     questions       = relationship("InterviewQuestion", back_populates="session")
#     tips            = relationship("InterviewTip",      back_populates="session")


# # =============================================================================
# # TABLE 30 — interview_checklist_items
# # =============================================================================

# class InterviewChecklistItem(Base):
#     __tablename__ = "interview_checklist_items"

#     id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
#                         nullable=False, index=True)

#     title       = Column(String(300), nullable=False)
#     description = Column(Text, nullable=True)

#     is_required  = Column(Boolean, default=True,  nullable=False)
#     is_completed = Column(Boolean, default=False, nullable=False)
#     completed_at = Column(DateTime(timezone=True), nullable=True)
#     completed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

#     document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                           nullable=True)
#     sort_order   = Column(Integer, default=0, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationship
#     session  = relationship("InterviewSession", back_populates="checklist_items")
#     document = relationship("Document",         foreign_keys=[document_id])


# # =============================================================================
# # TABLE 31 — interview_questions
# # =============================================================================

# class InterviewQuestion(Base):
#     __tablename__ = "interview_questions"

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     session_id   = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
#                           nullable=True, index=True)
#     # nullable — questions can be session-specific OR global templates

#     visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                           nullable=True)
#     # when session_id is null → visa_type_id scopes the template

#     question    = Column(Text, nullable=False)
#     guidance    = Column(Text, nullable=True)
#     user_answer = Column(Text, nullable=True)

#     sort_order  = Column(Integer, default=0, nullable=False)
#     is_active   = Column(Boolean, default=True, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     session   = relationship("InterviewSession", back_populates="questions")
#     visa_type = relationship("VisaType",         foreign_keys=[visa_type_id])


# # =============================================================================
# # TABLE 32 — interview_tips
# # =============================================================================

# class InterviewTip(Base):
#     __tablename__ = "interview_tips"

#     id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     session_id   = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id"),
#                           nullable=True, index=True)
#     visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                           nullable=True)

#     tip_group   = Column(
#                      Enum(
#                          "day_of_interview",
#                          "what_to_wear",
#                          "general",
#                          name="tip_group_enum"
#                      ),
#                      nullable=False, default="day_of_interview"
#                   )

#     title       = Column(String(300), nullable=False)
#     body        = Column(Text, nullable=True)
#     disclaimer  = Column(Text, nullable=True)

#     sort_order  = Column(Integer, default=0, nullable=False)
#     is_active   = Column(Boolean, default=True, nullable=False)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     session   = relationship("InterviewSession", back_populates="tips")
#     visa_type = relationship("VisaType",         foreign_keys=[visa_type_id])


# # =============================================================================
# # TABLE 33 — password_reset_tokens
# # =============================================================================

# class PasswordResetToken(Base):
#     __tablename__ = "password_reset_tokens"
#     # One row = one password reset request lifecycle
#     # Covers all 4 steps: Email → OTP → New Password → Success
#     # Never delete rows — mark used/expired for audit trail

#     id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)

#     # ── Step 1 — Email request ────────────────────────────────────────────────
#     requested_email    = Column(String(255), nullable=False)
#     request_ip         = Column(String(45),  nullable=True)
#     request_user_agent = Column(String(500), nullable=True)

#     # ── Step 2 — OTP ──────────────────────────────────────────────────────────
#     otp_code        = Column(String(10),  nullable=False)
#     otp_code_hash   = Column(String(255), nullable=True)
#     expires_at      = Column(DateTime(timezone=True),    nullable=False)

#     resend_count    = Column(Integer,  default=0,     nullable=False)
#     last_resent_at  = Column(DateTime(timezone=True), nullable=True)

#     otp_verified    = Column(Boolean,  default=False, nullable=False)
#     otp_verified_at = Column(DateTime(timezone=True), nullable=True)

#     failed_attempts = Column(Integer, default=0, nullable=False)

#     # ── Step 3 — Password reset state ─────────────────────────────────────────
#     password_reset_completed    = Column(Boolean,  default=False, nullable=False)
#     password_reset_completed_at = Column(DateTime(timezone=True), nullable=True)

#     # ── Overall token status ──────────────────────────────────────────────────
#     status = Column(
#                 Enum(
#                     "pending",
#                     "verified",
#                     "completed",
#                     "expired",
#                     "locked",
#                     "cancelled",
#                     name="reset_token_status_enum"
#                 ),
#                 nullable=False, default="pending"
#              )

#     # ── Audit ─────────────────────────────────────────────────────────────────
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user = relationship("User", foreign_keys=[user_id],
#                         back_populates="reset_tokens")


# # =============================================================================
# # TABLE 34 — support_articles
# # =============================================================================

# class SupportArticle(Base):
#     __tablename__ = "support_articles"
#     # Knowledge base articles — FAQ answers, guides, tutorials

#     id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     title    = Column(String(500), nullable=False)
#     body     = Column(Text, nullable=False)
#     summary  = Column(String(500), nullable=True)

#     article_type = Column(
#                       Enum(
#                           "faq",
#                           "guide",
#                           "video_tutorial",
#                           "policy",
#                           name="article_type_enum"
#                       ),
#                       nullable=False, default="faq"
#                    )

#     category = Column(
#                   Enum(
#                       "all",
#                       "account_profile",
#                       "active_cases",
#                       "documents",
#                       "billing_payments",
#                       "visa_types",
#                       "getting_started",
#                       name="support_category_enum"
#                   ),
#                   nullable=False, default="all"
#                )

#     tag      = Column(String(100), nullable=True)

#     video_url              = Column(String(1000), nullable=True)
#     video_duration_seconds = Column(Integer,      nullable=True)

#     search_keywords = Column(Text,    nullable=True)
#     view_count      = Column(Integer, default=0, nullable=False)
#     helpful_count   = Column(Integer, default=0, nullable=False)
#     not_helpful_count = Column(Integer, default=0, nullable=False)

#     sort_order   = Column(Integer, default=0,    nullable=False)
#     is_published = Column(Boolean, default=True,  nullable=False)
#     is_active    = Column(Boolean, default=True,  nullable=False)
#     is_featured  = Column(Boolean, default=False, nullable=False)

#     # Audit
#     created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     published_at = Column(DateTime(timezone=True), nullable=True)
#     created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)


# # =============================================================================
# # TABLE 35 — support_tickets
# # =============================================================================

# class SupportTicket(Base):
#     __tablename__ = "support_tickets"

#     id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     ticket_number = Column(String(50), nullable=False, unique=True)
#     # e.g. "TKT-2024-00891"

#     user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                        nullable=True, index=True)
#     # nullable — public page users can submit tickets before logging in

#     guest_name  = Column(String(200), nullable=True)
#     guest_email = Column(String(255), nullable=True)

#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=True)
#     document_id    = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                             nullable=True)

#     subject   = Column(String(500), nullable=False)
#     body      = Column(Text, nullable=False)

#     category  = Column(
#                    Enum(
#                        "account_profile",
#                        "active_cases",
#                        "documents",
#                        "billing_payments",
#                        "visa_types",
#                        "technical",
#                        "other",
#                        name="ticket_category_enum"
#                    ),
#                    nullable=False, default="other"
#                 )

#     priority  = Column(
#                    Enum(
#                        "urgent",
#                        "high",
#                        "medium",
#                        "low",
#                        name="ticket_priority_enum"
#                    ),
#                    nullable=False, default="medium"
#                 )

#     status    = Column(
#                    Enum(
#                        "open",
#                        "in_progress",
#                        "waiting_user",
#                        "resolved",
#                        "closed",
#                        name="ticket_status_enum"
#                    ),
#                    nullable=False, default="open"
#                 )

#     assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

#     sla_due_at        = Column(DateTime(timezone=True), nullable=True)
#     first_response_at = Column(DateTime(timezone=True), nullable=True)
#     resolved_at       = Column(DateTime(timezone=True), nullable=True)

#     channel   = Column(
#                    Enum(
#                        "web_form",
#                        "live_chat",
#                        "email",
#                        name="ticket_channel_enum"
#                    ),
#                    nullable=False, default="web_form"
#                 )

#     chat_session_id = Column(UUID(as_uuid=True),
#                              ForeignKey("support_chat_sessions.id"),
#                              nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

#     # Relationships
#     user           = relationship("User",    foreign_keys=[user_id],
#                                   back_populates="support_tickets")
#     assigned_agent = relationship("User",    foreign_keys=[assigned_to],
#                                   back_populates="assigned_tickets")
#     application    = relationship("Application", foreign_keys=[application_id])
#     replies        = relationship("SupportTicketReply", back_populates="ticket",
#                                   order_by="SupportTicketReply.created_at")


# # =============================================================================
# # TABLE 36 — support_ticket_replies
# # =============================================================================

# class SupportTicketReply(Base):
#     __tablename__ = "support_ticket_replies"

#     id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"),
#                        nullable=False, index=True)

#     sender_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     sender_type = Column(
#                      Enum("user", "agent", "system",
#                           name="reply_sender_type_enum"),
#                      nullable=False, default="user"
#                   )

#     body        = Column(Text, nullable=False)
#     document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"),
#                          nullable=True)

#     is_read  = Column(Boolean, default=False, nullable=False)
#     read_at  = Column(DateTime(timezone=True), nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationship
#     ticket = relationship("SupportTicket", back_populates="replies")
#     sender = relationship("User",          foreign_keys=[sender_id])


# # =============================================================================
# # TABLE 37 — support_chat_sessions
# # =============================================================================

# class SupportChatSession(Base):
#     __tablename__ = "support_chat_sessions"
#     # Live chat session — "Start Chat" button on Screen 29

#     id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

#     user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     agent_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

#     guest_name  = Column(String(200), nullable=True)
#     guest_email = Column(String(255), nullable=True)

#     status      = Column(
#                      Enum(
#                          "queued",
#                          "active",
#                          "ended",
#                          "escalated",
#                          "abandoned",
#                          name="chat_session_status_enum"
#                      ),
#                      nullable=False, default="queued"
#                   )

#     ticket_id   = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id"),
#                          nullable=True)

#     started_at   = Column(DateTime(timezone=True), nullable=True)
#     ended_at     = Column(DateTime(timezone=True), nullable=True)
#     wait_seconds = Column(Integer,  nullable=True)

#     rating      = Column(Integer,      nullable=True)
#     rating_note = Column(String(500),  nullable=True)

#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

#     # Relationships
#     user    = relationship("User", foreign_keys=[user_id],
#                            back_populates="chat_sessions_user")
#     agent   = relationship("User", foreign_keys=[agent_id],
#                            back_populates="chat_sessions_agent")
#     ticket  = relationship("SupportTicket", foreign_keys=[ticket_id])

# class FeeTemplate(Base):
#     __tablename__ = "fee_templates"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     # ── Identity ──────────────────────────────────────────────────────────────
#     code        = Column(String(100), nullable=False, unique=True)
#     # Machine-readable slug — e.g. "h1b_premium_processing", "i129_filing"
#     # Used in code to reference a specific fee type without relying on name
 
#     name        = Column(String(300), nullable=False)
#     # Display name — "H-1B Premium Processing Fee", "I-129 Filing Fee"
#     # Shown in: Screen 18 fee card title, invoice line items
 
#     description = Column(Text, nullable=True)
#     # Tooltip / help text explaining what this fee covers
 
#     # ── Category ──────────────────────────────────────────────────────────────
#     category = Column(
#         Enum(
#             "filing_fee",          # USCIS statutory filing fees
#             "premium_processing",  # I-907 premium processing — $2,805
#             "biometrics",          # ASC biometrics fee — $85
#             "attorney_fee",        # Law firm service fee
#             "document_fee",        # Notarisation, certified copies
#             "other",
#             name="fee_category_enum"
#         ),
#         nullable=False, default="other"
#     )
 
#     # ── Visa type scoping (optional) ─────────────────────────────────────────
#     visa_type_id = Column(UUID(as_uuid=True), ForeignKey("visa_types.id"),
#                           nullable=True)
#     # null  → fee applies to all visa types (e.g. biometrics)
#     # set   → fee is specific to one visa type (e.g. H-1B premium processing)
 
#     # ── Amounts ───────────────────────────────────────────────────────────────
#     default_amount_usd = Column(Integer, nullable=False)
#     # Stored in US cents — e.g. 280500 = $2,805.00
#     # Integer avoids floating-point rounding on money
 
#     is_government_fee = Column(Boolean, default=False, nullable=False)
#     # True  → USCIS/DOL statutory fee, cannot be discounted
#     # False → law firm service fee, may be negotiated
 
#     is_optional = Column(Boolean, default=False, nullable=False)
#     # True → premium processing — applicant chooses to add it
#     # False → mandatory — always included for this visa type
 
#     # ── Due date logic ────────────────────────────────────────────────────────
#     due_days_after_creation = Column(Integer, nullable=True)
#     # Automatically set due_date = created_at + N days
#     # null → due date is set manually by HR/attorney
 
#     # ── Display ───────────────────────────────────────────────────────────────
#     sort_order   = Column(Integer, default=0,    nullable=False)
#     is_active    = Column(Boolean, default=True, nullable=False)
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     fees      = relationship("Fee", back_populates="template")
#     visa_type = relationship("VisaType", foreign_keys=[visa_type_id])
 
 
# # =============================================================================
# # TABLE 39 — fees
# # One row = one fee owed by a user on a specific application.
# # Created by HR / attorney when initiating an application stage,
# # or auto-created by a trigger when a visa type requires mandatory fees.
# #
# # Screen 18 — Employee:
# #   "H-1B Premium Processing Fee  $2,805.00  Urgent: Due Oct 15, 2024  [Pay Now]"
# #   "I-129 Filing Fee              $460.00   Due Oct 20, 2024           [Pay Now]"
# #
# # Screen HR billing dashboard:
# #   List of all fees across all sponsored employees — status + amounts
# # =============================================================================
 
# class Fee(Base):
#     __tablename__ = "fees"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     # ── Core relationships ────────────────────────────────────────────────────
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=False, index=True)
#     # Which visa application this fee belongs to
 
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)
#     # The employee who owes this fee (application.user_id copied here for
#     # fast lookup without joining applications every time)
 
#     fee_template_id = Column(UUID(as_uuid=True), ForeignKey("fee_templates.id"),
#                              nullable=True)
#     # null allowed for ad-hoc fees created by HR without a template
 
#     # ── Fee details (copied from template, can be overridden per-instance) ────
#     title    = Column(String(300), nullable=False)
#     # "H-1B Premium Processing Fee" — may differ from template.name
#     # if HR customises the label for a specific case
 
#     category = Column(
#         Enum(
#             "filing_fee",
#             "premium_processing",
#             "biometrics",
#             "attorney_fee",
#             "document_fee",
#             "other",
#             name="fee_instance_category_enum"
#         ),
#         nullable=False, default="filing_fee"
#     )
 
#     # ── Amount ────────────────────────────────────────────────────────────────
#     amount_usd = Column(Integer, nullable=False)
#     # In US cents — e.g. 280500 = $2,805.00
#     # Copied from fee_template.default_amount_usd at creation time.
#     # HR can override for per-case adjustments.
 
#     # ── Status ────────────────────────────────────────────────────────────────
#     status = Column(
#         Enum(
#             "pending",    # created, not yet paid
#             "paid",       # payment_id is set, fully paid
#             "overdue",    # past due_date and still unpaid
#             "waived",     # HR/admin waived this fee
#             "refunded",   # payment reversed — refund_id is set
#             "cancelled",  # application withdrawn before payment
#             name="fee_status_enum"
#         ),
#         nullable=False, default="pending"
#     )
 
#     # ── Urgency ───────────────────────────────────────────────────────────────
#     is_urgent = Column(Boolean, default=False, nullable=False)
#     # True  → shown with red "Urgent: Due Oct 15" badge — Screen 18
#     # Auto-set by a scheduled job when due_date <= today + 3 days
 
#     due_date = Column(DateTime(timezone=True), nullable=True)
#     # Deadline for payment — drives urgency calculation
#     # "Due Oct 15, 2024" / "Due Oct 20, 2024" — Screen 18 fee cards
 
#     # ── Payment link ──────────────────────────────────────────────────────────
#     payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"),
#                         nullable=True)
#     # Set when this fee is successfully paid
#     # null = still unpaid
 
#     paid_at = Column(DateTime(timezone=True), nullable=True)
#     # Denormalised from payment.completed_at for fast unpaid queries
 
#     # ── Waiver ────────────────────────────────────────────────────────────────
#     waived_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     waived_at     = Column(DateTime(timezone=True), nullable=True)
#     waiver_reason = Column(String(500), nullable=True)
 
#     # ── Internal notes ────────────────────────────────────────────────────────
#     notes = Column(Text, nullable=True)
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     application = relationship("Application",  foreign_keys=[application_id])
#     user        = relationship("User",         foreign_keys=[user_id])
#     template    = relationship("FeeTemplate",  back_populates="fees")
#     payment     = relationship("Payment",      foreign_keys=[payment_id],
#                                back_populates="fees")
#     waived_by_user = relationship("User",      foreign_keys=[waived_by])
 
#     # Indexes
#     __table_args__ = (
#         Index("ix_fees_user_status",        "user_id",        "status"),
#         Index("ix_fees_application_status", "application_id", "status"),
#     )
 
 
# # =============================================================================
# # TABLE 40 — payment_methods
# # Saved payment instruments per user.
# # Screen 18 — "Payment Methods" panel:
# #   [Credit Card ●]  [PayPal ○]  [Apple Pay ○]  + Add New
# # =============================================================================
 
# class PaymentMethod(Base):
#     __tablename__ = "payment_methods"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)
 
#     # ── Method type ───────────────────────────────────────────────────────────
#     method_type = Column(
#         Enum(
#             "credit_card",  # Visa / Mastercard / Amex — Screen 18 shows both
#             "debit_card",
#             "paypal",       # Screen 18 PayPal option
#             "apple_pay",    # Screen 18 Apple Pay option
#             "google_pay",
#             "bank_transfer",
#             name="payment_method_type_enum"
#         ),
#         nullable=False
#     )
 
#     # ── Card details (credit_card / debit_card only) ──────────────────────────
#     card_brand = Column(
#         Enum("visa", "mastercard", "amex", "discover", "other",
#              name="card_brand_enum"),
#         nullable=True
#     )
#     # "VISA" + "MC" dual-badge shown in Screen 18 Credit Card tile
 
#     card_last4      = Column(String(4),   nullable=True)
#     card_exp_month  = Column(Integer,     nullable=True)   # 1–12
#     card_exp_year   = Column(Integer,     nullable=True)   # 4-digit year
#     card_holder_name = Column(String(200), nullable=True)
 
#     # ── Gateway token ─────────────────────────────────────────────────────────
#     gateway_customer_id = Column(String(255), nullable=True)
#     # Stripe customer ID / Braintree vault ID
#     # Never store raw card numbers — use gateway tokenisation
 
#     gateway_payment_method_id = Column(String(255), nullable=True)
#     # Stripe PaymentMethod ID / Braintree payment method nonce
 
#     # ── PayPal / Wallet fields ────────────────────────────────────────────────
#     paypal_email    = Column(String(255), nullable=True)
#     wallet_device_id = Column(String(255), nullable=True)
#     # Apple/Google Pay device-bound payment credential
 
#     # ── Billing address ───────────────────────────────────────────────────────
#     billing_name    = Column(String(200), nullable=True)
#     billing_line1   = Column(String(300), nullable=True)
#     billing_line2   = Column(String(300), nullable=True)
#     billing_city    = Column(String(100), nullable=True)
#     billing_state   = Column(String(100), nullable=True)
#     billing_zip     = Column(String(20),  nullable=True)
#     billing_country = Column(String(2),   nullable=True)   # ISO 3166-1 alpha-2
 
#     # ── Flags ─────────────────────────────────────────────────────────────────
#     is_default    = Column(Boolean, default=False, nullable=False)
#     # The ● selected method in Screen 18 — only one per user
 
#     is_verified   = Column(Boolean, default=False, nullable=False)
#     # True after gateway verifies the card / PayPal account is valid
 
#     is_active     = Column(Boolean, default=True, nullable=False)
#     # False → user deleted this method (soft delete so past payments reference it)
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     user     = relationship("User",    foreign_keys=[user_id])
#     payments = relationship("Payment", back_populates="payment_method")
 
 
# # =============================================================================
# # TABLE 41 — payments
# # One row = one payment transaction attempt.
# # A single transaction may pay multiple fees at once ("Pay All Securely").
# # Immutable after status = completed / failed — never update, only insert.
# #
# # Screen 18 — "Pay All Securely  $3,265.00" button creates one Payment
# # that references both the H-1B fee AND the I-129 fee.
# #
# # Screen 18 — Payment History tab shows all completed payments for a user.
# # HR billing dashboard shows all payments across all employees.
# # =============================================================================
 
# class Payment(Base):
#     __tablename__ = "payments"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     # ── Payer ─────────────────────────────────────────────────────────────────
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                      nullable=False, index=True)
#     # The employee / applicant who paid
 
#     # ── Payment method used ────────────────────────────────────────────────────
#     payment_method_id = Column(UUID(as_uuid=True),
#                                 ForeignKey("payment_methods.id"), nullable=True)
#     # null if payment method was deleted after the transaction
 
#     method_type_snapshot = Column(
#         Enum(
#             "credit_card", "debit_card", "paypal",
#             "apple_pay", "google_pay", "bank_transfer",
#             name="payment_method_snapshot_enum"
#         ),
#         nullable=False
#     )
#     # Denormalised copy of method_type at time of payment.
#     # Shown in Payment History even after payment_method is deleted.
 
#     card_last4_snapshot = Column(String(4), nullable=True)
#     # "•••• 4242" shown in payment history row
 
#     # ── Amount ────────────────────────────────────────────────────────────────
#     amount_usd = Column(Integer, nullable=False)
#     # Total charged in US cents — sum of all linked fee amounts
#     # "$3,265.00" = 326500
 
#     # ── Gateway ───────────────────────────────────────────────────────────────
#     gateway = Column(
#         Enum("stripe", "braintree", "paypal", "apple_pay", "manual",
#              name="payment_gateway_enum"),
#         nullable=False, default="stripe"
#     )
#     gateway_payment_intent_id = Column(String(255), nullable=True, index=True)
#     # Stripe PaymentIntent ID / Braintree transaction ID
#     # Used for webhook reconciliation and refund initiation
 
#     gateway_charge_id = Column(String(255), nullable=True)
#     # Stripe charge ID — needed for refund API calls
 
#     gateway_receipt_url = Column(String(1000), nullable=True)
#     # Stripe hosted receipt URL — can be emailed to user
 
#     # ── Status ────────────────────────────────────────────────────────────────
#     status = Column(
#         Enum(
#             "pending",            # payment initiated, awaiting gateway confirmation
#             "processing",         # gateway is processing (3DS, bank auth)
#             "completed",          # successful — fees are now paid
#             "failed",             # declined or errored
#             "cancelled",          # user cancelled before completing
#             "refunded",           # fully refunded
#             "partially_refunded", # partial refund applied
#             name="payment_status_enum"
#         ),
#         nullable=False, default="pending"
#     )
 
#     # ── Failure details ───────────────────────────────────────────────────────
#     failure_code    = Column(String(100), nullable=True)
#     # Gateway decline code — e.g. "card_declined", "insufficient_funds"
#     failure_message = Column(String(500), nullable=True)
#     # Human-readable error shown in UI: "Your card was declined."
 
#     # ── Timestamps ───────────────────────────────────────────────────────────
#     initiated_at  = Column(DateTime(timezone=True), nullable=True)
#     # When user clicked "Pay Now" / "Pay All Securely"
 
#     completed_at  = Column(DateTime(timezone=True), nullable=True)
#     # When gateway confirmed success — drives "paid_at" on linked fees
 
#     # ── Invoice ───────────────────────────────────────────────────────────────
#     invoice_id = Column(UUID(as_uuid=True), ForeignKey("payment_invoices.id"),
#                         nullable=True)
#     # Generated PDF invoice — linked after payment completes
 
#     # ── Description (for history view) ───────────────────────────────────────
#     description = Column(String(500), nullable=True)
#     # "H-1B Premium Processing Fee + I-129 Filing Fee"
#     # Auto-generated from linked fee titles
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          nullable=False, index=True)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     user           = relationship("User",          foreign_keys=[user_id])
#     payment_method = relationship("PaymentMethod", back_populates="payments")
#     fees           = relationship("Fee",           foreign_keys="Fee.payment_id",
#                                   back_populates="payment")
#     invoice        = relationship("PaymentInvoice", foreign_keys=[invoice_id],
#                                   back_populates="payment")
#     refunds        = relationship("PaymentRefund",  back_populates="payment")
 
#     # Indexes
#     __table_args__ = (
#         Index("ix_payments_user_status",   "user_id", "status"),
#         Index("ix_payments_gateway_intent", "gateway_payment_intent_id"),
#     )
 
 
# # =============================================================================
# # TABLE 42 — payment_invoices
# # PDF invoices generated after each successful payment.
# # Linked 1:1 with a Payment (one invoice per transaction).
# # Downloadable by employee + accessible to HR / attorney for the case.
# # =============================================================================
 
# class PaymentInvoice(Base):
#     __tablename__ = "payment_invoices"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     # ── Reference number ──────────────────────────────────────────────────────
#     invoice_number = Column(String(50), nullable=False, unique=True)
#     # e.g. "INV-2024-08921-001"
#     # Format: INV-{year}-{case_number_suffix}-{sequence}
 
#     # ── Who & what ────────────────────────────────────────────────────────────
#     user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),
#                             nullable=False, index=True)
#     application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"),
#                             nullable=True)
 
#     # ── Amounts ───────────────────────────────────────────────────────────────
#     subtotal_usd = Column(Integer, nullable=False)
#     tax_usd      = Column(Integer, nullable=False, default=0)
#     total_usd    = Column(Integer, nullable=False)
#     # All in US cents
 
#     currency = Column(String(3), nullable=False, default="USD")
 
#     # ── Storage ───────────────────────────────────────────────────────────────
#     pdf_url     = Column(String(1000), nullable=True)
#     # S3 URL of generated PDF — null until generation completes
 
#     pdf_generated_at = Column(DateTime(timezone=True), nullable=True)
 
#     # ── Status ────────────────────────────────────────────────────────────────
#     status = Column(
#         Enum("pending", "generated", "sent", "voided",
#              name="invoice_status_enum"),
#         nullable=False, default="pending"
#     )
 
#     sent_at  = Column(DateTime(timezone=True), nullable=True)
#     # When invoice email was sent to user
 
#     voided_at     = Column(DateTime(timezone=True), nullable=True)
#     void_reason   = Column(String(300), nullable=True)
#     # If a refund voids the invoice
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     user        = relationship("User",        foreign_keys=[user_id])
#     application = relationship("Application", foreign_keys=[application_id])
#     payment     = relationship("Payment",     foreign_keys="Payment.invoice_id",
#                                back_populates="invoice", uselist=False)
 
 
# # =============================================================================
# # TABLE 43 — payment_refunds
# # Refund requests and their outcomes.
# # One payment can have multiple partial refunds.
# # Initiated by HR / admin in the billing dashboard.
# # =============================================================================
 
# class PaymentRefund(Base):
#     __tablename__ = "payment_refunds"
 
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
#     # ── Source payment ────────────────────────────────────────────────────────
#     payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"),
#                         nullable=False, index=True)
 
#     # ── Amount ────────────────────────────────────────────────────────────────
#     amount_usd = Column(Integer, nullable=False)
#     # In US cents — may be less than original payment (partial refund)
 
#     # ── Reason ────────────────────────────────────────────────────────────────
#     reason = Column(
#         Enum(
#             "duplicate_payment",
#             "application_withdrawn",
#             "fee_waived",
#             "overpayment",
#             "admin_adjustment",
#             "other",
#             name="refund_reason_enum"
#         ),
#         nullable=False, default="other"
#     )
#     notes = Column(Text, nullable=True)
 
#     # ── Status ────────────────────────────────────────────────────────────────
#     status = Column(
#         Enum(
#             "pending",    # requested, awaiting gateway submission
#             "processing", # submitted to gateway
#             "completed",  # funds returned to user
#             "failed",     # gateway rejected refund
#             name="refund_status_enum"
#         ),
#         nullable=False, default="pending"
#     )
 
#     # ── Gateway ───────────────────────────────────────────────────────────────
#     gateway_refund_id = Column(String(255), nullable=True)
#     # Stripe refund ID — for reconciliation
 
#     # ── Timestamps ───────────────────────────────────────────────────────────
#     requested_at = Column(DateTime(timezone=True),
#                           default=lambda: datetime.now(timezone.utc), nullable=False)
#     completed_at = Column(DateTime(timezone=True), nullable=True)
 
#     # ── Who processed ─────────────────────────────────────────────────────────
#     requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     approved_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
 
#     # Audit
#     created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
#     created_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc), nullable=False)
#     updated_at  = Column(DateTime(timezone=True),
#                          default=lambda: datetime.now(timezone.utc),
#                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
 
#     # Relationships
#     payment      = relationship("Payment",  back_populates="refunds")
#     requested_by_user = relationship("User", foreign_keys=[requested_by])
#     approved_by_user  = relationship("User", foreign_keys=[approved_by])
 
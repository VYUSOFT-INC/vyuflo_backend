# =============================================================================
# new_seeds.py — VisaFlow Complete Seed Data
# Run once at DB init via seeddata_service.py
#
# SECTIONS
#   1. ROLES_SEED                  4 roles
#   2. PERMISSIONS_SEED            38 permission codes
#   3. ROLE_PERMISSIONS_SEED       which role gets which permissions
#   4. VISA_TYPES_SEED             20 visa types (added E-3 + lca_required)
#   5. DOCUMENT_TYPES_SEED         40+ document types
#   6. SUBSCRIPTION_PLANS_SEED     4 SaaS plans (Free/Starter/Pro/Enterprise)
#   7. PLAN_FEATURES_SEED          bullet points per plan
#   8. FEE_TEMPLATES_SEED          common USCIS + attorney fee types
#   9. SYSTEM_SETTINGS_SEED        platform config defaults
#  10. SUPPORT_ARTICLES_SEED       starter knowledge base articles
# =============================================================================

import json


# =============================================================================
# 1. ROLES — 4 roles, seeded once, never changed
# =============================================================================

ROLES_SEED = [
    {
        "name": "app_admin",
        "description": "Full system administrator. Can manage users, roles, visa types, content, and support.",
        "is_active": True,
        "is_system": True,
    },
    {
        "name": "hr",
        "description": "Employer HR Manager. Manages applications and documents for their company's employees.",
        "is_active": True,
        "is_system": True,
    },
    {
        "name": "attorney",
        "description": "Immigration Attorney. Manages assigned cases, verifies documents, updates status.",
        "is_active": True,
        "is_system": True,
    },
    {
        "name": "employee",
        "description": "Visa Applicant. Manages their own applications, uploads documents, tracks progress.",
        "is_active": True,
        "is_system": True,
    },
]


# =============================================================================
# 2. PERMISSIONS — 38 granular permission codes
# =============================================================================

PERMISSIONS_SEED = [
    # ── Dashboard ─────────────────────────────────────────────────────────────
    {"code": "dashboard.view_own",       "module": "dashboard",      "description": "View own role dashboard",                      "is_system": True},
    {"code": "dashboard.view_analytics", "module": "dashboard",      "description": "View analytics and workspace dashboards",       "is_system": True},

    # ── Applications ──────────────────────────────────────────────────────────
    {"code": "applications.create",        "module": "applications",  "description": "Start a new visa application",                  "is_system": True},
    {"code": "applications.view_own",      "module": "applications",  "description": "View own applications only",                    "is_system": True},
    {"code": "applications.view_all",      "module": "applications",  "description": "View all applications in the system",           "is_system": True},
    {"code": "applications.update_status", "module": "applications",  "description": "Change application status and stage",           "is_system": True},
    {"code": "applications.delete",        "module": "applications",  "description": "Permanently delete a draft application",        "is_system": True},
    {"code": "applications.add_comments",  "module": "applications",  "description": "Add internal comments on a case",               "is_system": True},

    # ── Documents ─────────────────────────────────────────────────────────────
    {"code": "documents.upload",        "module": "documents",  "description": "Upload a new document file",                "is_system": True},
    {"code": "documents.view_own",      "module": "documents",  "description": "View own documents only",                   "is_system": True},
    {"code": "documents.view_all",      "module": "documents",  "description": "View and download any user documents",      "is_system": True},
    {"code": "documents.verify",        "module": "documents",  "description": "Mark a document verified or rejected",      "is_system": True},
    {"code": "documents.delete",        "module": "documents",  "description": "Permanently delete a document",             "is_system": True},
    {"code": "documents.manage_rules",  "module": "documents",  "description": "Configure document rules engine",           "is_system": True},

    # ── Users ─────────────────────────────────────────────────────────────────
    {"code": "users.view_own_profile",  "module": "users",  "description": "View and edit own profile & security",        "is_system": True},
    {"code": "users.view_all",          "module": "users",  "description": "List and search all users",                   "is_system": True},
    {"code": "users.manage",            "module": "users",  "description": "Create, suspend, and delete any user",        "is_system": True},

    # ── Roles ─────────────────────────────────────────────────────────────────
    {"code": "roles.manage",       "module": "roles",  "description": "Create, edit, and deactivate roles",               "is_system": True},
    {"code": "permissions.manage", "module": "roles",  "description": "Assign and revoke permissions from roles",         "is_system": True},

    # ── Visa Types ────────────────────────────────────────────────────────────
    {"code": "visa_types.view",   "module": "visa_types",  "description": "Browse available visa types",                  "is_system": True},
    {"code": "visa_types.manage", "module": "visa_types",  "description": "Add and edit visa types in the master list",   "is_system": True},

    # ── Messages ──────────────────────────────────────────────────────────────
    {"code": "messages.send",             "module": "messages",  "description": "Send messages in any thread",             "is_system": True},
    {"code": "messages.view_all_threads", "module": "messages",  "description": "View every message thread",               "is_system": True},

    # ── Notifications ─────────────────────────────────────────────────────────
    {"code": "notifications.view",             "module": "notifications",  "description": "Receive and view notifications",         "is_system": True},
    {"code": "notifications.manage_templates", "module": "notifications",  "description": "Create and edit notification templates",  "is_system": True},

    # ── Support ───────────────────────────────────────────────────────────────
    {"code": "support.view_own_tickets", "module": "support",  "description": "View own support tickets",                 "is_system": True},
    {"code": "support.view_all_tickets", "module": "support",  "description": "View all support tickets",                 "is_system": True},
    {"code": "support.manage_tickets",   "module": "support",  "description": "Reply, reassign, and close tickets",       "is_system": True},

    # ── Content ───────────────────────────────────────────────────────────────
    {"code": "news.publish",          "module": "content",  "description": "Publish and unpublish news articles",          "is_system": True},
    {"code": "deadlines.manage",      "module": "content",  "description": "Create and edit application deadlines",        "is_system": True},
    {"code": "content.manage_guides", "module": "content",  "description": "Manage interview guides and onboarding flows", "is_system": True},

    # ── Reports ───────────────────────────────────────────────────────────────
    {"code": "reports.view_own", "module": "reports",  "description": "View own activity reports",                        "is_system": True},
    {"code": "reports.view_all", "module": "reports",  "description": "View all system reports and audit logs",           "is_system": True},
    {"code": "reports.export",   "module": "reports",  "description": "Export reports to PDF or CSV",                    "is_system": True},

    # ── Settings / Billing ────────────────────────────────────────────────────
    {"code": "settings.view",   "module": "settings",  "description": "View system settings",                            "is_system": True},
    {"code": "settings.manage", "module": "settings",  "description": "Modify system settings and security config",      "is_system": True},
    {"code": "billing.manage",  "module": "settings",  "description": "Manage subscriptions, pricing, and billing",      "is_system": True},
]


# =============================================================================
# 3. ROLE_PERMISSIONS — which role gets which permission codes
# =============================================================================

ROLE_PERMISSIONS_SEED = {

    # app_admin gets ALL permissions
    "app_admin": [p["code"] for p in PERMISSIONS_SEED],

    "hr": [
        "dashboard.view_own",
        "applications.create",
        "applications.view_own",
        "applications.view_all",
        "applications.update_status",
        "applications.add_comments",
        "documents.upload",
        "documents.view_own",
        "documents.view_all",
        "documents.verify",
        "documents.delete",
        "users.view_own_profile",
        "users.view_all",
        "visa_types.view",
        "messages.send",
        "messages.view_all_threads",
        "notifications.view",
        "support.view_own_tickets",
        "support.view_all_tickets",
        "support.manage_tickets",
        "deadlines.manage",
        "reports.view_own",
        "reports.view_all",
        "reports.export",
        "billing.manage",
    ],

    "attorney": [
        "dashboard.view_own",
        "applications.create",
        "applications.view_own",
        "applications.view_all",
        "applications.update_status",
        "applications.add_comments",
        "documents.upload",
        "documents.view_own",
        "documents.view_all",
        "documents.verify",
        "users.view_own_profile",
        "visa_types.view",
        "messages.send",
        "notifications.view",
        "support.view_own_tickets",
        "deadlines.manage",
        "reports.view_own",
        "content.manage_guides",
    ],

    "employee": [
        "dashboard.view_own",
        "applications.create",
        "applications.view_own",
        "documents.upload",
        "documents.view_own",
        "users.view_own_profile",
        "visa_types.view",
        "messages.send",
        "notifications.view",
        "support.view_own_tickets",
        "news.publish",   # employee can READ news (code="news.publish" = access news feed)
    ],
}


# =============================================================================
# 4. VISA_TYPES — 20 visa types
# required_documents stored as JSON string in DB (Text column)
# lca_required: True only where a DOL Labor Condition Application is legally
# required before filing — H-1B, H-1B-EXT, and E-3. Everything else is False.
# =============================================================================

VISA_TYPES_SEED = [
    # ── Employment ────────────────────────────────────────────────────────────
    {
        "code": "H-1B",
        "name": "H-1B Specialty Occupation",
        "short_label": "H-1B",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": True,
        "description": (
            "For temporary workers in specialty occupations that require "
            "theoretical or practical application of a body of highly "
            "specialized knowledge."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Educational Transcripts",
            "Resume / CV", "Offer Letter", "Previous I-797",
        ]),
        "typical_processing_days": 150,
        "government_fee_usd": 46000,   # $460 in cents
        "display_order": 1,
        "is_active": True,
    },
    {
        "code": "H-1B-EXT",
        "name": "H-1B Extension",
        "short_label": "H-1B Ext",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": True,
        "description": "Extension of an existing H-1B status with the same or a new employer.",
        "required_documents": json.dumps([
            "Passport Copy", "Current I-797 Approval Notice",
            "Offer Letter", "Resume / CV", "Pay Stubs (Last 3 Months)",
        ]),
        "typical_processing_days": 120,
        "government_fee_usd": 46000,
        "display_order": 2,
        "is_active": True,
    },
    {
        "code": "L-1A",
        "name": "L-1A Intracompany Transferee (Manager/Executive)",
        "short_label": "L-1A",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "For executives or managers transferring to a U.S. office "
            "of the same multinational company."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Offer Letter", "Organizational Chart",
            "Company Financial Statements", "Proof of Employment Abroad",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 46000,
        "display_order": 3,
        "is_active": True,
    },
    {
        "code": "L-1B",
        "name": "L-1B Intracompany Transferee (Specialized Knowledge)",
        "short_label": "L-1B",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "For employees with specialized knowledge transferring "
            "to a U.S. office of the same multinational company."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Offer Letter", "Proof of Specialized Knowledge",
            "Proof of Employment Abroad", "Company Financial Statements",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 46000,
        "display_order": 4,
        "is_active": True,
    },
    {
        "code": "O-1A",
        "name": "O-1A Extraordinary Ability (Science/Business/Athletics)",
        "short_label": "O-1A",
        "category": "employment",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For individuals with extraordinary ability in sciences, "
            "education, business, or athletics."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Resume / CV", "Awards and Recognition Evidence",
            "Published Work or Media Coverage", "Expert Reference Letters",
            "Contracts or Itinerary",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 46000,
        "display_order": 5,
        "is_active": True,
    },
    {
        "code": "O-1B",
        "name": "O-1B Extraordinary Ability (Arts/Film/TV)",
        "short_label": "O-1B",
        "category": "employment",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For individuals with extraordinary achievement in motion "
            "picture or television productions, or extraordinary ability in the arts."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Resume / CV", "Portfolio or Showreel",
            "Critical Role Evidence", "Expert Reference Letters",
            "Contracts or Itinerary",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 46000,
        "display_order": 6,
        "is_active": True,
    },
    {
        "code": "TN",
        "name": "TN NAFTA/USMCA",
        "short_label": "TN",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "For Canadian and Mexican citizens in specific professional categories "
            "under the USMCA trade agreement."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Offer Letter", "Educational Transcripts",
            "Professional License (if applicable)", "Resume / CV",
        ]),
        "typical_processing_days": 30,
        "government_fee_usd": 0,
        "display_order": 7,
        "is_active": True,
    },
    {
        "code": "E-2",
        "name": "E-2 Treaty Investor",
        "short_label": "E-2",
        "category": "employment",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For nationals of treaty countries investing a substantial amount "
            "of capital in a U.S. business."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Investment Evidence", "Business Plan",
            "Source of Funds Documentation", "Company Registration Documents",
        ]),
        "typical_processing_days": 120,
        "government_fee_usd": 20500,   # $205 in cents
        "display_order": 8,
        "is_active": True,
    },
    {
        "code": "E-3",
        "name": "E-3 Australian Specialty Occupation",
        "short_label": "E-3",
        "category": "employment",
        "requires_employer_sponsor": True,
        "lca_required": True,
        "description": (
            "For Australian citizens in specialty occupations, renewable "
            "indefinitely in 2-year increments, under the US-Australia treaty."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Educational Transcripts",
            "Offer Letter", "DS-160 Form",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 0,   # consular processing, no I-129 filing fee
        "display_order": 9,
        "is_active": True,
    },

    # ── Student ───────────────────────────────────────────────────────────────
    {
        "code": "F-1",
        "name": "F-1 Initial",
        "short_label": "F-1",
        "category": "student",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For international students enrolled full-time at a "
            "SEVP-approved U.S. academic institution."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Form I-20", "SEVIS Fee Receipt",
            "Financial Support Evidence", "Acceptance Letter",
        ]),
        "typical_processing_days": 60,
        "government_fee_usd": 18500,   # $185 in cents
        "display_order": 10,
        "is_active": True,
    },
    {
        "code": "F-1-OPT",
        "name": "F-1 OPT",
        "short_label": "F-1 OPT",
        "category": "student",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "Optional Practical Training — allows F-1 students to work "
            "in a job related to their major for up to 12 months."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Form I-20 (OPT Recommendation)",
            "EAD Application (Form I-765)", "Passport Photos",
            "Copy of Current Visa",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 41000,   # $410 in cents
        "display_order": 11,
        "is_active": True,
    },
    {
        "code": "F-1-OPT-EXT",
        "name": "F-1 OPT Extension",
        "short_label": "F-1 OPT Ext",
        "category": "student",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": "Extension of F-1 OPT for non-STEM degree holders under special circumstances.",
        "required_documents": json.dumps([
            "Passport Copy", "Current EAD Card",
            "Form I-20 (Updated)", "Employment Verification Letter",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 41000,
        "display_order": 12,
        "is_active": True,
    },
    {
        "code": "F-1-STEM-OPT",
        "name": "F-1 STEM OPT Extension",
        "short_label": "STEM OPT",
        "category": "student",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "24-month STEM OPT extension for F-1 students who graduated "
            "with a STEM degree and are employed by an E-Verify employer."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "EAD Card", "Form I-20",
            "I-983 Training Plan", "Employer Attestation",
            "STEM Degree Transcript",
        ]),
        "typical_processing_days": 90,
        "government_fee_usd": 41000,
        "display_order": 13,
        "is_active": True,
    },
    {
        "code": "F-1-CPT",
        "name": "F-1 CPT",
        "short_label": "CPT",
        "category": "student",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "Curricular Practical Training — allows F-1 students to work "
            "off-campus as part of their academic program."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Form I-20 (CPT Authorization)",
            "Offer Letter", "Enrollment Verification",
        ]),
        "typical_processing_days": 14,
        "government_fee_usd": 0,
        "display_order": 14,
        "is_active": True,
    },

    # ── Exchange ──────────────────────────────────────────────────────────────
    {
        "code": "J-1",
        "name": "J-1 Exchange Visitor",
        "short_label": "J-1",
        "category": "exchange",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For participants in approved exchange visitor programs — "
            "researchers, students, professors, and trainees."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Form DS-2019", "SEVIS Fee Receipt",
            "Financial Support Evidence", "Program Sponsor Letter",
        ]),
        "typical_processing_days": 60,
        "government_fee_usd": 22000,   # $220 SEVIS fee in cents
        "display_order": 15,
        "is_active": True,
    },

    # ── Visitor ───────────────────────────────────────────────────────────────
    {
        "code": "B-1-B-2",
        "name": "B-1/B-2 Visitor",
        "short_label": "B1/B2",
        "category": "visitor",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": "For temporary visitors for business (B-1) or tourism/pleasure (B-2).",
        "required_documents": json.dumps([
            "Passport Copy", "Bank Statements (Last 3 Months)",
            "Travel Itinerary", "Ties to Home Country Evidence",
            "Invitation Letter (if applicable)",
        ]),
        "typical_processing_days": 60,
        "government_fee_usd": 18500,
        "display_order": 16,
        "is_active": True,
    },

    # ── Permanent Resident ────────────────────────────────────────────────────
    {
        "code": "EB-1",
        "name": "EB-1 Priority Worker",
        "short_label": "EB-1",
        "category": "permanent_resident",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For individuals with extraordinary ability, outstanding professors "
            "or researchers, or multinational managers/executives."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Resume / CV", "Awards and Recognition Evidence",
            "Published Work or Media Coverage", "Expert Reference Letters",
            "Form I-140 Supporting Documents",
        ]),
        "typical_processing_days": 180,
        "government_fee_usd": 70000,   # $700 in cents
        "display_order": 17,
        "is_active": True,
    },
    {
        "code": "EB-2",
        "name": "EB-2 Advanced Degree / NIW",
        "short_label": "EB-2",
        "category": "permanent_resident",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "For professionals with advanced degrees or exceptional ability. "
            "NIW allows self-petition if the work benefits the U.S. national interest."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Educational Transcripts", "Resume / CV",
            "Expert Reference Letters",
            "National Interest Waiver Justification Letter",
            "Form I-140 Supporting Documents",
        ]),
        "typical_processing_days": 180,
        "government_fee_usd": 70000,
        "display_order": 18,
        "is_active": True,
    },
    {
        "code": "EB-3",
        "name": "EB-3 Skilled Worker",
        "short_label": "EB-3",
        "category": "permanent_resident",
        "requires_employer_sponsor": True,
        "lca_required": False,
        "description": (
            "For skilled workers, professionals, and unskilled workers "
            "with a permanent job offer from a U.S. employer."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Educational Transcripts", "Resume / CV",
            "Offer Letter", "PERM Labor Certification",
            "Form I-140 Supporting Documents",
        ]),
        "typical_processing_days": 365,
        "government_fee_usd": 70000,
        "display_order": 19,
        "is_active": True,
    },
    {
        "code": "GREEN-CARD",
        "name": "Green Card (Adjustment of Status)",
        "short_label": "Green Card",
        "category": "permanent_resident",
        "requires_employer_sponsor": False,
        "lca_required": False,
        "description": (
            "Adjustment of Status (Form I-485) for individuals already in the U.S. "
            "who are eligible for lawful permanent residence."
        ),
        "required_documents": json.dumps([
            "Passport Copy", "Birth Certificate", "Form I-485",
            "Medical Examination (Form I-693)",
            "Affidavit of Support (Form I-864)",
            "Two Passport Photos", "Current Immigration Status Evidence",
        ]),
        "typical_processing_days": 365,
        "government_fee_usd": 134500,  # $1,345 in cents
        "display_order": 20,
        "is_active": True,
    },
]


# =============================================================================
# 5. DOCUMENT_TYPES — complete master list of allowed document types
# =============================================================================

DOCUMENT_TYPES_SEED = [
    # ── Identity ──────────────────────────────────────────────────────────────
    {"name": "Passport Copy",                  "category": "identity",    "description": "Biographical page showing photo, personal details, and expiration date.",         "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Birth Certificate",              "category": "identity",    "description": "Official government-issued birth certificate.",                                     "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Two Passport Photos",            "category": "identity",    "description": "Two recent passport-style photographs meeting USCIS specifications.",               "is_optional": False, "accepted_formats": "JPG,PNG",     "max_file_size_mb": 5},
    {"name": "Copy of Current Visa",           "category": "identity",    "description": "Copy of current valid visa stamp in passport.",                                    "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Current Immigration Status Evidence", "category": "identity","description": "I-94, current visa, or other evidence of lawful immigration status.",             "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "EAD Card",                       "category": "identity",    "description": "Employment Authorization Document (EAD) card front and back.",                     "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Current EAD Card",               "category": "identity",    "description": "Current valid EAD card for OPT or other work authorization.",                     "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},

    # ── Employment ────────────────────────────────────────────────────────────
    {"name": "Offer Letter",                        "category": "employment", "description": "Signed offer letter from the sponsoring employer.",                                "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Resume / CV",                         "category": "employment", "description": "Current resume highlighting relevant work experience and qualifications.",         "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Pay Stubs (Last 3 Months)",           "category": "employment", "description": "Most recent three months of pay stubs from current employer.",                    "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Employment Verification Letter",      "category": "employment", "description": "Letter from employer confirming current employment status and compensation.",      "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Organizational Chart",                "category": "employment", "description": "Company org chart showing applicant's position and reporting structure.",          "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Proof of Employment Abroad",          "category": "employment", "description": "Letter confirming employment at foreign parent/affiliate company.",               "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Contracts or Itinerary",              "category": "employment", "description": "Signed contracts or detailed itinerary for engagements.",                         "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Professional License (if applicable)","category": "employment", "description": "State or national professional license if required by occupation.",              "is_optional": True,  "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Employer Attestation",               "category": "employment", "description": "E-Verify employer attestation confirming training plan compliance.",              "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},

    # ── Education ─────────────────────────────────────────────────────────────
    {"name": "Educational Transcripts",        "category": "education",  "description": "Official transcripts from degree-granting institutions.",                           "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 20},
    {"name": "Degree Certificate",             "category": "education",  "description": "Official degree or diploma certificate.",                                            "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Acceptance Letter",              "category": "education",  "description": "Official acceptance letter from the U.S. institution.",                             "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "STEM Degree Transcript",         "category": "education",  "description": "Transcript confirming graduation from an approved STEM field.",                     "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 20},
    {"name": "Enrollment Verification",        "category": "education",  "description": "DSO-issued enrollment verification confirming full-time status.",                   "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},

    # ── Legal / Government Forms ───────────────────────────────────────────────
    {"name": "Previous I-797",                      "category": "legal",  "description": "Prior USCIS approval notice (I-797) for the same or related petition.",           "is_optional": True,  "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Current I-797 Approval Notice",       "category": "legal",  "description": "Most recent valid USCIS I-797 approval for current status.",                      "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Form I-20",                           "category": "legal",  "description": "I-20 Certificate of Eligibility from DSO-authorized institution.",                "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form I-20 (OPT Recommendation)",      "category": "legal",  "description": "I-20 with DSO recommendation for OPT endorsement.",                              "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form I-20 (Updated)",                 "category": "legal",  "description": "Updated I-20 reflecting current program/status.",                                 "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form I-20 (CPT Authorization)",        "category": "legal",  "description": "I-20 with CPT authorization endorsed by DSO.",                                  "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form DS-2019",                        "category": "legal",  "description": "Certificate of Eligibility for Exchange Visitor status.",                         "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form I-485",                          "category": "legal",  "description": "Application to Register Permanent Residence (Green Card).",                       "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "EAD Application (Form I-765)",        "category": "legal",  "description": "Application for Employment Authorization.",                                       "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "I-983 Training Plan",                 "category": "legal",  "description": "Training Plan for STEM OPT students (Form I-983).",                              "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Medical Examination (Form I-693)",    "category": "legal",  "description": "Sealed medical examination results from a USCIS-designated physician.",           "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Affidavit of Support (Form I-864)",   "category": "legal",  "description": "Affidavit of Support from U.S. sponsor for Green Card applicants.",               "is_optional": False, "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "SEVIS Fee Receipt",                   "category": "legal",  "description": "Receipt confirming SEVIS fee payment (I-901 SEVIS fee).",                         "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "PERM Labor Certification",            "category": "legal",  "description": "Approved ETA Form 9089 PERM Labor Certification from DOL.",                       "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Form I-140 Supporting Documents",     "category": "legal",  "description": "Supporting evidence package for the I-140 immigrant petition.",                   "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 20},
    {"name": "National Interest Waiver Justification Letter", "category": "legal", "description": "Detailed letter arguing national interest for EB-2 NIW self-petition.", "is_optional": False, "accepted_formats": "PDF,DOCX",   "max_file_size_mb": 10},
    {"name": "DS-160 Form",                         "category": "legal",  "description": "Online Nonimmigrant Visa Electronic Application confirmation page.",              "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},

    # ── Personal ──────────────────────────────────────────────────────────────
    {"name": "Financial Support Evidence",      "category": "personal", "description": "Bank statements or sponsor letter proving ability to support self.",                "is_optional": False, "accepted_formats": "PDF,JPG,PNG", "max_file_size_mb": 10},
    {"name": "Bank Statements (Last 3 Months)", "category": "personal", "description": "Three months of personal bank statements showing available funds.",                 "is_optional": False, "accepted_formats": "PDF",         "max_file_size_mb": 10},
    {"name": "Travel Itinerary",                "category": "personal", "description": "Detailed travel plan including flight bookings and accommodation.",                  "is_optional": True,  "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},
    {"name": "Ties to Home Country Evidence",   "category": "personal", "description": "Property, family, employment or other evidence of intent to return.",                "is_optional": False, "accepted_formats": "PDF,JPG,PNG,DOCX", "max_file_size_mb": 10},
    {"name": "Invitation Letter (if applicable)","category": "personal", "description": "Letter from U.S. host confirming purpose and duration of visit.",                  "is_optional": True,  "accepted_formats": "PDF,DOCX",    "max_file_size_mb": 10},

    # ── Other / Evidence ──────────────────────────────────────────────────────
    {"name": "Awards and Recognition Evidence",  "category": "other",  "description": "Certificates, trophies, letters confirming awards or prizes.",                       "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Published Work or Media Coverage", "category": "other",  "description": "Published articles, press coverage, or citations evidencing prominence.",             "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Expert Reference Letters",         "category": "other",  "description": "Reference letters from recognized experts in the field.",                             "is_optional": False, "accepted_formats": "PDF,DOCX",     "max_file_size_mb": 10},
    {"name": "Proof of Specialized Knowledge",   "category": "other",  "description": "Patents, publications, or technical documentation proving specialized knowledge.",    "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Investment Evidence",              "category": "other",  "description": "Bank wire transfers, contracts, or receipts proving capital investment.",             "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Business Plan",                    "category": "other",  "description": "Detailed business plan for the E-2 investment enterprise.",                          "is_optional": False, "accepted_formats": "PDF,DOCX",     "max_file_size_mb": 20},
    {"name": "Source of Funds Documentation",    "category": "other",  "description": "Evidence showing the lawful source of investment funds.",                            "is_optional": False, "accepted_formats": "PDF",          "max_file_size_mb": 20},
    {"name": "Company Registration Documents",   "category": "other",  "description": "Articles of incorporation, operating agreement, or business license.",               "is_optional": False, "accepted_formats": "PDF",          "max_file_size_mb": 10},
    {"name": "Company Financial Statements",     "category": "other",  "description": "Audited or unaudited financial statements for the past 2 years.",                    "is_optional": False, "accepted_formats": "PDF",          "max_file_size_mb": 20},
    {"name": "Portfolio or Showreel",            "category": "other",  "description": "Portfolio, showreel link, or representative work samples.",                          "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Critical Role Evidence",           "category": "other",  "description": "Evidence of critical or essential role in productions or performances.",             "is_optional": False, "accepted_formats": "PDF,JPG,PNG",  "max_file_size_mb": 20},
    {"name": "Program Sponsor Letter",           "category": "other",  "description": "Letter from J-1 program sponsor confirming program details.",                        "is_optional": False, "accepted_formats": "PDF,DOCX",     "max_file_size_mb": 10},
    {"name": "Passport Photos",                  "category": "other",  "description": "Passport-style photos meeting USCIS/DOS photo requirements.",                        "is_optional": False, "accepted_formats": "JPG,PNG",      "max_file_size_mb": 5},
]


# =============================================================================
# 6. SUBSCRIPTION_PLANS — 4 SaaS plans for admin billing dashboard
# All amounts in US CENTS to avoid float rounding.
# =============================================================================

SUBSCRIPTION_PLANS_SEED = [
    {
        "name":        "Free",
        "slug":        "free",
        "description": "Get started with basic case tracking. No payment required.",
        "price_monthly_cents": 0,
        "price_annual_cents":  0,
        "trial_days":          0,
        "max_applications":    1,
        "max_documents":       10,
        "max_messages":        20,
        "is_active":    True,
        "is_public":    True,
        "is_featured":  False,
        "display_order": 0,
        "highlight_color": None,
    },
    {
        "name":        "Starter",
        "slug":        "starter",
        "description": "Perfect for individual visa applicants managing a single case.",
        "price_monthly_cents": 2900,   # $29.00 / month
        "price_annual_cents":  29000,  # $290.00 / year (saves ~17%)
        "trial_days":          14,
        "max_applications":    3,
        "max_documents":       50,
        "max_messages":        None,   # unlimited
        "is_active":    True,
        "is_public":    True,
        "is_featured":  False,
        "display_order": 1,
        "highlight_color": None,
    },
    {
        "name":        "Professional",
        "slug":        "professional",
        "description": "For HR teams and attorneys managing multiple cases at once.",
        "price_monthly_cents": 7900,   # $79.00 / month
        "price_annual_cents":  79000,  # $790.00 / year
        "trial_days":          14,
        "max_applications":    None,   # unlimited
        "max_documents":       None,
        "max_messages":        None,
        "is_active":    True,
        "is_public":    True,
        "is_featured":  True,          # "Most Popular" badge
        "display_order": 2,
        "highlight_color": "#5B6CF6",
    },
    {
        "name":        "Enterprise",
        "slug":        "enterprise",
        "description": "Custom pricing for large organisations. Contact sales.",
        "price_monthly_cents": 0,      # 0 = custom / negotiated
        "price_annual_cents":  0,
        "trial_days":          0,
        "max_applications":    None,
        "max_documents":       None,
        "max_messages":        None,
        "is_active":    True,
        "is_public":    False,         # admin-assign only
        "is_featured":  False,
        "display_order": 3,
        "highlight_color": None,
    },
]


# =============================================================================
# 7. PLAN_FEATURES — bullet points per pricing card
# plan_slug maps to subscription_plans.slug
# =============================================================================

PLAN_FEATURES_SEED = [
    # Free
    {"plan_slug": "free", "feature_text": "1 active visa application",       "is_included": True,  "is_highlighted": False, "sort_order": 0},
    {"plan_slug": "free", "feature_text": "10 document uploads",             "is_included": True,  "is_highlighted": False, "sort_order": 1},
    {"plan_slug": "free", "feature_text": "20 messages per month",           "is_included": True,  "is_highlighted": False, "sort_order": 2},
    {"plan_slug": "free", "feature_text": "Email notifications",             "is_included": True,  "is_highlighted": False, "sort_order": 3},
    {"plan_slug": "free", "feature_text": "Priority support",                "is_included": False, "is_highlighted": False, "sort_order": 4},
    {"plan_slug": "free", "feature_text": "Interview prep tools",            "is_included": False, "is_highlighted": False, "sort_order": 5},
    {"plan_slug": "free", "feature_text": "Analytics dashboard",             "is_included": False, "is_highlighted": False, "sort_order": 6},

    # Starter
    {"plan_slug": "starter", "feature_text": "Up to 3 active visa applications", "is_included": True,  "is_highlighted": False, "sort_order": 0},
    {"plan_slug": "starter", "feature_text": "50 document uploads",              "is_included": True,  "is_highlighted": False, "sort_order": 1},
    {"plan_slug": "starter", "feature_text": "Unlimited messaging",              "is_included": True,  "is_highlighted": True,  "sort_order": 2},
    {"plan_slug": "starter", "feature_text": "Email + push notifications",       "is_included": True,  "is_highlighted": False, "sort_order": 3},
    {"plan_slug": "starter", "feature_text": "Interview prep tools",             "is_included": True,  "is_highlighted": False, "sort_order": 4},
    {"plan_slug": "starter", "feature_text": "14-day free trial",                "is_included": True,  "is_highlighted": False, "sort_order": 5},
    {"plan_slug": "starter", "feature_text": "Analytics dashboard",              "is_included": False, "is_highlighted": False, "sort_order": 6},

    # Professional
    {"plan_slug": "professional", "feature_text": "Unlimited visa applications",      "is_included": True, "is_highlighted": True,  "sort_order": 0},
    {"plan_slug": "professional", "feature_text": "Unlimited document uploads",       "is_included": True, "is_highlighted": False, "sort_order": 1},
    {"plan_slug": "professional", "feature_text": "Unlimited messaging",              "is_included": True, "is_highlighted": False, "sort_order": 2},
    {"plan_slug": "professional", "feature_text": "Email + push + SMS notifications","is_included": True, "is_highlighted": False, "sort_order": 3},
    {"plan_slug": "professional", "feature_text": "Interview prep tools",             "is_included": True, "is_highlighted": False, "sort_order": 4},
    {"plan_slug": "professional", "feature_text": "Analytics dashboard",              "is_included": True, "is_highlighted": True,  "sort_order": 5},
    {"plan_slug": "professional", "feature_text": "Priority support",                 "is_included": True, "is_highlighted": False, "sort_order": 6},
    {"plan_slug": "professional", "feature_text": "14-day free trial",                "is_included": True, "is_highlighted": False, "sort_order": 7},

    # Enterprise
    {"plan_slug": "enterprise", "feature_text": "Everything in Professional",     "is_included": True, "is_highlighted": True,  "sort_order": 0},
    {"plan_slug": "enterprise", "feature_text": "Custom user limits",             "is_included": True, "is_highlighted": False, "sort_order": 1},
    {"plan_slug": "enterprise", "feature_text": "Dedicated account manager",      "is_included": True, "is_highlighted": True,  "sort_order": 2},
    {"plan_slug": "enterprise", "feature_text": "SSO / SAML integration",         "is_included": True, "is_highlighted": False, "sort_order": 3},
    {"plan_slug": "enterprise", "feature_text": "Custom SLA and support",         "is_included": True, "is_highlighted": False, "sort_order": 4},
    {"plan_slug": "enterprise", "feature_text": "Audit logs export",              "is_included": True, "is_highlighted": False, "sort_order": 5},
    {"plan_slug": "enterprise", "feature_text": "On-premise deployment option",   "is_included": True, "is_highlighted": False, "sort_order": 6},
]


# =============================================================================
# 8. FEE_TEMPLATES — common USCIS and attorney fee types
# All amounts in US CENTS.
# =============================================================================

FEE_TEMPLATES_SEED = [
    # USCIS government fees
    {
        "code": "i129_filing",
        "name": "I-129 Filing Fee",
        "description": "USCIS statutory filing fee for Form I-129 (H-1B, L-1, O-1, TN petitions).",
        "category": "filing_fee",
        "default_amount_usd": 46000,   # $460 in cents
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 30,
        "sort_order": 0,
        "is_active": True,
    },
    {
        "code": "h1b_premium_processing",
        "name": "H-1B Premium Processing Fee",
        "description": "USCIS I-907 fee for expedited 15-business-day processing of H-1B petitions.",
        "category": "premium_processing",
        "default_amount_usd": 280500,  # $2,805 in cents
        "is_government_fee": True,
        "is_optional": True,
        "due_days_after_creation": 30,
        "sort_order": 1,
        "is_active": True,
    },
    {
        "code": "biometrics_fee",
        "name": "Biometrics Fee",
        "description": "USCIS biometrics fee for fingerprinting at an ASC.",
        "category": "biometrics",
        "default_amount_usd": 8500,    # $85 in cents
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 45,
        "sort_order": 2,
        "is_active": True,
    },
    {
        "code": "i485_filing",
        "name": "I-485 Filing Fee",
        "description": "USCIS filing fee for Adjustment of Status (Green Card).",
        "category": "filing_fee",
        "default_amount_usd": 134500,  # $1,345 in cents
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 30,
        "sort_order": 3,
        "is_active": True,
    },
    {
        "code": "i765_ead",
        "name": "EAD Application Fee (I-765)",
        "description": "USCIS filing fee for Employment Authorization Document.",
        "category": "filing_fee",
        "default_amount_usd": 41000,   # $410 in cents
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 30,
        "sort_order": 4,
        "is_active": True,
    },
    {
        "code": "i140_filing",
        "name": "I-140 Immigrant Petition Fee",
        "description": "USCIS filing fee for Immigrant Petition for Alien Workers (EB-1, EB-2, EB-3).",
        "category": "filing_fee",
        "default_amount_usd": 70000,   # $700 in cents
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 30,
        "sort_order": 5,
        "is_active": True,
    },
    {
        "code": "sevis_fee",
        "name": "SEVIS Fee (I-901)",
        "description": "Student and Exchange Visitor Information System fee.",
        "category": "filing_fee",
        "default_amount_usd": 35000,   # $350 F-1 | $220 J-1 — use F-1 as default
        "is_government_fee": True,
        "is_optional": False,
        "due_days_after_creation": 21,
        "sort_order": 6,
        "is_active": True,
    },
    # Attorney / service fees
    {
        "code": "attorney_service_fee",
        "name": "Attorney Service Fee",
        "description": "Law firm service fee for preparing and filing the visa petition.",
        "category": "attorney_fee",
        "default_amount_usd": 300000,  # $3,000 in cents — default, HR can override
        "is_government_fee": False,
        "is_optional": False,
        "due_days_after_creation": 14,
        "sort_order": 7,
        "is_active": True,
    },
    {
        "code": "document_notarization",
        "name": "Document Notarization Fee",
        "description": "Fee for notarizing required legal documents.",
        "category": "document_fee",
        "default_amount_usd": 15000,   # $150 in cents
        "is_government_fee": False,
        "is_optional": True,
        "due_days_after_creation": 21,
        "sort_order": 8,
        "is_active": True,
    },
]


# =============================================================================
# 9. SYSTEM_SETTINGS — platform config defaults for admin Screen 30
# All values stored as strings; value_type tells the service how to cast them.
# =============================================================================

SYSTEM_SETTINGS_SEED = [
    # ── General ───────────────────────────────────────────────────────────────
    {
        "key": "platform.name",
        "value": "VisaFlow",
        "value_type": "string",
        "setting_group": "general",
        "label": "Platform Name",
        "description": "The name shown in the browser tab, emails, and footer.",
        "is_public": True,
        "is_readonly": True,
        "display_order": 0,
    },
    {
        "key": "platform.support_email",
        "value": "support@visaflow.io",
        "value_type": "string",
        "setting_group": "general",
        "label": "Support Email",
        "description": "Public-facing support email address.",
        "is_public": True,
        "is_readonly": False,
        "display_order": 1,
    },
    {
        "key": "platform.default_timezone",
        "value": "America/New_York",
        "value_type": "string",
        "setting_group": "general",
        "label": "Default Timezone",
        "description": "Default timezone for deadline calculations and reports.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 2,
    },
    {
        "key": "platform.default_language",
        "value": "en",
        "value_type": "string",
        "setting_group": "general",
        "label": "Default Language",
        "description": "Default language for new user accounts.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 3,
    },

    # ── Security ──────────────────────────────────────────────────────────────
    {
        "key": "security.session_timeout_minutes",
        "value": "60",
        "value_type": "integer",
        "setting_group": "security",
        "label": "Session Timeout (minutes)",
        "description": "Inactive sessions are logged out after this many minutes.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 0,
    },
    {
        "key": "security.max_failed_login_attempts",
        "value": "5",
        "value_type": "integer",
        "setting_group": "security",
        "label": "Max Failed Login Attempts",
        "description": "Account locked after this many consecutive failed logins.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 1,
    },
    {
        "key": "security.require_2fa_for_admins",
        "value": "true",
        "value_type": "boolean",
        "setting_group": "security",
        "label": "Require 2FA for Admins",
        "description": "Force two-factor authentication for app_admin accounts.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 2,
    },
    {
        "key": "security.password_min_length",
        "value": "8",
        "value_type": "integer",
        "setting_group": "security",
        "label": "Minimum Password Length",
        "description": "Minimum number of characters for user passwords.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 3,
    },

    # ── Email ─────────────────────────────────────────────────────────────────
    {
        "key": "email.smtp_host",
        "value": "smtp.sendgrid.net",
        "value_type": "string",
        "setting_group": "email",
        "label": "SMTP Host",
        "description": "Outbound email SMTP server hostname.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 0,
    },
    {
        "key": "email.smtp_port",
        "value": "587",
        "value_type": "integer",
        "setting_group": "email",
        "label": "SMTP Port",
        "description": "SMTP server port (587 for TLS, 465 for SSL).",
        "is_public": False,
        "is_readonly": False,
        "display_order": 1,
    },
    {
        "key": "email.from_address",
        "value": "noreply@visaflow.io",
        "value_type": "string",
        "setting_group": "email",
        "label": "From Address",
        "description": "Email address shown in the From field.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 2,
    },
    {
        "key": "email.from_name",
        "value": "VisaFlow",
        "value_type": "string",
        "setting_group": "email",
        "label": "From Name",
        "description": "Display name shown next to the From address.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 3,
    },

    # ── SMS ───────────────────────────────────────────────────────────────────
    {
        "key": "sms.enabled",
        "value": "false",
        "value_type": "boolean",
        "setting_group": "sms",
        "label": "SMS Notifications Enabled",
        "description": "Enable SMS notifications globally. Requires Twilio credentials.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 0,
    },
    {
        "key": "sms.provider",
        "value": "twilio",
        "value_type": "string",
        "setting_group": "sms",
        "label": "SMS Provider",
        "description": "SMS provider: twilio or aws_sns.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 1,
    },

    # ── Features ──────────────────────────────────────────────────────────────
    {
        "key": "features.ocr_enabled",
        "value": "true",
        "value_type": "boolean",
        "setting_group": "features",
        "label": "OCR Document Processing",
        "description": "Automatically extract field data from uploaded documents.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 0,
    },
    {
        "key": "features.live_chat_enabled",
        "value": "true",
        "value_type": "boolean",
        "setting_group": "features",
        "label": "Live Chat Support",
        "description": "Show the 'Start Chat' button on the Help & Support screen.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 1,
    },
    {
        "key": "features.interview_prep_enabled",
        "value": "true",
        "value_type": "boolean",
        "setting_group": "features",
        "label": "Interview Prep Module",
        "description": "Enable the Interview Prep section for employee accounts.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 2,
    },
    {
        "key": "features.news_feed_enabled",
        "value": "true",
        "value_type": "boolean",
        "setting_group": "features",
        "label": "News Feed",
        "description": "Enable the Immigration News feed for all users.",
        "is_public": False,
        "is_readonly": False,
        "display_order": 3,
    },

    # ── Maintenance ───────────────────────────────────────────────────────────
    {
        "key": "maintenance.enabled",
        "value": "false",
        "value_type": "boolean",
        "setting_group": "maintenance",
        "label": "Maintenance Mode",
        "description": "Show maintenance page to all non-admin users.",
        "is_public": True,
        "is_readonly": False,
        "display_order": 0,
    },
    {
        "key": "maintenance.message",
        "value": "VisaFlow is temporarily down for scheduled maintenance. We'll be back shortly.",
        "value_type": "string",
        "setting_group": "maintenance",
        "label": "Maintenance Message",
        "description": "Message shown to users during maintenance mode.",
        "is_public": True,
        "is_readonly": False,
        "display_order": 1,
    },
]


# =============================================================================
# 10. SUPPORT_ARTICLES — starter knowledge base for Help & Support screen
# =============================================================================

SUPPORT_ARTICLES_SEED = [
    # ── Getting Started ───────────────────────────────────────────────────────
    {
        "title":        "How do I create my account?",
        "summary":      "Step-by-step guide to signing up for VisaFlow.",
        "body":         "To create your account, click 'Sign Up' on the login page. Enter your name, email, and password. You'll receive a verification email — click the link to activate your account. You can also sign up with Google or Microsoft.",
        "article_type": "faq",
        "category":     "getting_started",
        "tag":          "Account",
        "sort_order":   0,
        "is_published": True,
        "is_featured":  True,
    },
    {
        "title":        "How do I complete the onboarding process?",
        "summary":      "Walk through each onboarding step to set up your profile.",
        "body":         "After verifying your email, you'll go through 4 onboarding steps: (1) Choose your target visa type, (2) Complete your personal profile, (3) Verify your email, (4) Review a summary. You can save progress and return later.",
        "article_type": "guide",
        "category":     "getting_started",
        "tag":          "Onboarding",
        "sort_order":   1,
        "is_published": True,
        "is_featured":  False,
    },

    # ── Account & Profile ─────────────────────────────────────────────────────
    {
        "title":        "How do I reset my password?",
        "summary":      "Recover access to your account using the password reset flow.",
        "body":         "Click 'Forgot Password' on the login screen. Enter your registered email. You'll receive a 6-digit OTP code by email — enter it on the next screen. Then set your new password. The OTP expires after 15 minutes.",
        "article_type": "faq",
        "category":     "account_profile",
        "tag":          "Security",
        "sort_order":   0,
        "is_published": True,
        "is_featured":  False,
    },
    {
        "title":        "How do I update my profile picture?",
        "summary":      "Change your profile photo from the Profile & Security screen.",
        "body":         "Go to Profile & Security (top right menu) and click the avatar. Select 'Change Photo' and upload a JPG or PNG under 5MB. Your new photo appears immediately across the platform.",
        "article_type": "faq",
        "category":     "account_profile",
        "tag":          "Profile",
        "sort_order":   1,
        "is_published": True,
        "is_featured":  False,
    },

    # ── Active Cases ──────────────────────────────────────────────────────────
    {
        "title":        "How do I track my visa application status?",
        "summary":      "Find your application progress and current stage.",
        "body":         "Your active applications appear on the Dashboard. Each card shows the current stage, progress percentage, and any pending actions. Click an application to see the full status timeline and checklist.",
        "article_type": "faq",
        "category":     "active_cases",
        "tag":          "Applications",
        "sort_order":   0,
        "is_published": True,
        "is_featured":  True,
    },
    {
        "title":        "What does 'Action Needed' mean on my case?",
        "summary":      "Understand why your case is flagged and what to do next.",
        "body":         "An 'Action Needed' status means your attorney or HR manager requires something from you — usually a missing document, a signature, or additional information. Check the case detail screen for the specific action note and deadline.",
        "article_type": "faq",
        "category":     "active_cases",
        "tag":          "Status",
        "sort_order":   1,
        "is_published": True,
        "is_featured":  False,
    },

    # ── Documents ─────────────────────────────────────────────────────────────
    {
        "title":        "What file formats are accepted for document uploads?",
        "summary":      "Supported formats and file size limits for uploads.",
        "body":         "VisaFlow accepts PDF, JPG, and PNG files. The maximum file size is 10MB per document (5MB for passport photos). Make sure documents are clear, legible, and not password-protected.",
        "article_type": "faq",
        "category":     "documents",
        "tag":          "Documents",
        "sort_order":   0,
        "is_published": True,
        "is_featured":  False,
    },
    {
        "title":        "Why was my document rejected?",
        "summary":      "Common reasons for document rejection and how to fix them.",
        "body":         "Documents are rejected when they are blurry, expired, incomplete, or in the wrong format. Your attorney or HR admin will leave a rejection reason on the document. Upload a corrected version — the case will automatically move back into review.",
        "article_type": "faq",
        "category":     "documents",
        "tag":          "Documents",
        "sort_order":   1,
        "is_published": True,
        "is_featured":  False,
    },

    # ── Billing & Payments ────────────────────────────────────────────────────
    {
        "title":        "How do I pay my visa application fees?",
        "summary":      "Pay outstanding fees from the Payments screen.",
        "body":         "Go to the Payments screen from the left navigation. You'll see all outstanding fees with due dates. Select a payment method (Credit Card, PayPal, or Apple Pay) and click 'Pay Now' for a single fee or 'Pay All Securely' to settle everything at once.",
        "article_type": "guide",
        "category":     "billing_payments",
        "tag":          "Billing",
        "sort_order":   0,
        "is_published": True,
        "is_featured":  True,
    },
    {
        "title":        "Can I get a refund on a paid fee?",
        "summary":      "Understand the refund policy for visa application fees.",
        "body":         "Government fees (USCIS filing fees, biometrics) are generally non-refundable once submitted. Attorney service fees may be refundable depending on the case status — contact your HR manager or attorney. USCIS premium processing fees can be refunded if they fail to meet the processing time guarantee.",
        "article_type": "faq",
        "category":     "billing_payments",
        "tag":          "Billing",
        "sort_order":   1,
        "is_published": True,
        "is_featured":  False,
    },
]
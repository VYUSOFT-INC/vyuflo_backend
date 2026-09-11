# import json
# import uuid

# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.models.visamodels import DocumentType, Role, Permission, RolePermission, VisaType
# from app.models.seeds import DOCUMENT_TYPES_SEED, ROLES_SEED, PERMISSIONS_SEED, ROLE_PERMISSIONS_SEED, VISA_TYPES_SEED

# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.security import hash_password
# from enum import Enum


# async def seed_document_types(db: AsyncSession):
#     """
#     Seed document_types table.
#     - Skips existing records (based on unique 'name')
#     """

#     for doc_data in DOCUMENT_TYPES_SEED:
#         # 🔍 Check if already exists
#         result = await db.execute(
#             select(DocumentType).where(DocumentType.name == doc_data["name"])
#         )
#         existing = result.scalar_one_or_none()

#         if existing:
#             continue

#         # 🆕 Create new record
#         new_doc_type = DocumentType(
#             id=uuid.uuid4(),
#             name=doc_data["name"],
#             category=doc_data["category"],
#             description=doc_data.get("description"),
#             is_optional=doc_data.get("is_optional", False),
#             accepted_formats=doc_data.get("accepted_formats", "PDF,JPG,PNG"),
#             max_file_size_mb=doc_data.get("max_file_size_mb", 10),
#             is_active=True,
#             created_by=None,
#             modified_by=None,
#         )

#         db.add(new_doc_type)

#     await db.commit()
    
# async def seed_visa_types(db: AsyncSession):
#     """
#     Seed visa_types table.
#     - Skips existing records (based on unique 'code')
#     - Converts required_documents list → JSON string
#     """

#     for visa_data in VISA_TYPES_SEED:
#         # 🔍 Check if already exists
#         result = await db.execute(
#             select(VisaType).where(VisaType.code == visa_data["code"])
#         )
#         existing = result.scalar_one_or_none()

#         if existing:
#             continue

#         # 🧠 Convert list → JSON string (since column is Text)
#         required_docs = visa_data.get("required_documents")
#         if required_docs:
#             required_docs = json.dumps(required_docs)

#         # 🆕 Create new record
#         new_visa = VisaType(
#             id=uuid.uuid4(),
#             code=visa_data["code"],
#             name=visa_data["name"],
#             short_label=visa_data.get("short_label"),
#             category=visa_data["category"],
#             requires_employer_sponsor=visa_data.get("requires_employer_sponsor", False),
#             description=visa_data.get("description"),
#             required_documents=required_docs,
#             display_order=visa_data.get("display_order", 0),

#             # now allowed
#             created_by=None,
#             modified_by=None,
#         )

#         db.add(new_visa)

#     await db.commit()
    
# async def seed_rbac(db: AsyncSession):
#     # ── Insert Roles ─────────────────────────────
#     for role_data in ROLES_SEED:
#         result = await db.execute(
#             select(Role).where(Role.name == role_data["name"])
#         )
#         role = result.scalar_one_or_none()

#         if not role:
#             role = Role(**role_data)
#             print(role,"role")
#             db.add(role)

#     # ── Insert Permissions ───────────────────────
#     for perm_data in PERMISSIONS_SEED:
#         result = await db.execute(
#             select(Permission).where(Permission.code == perm_data["code"])
#         )
#         perm = result.scalar_one_or_none()

#         if not perm:
#             perm = Permission(**perm_data)
#             db.add(perm)

#     await db.commit()

#     # ── Fetch fresh data ─────────────────────────
#     roles = (await db.execute(select(Role))).scalars().all()
#     permissions = (await db.execute(select(Permission))).scalars().all()

#     role_map = {r.name: r for r in roles}
#     perm_map = {p.code: p for p in permissions}

#     # ── Insert Role-Permissions ──────────────────
#     for role_name, perm_codes in ROLE_PERMISSIONS_SEED.items():
#         for code in perm_codes:
#             role = role_map[role_name]
#             perm = perm_map[code]

#             result = await db.execute(
#                 select(RolePermission).where(
#                     RolePermission.role_id == role.id,
#                     RolePermission.permission_id == perm.id
#                 )
#             )

#             exists = result.scalar_one_or_none()

#             if not exists:
#                 db.add(RolePermission(
#                     role_id=role.id,
#                     permission_id=perm.id
#                 ))

#     await db.commit()


# =============================================================================
# seeddata_service.py
# Called from main.py lifespan on every startup.
# All functions are idempotent — safe to run on an already-seeded DB.
# =============================================================================

from asyncio.log import logger
import uuid
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    DocumentFieldConfiguration,
    NotificationTemplate,
    Role,
    Permission,
    RolePermission,
    UserRole,
    User,
    UserProfile,
    UserEmail,
    EmployerProfile,
    EmployerEmployee,
    EmployerFirmConnection,
    AttorneyProfile,
    OrganizationMember,
    VisaType,
    DocumentType,
    SubscriptionPlan,
    PlanFeature,
    FeeTemplate,
    SystemSetting,
    SupportArticle,
)

from app.models.seeds import (
    DOCUMENT_FIELD_CONFIG_SEED,
    NOTIFICATION_TEMPLATES_SEED,
    ROLES_SEED,
    PERMISSIONS_SEED,
    ROLE_PERMISSIONS_SEED,
    VISA_TYPES_SEED,
    DOCUMENT_TYPES_SEED,
    SUBSCRIPTION_PLANS_SEED,
    PLAN_FEATURES_SEED,
    FEE_TEMPLATES_SEED,
    SYSTEM_SETTINGS_SEED,
    SUPPORT_ARTICLES_SEED,
)


# =============================================================================
# seed_rbac
# Seeds: roles → permissions → role_permissions
# =============================================================================

async def seed_rbac(db: AsyncSession):
    # ── Roles ─────────────────────────────────────────────────────────────────
    for role_data in ROLES_SEED:
        result = await db.execute(
            select(Role).where(Role.name == role_data["name"])
        )
        if not result.scalar_one_or_none():
            db.add(Role(**role_data))

    # ── Permissions ───────────────────────────────────────────────────────────
    for perm_data in PERMISSIONS_SEED:
        result = await db.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        if not result.scalar_one_or_none():
            db.add(Permission(**perm_data))

    await db.commit()

    # ── Role-Permissions ──────────────────────────────────────────────────────
    roles       = (await db.execute(select(Role))).scalars().all()
    permissions = (await db.execute(select(Permission))).scalars().all()

    role_map = {r.name: r for r in roles}
    perm_map = {p.code: p for p in permissions}

    for role_name, perm_codes in ROLE_PERMISSIONS_SEED.items():
        role = role_map.get(role_name)
        if not role:
            continue

        for code in perm_codes:
            perm = perm_map.get(code)
            if not perm:
                continue

            result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id       == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if not result.scalar_one_or_none():
                db.add(RolePermission(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    permission_id=perm.id,
                ))

    await db.commit()
    print("✅ RBAC seeded")

    await _sync_org_admin_permissions(db)


async def _sync_org_admin_permissions(db: AsyncSession) -> None:
    """
    Org admins must not keep platform billing/pricing permissions.
    Seed only inserts RolePermission rows — this revoke keeps org_admin in sync.
    """
    from app.models.seeds import ORG_ADMIN_PERMISSIONS

    role = (
        await db.execute(select(Role).where(Role.name == "org_admin"))
    ).scalar_one_or_none()
    if not role:
        return

    allowed = set(ORG_ADMIN_PERMISSIONS)
    rows = (
        await db.execute(
            select(RolePermission, Permission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role.id)
        )
    ).all()

    revoked = 0
    for rp, perm in rows:
        if perm.code not in allowed:
            await db.delete(rp)
            revoked += 1

    # Ensure billing.subscribe is present
    sub_perm = (
        await db.execute(select(Permission).where(Permission.code == "billing.subscribe"))
    ).scalar_one_or_none()
    if sub_perm:
        existing = (
            await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == sub_perm.id,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(RolePermission(
                id=uuid.uuid4(),
                role_id=role.id,
                permission_id=sub_perm.id,
            ))

    await db.commit()
    if revoked:
        print(f"✅ org_admin permissions synced (revoked {revoked})")


# =============================================================================
# migrate_app_admin_to_super_admin
# Idempotent: move user_roles from legacy app_admin → super_admin.
# =============================================================================

async def migrate_app_admin_to_super_admin(db: AsyncSession):
    super_role = (
        await db.execute(select(Role).where(Role.name == "super_admin"))
    ).scalar_one_or_none()
    legacy = (
        await db.execute(select(Role).where(Role.name == "app_admin"))
    ).scalar_one_or_none()
    if not super_role or not legacy:
        return

    legacy_urs = (
        await db.execute(select(UserRole).where(UserRole.role_id == legacy.id))
    ).scalars().all()
    migrated = 0
    for ur in legacy_urs:
        existing = (
            await db.execute(
                select(UserRole).where(
                    UserRole.user_id == ur.user_id,
                    UserRole.role_id == super_role.id,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(UserRole(
                id=uuid.uuid4(),
                user_id=ur.user_id,
                role_id=super_role.id,
                assigned_by=ur.assigned_by,
                created_by=ur.created_by,
                modified_by=ur.modified_by,
            ))
            migrated += 1
        await db.delete(ur)

    # Mark platform users
    platform_users = (
        await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == super_role.id)
        )
    ).scalars().unique().all()
    for u in platform_users:
        if not getattr(u, "is_platform_user", False):
            u.is_platform_user = True

    # Deactivate legacy role so it is not reassigned
    legacy.is_active = False

    await db.commit()
    print(f"✅ Migrated app_admin → super_admin ({migrated} role rows)")


# =============================================================================
# seed_super_admin_user
# Ensures superadmin@vyuflo.com and admin@vyuflo.com exist as super_admin.
# Password matches other local test accounts: "password"
# =============================================================================

SUPER_ADMIN_EMAIL = "superadmin@vyuflo.com"
LEGACY_ADMIN_EMAIL = "admin@vyuflo.com"
SEED_ADMIN_PASSWORD = "password"


async def seed_super_admin_user(db: AsyncSession):
    from app.core.security import hash_password

    role = (
        await db.execute(select(Role).where(Role.name == "super_admin"))
    ).scalar_one_or_none()
    if not role:
        print("⚠️  super_admin role missing — skip seed_super_admin_user")
        return

    async def _ensure_user(email: str, first: str, last: str) -> None:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                first_name=first,
                last_name=last,
                email=email,
                password_hash=hash_password(SEED_ADMIN_PASSWORD),
                auth_provider="email",
                is_active=True,
                is_verified=True,
                terms_accepted=True,
                is_platform_user=True,
            )
            db.add(user)
            await db.flush()
            print(f"  CREATED {email}")
        else:
            user.password_hash = hash_password(SEED_ADMIN_PASSWORD)
            user.is_active = True
            user.is_verified = True
            user.terms_accepted = True
            user.is_platform_user = True
            print(f"  UPDATED {email}")

        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        ).scalar_one_or_none()
        if profile is None:
            db.add(UserProfile(
                user_id=user.id,
                full_legal_name=f"{first} {last}",
                onboarding_step=4,
                onboarding_completed=True,
            ))
        else:
            profile.onboarding_step = 4
            profile.onboarding_completed = True

        # Login resolves via user_emails (verified), not users.email alone.
        linked = (
            await db.execute(
                select(UserEmail).where(UserEmail.email == email.lower().strip())
            )
        ).scalar_one_or_none()
        if linked is None:
            db.add(UserEmail(
                user_id=user.id,
                email=email.lower().strip(),
                is_verified=True,
                is_primary=True,
                source="signup",
            ))
            print(f"  CREATED_USER_EMAIL {email}")
        else:
            linked.user_id = user.id
            linked.is_verified = True
            linked.is_primary = True
            print(f"  USER_EMAIL_OK {email}")

        ur = (
            await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                )
            )
        ).scalar_one_or_none()
        if ur is None:
            others = (
                await db.execute(select(UserRole).where(UserRole.user_id == user.id))
            ).scalars().all()
            for o in others:
                await db.delete(o)
            db.add(UserRole(user_id=user.id, role_id=role.id))

    await _ensure_user(SUPER_ADMIN_EMAIL, "Vyuflo", "SuperAdmin")
    await _ensure_user(LEGACY_ADMIN_EMAIL, "Vyuflo", "Admin")
    await db.commit()
    print(f"✅ Super admin ready: {SUPER_ADMIN_EMAIL} / {SEED_ADMIN_PASSWORD}")


# =============================================================================
# backfill_organization_members
# Owners → org_admin; employer_employees → employee; firm connections → attorney
# =============================================================================

async def backfill_organization_members(db: AsyncSession):
    async def _upsert(profile_id, user_id, org_role: str) -> bool:
        existing = (
            await db.execute(
                select(OrganizationMember).where(
                    OrganizationMember.employer_profile_id == profile_id,
                    OrganizationMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            if not existing.is_active:
                existing.is_active = True
            # Prefer higher privilege if already present
            rank = {"employee": 1, "attorney": 2, "hr": 3, "org_admin": 4}
            if rank.get(org_role, 0) > rank.get(existing.org_role, 0):
                existing.org_role = org_role
            return False
        db.add(OrganizationMember(
            id=uuid.uuid4(),
            employer_profile_id=profile_id,
            user_id=user_id,
            org_role=org_role,
            is_active=True,
        ))
        return True

    added = 0
    profiles = (await db.execute(select(EmployerProfile))).scalars().all()
    for ep in profiles:
        if await _upsert(ep.id, ep.user_id, "org_admin"):
            added += 1

    links = (await db.execute(select(EmployerEmployee))).scalars().all()
    for link in links:
        if link.employer_profile_id and link.employee_id:
            if await _upsert(link.employer_profile_id, link.employee_id, "employee"):
                added += 1
        # Also ensure the HR owner link is present as hr if not already org_admin
        if link.employer_profile_id and link.employer_id:
            existing = (
                await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.employer_profile_id == link.employer_profile_id,
                        OrganizationMember.user_id == link.employer_id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                if await _upsert(link.employer_profile_id, link.employer_id, "hr"):
                    added += 1

    # Attorneys connected via employer_firm_connections
    conns = (
        await db.execute(
            select(EmployerFirmConnection).where(EmployerFirmConnection.is_active == True)
        )
    ).scalars().all()
    for conn in conns:
        attorneys = (
            await db.execute(
                select(AttorneyProfile).where(
                    AttorneyProfile.firm_id == conn.firm_id,
                    AttorneyProfile.is_active == True,
                )
            )
        ).scalars().all()
        for ap in attorneys:
            if await _upsert(conn.employer_profile_id, ap.user_id, "attorney"):
                added += 1

    await db.commit()
    print(f"✅ Organization members backfilled (+{added})")


# =============================================================================
# seed_visa_types
# Seeds: visa_types
# required_documents is already a JSON string in new_seeds.py
# =============================================================================

async def seed_visa_types(db: AsyncSession):
    for visa_data in VISA_TYPES_SEED:
        result = await db.execute(
            select(VisaType).where(VisaType.code == visa_data["code"])
        )
        if result.scalar_one_or_none():
            continue

        # required_documents is already json.dumps()'d in seeds.py
        # If it ever comes in as a list, handle it safely here too
        required_docs = visa_data.get("required_documents")
        if isinstance(required_docs, list):
            required_docs = json.dumps(required_docs)

        db.add(VisaType(
            id=uuid.uuid4(),
            code=visa_data["code"],
            name=visa_data["name"],
            short_label=visa_data.get("short_label"),
            category=visa_data["category"],
            requires_employer_sponsor=visa_data.get("requires_employer_sponsor", False),
            description=visa_data.get("description"),
            required_documents=required_docs,
            typical_processing_days=visa_data.get("typical_processing_days"),
            government_fee_usd=visa_data.get("government_fee_usd"),
            uscis_url=visa_data.get("uscis_url"),
            display_order=visa_data.get("display_order", 0),
            is_active=visa_data.get("is_active", True),
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ Visa types seeded")


# =============================================================================
# seed_document_types
# Seeds: document_types
# =============================================================================
async def seed_document_types(db: AsyncSession):
    for doc_data in DOCUMENT_TYPES_SEED:
        result = await db.execute(
            select(DocumentType).where(DocumentType.name == doc_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.ocr_slug = doc_data.get("ocr_slug")
            continue

        db.add(DocumentType(
            id=uuid.uuid4(),
            name=doc_data["name"],
            category=doc_data["category"],
            ocr_slug=doc_data.get("ocr_slug"),
            description=doc_data.get("description"),
            is_optional=doc_data.get("is_optional", False),
            accepted_formats=doc_data.get("accepted_formats", "PDF,JPG,PNG"),
            max_file_size_mb=doc_data.get("max_file_size_mb", 10),
            is_active=True,
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ Document types seeded")

# =============================================================================
# seed_subscription_plans
# Seeds: subscription_plans → plan_features
# =============================================================================

async def seed_subscription_plans(db: AsyncSession):
    # ── Plans ─────────────────────────────────────────────────────────────────
    for plan_data in SUBSCRIPTION_PLANS_SEED:
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.slug == plan_data["slug"])
        )
        if result.scalar_one_or_none():
            continue

        db.add(SubscriptionPlan(
            id=uuid.uuid4(),
            name=plan_data["name"],
            slug=plan_data["slug"],
            description=plan_data.get("description"),
            price_monthly_cents=plan_data.get("price_monthly_cents", 0),
            price_annual_cents=plan_data.get("price_annual_cents", 0),
            currency=plan_data.get("currency", "USD"),
            trial_days=plan_data.get("trial_days", 0),
            max_applications=plan_data.get("max_applications"),
            max_documents=plan_data.get("max_documents"),
            max_messages=plan_data.get("max_messages"),
            max_employees=plan_data.get("max_employees"),
            is_active=plan_data.get("is_active", True),
            is_public=plan_data.get("is_public", True),
            is_featured=plan_data.get("is_featured", False),
            display_order=plan_data.get("display_order", 0),
            highlight_color=plan_data.get("highlight_color"),
            created_by=None,
            modified_by=None,
        ))

    await db.commit()

    # ── Plan Features ─────────────────────────────────────────────────────────
    for feat_data in PLAN_FEATURES_SEED:
        # look up the parent plan
        plan_result = await db.execute(
            select(SubscriptionPlan).where(
                SubscriptionPlan.slug == feat_data["plan_slug"]
            )
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            continue

        db.add(PlanFeature(
            id=uuid.uuid4(),
            plan_id=plan.id,
            feature_text=feat_data["feature_text"],
            is_included=feat_data.get("is_included", True),
            is_highlighted=feat_data.get("is_highlighted", False),
            sort_order=feat_data.get("sort_order", 0),
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ Subscription plans seeded")


# =============================================================================
# seed_fee_templates
# Seeds: fee_templates
# =============================================================================

async def seed_fee_templates(db: AsyncSession):
    for fee_data in FEE_TEMPLATES_SEED:
        result = await db.execute(
            select(FeeTemplate).where(FeeTemplate.code == fee_data["code"])
        )
        if result.scalar_one_or_none():
            continue

        db.add(FeeTemplate(
            id=uuid.uuid4(),
            code=fee_data["code"],
            name=fee_data["name"],
            description=fee_data.get("description"),
            category=fee_data["category"],
            default_amount_usd=fee_data["default_amount_usd"],
            is_government_fee=fee_data.get("is_government_fee", False),
            is_optional=fee_data.get("is_optional", False),
            due_days_after_creation=fee_data.get("due_days_after_creation"),
            sort_order=fee_data.get("sort_order", 0),
            is_active=fee_data.get("is_active", True),
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ Fee templates seeded")


# =============================================================================
# seed_system_settings
# Seeds: system_settings
# =============================================================================

async def seed_system_settings(db: AsyncSession):
    for setting_data in SYSTEM_SETTINGS_SEED:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == setting_data["key"])
        )
        if result.scalar_one_or_none():
            continue

        db.add(SystemSetting(
            id=uuid.uuid4(),
            key=setting_data["key"],
            value=setting_data["value"],
            value_type=setting_data["value_type"],
            setting_group=setting_data["setting_group"],
            label=setting_data["label"],
            description=setting_data.get("description"),
            is_public=setting_data.get("is_public", False),
            is_readonly=setting_data.get("is_readonly", False),
            display_order=setting_data.get("display_order", 0),
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ System settings seeded")


# =============================================================================
# seed_support_articles
# Seeds: support_articles
# Note: created_by is nullable=False in model but we pass None here.
# If your column is NOT NULL, change to a known system user UUID after
# your first admin user is created.
# =============================================================================

async def seed_support_articles(db: AsyncSession):
    for article_data in SUPPORT_ARTICLES_SEED:
        result = await db.execute(
            select(SupportArticle)
            .where(SupportArticle.title == article_data["title"])
            .limit(1)
        )
        # scalars().first() just checks "does at least one exist?" and never
        # raises, even if duplicates are already in the table (unlike
        # scalar_one_or_none(), which crashes the whole app startup on 2+ rows).
        if result.scalars().first():
            continue

        db.add(SupportArticle(
            id=uuid.uuid4(),
            title=article_data["title"],
            summary=article_data.get("summary"),
            body=article_data["body"],
            article_type=article_data.get("article_type", "faq"),
            category=article_data.get("category", "all"),
            tag=article_data.get("tag"),
            sort_order=article_data.get("sort_order", 0),
            is_published=article_data.get("is_published", True),
            is_active=True,
            is_featured=article_data.get("is_featured", False),
            view_count=0,
            helpful_count=0,
            not_helpful_count=0,
            created_by=None,
            modified_by=None,
        ))

    await db.commit()
    print("✅ Support articles seeded")


# async def seed_notification_templates(db: AsyncSession) -> None:
#     """
#     Idempotent — skips already-seeded event_keys.
#     Safe to run on every startup or migration.
#     """
#     for item in NOTIFICATION_TEMPLATES_SEED:
#         exists = (await db.execute(
#             select(NotificationTemplate).where(
#                 NotificationTemplate.event_key == item["event_key"]
#             )
#         )).scalar_one_or_none()
#         if not exists:
#             db.add(NotificationTemplate(**item))
#     await db.commit()
#     print("✅ NotificationTemplate seeded")


from sqlalchemy.dialects.postgresql import insert


async def seed_notification_templates(db: AsyncSession) -> None:
    try:
        if not NOTIFICATION_TEMPLATES_SEED:
            return

        stmt = insert(NotificationTemplate).values(
            NOTIFICATION_TEMPLATES_SEED
        )

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                NotificationTemplate.event_key,
                NotificationTemplate.channel,
            ]
        )

        result = await db.execute(stmt)
        await db.commit()

        logger.info(
            "Notification templates seeded; inserted %s row(s)",
            result.rowcount,
        )

    except Exception:
        await db.rollback()
        logger.exception("Failed to seed notification templates")
        raise



async def seed_document_field_configurations(db: AsyncSession) -> None:
    """Idempotent — skips any (ocr_slug, field_name) pair that already exists."""
    for row in DOCUMENT_FIELD_CONFIG_SEED:
        result = await db.execute(
            select(DocumentFieldConfiguration).where(
                DocumentFieldConfiguration.ocr_slug == row["ocr_slug"],
                DocumentFieldConfiguration.field_name == row["field_name"],
            ).limit(1)
        )
        if result.scalars().first():
            continue
 
        db.add(DocumentFieldConfiguration(
            ocr_slug=row["ocr_slug"],
            field_name=row["field_name"],
            is_mandatory=row["is_mandatory"],
            is_expiry_field=row["is_expiry_field"],
            display_order=row["display_order"],
        ))
 
    await db.commit()
    print("✅ Document field configurations seeded")
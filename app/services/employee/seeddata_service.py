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
    NotificationTemplate,
    Role,
    Permission,
    RolePermission,
    VisaType,
    DocumentType,
    SubscriptionPlan,
    PlanFeature,
    FeeTemplate,
    SystemSetting,
    SupportArticle,
)

from app.models.seeds import (
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
        if result.scalar_one_or_none():
            continue

        db.add(DocumentType(
            id=uuid.uuid4(),
            name=doc_data["name"],
            category=doc_data["category"],
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
            select(SupportArticle).where(
                SupportArticle.title == article_data["title"]
            )
        )
        if result.scalar_one_or_none():
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
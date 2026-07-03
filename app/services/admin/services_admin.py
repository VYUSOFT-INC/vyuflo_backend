# # =============================================================================
# #  services_admin.py — Business Logic for Admin Role
# #  VisaFlow — Admin Role
# #
# #  All DB queries go here. Routers call these functions — never query directly.
# # =============================================================================

# import uuid
# import math
# from datetime import datetime, timezone, timedelta
# from decimal import Decimal
# from typing import Optional, List, Dict, Any, Tuple

# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, update, delete, func, and_, or_, desc, text
# from sqlalchemy.orm import selectinload

# # ── Your EXISTING models (tables 1–37) ────────────────────────────────────────
# from app.models.models import (
#     User, VisaType, SupportTicket, SupportTicketReply,
#     Role, Permission, RolePermission, UserRole, DocumentType
# )

# # ── New admin models (tables 38–53) ───────────────────────────────────────────
# from app.models_admin import (
#     AdminProfile, AdminAuditLog, PlatformSetting,
#     VisaTypeDocumentRule, SubscriptionPlan, OrganizationSubscription,
#     BillingInvoice, NotificationTemplate, BroadcastNotification,
#     FeatureFlag, OnboardingFlow, OnboardingStep, UserOnboardingProgress,
#     PlatformMetricsCache, WorkspaceMember, AdminNotification
# )


# # =============================================================================
# # HELPER — Log Admin Action (call this after every mutating operation)
# # =============================================================================

# async def log_admin_action(
#     db            : AsyncSession,
#     admin_user_id : uuid.UUID,
#     action_type   : str,
#     description   : str,
#     entity_type   : Optional[str] = None,
#     entity_id     : Optional[uuid.UUID] = None,
#     old_value     : Optional[Dict] = None,
#     new_value     : Optional[Dict] = None,
#     ip_address    : Optional[str] = None,
#     severity      : str = "info"
# ) -> AdminAuditLog:
#     log = AdminAuditLog(
#         admin_user_id=admin_user_id,
#         action_type=action_type,
#         entity_type=entity_type,
#         entity_id=entity_id,
#         old_value=old_value,
#         new_value=new_value,
#         description=description,
#         ip_address=ip_address,
#         severity=severity,
#     )
#     db.add(log)
#     await db.flush()
#     return log


# # =============================================================================
# # ADMIN-01 — Dashboard Stats
# # =============================================================================

# async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
#     total_users = (await db.execute(select(func.count(User.id)))).scalar_one()

#     new_signups = (await db.execute(
#         select(func.count(User.id)).where(
#             User.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
#         )
#     )).scalar_one()

#     open_tickets = (await db.execute(
#         select(func.count(SupportTicket.id)).where(
#             SupportTicket.status.in_(["open", "in_progress"])
#         )
#     )).scalar_one()

#     doc_types = (await db.execute(
#         select(func.count(DocumentType.id)).where(DocumentType.is_active == True)
#     )).scalar_one()

#     monthly_rev = (await db.execute(
#         select(func.coalesce(func.sum(BillingInvoice.total_usd), 0)).where(
#             BillingInvoice.status == "paid",
#             BillingInvoice.paid_at >= datetime.now(timezone.utc) - timedelta(days=30)
#         )
#     )).scalar_one()

#     return {
#         "total_users"          : total_users,
#         "active_cases"         : 0,           # join your applications table here
#         "document_types_count" : doc_types,
#         "ai_accuracy_pct"      : 98.7,        # read from platform_metrics_cache
#         "open_tickets"         : open_tickets,
#         "system_uptime_pct"    : 99.98,
#         "monthly_revenue_usd"  : Decimal(str(monthly_rev)),
#         "new_signups_30d"      : new_signups,
#     }


# # =============================================================================
# # ADMIN-02 — User Management (uses existing users table)
# # =============================================================================

# async def list_users(
#     db        : AsyncSession,
#     search    : Optional[str] = None,
#     status    : Optional[str] = None,
#     page      : int = 1,
#     page_size : int = 20,
# ) -> Tuple[List[User], int]:
#     q = select(User)
#     filters = []
#     if search:
#         filters.append(or_(
#             User.email.ilike(f"%{search}%"),
#             User.first_name.ilike(f"%{search}%"),
#             User.last_name.ilike(f"%{search}%"),
#         ))
#     if status == "active":    filters.append(User.is_active == True)
#     if status == "suspended": filters.append(User.is_active == False)
#     if filters: q = q.where(and_(*filters))

#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# async def suspend_user(
#     db             : AsyncSession,
#     target_user_id : uuid.UUID,
#     admin_user_id  : uuid.UUID,
#     reason         : str,
#     ip_address     : Optional[str] = None,
# ) -> User:
#     user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
#     if not user:
#         raise ValueError("User not found")
#     old_status = user.is_active
#     user.is_active = False
#     user.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "user.suspend",
#         f"Suspended user {user.email}: {reason}",
#         entity_type="user", entity_id=target_user_id,
#         old_value={"is_active": old_status}, new_value={"is_active": False, "reason": reason},
#         ip_address=ip_address, severity="warning"
#     )
#     await db.commit()
#     await db.refresh(user)
#     return user


# async def activate_user(
#     db             : AsyncSession,
#     target_user_id : uuid.UUID,
#     admin_user_id  : uuid.UUID,
#     ip_address     : Optional[str] = None,
# ) -> User:
#     user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
#     if not user:
#         raise ValueError("User not found")
#     user.is_active = True
#     user.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "user.activate",
#         f"Activated user {user.email}",
#         entity_type="user", entity_id=target_user_id,
#         old_value={"is_active": False}, new_value={"is_active": True},
#         ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(user)
#     return user


# # =============================================================================
# # ADMIN-03 — Roles & Permissions (uses existing roles/permissions tables)
# # =============================================================================

# async def list_roles(db: AsyncSession) -> List[Role]:
#     return (await db.execute(
#         select(Role).options(selectinload(Role.role_permissions))
#         .order_by(Role.name)
#     )).scalars().all()


# async def list_permissions(db: AsyncSession) -> List[Permission]:
#     return (await db.execute(
#         select(Permission).order_by(Permission.module, Permission.code)
#     )).scalars().all()


# async def assign_user_role(
#     db            : AsyncSession,
#     user_id       : uuid.UUID,
#     role_id       : uuid.UUID,
#     assigned_by   : uuid.UUID,
# ) -> None:
#     exists = (await db.execute(
#         select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
#     )).scalar_one_or_none()
#     if not exists:
#         db.add(UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by))
#         await db.commit()


# async def remove_user_role(db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
#     await db.execute(
#         delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
#     )
#     await db.commit()


# # =============================================================================
# # ADMIN-04 — System Settings
# # =============================================================================

# async def get_all_settings(db: AsyncSession, category: Optional[str] = None) -> List[PlatformSetting]:
#     q = select(PlatformSetting)
#     if category:
#         q = q.where(PlatformSetting.category == category)
#     return (await db.execute(q.order_by(PlatformSetting.category, PlatformSetting.setting_key))).scalars().all()


# async def update_setting(
#     db            : AsyncSession,
#     key           : str,
#     value         : str,
#     updated_by    : uuid.UUID,
#     admin_user_id : uuid.UUID,
#     ip_address    : Optional[str] = None,
# ) -> PlatformSetting:
#     setting = (await db.execute(
#         select(PlatformSetting).where(PlatformSetting.setting_key == key)
#     )).scalar_one_or_none()
#     if not setting:
#         raise ValueError(f"Setting '{key}' not found")
#     old_val = setting.setting_value
#     setting.setting_value = value
#     setting.updated_by = updated_by
#     setting.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "settings.update",
#         f"Setting '{key}' changed from '{old_val}' → '{value}'",
#         entity_type="platform_setting", ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(setting)
#     return setting


# async def list_feature_flags(db: AsyncSession) -> List[FeatureFlag]:
#     return (await db.execute(select(FeatureFlag).order_by(FeatureFlag.flag_key))).scalars().all()


# async def toggle_feature_flag(
#     db            : AsyncSession,
#     flag_key      : str,
#     admin_user_id : uuid.UUID,
#     ip_address    : Optional[str] = None,
# ) -> FeatureFlag:
#     flag = (await db.execute(
#         select(FeatureFlag).where(FeatureFlag.flag_key == flag_key)
#     )).scalar_one_or_none()
#     if not flag:
#         raise ValueError(f"Feature flag '{flag_key}' not found")
#     old_state = flag.is_enabled
#     flag.is_enabled = not flag.is_enabled
#     flag.updated_by = admin_user_id
#     flag.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "feature_flag.toggle",
#         f"Flag '{flag_key}' toggled {'ON' if flag.is_enabled else 'OFF'}",
#         entity_type="feature_flag",
#         old_value={"is_enabled": old_state}, new_value={"is_enabled": flag.is_enabled},
#         ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(flag)
#     return flag


# # =============================================================================
# # ADMIN-05 — Notification Templates + Broadcasts
# # =============================================================================

# async def list_templates(db: AsyncSession, channel: Optional[str] = None) -> List[NotificationTemplate]:
#     q = select(NotificationTemplate)
#     if channel:
#         q = q.where(NotificationTemplate.channel == channel)
#     return (await db.execute(q.order_by(NotificationTemplate.name))).scalars().all()


# async def upsert_template(
#     db           : AsyncSession,
#     template_key : str,
#     data         : Dict,
#     updated_by   : uuid.UUID,
# ) -> NotificationTemplate:
#     tmpl = (await db.execute(
#         select(NotificationTemplate).where(NotificationTemplate.template_key == template_key)
#     )).scalar_one_or_none()
#     if tmpl:
#         for k, v in data.items():
#             setattr(tmpl, k, v)
#         tmpl.updated_by = updated_by
#         tmpl.updated_at = datetime.now(timezone.utc)
#     else:
#         tmpl = NotificationTemplate(template_key=template_key, updated_by=updated_by, **data)
#         db.add(tmpl)
#     await db.commit()
#     await db.refresh(tmpl)
#     return tmpl


# async def send_broadcast(
#     db                : AsyncSession,
#     title             : str,
#     message           : str,
#     notification_type : str,
#     target_audience   : str,
#     channels          : List[str],
#     sent_by           : uuid.UUID,
#     scheduled_at      : Optional[datetime] = None,
#     target_plan_id    : Optional[uuid.UUID] = None,
#     ip_address        : Optional[str] = None,
# ) -> BroadcastNotification:
#     recipient_count = (await db.execute(
#         select(func.count(User.id)).where(User.is_active == True)
#     )).scalar_one()

#     broadcast = BroadcastNotification(
#         title=title, message=message, notification_type=notification_type,
#         target_audience=target_audience, channels=channels, sent_by=sent_by,
#         scheduled_at=scheduled_at, target_plan_id=target_plan_id,
#         total_recipients=recipient_count,
#         sent_at=datetime.now(timezone.utc) if not scheduled_at else None,
#     )
#     db.add(broadcast)
#     await log_admin_action(
#         db, sent_by, "broadcast.send",
#         f"Broadcast '{title}' sent to {recipient_count} {target_audience}",
#         ip_address=ip_address,
#         severity="warning" if notification_type in ("critical", "maintenance") else "info"
#     )
#     await db.commit()
#     await db.refresh(broadcast)
#     return broadcast


# # =============================================================================
# # ADMIN-06 — Visa Types Manager (extends existing visa_types table)
# # =============================================================================

# async def list_visa_types_admin(db: AsyncSession, active_only: bool = False) -> List[VisaType]:
#     q = select(VisaType).options(selectinload(VisaType.document_rules))
#     if active_only:
#         q = q.where(VisaType.is_active == True)
#     return (await db.execute(q.order_by(VisaType.display_order, VisaType.code))).scalars().all()


# async def update_visa_type(
#     db            : AsyncSession,
#     visa_type_id  : uuid.UUID,
#     data          : Dict,
#     admin_user_id : uuid.UUID,
#     ip_address    : Optional[str] = None,
# ) -> VisaType:
#     vt = (await db.execute(
#         select(VisaType).where(VisaType.id == visa_type_id)
#     )).scalar_one_or_none()
#     if not vt:
#         raise ValueError("Visa type not found")
#     old_data = {k: getattr(vt, k, None) for k in data}
#     for k, v in data.items():
#         if v is not None:
#             setattr(vt, k, v)
#     vt.modified_by = admin_user_id
#     vt.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "visa_type.update",
#         f"Updated visa type {vt.code}",
#         entity_type="visa_type", entity_id=visa_type_id,
#         old_value=old_data, new_value=data, ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(vt)
#     return vt


# async def add_document_rule(
#     db         : AsyncSession,
#     data       : Dict,
#     created_by : uuid.UUID,
# ) -> VisaTypeDocumentRule:
#     rule = VisaTypeDocumentRule(**data, created_by=created_by)
#     db.add(rule)
#     await db.commit()
#     await db.refresh(rule)
#     return rule


# async def update_document_rule(
#     db      : AsyncSession,
#     rule_id : uuid.UUID,
#     data    : Dict,
# ) -> VisaTypeDocumentRule:
#     rule = (await db.execute(
#         select(VisaTypeDocumentRule).where(VisaTypeDocumentRule.id == rule_id)
#     )).scalar_one_or_none()
#     if not rule:
#         raise ValueError("Document rule not found")
#     for k, v in data.items():
#         if v is not None:
#             setattr(rule, k, v)
#     rule.updated_at = datetime.now(timezone.utc)
#     await db.commit()
#     await db.refresh(rule)
#     return rule


# async def delete_document_rule(db: AsyncSession, rule_id: uuid.UUID) -> None:
#     await db.execute(delete(VisaTypeDocumentRule).where(VisaTypeDocumentRule.id == rule_id))
#     await db.commit()


# # =============================================================================
# # ADMIN-07 — Subscription & Pricing
# # =============================================================================

# async def list_plans(db: AsyncSession) -> List[SubscriptionPlan]:
#     return (await db.execute(
#         select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order)
#     )).scalars().all()


# async def create_plan(db: AsyncSession, data: Dict, created_by: uuid.UUID) -> SubscriptionPlan:
#     plan = SubscriptionPlan(**data, updated_by=created_by)
#     db.add(plan)
#     await db.commit()
#     await db.refresh(plan)
#     return plan


# async def update_plan(
#     db            : AsyncSession,
#     plan_id       : uuid.UUID,
#     data          : Dict,
#     admin_user_id : uuid.UUID,
#     ip_address    : Optional[str] = None,
# ) -> SubscriptionPlan:
#     plan = (await db.execute(
#         select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
#     )).scalar_one_or_none()
#     if not plan:
#         raise ValueError("Plan not found")
#     old_price = float(plan.price_monthly_usd)
#     for k, v in data.items():
#         setattr(plan, k, v)
#     plan.updated_by = admin_user_id
#     plan.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "subscription_plan.update",
#         f"Updated plan '{plan.name}'",
#         entity_type="subscription_plan", entity_id=plan_id,
#         old_value={"price_monthly_usd": old_price}, new_value=data,
#         ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(plan)
#     return plan


# async def list_subscriptions(
#     db        : AsyncSession,
#     status    : Optional[str] = None,
#     page      : int = 1,
#     page_size : int = 20,
# ) -> Tuple[List[OrganizationSubscription], int]:
#     q = select(OrganizationSubscription).options(selectinload(OrganizationSubscription.plan))
#     if status:
#         q = q.where(OrganizationSubscription.status == status)
#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(desc(OrganizationSubscription.created_at))
#         .offset((page - 1) * page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# # =============================================================================
# # ADMIN-08 — Revenue Dashboard
# # =============================================================================

# async def get_revenue_metrics(db: AsyncSession) -> Dict[str, Any]:
#     total_rev = (await db.execute(
#         select(func.coalesce(func.sum(BillingInvoice.total_usd), 0))
#         .where(BillingInvoice.status == "paid")
#     )).scalar_one()

#     monthly_rev = (await db.execute(
#         select(func.coalesce(func.sum(BillingInvoice.total_usd), 0))
#         .where(
#             BillingInvoice.status == "paid",
#             BillingInvoice.paid_at >= datetime.now(timezone.utc) - timedelta(days=30)
#         )
#     )).scalar_one()

#     active_subs = (await db.execute(
#         select(func.count(OrganizationSubscription.id))
#         .where(OrganizationSubscription.status.in_(["active", "trialing"]))
#     )).scalar_one()

#     mrr = Decimal(str(monthly_rev))
#     return {
#         "total_revenue_usd"    : Decimal(str(total_rev)),
#         "monthly_revenue_usd"  : mrr,
#         "active_subscriptions" : active_subs,
#         "mrr_usd"              : mrr,
#         "arr_usd"              : mrr * 12,
#         "revenue_by_plan"      : [],   # extend with GROUP BY plan_id query
#         "revenue_by_month"     : [],   # extend with DATE_TRUNC('month') query
#     }


# async def list_invoices(
#     db        : AsyncSession,
#     status    : Optional[str] = None,
#     page      : int = 1,
#     page_size : int = 20,
# ) -> Tuple[List[BillingInvoice], int]:
#     q = select(BillingInvoice)
#     if status:
#         q = q.where(BillingInvoice.status == status)
#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(desc(BillingInvoice.created_at)).offset((page-1)*page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# # =============================================================================
# # ADMIN-09 — Audit Logs
# # =============================================================================

# async def get_audit_logs(
#     db            : AsyncSession,
#     action_type   : Optional[str] = None,
#     entity_type   : Optional[str] = None,
#     severity      : Optional[str] = None,
#     admin_user_id : Optional[uuid.UUID] = None,
#     date_from     : Optional[datetime] = None,
#     date_to       : Optional[datetime] = None,
#     search        : Optional[str] = None,
#     page          : int = 1,
#     page_size     : int = 20,
# ) -> Tuple[List[AdminAuditLog], int]:
#     q = select(AdminAuditLog)
#     filters = []
#     if action_type:   filters.append(AdminAuditLog.action_type.ilike(f"%{action_type}%"))
#     if entity_type:   filters.append(AdminAuditLog.entity_type == entity_type)
#     if severity:      filters.append(AdminAuditLog.severity == severity)
#     if admin_user_id: filters.append(AdminAuditLog.admin_user_id == admin_user_id)
#     if date_from:     filters.append(AdminAuditLog.created_at >= date_from)
#     if date_to:       filters.append(AdminAuditLog.created_at <= date_to)
#     if search:
#         filters.append(AdminAuditLog.description.ilike(f"%{search}%"))
#     if filters:
#         q = q.where(and_(*filters))
#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(desc(AdminAuditLog.created_at)).offset((page-1)*page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# # =============================================================================
# # ADMIN-10 — Workspace Dashboard
# # =============================================================================

# async def list_workspace_members(
#     db        : AsyncSession,
#     owner_id  : uuid.UUID,
#     page      : int = 1,
#     page_size : int = 20,
# ) -> Tuple[List[WorkspaceMember], int]:
#     q = select(WorkspaceMember).where(
#         WorkspaceMember.owner_id == owner_id,
#         WorkspaceMember.is_active == True
#     )
#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(WorkspaceMember.joined_at).offset((page-1)*page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# async def add_workspace_member(
#     db         : AsyncSession,
#     owner_id   : uuid.UUID,
#     member_id  : uuid.UUID,
#     job_title  : Optional[str],
#     department : Optional[str],
#     invited_by : uuid.UUID,
# ) -> WorkspaceMember:
#     wm = WorkspaceMember(
#         owner_id=owner_id, member_id=member_id,
#         job_title=job_title, department=department, invited_by=invited_by
#     )
#     db.add(wm)
#     await db.commit()
#     await db.refresh(wm)
#     return wm


# # =============================================================================
# # ADMIN-11 — Onboarding Flow Manager
# # =============================================================================

# async def list_flows(db: AsyncSession) -> List[OnboardingFlow]:
#     return (await db.execute(
#         select(OnboardingFlow).options(selectinload(OnboardingFlow.steps))
#         .order_by(OnboardingFlow.target_role, OnboardingFlow.name)
#     )).scalars().all()


# async def create_flow(db: AsyncSession, data: Dict, created_by: uuid.UUID) -> OnboardingFlow:
#     flow = OnboardingFlow(**data, created_by=created_by, updated_by=created_by)
#     db.add(flow)
#     await db.commit()
#     await db.refresh(flow)
#     return flow


# async def add_flow_step(db: AsyncSession, data: Dict) -> OnboardingStep:
#     step = OnboardingStep(**data)
#     db.add(step)
#     await db.execute(
#         update(OnboardingFlow)
#         .where(OnboardingFlow.id == data["flow_id"])
#         .values(total_steps=OnboardingFlow.total_steps + 1,
#                 updated_at=datetime.now(timezone.utc))
#     )
#     await db.commit()
#     await db.refresh(step)
#     return step


# # =============================================================================
# # ADMIN-12 — Support Tickets (admin view of existing support_tickets table)
# # =============================================================================

# async def list_tickets(
#     db          : AsyncSession,
#     status      : Optional[str] = None,
#     priority    : Optional[str] = None,
#     assigned_to : Optional[uuid.UUID] = None,
#     page        : int = 1,
#     page_size   : int = 20,
# ) -> Tuple[List[SupportTicket], int]:
#     q = select(SupportTicket)
#     filters = []
#     if status:      filters.append(SupportTicket.status == status)
#     if priority:    filters.append(SupportTicket.priority == priority)
#     if assigned_to: filters.append(SupportTicket.assigned_to == assigned_to)
#     if filters:     q = q.where(and_(*filters))
#     total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
#     rows  = (await db.execute(
#         q.order_by(desc(SupportTicket.created_at)).offset((page-1)*page_size).limit(page_size)
#     )).scalars().all()
#     return rows, total


# async def get_ticket_with_replies(
#     db        : AsyncSession,
#     ticket_id : uuid.UUID,
# ) -> Optional[SupportTicket]:
#     return (await db.execute(
#         select(SupportTicket).options(selectinload(SupportTicket.replies))
#         .where(SupportTicket.id == ticket_id)
#     )).scalar_one_or_none()


# async def update_ticket(
#     db            : AsyncSession,
#     ticket_id     : uuid.UUID,
#     data          : Dict,
#     admin_user_id : uuid.UUID,
#     ip_address    : Optional[str] = None,
# ) -> SupportTicket:
#     ticket = (await db.execute(
#         select(SupportTicket).where(SupportTicket.id == ticket_id)
#     )).scalar_one_or_none()
#     if not ticket:
#         raise ValueError("Ticket not found")
#     for k, v in data.items():
#         if v is not None:
#             setattr(ticket, k, v)
#     if data.get("status") == "resolved" and not ticket.resolved_at:
#         ticket.resolved_at = datetime.now(timezone.utc)
#     if data.get("status") == "closed" and not ticket.closed_at:
#         ticket.closed_at = datetime.now(timezone.utc)
#     ticket.updated_at = datetime.now(timezone.utc)
#     await log_admin_action(
#         db, admin_user_id, "support_ticket.update",
#         f"Updated ticket {ticket.ticket_number}",
#         entity_type="support_ticket", entity_id=ticket_id,
#         new_value=data, ip_address=ip_address
#     )
#     await db.commit()
#     await db.refresh(ticket)
#     return ticket


# async def add_ticket_reply(
#     db            : AsyncSession,
#     ticket_id     : uuid.UUID,
#     sender_id     : uuid.UUID,
#     body          : str,
#     is_internal   : bool = False,
# ) -> SupportTicketReply:
#     """Uses your EXISTING SupportTicketReply model — no new table needed."""
#     reply = SupportTicketReply(
#         ticket_id=ticket_id,
#         sender_id=sender_id,
#         sender_type="agent",   # admin is always 'agent' sender_type
#         body=body,
#         created_by=sender_id,
#     )
#     db.add(reply)
#     # Set first_response_at if this is the first admin reply
#     ticket = (await db.execute(
#         select(SupportTicket).where(SupportTicket.id == ticket_id)
#     )).scalar_one_or_none()
#     if ticket and not ticket.first_response_at:
#         ticket.first_response_at = datetime.now(timezone.utc)
#         if ticket.status == "open":
#             ticket.status = "in_progress"
#     await db.commit()
#     await db.refresh(reply)
#     return reply

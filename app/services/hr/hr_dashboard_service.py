# app/services/hr/hr_dashboard_service.py
#
# Assembles the HR Compliance Dashboard payload.
#
# SCOPING: every query below filters to Application.assigned_hr_id ==
# hr_user_id, matching the same scoping hr_case_service.py already uses for
# hr_list_cases(). If your HR users are meant to see ALL company cases
# rather than only ones explicitly assigned to them, swap this for a join
# through EmployerEmployee.employer_id instead — see the ASSUMPTION notes
# below for exactly where that would change.
#
# ASSUMPTIONS FLAGGED (no confirmed data source for these — approximated
# from what actually exists on Application/EmployerEmployee/Document):
#   1. "Visa expiry date" — there's no dedicated visa-expiry field anywhere
#      I've seen (Application only has due_date, a case-submission target,
#      not a visa validity expiry). Using Application.due_date as the proxy.
#      Replace with a real expiry field once one exists (e.g. on a
#      UserVisaTarget or dedicated Visa record).
#   2. "Employee code" (e.g. EMP-0041) — no such field exists on User or
#      EmployerEmployee. Synthesized from the user id, same pattern
#      _generate_application_number() uses elsewhere in this codebase.
#   3. Quarter-over-quarter deltas — no historical snapshot table exists,
#      so these are computed live: this calendar quarter's count vs the
#      previous quarter's, by created_at. Recomputes on every request
#      rather than reading a stored trend.
#   4. "Industry benchmark" processing days — no external benchmark data
#      source exists in this app. Using a static reference table; avg_days
#      is real (computed from your own approved cases).
#   5. "Pending renewals" / per-row status+action — no renewal-tracking
#      table exists. Derived heuristically from days-to-due-date and
#      whether the case's documents are all verified yet.

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.visamodels import (
    Application,
    ApplicationStatusHistory,
    Document,
    DocumentType,
    EmployerEmployee,
    User,
    VisaType,
)
from app.schemas.hr.hr_dashboard import (
    HRActivityItem,
    HRCasesByStage,
    HRComplianceScore,
    HRDashboardResponse,
    HRDashboardStats,
    HRDepartmentCompliance,
    HRDocumentCompletion,
    HRExpiringVisa,
    HRMonthlyTrend,
    HRProcessingTime,
    HRTimelineBucket,
    HRVisaDistribution,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE_STAGE_LABELS: dict[str, str] = {
    "profile_eligibility": "Profile & Eligibility",
    "documentation":       "Document Collection",
    "lca_filing":          "LCA Filing",
    "uscis_submission":    "USCIS Submission",
}

# ASSUMPTION #4 — no real industry-benchmark data source exists. These are
# rough, static reference values; replace with a real source if one becomes
# available (DOL/USCIS published averages, a paid data feed, etc).
INDUSTRY_BENCHMARK_DAYS: dict[str, int] = {
    "H-1B": 165, "L-1": 110, "O-1": 130, "TN": 50, "E-3": 75,
}

ACTIVE_STATUSES = ("in_progress", "action_needed", "rfe_response", "submitted", "approved")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt) -> str:
    if dt is None:
        return _now().isoformat()
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
    return dt.isoformat() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).isoformat()


def _days_between(target, ref: datetime | None = None) -> int:
    ref = ref or _now()
    if isinstance(target, date) and not isinstance(target, datetime):
        target = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return (target - ref).days


def _employee_code(user_id: uuid.UUID) -> str:
    """ASSUMPTION #2 — no real employee-code field exists; synthesized."""
    return f"EMP-{str(user_id).replace('-', '')[:4].upper()}"


def _pct_delta(current: int, previous: int) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round(((current - previous) / previous) * 100, 1)


def _quarter_bounds(offset: int = 0) -> tuple[datetime, datetime]:
    """Start/end of the current calendar quarter, or `offset` quarters back."""
    now = _now()
    q = (now.month - 1) // 3 - offset
    year = now.year + (q // 4)
    q = q % 4
    start_month = q * 3 + 1
    start = datetime(year, start_month, 1, tzinfo=timezone.utc)
    end_month = start_month + 3
    end_year = year + (1 if end_month > 12 else 0)
    end_month = end_month - 12 if end_month > 12 else end_month
    end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)
    return start, end


def _urgency_for(days_left: int) -> str:
    if days_left <= 30:
        return "critical"
    if days_left <= 90:
        return "warning"
    return "upcoming"


def _row_status_and_action(days_left: int, all_docs_verified: bool) -> tuple[str, str]:
    """ASSUMPTION #5 — heuristic, no dedicated renewal-tracking table."""
    if days_left <= 0:
        return "renewal_pending", "renew"
    if days_left <= 30:
        return ("in_progress" if all_docs_verified else "docs_needed"), "renew"
    if days_left <= 90:
        return "in_progress", "review"
    return "active", "monitor"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────────────────────────────────────

async def service_get_hr_dashboard(
    db: AsyncSession,
    hr_user_id: uuid.UUID,
) -> HRDashboardResponse:

    # ── 1. This HR user's roster (EmployerEmployee) ───────────────────────────
    emp_result = await db.execute(
        select(EmployerEmployee).where(
            EmployerEmployee.employer_id == hr_user_id,
            EmployerEmployee.is_active == True,  # noqa: E712
        )
    )
    roster = emp_result.scalars().all()
    total_employees = len(roster)
    dept_by_employee_user_id = {r.employee_id: (r.department or "Unassigned") for r in roster}
    # FIXED — /employer/employees/:id (and its detail endpoint) expects
    # EmployerEmployee.id, matching the convention used everywhere else in
    # this app (see createCaseApi.getEmployees(): id = e.id, the roster
    # link row, while e.employee_id/users.id is never sent to the frontend).
    # This was previously keyed on User.id, causing the 400 you hit when
    # clicking into an expiring-visa row.
    emp_link_id_by_user_id = {r.employee_id: r.id for r in roster}

    prev_q_start, _ = _quarter_bounds(offset=1)
    cur_q_start, _  = _quarter_bounds(offset=0)
    employees_prev_q = sum(1 for r in roster if getattr(r, "created_at", None) and r.created_at < cur_q_start)

    # ── 2. This HR user's cases (Application.assigned_hr_id) ─────────────────
    apps_result = await db.execute(
        select(Application)
        .options(joinedload(Application.visa_type))
        .where(Application.assigned_hr_id == hr_user_id)
    )
    apps = apps_result.unique().scalars().all()

    active_apps      = [a for a in apps if a.status in ACTIVE_STATUSES]
    prev_q_active     = [a for a in active_apps if a.created_at and a.created_at < cur_q_start]

    # ── 3. Documents across this HR's cases (for compliance/completion) ──────
    app_ids = [a.id for a in apps]
    all_docs = []
    if app_ids:
        docs_result = await db.execute(
            select(Document)
            .options(joinedload(Document.document_type))
            .where(Document.application_id.in_(app_ids))
        )
        all_docs = docs_result.unique().scalars().all()
    docs_by_app: dict[uuid.UUID, list] = {}
    for d in all_docs:
        docs_by_app.setdefault(d.application_id, []).append(d)

    # ── 4. Expiring visas list (ASSUMPTION #1 — due_date as expiry proxy) ────
    expiring: list[HRExpiringVisa] = []
    for a in active_apps:
        if not a.due_date:
            continue
        days_left = _days_between(a.due_date)
        if days_left > 180:
            continue  # out of the "expiring soon" window entirely

        user_result = await db.execute(select(User).where(User.id == a.user_id))
        user = user_result.scalars().first()
        if not user:
            continue

        app_docs = docs_by_app.get(a.id, [])
        all_verified = bool(app_docs) and all(d.status == "verified" for d in app_docs)
        status, action = _row_status_and_action(days_left, all_verified)

        expiring.append(HRExpiringVisa(
            id=str(a.id),
            employee_id=str(emp_link_id_by_user_id.get(user.id, user.id)),
            employee_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            employee_code=_employee_code(user.id),
            department=dept_by_employee_user_id.get(user.id),
            visa_code=a.visa_type.code if a.visa_type else "—",
            visa_label=a.visa_type.name if a.visa_type else None,
            expiry_date=_iso(a.due_date),
            days_left=days_left,
            urgency=_urgency_for(days_left),
            status=status,
            action=action,
        ))
    expiring.sort(key=lambda e: e.days_left)

    expiring_soon    = sum(1 for e in expiring if e.urgency in ("critical", "warning"))
    prev_q_expiring  = sum(
        1 for a in active_apps
        if a.due_date and a.created_at and a.created_at < cur_q_start
        and 0 < _days_between(a.due_date, prev_q_start) <= 90
    )
    pending_renewals = sum(1 for e in expiring if e.status in ("renewal_pending", "docs_needed", "in_progress"))

    # ── 5. Stats block ────────────────────────────────────────────────────────
    stats = HRDashboardStats(
        total_employees=total_employees,
        active_visas=len(active_apps),
        expiring_soon=expiring_soon,
        pending_renewals=pending_renewals,
        total_employees_delta=_pct_delta(total_employees, employees_prev_q),
        active_visas_delta=_pct_delta(len(active_apps), len(prev_q_active)),
        expiring_soon_delta=_pct_delta(expiring_soon, prev_q_expiring),
        pending_renewals_delta=0.0,  # no historical snapshot to diff against
    )

    # ── 6. Compliance score ───────────────────────────────────────────────────
    expiring_under_30 = sum(1 for e in expiring if e.days_left <= 30)
    expiring_30_90    = sum(1 for e in expiring if 30 < e.days_left <= 90)
    active_compliant  = len(active_apps) - expiring_under_30 - expiring_30_90
    score = round((active_compliant / len(active_apps)) * 100) if active_apps else 100
    compliance = HRComplianceScore(
        score=score,
        label="Good Standing" if score >= 80 else "Needs Attention" if score >= 60 else "At Risk",
        period=_now().strftime("%b %Y").upper(),
        needs_action_count=expiring_under_30 + expiring_30_90,
        active_compliant=max(active_compliant, 0),
        expiring_under_30=expiring_under_30,
        expiring_30_90=expiring_30_90,
    )

    # ── 7. Activity feed — from ApplicationStatusHistory across HR's cases ────
    activity: list[HRActivityItem] = []
    if app_ids:
        hist_result = await db.execute(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id.in_(app_ids))
            .order_by(ApplicationStatusHistory.created_at.desc())
            .limit(10)
        )
        for h in hist_result.scalars().all():
            type_map = {"approved": "visa_approved", "rejected": "application_rejected"}
            activity.append(HRActivityItem(
                id=str(h.id),
                type=type_map.get(h.status, "renewal_initiated"),
                title=f"Status: {(h.status or '').replace('_', ' ').title()}",
                description=h.note or f"Stage: {(h.stage or 'unknown').replace('_', ' ')}",
                created_at=_iso(h.created_at),
            ))

    # ── 8. Expiration timeline — next 6 months, bucketed by due_date ─────────
    timeline: list[HRTimelineBucket] = []
    now = _now()
    for i in range(6):
        month_start = datetime(now.year + (now.month - 1 + i) // 12, (now.month - 1 + i) % 12 + 1, 1, tzinfo=timezone.utc)
        month_end   = datetime(now.year + (now.month + i) // 12, (now.month + i) % 12 + 1, 1, tzinfo=timezone.utc)
        bucket_apps = [a for a in active_apps if a.due_date and month_start.date() <= a.due_date < month_end.date()]
        timeline.append(HRTimelineBucket(
            month=month_start.strftime("%b %Y"),
            critical=sum(1 for a in bucket_apps if _days_between(a.due_date) <= 30),
            warning=sum(1 for a in bucket_apps if 30 < _days_between(a.due_date) <= 90),
            upcoming=sum(1 for a in bucket_apps if _days_between(a.due_date) > 90),
        ))

    # ── 9. Visa type distribution ──────────────────────────────────────────────
    visa_counts: dict[str, int] = {}
    for a in active_apps:
        code = a.visa_type.code if a.visa_type else "Other"
        visa_counts[code] = visa_counts.get(code, 0) + 1
    total_active = len(active_apps) or 1
    visa_distribution = [
        HRVisaDistribution(visa_code=code, count=count, percentage=round(count / total_active * 100, 1))
        for code, count in sorted(visa_counts.items(), key=lambda x: -x[1])
    ]

    # ── 10. Cases by stage ──────────────────────────────────────────────────────
    stage_counts: dict[str, int] = {}
    for a in apps:
        label = PIPELINE_STAGE_LABELS.get(a.current_stage or "", "Other")
        stage_counts[label] = stage_counts.get(label, 0) + 1
    stage_counts["Approved"] = sum(1 for a in apps if a.status == "approved")
    cases_by_stage = [HRCasesByStage(stage=s, count=c) for s, c in stage_counts.items() if c > 0]

    # ── 11. Monthly trend — filed / approved / rejected, last 6 months ────────
    monthly_trend: list[HRMonthlyTrend] = []
    for i in range(5, -1, -1):
        m_start = datetime(now.year + (now.month - 1 - i) // 12, (now.month - 1 - i) % 12 + 1, 1, tzinfo=timezone.utc)
        m_end_month = m_start.month + 1
        m_end = datetime(m_start.year + (1 if m_end_month > 12 else 0), m_end_month - 12 if m_end_month > 12 else m_end_month, 1, tzinfo=timezone.utc)
        m_apps = [a for a in apps if a.created_at and m_start <= a.created_at.replace(tzinfo=timezone.utc) < m_end]
        monthly_trend.append(HRMonthlyTrend(
            month=m_start.strftime("%b %Y"),
            filed=len(m_apps),
            approved=sum(1 for a in m_apps if a.status == "approved"),
            rejected=sum(1 for a in m_apps if a.status == "rejected"),
        ))

    # ── 12. Department compliance ─────────────────────────────────────────────
    dept_totals: dict[str, int] = {}
    dept_compliant: dict[str, int] = {}
    active_by_user = {a.user_id: a for a in active_apps}
    for r in roster:
        dept = r.department or "Unassigned"
        dept_totals[dept] = dept_totals.get(dept, 0) + 1
        app = active_by_user.get(r.employee_id)
        is_compliant = (not app) or (app.due_date is None) or (_days_between(app.due_date) > 30)
        if is_compliant:
            dept_compliant[dept] = dept_compliant.get(dept, 0) + 1
    department_compliance = [
        HRDepartmentCompliance(
            department=dept,
            compliance_rate=round((dept_compliant.get(dept, 0) / total) * 100) if total else 100,
            total_employees=total,
        )
        for dept, total in dept_totals.items()
    ]

    # ── 13. Processing time — real avg from approved cases, static benchmark ──
    processing_time: list[HRProcessingTime] = []
    for code in visa_counts.keys():
        approved_this_code = [
            a for a in apps
            if a.status == "approved" and a.visa_type and a.visa_type.code == code
            and a.submission_date and a.created_at
        ]
        if approved_this_code:
            avg_days = round(sum(
                (a.submission_date.replace(tzinfo=timezone.utc) - a.created_at.replace(tzinfo=timezone.utc)).days
                for a in approved_this_code
            ) / len(approved_this_code))
        else:
            avg_days = INDUSTRY_BENCHMARK_DAYS.get(code, 90)  # no completed cases yet — fall back to benchmark
        processing_time.append(HRProcessingTime(
            visa_code=code,
            avg_days=avg_days,
            benchmark_days=INDUSTRY_BENCHMARK_DAYS.get(code, 90),
        ))

    # ── 14. Document completion by category ───────────────────────────────────
    cat_totals: dict[str, int] = {}
    cat_completed: dict[str, int] = {}
    for d in all_docs:
        cat = (d.document_type.category.title() if d.document_type and d.document_type.category else "Other")
        cat_totals[cat] = cat_totals.get(cat, 0) + 1
        if d.status == "verified":
            cat_completed[cat] = cat_completed.get(cat, 0) + 1
    document_completion = [
        HRDocumentCompletion(
            category=cat,
            completed=cat_completed.get(cat, 0),
            total=total,
            percentage=round((cat_completed.get(cat, 0) / total) * 100) if total else 0,
        )
        for cat, total in cat_totals.items()
    ]

    return HRDashboardResponse(
        stats=stats,
        compliance=compliance,
        expiring=expiring[:20],
        activity=activity,
        timeline=timeline,
        visa_distribution=visa_distribution,
        cases_by_stage=cases_by_stage,
        monthly_trend=monthly_trend,
        department_compliance=department_compliance,
        processing_time=processing_time,
        document_completion=document_completion,
    )
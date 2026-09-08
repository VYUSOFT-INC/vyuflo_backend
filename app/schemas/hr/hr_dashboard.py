# app/schemas/hr/hr_dashboard.py
#
# HR Compliance Dashboard response models — mirrors
# src/types/hr/dashboard.types.ts field-for-field so the frontend types
# and this schema never drift silently.

from typing import Optional
from pydantic import BaseModel


# ── Expiring visas ────────────────────────────────────────────────────────────

class HRExpiringVisa(BaseModel):
    id:            str
    employee_id:   str
    employee_name: str
    employee_code: str
    avatar_url:    Optional[str] = None
    department:    Optional[str] = None
    visa_code:     str
    visa_label:    Optional[str] = None
    expiry_date:   str
    days_left:     int
    urgency:       str   # "critical" | "warning" | "upcoming"
    status:        str   # "renewal_pending" | "docs_needed" | "in_progress" | "active"
    action:        str   # "renew" | "review" | "monitor"


# ── Stat cards ────────────────────────────────────────────────────────────────

class HRDashboardStats(BaseModel):
    total_employees:  int
    active_visas:     int
    expiring_soon:    int
    pending_renewals: int
    total_employees_delta:  Optional[float] = None
    active_visas_delta:     Optional[float] = None
    expiring_soon_delta:    Optional[float] = None
    pending_renewals_delta: Optional[float] = None


# ── Compliance score ──────────────────────────────────────────────────────────

class HRComplianceScore(BaseModel):
    score:              int
    label:              str
    period:             Optional[str] = None
    needs_action_count: int
    active_compliant:   int
    expiring_under_30:  int
    expiring_30_90:     int


# ── Recent activity feed ──────────────────────────────────────────────────────

class HRActivityItem(BaseModel):
    id:          str
    type:        str
    title:       str
    description: str
    created_at:  str


# ── Expiration timeline (stacked bars) ───────────────────────────────────────

class HRTimelineBucket(BaseModel):
    month:    str
    critical: int
    warning:  int
    upcoming: int


# ── Chart data ────────────────────────────────────────────────────────────────

class HRVisaDistribution(BaseModel):
    visa_code:  str
    count:      int
    percentage: float


class HRCasesByStage(BaseModel):
    stage: str
    count: int


class HRMonthlyTrend(BaseModel):
    month:    str
    filed:    int
    approved: int
    rejected: int


class HRDepartmentCompliance(BaseModel):
    department:      str
    compliance_rate: int
    total_employees: int


class HRProcessingTime(BaseModel):
    visa_code:      str
    avg_days:       int
    benchmark_days: int


class HRDocumentCompletion(BaseModel):
    category:   str
    completed:  int
    total:      int
    percentage: int


# ── Aggregate response ────────────────────────────────────────────────────────

class HRDashboardResponse(BaseModel):
    stats:      HRDashboardStats
    compliance: HRComplianceScore
    expiring:   list[HRExpiringVisa]
    activity:   list[HRActivityItem]
    timeline:   list[HRTimelineBucket]
    visa_distribution:     list[HRVisaDistribution]
    cases_by_stage:        list[HRCasesByStage]
    monthly_trend:         list[HRMonthlyTrend]
    department_compliance: list[HRDepartmentCompliance]
    processing_time:       list[HRProcessingTime]
    document_completion:   list[HRDocumentCompletion]
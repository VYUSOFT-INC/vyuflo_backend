"""
app/services/employee/task_relay.py

Shared JSON-packing helpers for ApplicationTask.description.

Single source of truth for hr_task_service.py, application_services.py, and
new_case_service.py.

NEW — `target` field ("hr" | "employee"), chosen by the ATTORNEY at task
creation time (see new_case_service.py's attorney_create_task). This closes
a real gap: previously every attorney-created intake request was assumed to
be FOR the employee, routed through the full relay
(pending_hr_intake -> assigned_to_employee -> pending_hr_relay ->
sent_to_lawyer). But some things an attorney needs are things only HR can
answer directly (e.g. "confirm the sponsor letter is signed") — there was
no way to say "this one's for HR, don't involve the employee at all."

  target="employee" (default) — full relay, exactly as before. assigned_to
    starts at "employee" but gated by relay_status until HR explicitly
    assigns it.
  target="hr" — assigned_to is set to "hr" immediately. Visible to HR right
    away, no relay_status gating at all (mirrors the existing "HR requests
    a document from the attorney" pattern — assigned_to="attorney",
    origin="hr" — just in the opposite direction). HR completes it
    directly via the same hr_complete_task() used for every other task;
    no employee ever sees it, since application_services.list_tasks() only
    ever shows the employee tasks where assigned_to == "employee".

State machine (relay_status), for tasks where origin="attorney" AND
target="employee":

  pending_hr_intake      lawyer just created the task; HR hasn't reviewed
                         it yet. Not visible to the employee.
    -> (HR action: hr_assign_intake_task)
  assigned_to_employee   HR approved it; the employee can see and complete it.
    -> (employee or HR completes the task — automatic transition below)
  pending_hr_relay       employee marked it done; sitting with HR before
                         the lawyer sees it.
    -> (HR action: hr_relay_task_to_attorney)
  sent_to_lawyer         HR relayed it. The attorney's task list ONLY ever
                         shows target="employee" tasks in this state.

For target="hr" tasks, relay_status is set to "sent_to_lawyer" at creation
and is never gated on — it's a leftover default, not meaningful for this
target. The attorney's own list always shows target="hr" tasks
unconditionally (via assigned_to == "hr"), since there's no employee
step to protect.

Tasks with origin="hr" (ordinary HR-created tasks, e.g. "Request Document
from Attorney") are created with relay_status="sent_to_lawyer" and
target="employee" directly — target is not meaningful for HR-origin tasks
either; it predates this concept and is unaffected by it.
"""
from __future__ import annotations

import json


def pack_task_description(
    priority: str,
    text: str | None,
    due_date: str | None = None,
    assigned_to: str = "employee",
    relay_status: str = "sent_to_lawyer",
    origin: str = "hr",
    target: str = "employee",
) -> str:
    """
    Store priority + due_date + assigned_to + relay_status + origin +
    target in description JSON — no new columns needed.

    Defaults match every EXISTING call site (hr_create_task,
    hr_update_task/update_task with no relay fields touched) so those
    keep producing tasks that are immediately visible wherever they always
    were. `target` only changes behavior when explicitly passed as "hr" by
    attorney_create_task().
    """
    return json.dumps(
        {
            "priority": priority,
            "text": text or "",
            "due_date": due_date,
            "assigned_to": assigned_to,
            "relay_status": relay_status,
            "origin": origin,
            "target": target,
        },
        ensure_ascii=False,
    )


def unpack_task_description(raw: str | None) -> tuple[str, str, str | None, str, str, str, str]:
    """
    Returns (priority, plain_text_description, due_date, assigned_to,
    relay_status, origin, target).

    Legacy rows (packed before `target` existed, or genuinely plain-text)
    get target="employee" — they predate this concept entirely and behave
    exactly as target="employee" tasks always have.
    """
    if not raw:
        return "medium", "", None, "employee", "sent_to_lawyer", "hr", "employee"
    try:
        if raw.startswith("{"):
            data = json.loads(raw)
            return (
                data.get("priority", "medium"),
                data.get("text", ""),
                data.get("due_date"),
                data.get("assigned_to", "employee"),
                data.get("relay_status", "sent_to_lawyer"),
                data.get("origin", "hr"),
                data.get("target", "employee"),
            )
    except (json.JSONDecodeError, TypeError):
        pass
    return "medium", raw, None, "employee", "sent_to_lawyer", "hr", "employee"  # legacy plain text


def advance_relay_on_completion(current_relay_status: str, origin: str, is_completed: bool) -> str:
    """
    The single automatic transition in the state machine: a
    target="employee" attorney-origin task assigned to the employee, once
    completed, drops into HR's "needs relay" queue on its own — HR
    shouldn't have to separately notice and manually flip a status just
    because the employee finished something.

    Every OTHER transition (pending_hr_intake -> assigned_to_employee,
    pending_hr_relay -> sent_to_lawyer) stays an explicit HR action
    (hr_assign_intake_task, hr_relay_task_to_attorney in
    hr_task_service.py) — those are deliberate handoffs, not automatic.

    For target="hr" tasks this function is effectively a no-op — their
    relay_status never enters "assigned_to_employee" or "pending_hr_relay"
    in the first place, so neither branch below ever matches and the
    value passes through unchanged. HR completing a target="hr" task is
    just a plain is_completed flip with no relay_status side effect.

    Called from BOTH hr_complete_task (HR completing on the employee's
    behalf, or completing a target="hr" task directly) and complete_task
    (the employee completing it themselves via application_services.py)
    — same rule, same result, regardless of which side triggers it.
    """
    if origin == "attorney" and is_completed and current_relay_status == "assigned_to_employee":
        return "pending_hr_relay"
    if not is_completed and current_relay_status == "pending_hr_relay":
        # Uncompleting a task HR hasn't relayed yet — send it back a step
        # rather than leaving it stuck as "pending_hr_relay" with
        # is_completed=False, which would look like a self-contradiction.
        return "assigned_to_employee"
    return current_relay_status
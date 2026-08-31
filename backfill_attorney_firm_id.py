# =============================================================================
# backfill_attorney_firm_id.py
#
# ONE-TIME repair script.
#
# What it fixes:
#   Attorneys who onboarded BEFORE the fix in onboarding_services.py have
#   law_firm_name filled in but firm_id = NULL. That NULL is what makes
#   _validate_attorney_from_connected_firm() 403 when HR tries to assign
#   them to a case ("This attorney is not part of any firm").
#
# What it does:
#   For every attorney_profiles row where firm_id IS NULL and
#   law_firm_name IS NOT NULL:
#     1. Find or create a matching LawFirm by name (same lookup the app uses).
#     2. Set attorney_profiles.firm_id to that firm's id.
#
# It does NOT touch attorneys who never entered a firm name — those are
# legitimately "no firm" and should stay that way (or be fixed by hand).
#
# It does NOT create any EmployerFirmConnection rows — that's a separate,
# per-employer decision (HR still needs to "connect" to that firm, e.g. via
# hr_connect_firm(), before they can assign that attorney to a case).
#
# HOW TO RUN
# -----------
#   cd vyuflo_backend_dev
#   python backfill_attorney_firm_id.py            # dry run — shows what WOULD change
#   python backfill_attorney_firm_id.py --apply     # actually writes the changes
# =============================================================================

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.visamodels import AttorneyProfile, LawFirm


async def get_or_create_firm(db, firm_name: str) -> LawFirm:
    existing = await db.scalar(select(LawFirm).where(LawFirm.name == firm_name))
    if existing:
        return existing
    firm = LawFirm(id=uuid.uuid4(), name=firm_name, is_active=True)
    db.add(firm)
    await db.flush()
    return firm


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AttorneyProfile).where(
                AttorneyProfile.firm_id.is_(None),
                AttorneyProfile.law_firm_name.is_not(None),
            )
        )
        broken = result.scalars().all()

        if not broken:
            print("No affected attorneys found. Nothing to do.")
            return

        print(f"Found {len(broken)} attorney(s) with a firm name but no firm_id:\n")

        for attorney in broken:
            firm_name = attorney.law_firm_name.strip()
            if not firm_name:
                continue

            firm = await get_or_create_firm(db, firm_name)
            print(
                f"  attorney_id={attorney.id}  "
                f"law_firm_name='{firm_name}'  ->  firm_id={firm.id}"
            )
            if apply:
                attorney.firm_id = firm.id

        if apply:
            await db.commit()
            print("\nDone. firm_id has been backfilled for the attorneys listed above.")
            print(
                "Reminder: each affected employer still needs a LawFirm connection "
                "(via the existing hr_connect_firm flow) before they can assign "
                "these attorneys to a case."
            )
        else:
            print(
                "\nDRY RUN — no changes were written. "
                "Re-run with --apply to actually save these firm_id values."
            )


if __name__ == "__main__":
    asyncio.run(main(apply="--apply" in sys.argv))


import asyncio
import json
import logging
import uuid
from typing import Optional

from pywebpush import webpush, WebPushException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.visamodels import PushSubscription

logger = logging.getLogger(__name__)


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================

async def save_push_subscription(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    endpoint: str,
    p256dh:   str,
    auth:     str,
) -> None:
    """Upsert a browser push subscription for a user."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id  == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.p256dh = p256dh
        existing.auth   = auth
    else:
        db.add(PushSubscription(
            user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth,
        ))
    await db.flush()


async def delete_push_subscription(
    db:       AsyncSession,
    user_id:  uuid.UUID,
    endpoint: Optional[str] = None,
) -> None:
    """Remove push subscription(s) for a user. If endpoint omitted, removes all."""
    stmt = delete(PushSubscription).where(PushSubscription.user_id == user_id)
    if endpoint:
        stmt = stmt.where(PushSubscription.endpoint == endpoint)
    await db.execute(stmt)
    await db.flush()


# =============================================================================
# SEND
# =============================================================================

def _send_one(subscription_info: dict, payload: str) -> None:
    """Sync webpush call — runs inside asyncio.to_thread."""
    webpush(
        subscription_info=subscription_info,
        data=payload,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
    )


async def send_push_to_user(
    db:      AsyncSession,
    user_id: uuid.UUID,
    title:   str,
    body:    str,
    url:     str = "/notifications",
    icon:    str = "/logo192.png",
) -> None:
    """
    Sends a Web Push notification to all registered browser subscriptions
    for the given user. Called from notification_service.py's
    _deliver_push() when prefs.push_enabled is True.

    Silently no-ops if VAPID isn't configured or user has no subscriptions.
    Expired/invalid subscriptions (404/410) are auto-cleaned.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_CLAIMS_EMAIL:
        return

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()
    if not subscriptions:
        return

    payload = json.dumps({"title": title, "body": body, "url": url, "icon": icon})

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        try:
            await asyncio.to_thread(_send_one, subscription_info, payload)
            logger.info("[Push] Sent to user %s", user_id)

        except WebPushException as e:
            logger.warning("[Push] Failed for %s: %s", sub.endpoint[:40], e)
            # 404/410 = subscription expired or unsubscribed — clean it up
            if e.response is not None and e.response.status_code in (404, 410):
                await db.execute(
                    delete(PushSubscription).where(PushSubscription.id == sub.id)
                )
                await db.flush()

        except Exception as e:
            logger.exception("[Push] Unexpected error for user %s: %s", user_id, e)
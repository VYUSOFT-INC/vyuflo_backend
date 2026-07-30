"""
IP-based geolocation for login history.
Uses ip-api.com (free tier: 45 req/min, no key required).
Fails silently — geolocation is nice-to-have, never blocks login.
"""
import httpx
import structlog

log = structlog.get_logger(__name__)

# Private/local IPs won't resolve — skip the lookup entirely for these
_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")


async def get_ip_location(ip_address: str | None) -> dict:
    """Returns {'city': str | None, 'country': str | None}."""
    if not ip_address or ip_address.startswith(_PRIVATE_PREFIXES):
        return {"city": None, "country": None}

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,city,country"},
            )
            data = resp.json()
            if data.get("status") == "success":
                return {"city": data.get("city"), "country": data.get("country")}
    except Exception as e:
        log.warning("geolocation_lookup_failed", ip=ip_address, error=str(e))

    return {"city": None, "country": None}
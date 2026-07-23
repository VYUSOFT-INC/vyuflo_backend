"""
Parses User-Agent strings into browser / OS / device_type for login history.
"""
from user_agents import parse as parse_ua


def parse_device(user_agent: str | None) -> dict:
    if not user_agent:
        return {"browser": None, "os": None, "device_type": "unknown"}

    ua = parse_ua(user_agent)

    if ua.is_mobile:
        device_type = "mobile"
    elif ua.is_tablet:
        device_type = "tablet"
    elif ua.is_pc:
        device_type = "desktop"
    else:
        device_type = "unknown"

    os_str = f"{ua.os.family} {ua.os.version_string}".strip()

    return {
        "browser": ua.browser.family or None,
        "os": os_str or None,
        "device_type": device_type,
    }
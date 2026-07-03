"""
App-wide constants.
"""
import uuid

# ── OTP ───────────────────────────────────────────────────────────────────────
OTP_LENGTH = 6
OTP_EXPIRE_SECONDS = 600        # 10 minutes
OTP_MAX_RESEND = 3

# ── JWT prefixes in Redis (blacklisting) ─────────────────────────────────────
REFRESH_TOKEN_REDIS_PREFIX = "refresh_token:"
BLACKLIST_TOKEN_REDIS_PREFIX = "blacklist_token:"

# ── Onboarding steps ─────────────────────────────────────────────────────────
ONBOARDING_TOTAL_STEPS = 4

ONBOARDING_STEP_WELCOME    = 1   # Screen 03
ONBOARDING_STEP_ROLE       = 2   # Screen 04  (Employee / Student / Dependent)
ONBOARDING_STEP_PROFILE    = 3   # Screen 05  (Full name, visa, nationality)
ONBOARDING_STEP_REVIEW     = 4   # Screen 06  (Summary → Start Application)

# ── User roles (from Figma Screen 04) ────────────────────────────────────────
ROLE_EMPLOYEE  = "employee"
ROLE_STUDENT   = "student"
ROLE_DEPENDENT = "dependent"
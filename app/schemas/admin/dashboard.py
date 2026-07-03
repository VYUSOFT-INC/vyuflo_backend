
# -------- admin-role-----

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
import uuid


class DashboardCountsResponse(BaseModel):
    total_users: int
    total_active_users: int



class UserLoginCardResponse(BaseModel):
    full_name: str
    email: EmailStr
    role_name: str
    status: Optional[str] = None
    last_login: Optional[datetime] = None



class UserLoginCardListResponse(BaseModel):
    items: List[UserLoginCardResponse]
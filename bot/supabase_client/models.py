from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class User(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    isAudio: Optional[bool] = False
    notification: Optional[bool] = False
    payment_status: Optional[bool] = False
    payment_amount: Optional[float] = None
    payment_currency: Optional[str] = None
    payment_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
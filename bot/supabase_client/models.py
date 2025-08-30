from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class User(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    isAudio: Optional[bool] = False
    notification: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
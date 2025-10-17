from pydantic import BaseModel, Field, constr
from typing import Optional


class RegisterRequestSchema(BaseModel):
    login: constr(min_length=3, max_length=16)
    password: constr(min_length=6, max_length=20)
    gender: int = Field(..., ge=0, le=1)
    telegram_id: int
    username: Optional[str] = None
    Request_Id: Optional[str] = Field(default=None, alias="Request-Id")




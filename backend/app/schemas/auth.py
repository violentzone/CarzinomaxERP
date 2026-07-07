from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = "employee"
    is_active: Optional[bool] = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "employee"

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

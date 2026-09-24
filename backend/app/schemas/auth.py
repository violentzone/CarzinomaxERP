from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    iat: float

class UserBase(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    has_finance_access: Optional[bool] = False
    has_scm_access: Optional[bool] = False
    has_hr_access: Optional[bool] = False
    has_dev_access: Optional[bool] = False

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    has_finance_access: Optional[bool] = False
    has_scm_access: Optional[bool] = False
    has_hr_access: Optional[bool] = False
    has_dev_access: Optional[bool] = False

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

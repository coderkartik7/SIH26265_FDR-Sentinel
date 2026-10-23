from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    role: str = Field(default="institution", pattern="^(institution|official|admin)$")
    institution_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    totp_required: bool = False
    user_id: str
    email: str
    full_name: str
    institution_id: Optional[str] = None

    @field_validator("role", mode="before")
    def uppercase_role(cls, v):
        return v.upper() if isinstance(v, str) else v


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str
    message: str = "Scan this QR code with Google Authenticator or any TOTP app"


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    institution_id: Optional[str] = None
    is_active: bool
    totp_enabled: bool
    created_at: datetime

    @field_validator("role", mode="before")
    def uppercase_role(cls, v):
        return v.upper() if isinstance(v, str) else v

    class Config:
        from_attributes = True

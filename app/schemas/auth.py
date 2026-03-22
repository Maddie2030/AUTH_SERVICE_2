import re
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

from app.core.constants import UserRole


PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#^()+={}[\]|\\:;<>,.?/~`])[A-Za-z\d@$!%*?&_\-#^()+={}[\]|\\:;<>,.?/~`]{8,}$"
)
MOBILE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")


class RegisterRequest(BaseModel):
    mobile_number: str
    password: str
    full_name: str
    role: UserRole

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        v = v.strip()
        if not MOBILE_REGEX.match(v):
            raise ValueError("Invalid mobile number format.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character."
            )
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError("Admin registration is not allowed via this endpoint.")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v


class LoginRequest(BaseModel):
    mobile_number: str
    password: str
    device_id: Optional[str] = None

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        return v.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character."
            )
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match.")
        return self


class ForgotPasswordRequest(BaseModel):
    mobile_number: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        return v.strip()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character."
            )
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self

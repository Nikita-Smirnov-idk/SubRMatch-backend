from pydantic import BaseModel, Field, EmailStr
import uuid
from datetime import datetime


class UserCreateByEmailModel(BaseModel):
    name: str = Field(max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserCreateByOauthModel(BaseModel):
    name: str = Field(max_length=50)
    email: EmailStr
    is_verified: bool
    google_id: str


class UserLoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserModel(BaseModel):
    uid : uuid.UUID
    name : str = Field(max_length=50)
    email : EmailStr
    is_verified : bool
    password_hash : str = Field(exclude=True, min_length=8, max_length=128)
    created_at : datetime
    google_id: str = Field(exclude=True)

class PasswordResetModel(BaseModel):
    email: EmailStr

class PassswordResetConfirmModel(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)
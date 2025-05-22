import uuid
from datetime import datetime, timezone
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, Relationship, SQLModel, String
import json

class User(SQLModel, table=True):
    __tablename__ = "users"
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID,
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )
    )
    name: str = Field(
        max_length=50
    )
    email: str = Field(
        unique=True
    )
    role: str = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            server_default="user",
        )
    )
    is_verified: bool = False
    password_hash: str = Field(
        exclude=True,
        nullable=True
    )
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP,
            nullable=False,
            default=datetime.now,
        )
    )
    google_id: str = Field(
        sa_column = Column(
            String,
            unique=True,
            nullable=True
        )
    )  # Для Google OAuth


    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email}, is_verified={self.is_verified}, created_at={self.created_at})"
    
    def get_safe_as_dict(self) -> dict:
        return dict({
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
        })
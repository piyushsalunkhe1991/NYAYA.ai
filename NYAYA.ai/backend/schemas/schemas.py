"""Pydantic request models (input validation)."""
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=6, max_length=128)
    language: str = Field(default="auto", pattern="^(auto|en|hi)$")

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid e-mail address")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    language: Optional[str] = Field(default=None, pattern="^(auto|en|hi)$")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[int] = None
    language: str = Field(default="auto", pattern="^(auto|en|hi)$")
    demo: bool = False  # True = local knowledge-base answer, NO AI model is used


class SaveIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    category: Optional[str] = None

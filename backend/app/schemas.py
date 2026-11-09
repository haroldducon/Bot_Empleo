from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExperienceIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    company: str = Field(max_length=150)
    position: str = Field(max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    description: str = ""


class ExperienceOut(ExperienceIn):
    id: int

    model_config = {"from_attributes": True}


class EducationIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    institution: str = Field(max_length=150)
    degree: str = Field(max_length=150)
    field: str = ""
    start_year: int | None = None
    end_year: int | None = None


class EducationOut(EducationIn):
    id: int

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    full_name: str = Field(default="", max_length=150)
    headline: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=5000)
    city: str = Field(default="", max_length=100)
    modality: Literal["remoto", "presencial", "hibrido", "cualquiera"] = "cualquiera"
    desired_titles: list[str] = Field(default_factory=list, max_length=34)
    skills: list[str] = Field(default_factory=list, max_length=60)
    salary_min: int | None = None
    notification_email: EmailStr | None = None
    notify_enabled: bool = True
    experiences: list[ExperienceIn] = Field(default_factory=list, max_length=30)
    education: list[EducationIn] = Field(default_factory=list, max_length=30)


class ProfileOut(BaseModel):
    full_name: str
    headline: str
    summary: str
    city: str
    modality: str
    desired_titles: list[str]
    skills: list[str]
    salary_min: int | None
    notification_email: str
    notify_enabled: bool
    experiences: list[ExperienceOut]
    education: list[EducationOut]

    model_config = {"from_attributes": True}


Provider = Literal["gemini", "claude", "openai", "groq", "openrouter"]


class AIKeyIn(BaseModel):
    api_key: str = Field(min_length=10, max_length=500, pattern=r"^\S+$")


class AIKeyOut(BaseModel):
    provider: str
    hint: str  # solo los últimos 4 caracteres
    is_active: bool


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: EmailStr


class PasswordResetComplete(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    token: str = Field(min_length=32, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)

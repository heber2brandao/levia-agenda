from datetime import time
from itertools import pairwise
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class WorkingPeriodInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    weekday: int = Field(ge=0, le=6)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def valid_period(self):
        if self.starts_at.tzinfo or self.ends_at.tzinfo or self.starts_at >= self.ends_at:
            raise ValueError("Expediente deve ter início anterior ao fim, sem fuso no horário")
        return self


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)
    name: str = Field(min_length=1, max_length=100)
    studio_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    email: EmailStr | None = None
    specialties: list[str] = Field(min_length=1, max_length=15)
    timezone: str = "America/Cuiaba"
    primary_color: str = Field(default="#9a746d", pattern=r"^#[0-9a-fA-F]{6}$")
    background_color: str = Field(default="#f7f3ef", pattern=r"^#[0-9a-fA-F]{6}$")
    working_periods: list[WorkingPeriodInput] = Field(default_factory=list, max_length=28)

    @field_validator("specialties")
    @classmethod
    def valid_specialties(cls, values):
        cleaned = list(dict.fromkeys(value.strip() for value in values))
        if any(not value or len(value) > 60 for value in cleaned):
            raise ValueError("Especialidades devem ter de 1 a 60 caracteres")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso horário inválido") from None
        return value

    @model_validator(mode="after")
    def non_overlapping_periods(self):
        ordered = sorted(self.working_periods, key=lambda p: (p.weekday, p.starts_at))
        for previous, current in pairwise(ordered):
            if previous.weekday == current.weekday and previous.ends_at > current.starts_at:
                raise ValueError("Períodos de expediente não podem se sobrepor")
        return self


class ProfileOutput(ProfileInput):
    id: UUID
    logo: str | None = None

from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .form import validate_form_json


def _validate_required_form_json(value: dict) -> dict:
    """A form template must hold a form, so {} is not allowed here"""
    if not value:
        raise ValueError("form_json must be a form definition")
    return validate_form_json(value) or {}


class FormTemplateBase(SQLModel):
    """Shared fields between table and API models for FormTemplate"""

    form_json: dict = Field(sa_column=Column(JSONB, nullable=False))


class FormTemplate(FormTemplateBase, BaseModel, table=True):
    """A reusable form (e.g. a feedback form) that submissions can answer"""

    __tablename__ = "forms"

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class FormTemplateCreate(FormTemplateBase):
    """FormTemplate creation request"""

    @field_validator("form_json")
    @classmethod
    def _validate_form_json(cls, value: dict) -> dict:
        return _validate_required_form_json(value)


class FormTemplateRead(FormTemplateBase):
    """FormTemplate response model"""

    id: UUID


class FormTemplateUpdate(SQLModel):
    """FormTemplate update request - all fields optional"""

    form_json: dict | None = Field(default=None)

    @field_validator("form_json")
    @classmethod
    def _validate_form_json(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        return _validate_required_form_json(value)

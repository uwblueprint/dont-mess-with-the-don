from sqlalchemy import ARRAY, Enum, String
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel
from .enum import SimpleEntityEnum


class SimpleEntityBase(SQLModel):
    """Shared fields between table and API models"""

    string_field: str = Field(min_length=1, max_length=255)
    int_field: int = Field(ge=0)
    enum_field: SimpleEntityEnum = Field(
        default=SimpleEntityEnum.A,
        sa_column=Column(
            Enum(
                SimpleEntityEnum,
                values_callable=lambda obj: [e.value for e in obj],
                name="simpleentityenum",
            )
        ),
    )
    string_array_field: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    bool_field: bool = Field(default=False)


class SimpleEntity(SimpleEntityBase, BaseModel, table=True):
    """SimpleEntity model for demonstration purposes"""

    __tablename__ = "simple_entities"

    id: int | None = Field(default=None, primary_key=True)


class SimpleEntityCreate(SimpleEntityBase):
    """SimpleEntity creation request"""

    pass


class SimpleEntityRead(SimpleEntityBase):
    """SimpleEntity response model"""

    id: int


class SimpleEntityUpdate(SQLModel):
    """SimpleEntity update request - all fields optional"""

    string_field: str | None = Field(default=None, min_length=1, max_length=255)
    int_field: int | None = Field(default=None, ge=0)
    enum_field: SimpleEntityEnum | None = Field(default=None)
    string_array_field: list[str] | None = Field(default=None)
    bool_field: bool | None = Field(default=None)

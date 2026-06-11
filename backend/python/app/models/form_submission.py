from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel

from .base import BaseModel

# common columns and methods across multiple data models can be added via a Mixin class:
# https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html

# see examples of Mixins in current and past Blueprint projects:
# https://github.com/uwblueprint/dancefest-web/blob/master/db/models.py#L10-L70
# https://github.com/uwblueprint/plasta/blob/master/backend/app/models/mixins.py#L10-L95


class FormSubmissionBase(SQLModel):

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    event_instance_id: UUID = Field(foreign_key="events.id")
    response_json: dict | None = Field(default=None, sa_column=Column(JSON))


class FormSubmission(FormSubmissionBase, BaseModel, table=True):
    """Entity model for demonstration purposes"""

    __tablename__ = "form_submissions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    event_instance_id: UUID = Field(foreign_key="events.id")
    response_json: dict | None = Field(default=None, sa_column=Column(JSON))


class FormSubmissionCreate(FormSubmissionBase):
    """Entity creation request"""

    pass


class FormSubmissionRead(FormSubmissionBase):
    """Entity response model"""

    id: int


class FormSubmissionUpdate(SQLModel):
    """Entity update request - all fields optional"""

    pass


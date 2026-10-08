"""Pydantic schemas for registration form JSON.

Contains the form definition models (FormDefinition, FormQuestion, FormOption),
the form response model (FormResponse), and the column helpers used by the
Event/EventType models (validate_form_json) and the FormSubmission models
(validate_response_json). Structural rules are enforced as model validators, so
an invalid definition or response shape can never be constructed.

Validating a response against a form definition is business logic and lives in
app.utilities.form_validation; FormSubmissionService runs it on create and
update. The form JSON structure is documented in the
"Registration Forms" section of the repository README.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enum import QuestionTypeEnum

CHOICE_QUESTION_TYPES = frozenset({QuestionTypeEnum.MULTIPLE_CHOICE, QuestionTypeEnum.CHECKBOXES})


class FormOption(BaseModel):
    """A selectable option of a multiple choice or checkboxes question"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class FormQuestion(BaseModel):
    """A single question in a form"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    type: QuestionTypeEnum
    label: str = Field(min_length=1)
    required: bool = False
    options: list[FormOption] | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> "FormQuestion":
        if self.type in CHOICE_QUESTION_TYPES:
            if not self.options:
                raise ValueError(
                    f"Question '{self.id}' of type {self.type.value} must define options"
                )
            option_ids = [option.id for option in self.options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"Question '{self.id}' has duplicate option ids")
        elif self.options:
            raise ValueError(f"Question '{self.id}' of type {self.type.value} cannot have options")
        return self


class FormDefinition(BaseModel):
    """A complete registration form; questions render in list order"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    form_id: str = Field(min_length=1, alias="formId")
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1)
    questions: list[FormQuestion] = Field(min_length=1)

    @property
    def questions_by_id(self) -> dict[str, FormQuestion]:
        return {question.id: question for question in self.questions}

    @model_validator(mode="after")
    def _validate_unique_question_ids(self) -> "FormDefinition":
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Form has duplicate question ids")
        return self


class FormResponse(BaseModel):
    """A respondent's answers to a form, keyed by question id"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    form_id: str = Field(min_length=1, alias="formId")
    form_version: int = Field(ge=1, alias="formVersion")
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    response_version: int = Field(default=1, ge=1, alias="responseVersion")


def validate_form_json(value: dict | None) -> dict | None:
    """Validate a form_json column value; None and {} mean 'no form'.

    Parsing through FormDefinition enforces the structural authoring rules
    defined above: unique question and option ids, and options present only
    on choice questions.

    Returns the normalized definition JSON on success, raises ValueError otherwise.
    """
    if not value:
        return value
    return FormDefinition.model_validate(value).model_dump(mode="json", by_alias=True)


def validate_response_json(value: dict | None) -> dict | None:
    """Validate a response_json column value's shape; None and {} mean 'no response'.

    Parsing through FormResponse only guarantees the stored JSON is shaped like
    a response: formId and formVersion present, answers as a map of question
    id -> string or list of strings, and no unknown keys.

    Validating the answers against the event's form definition (required
    questions, answer types, option ids) needs the definition itself; see
    app.utilities.form_validation.validate_form_response.
    """
    if not value:
        return value
    return FormResponse.model_validate(value).model_dump(mode="json", by_alias=True)

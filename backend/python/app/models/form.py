"""Pydantic schemas for registration form JSON.

Contains the form definition models (FormDefinition, FormSection, FormQuestion,
FormOption), the form response model (FormResponse), and the column helpers used
by the Event/EventType models (validate_form_json) and the FormSubmission models
(validate_response_json). Structural rules are enforced as model validators, so
an invalid definition or response shape can never be constructed.

Validating a response against a form definition is business logic and lives in
app.utilities.form_validation. The form JSON structure is documented in the
"Registration Forms" section of the repository README.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enum import QuestionTypeEnum


class FormOption(BaseModel):
    """A selectable option of a multiple choice or checkboxes question"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    go_to_section: str | None = Field(default=None, alias="goToSection")


class FormQuestion(BaseModel):
    """A single question within a form section"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    type: QuestionTypeEnum
    label: str = Field(min_length=1)
    required: bool = False
    options: list[FormOption] | None = None

    @property
    def is_routing(self) -> bool:
        """Whether this question routes to other sections via its options"""
        return self.type == QuestionTypeEnum.MULTIPLE_CHOICE and any(
            option.go_to_section is not None for option in self.options or []
        )

    @model_validator(mode="after")
    def _validate_options(self) -> "FormQuestion":
        has_choices = self.type in (QuestionTypeEnum.MULTIPLE_CHOICE, QuestionTypeEnum.CHECKBOXES)
        if has_choices:
            if not self.options:
                raise ValueError(
                    f"Question '{self.id}' of type {self.type.value} must define options"
                )
            option_ids = [option.id for option in self.options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"Question '{self.id}' has duplicate option ids")
        elif self.options:
            raise ValueError(f"Question '{self.id}' of type {self.type.value} cannot have options")
        if self.type != QuestionTypeEnum.MULTIPLE_CHOICE and any(
            option.go_to_section is not None for option in self.options or []
        ):
            raise ValueError(
                f"Question '{self.id}': only multiple choice options may set goToSection"
            )
        return self


class FormSection(BaseModel):
    """An ordered group of questions with a pointer to the next section"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    questions: list[FormQuestion] = Field(min_length=1)
    default_next: str | None = Field(default=None, alias="defaultNext")

    @property
    def routing_question(self) -> FormQuestion | None:
        return next((question for question in self.questions if question.is_routing), None)

    @model_validator(mode="after")
    def _validate_single_routing_question(self) -> "FormSection":
        routing = [question for question in self.questions if question.is_routing]
        if len(routing) > 1:
            raise ValueError(
                f"Section '{self.id}' has {len(routing)} conditional multiple choice "
                "questions; at most one is allowed per section"
            )
        return self


class FormDefinition(BaseModel):
    """A complete registration form"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    form_id: str = Field(min_length=1, alias="formId")
    version: int = Field(default=1, ge=1)
    title: str = Field(min_length=1)
    sections: list[FormSection] = Field(min_length=1)

    @property
    def sections_by_id(self) -> dict[str, FormSection]:
        return {section.id: section for section in self.sections}

    @model_validator(mode="after")
    def _validate_structure(self) -> "FormDefinition":
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Form has duplicate section ids")

        question_ids = [question.id for section in self.sections for question in section.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Form has duplicate question ids")

        valid_ids = set(section_ids)
        for section in self.sections:
            targets = [section.default_next]
            for question in section.questions:
                targets.extend(option.go_to_section for option in question.options or [])
            for target in targets:
                if target is not None and target not in valid_ids:
                    raise ValueError(
                        f"Section '{section.id}' references unknown section '{target}'"
                    )

        self._ensure_acyclic()
        return self

    def _ensure_acyclic(self) -> None:
        """Reject section routing graphs that contain a cycle"""
        edges: dict[str, set[str]] = {}
        for section in self.sections:
            targets: set[str] = set()
            if section.default_next is not None:
                targets.add(section.default_next)
            for question in section.questions:
                for option in question.options or []:
                    if option.go_to_section is not None:
                        targets.add(option.go_to_section)
            edges[section.id] = targets

        # 0 = unvisited, 1 = in progress, 2 = done
        state = dict.fromkeys(edges, 0)

        def visit(section_id: str) -> None:
            if state[section_id] == 1:
                raise ValueError(f"Form section routing contains a cycle at '{section_id}'")
            if state[section_id] == 2:
                return
            state[section_id] = 1
            for target in edges[section_id]:
                visit(target)
            state[section_id] = 2

        for section_id in edges:
            visit(section_id)


class FormResponse(BaseModel):
    """A respondent's answers to a form, including the section path taken"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    form_id: str = Field(min_length=1, alias="formId")
    form_version: int = Field(ge=1, alias="formVersion")
    path: list[str] = Field(min_length=1)
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    response_version: int = Field(default=1, ge=1, alias="responseVersion")


def validate_form_json(value: dict | None) -> dict | None:
    """Validate a form_json column value; None and {} mean 'no form'.

    Parsing through FormDefinition enforces the structural authoring rules
    defined above: unique section/question/option ids, options present only on
    choice questions, at most one conditional multiple choice question per
    section, all goToSection/defaultNext targets existing, and no routing
    cycles.

    Returns the normalized definition JSON on success, raises ValueError otherwise.
    """
    if not value:
        return value
    return FormDefinition.model_validate(value).model_dump(mode="json", by_alias=True)


def validate_response_json(value: dict | None) -> dict | None:
    """Validate a response_json column value's shape; None and {} mean 'no response'.

    Parsing through FormResponse only guarantees the stored JSON is shaped like
    a response: formId and formVersion present, a non-empty path, answers as a
    map of question id -> string or list of strings, and no unknown keys.

    Full validation against the event's form definition (path routing, required
    questions, answer types) needs the definition itself and happens in the form
    submission service via app.utilities.form_validation.validate_form_response.
    """
    if not value:
        return value
    return FormResponse.model_validate(value).model_dump(mode="json", by_alias=True)

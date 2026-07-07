"""Form definition and response schemas for event registration forms.

A form definition is stored as JSON on ``event_types.form_json`` (the template
for a recurring event) and may be overridden per event on ``events.form_json``.
A user's answers are stored as a form response JSON on
``form_submissions.response_json``; each user has at most one submission per
event, and submitting again edits the existing submission.

Authoring rules:
- Sections are ordered; the first section is the entry point of the form.
- Conditional logic (multiple routes through the form) is expressed with
  ``goToSection`` on multiple choice options. Each section may contain at most
  one multiple choice question with routing options.
- A yes/no question should be modelled as a multiple choice question with two
  options.
- If the answered routing option has no ``goToSection`` (or the routing
  question was not answered), the section's ``defaultNext`` is used.
  ``defaultNext: null`` marks a terminal section.
- Question ids must be unique across the form; option ids must be unique
  within their question. Section routing must not form a cycle.

In a response, ``path`` records the sections the respondent traversed and
``answers`` maps question ids to answers (``""`` / ``[]`` mean unanswered).
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enum import QuestionTypeEnum

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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

    Returns the normalized definition JSON on success, raises ValueError otherwise.
    """
    if not value:
        return value
    return FormDefinition.model_validate(value).model_dump(mode="json", by_alias=True)


def validate_response_json(value: dict | None) -> dict | None:
    """Validate a response_json column value's shape; None and {} mean 'no response'.

    This only guarantees the stored JSON is shaped like a FormResponse. Full
    validation against the event's form definition (path, required questions,
    answer types) needs the definition and happens in the form submission service.
    """
    if not value:
        return value
    return FormResponse.model_validate(value).model_dump(mode="json", by_alias=True)


def validate_form_response(definition: FormDefinition, response_json: dict) -> FormResponse:
    """Validate a response against a form definition; raises ValueError on failure"""
    response = FormResponse.model_validate(response_json)

    if response.form_id != definition.form_id:
        raise ValueError(
            f"Response is for form '{response.form_id}' but the event's form "
            f"is '{definition.form_id}'"
        )
    if response.form_version != definition.version:
        raise ValueError(
            f"Response is for form version {response.form_version} but the event's "
            f"form is version {definition.version}"
        )

    sections = definition.sections_by_id
    unknown_sections = [section_id for section_id in response.path if section_id not in sections]
    if unknown_sections:
        raise ValueError(f"Path references unknown sections: {unknown_sections}")
    if response.path[0] != definition.sections[0].id:
        raise ValueError(f"Path must start at section '{definition.sections[0].id}'")
    if len(response.path) != len(set(response.path)):
        raise ValueError("Path visits a section more than once")

    _validate_path_transitions(response, sections)

    path_questions = {
        question.id: question
        for section_id in response.path
        for question in sections[section_id].questions
    }
    for question_id in response.answers:
        if question_id not in path_questions:
            raise ValueError(
                f"Answer given for question '{question_id}' which is not on the response path"
            )

    for question in path_questions.values():
        answer = response.answers.get(question.id)
        if answer is None or answer == "" or answer == []:
            if question.required:
                raise ValueError(f"Question '{question.id}' is required")
            continue
        error = _validate_answer(question, answer)
        if error:
            raise ValueError(error)

    return response


def _validate_path_transitions(response: FormResponse, sections: dict[str, FormSection]) -> None:
    """Check that each step of the path follows the section routing rules"""
    for index, section_id in enumerate(response.path):
        section = sections[section_id]
        expected_next = section.default_next
        routing_question = section.routing_question
        if routing_question is not None:
            answer = response.answers.get(routing_question.id)
            if isinstance(answer, str) and answer:
                option = next(
                    (opt for opt in routing_question.options or [] if opt.id == answer),
                    None,
                )
                if option is not None and option.go_to_section is not None:
                    expected_next = option.go_to_section

        if index == len(response.path) - 1:
            if expected_next is not None:
                raise ValueError(
                    f"Path ends at section '{section_id}' but the form continues "
                    f"to '{expected_next}'"
                )
        elif response.path[index + 1] != expected_next:
            raise ValueError(
                f"Invalid path: section '{section_id}' leads to '{expected_next}' "
                f"but path goes to '{response.path[index + 1]}'"
            )


def _validate_answer(question: FormQuestion, answer: str | list[str]) -> str | None:
    """Return an error message if the answer does not match the question type"""
    if question.type == QuestionTypeEnum.CHECKBOXES:
        if not isinstance(answer, list):
            return f"Question '{question.id}' expects a list of option ids"
        if len(answer) != len(set(answer)):
            return f"Question '{question.id}' has duplicate selections"
        option_ids = {option.id for option in question.options or []}
        invalid = [selection for selection in answer if selection not in option_ids]
        if invalid:
            return f"Question '{question.id}' has invalid selections: {invalid}"
        return None

    if not isinstance(answer, str):
        return f"Question '{question.id}' expects a single string answer"

    if question.type == QuestionTypeEnum.MULTIPLE_CHOICE:
        option_ids = {option.id for option in question.options or []}
        if answer not in option_ids:
            return f"Question '{question.id}' has invalid selection '{answer}'"
    elif question.type == QuestionTypeEnum.EMAIL:
        if not _EMAIL_REGEX.match(answer):
            return f"Question '{question.id}' expects a valid email address"
    elif question.type == QuestionTypeEnum.DATE:
        try:
            datetime.strptime(answer, "%Y-%m-%d")
        except ValueError:
            return f"Question '{question.id}' expects a date in YYYY-MM-DD format"
    elif question.type == QuestionTypeEnum.TIME:
        try:
            datetime.strptime(answer, "%H:%M")
        except ValueError:
            return f"Question '{question.id}' expects a time in HH:MM format"

    return None

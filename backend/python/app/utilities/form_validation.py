"""Business-rule validation of a form response against a form definition.

Used by the form submission service when a response is submitted or edited.
Shape-only validation of the stored JSON columns lives with the schemas in
app.models.form (validate_form_json / validate_response_json).
"""

import re
from datetime import datetime

from app.models.enum import QuestionTypeEnum
from app.models.form import FormDefinition, FormQuestion, FormResponse, FormSection

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_form_response(definition: FormDefinition, response_json: dict) -> FormResponse:
    """Validate a response against a form definition; raises ValueError on failure.

    Checks, in order:
    1. The response is shaped like a FormResponse (via model parsing).
    2. The response was written for this exact form (formId and formVersion match).
    3. The path is plausible: only known sections, starts at the form's first
       section, and never visits a section twice.
    4. The path is the route the form actually dictates for the given answers
       (conditional goToSection / defaultNext routing; see
       _validate_path_transitions).
    5. Answers only reference questions in sections the respondent visited.
    6. Every required question on the path is answered ("", [] and a missing
       key all count as unanswered).
    7. Each given answer matches its question's type (see _validate_answer).
    """
    response = FormResponse.model_validate(response_json)

    # The response must target this exact form and version
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

    # The path may only contain known sections, must begin at the form's entry
    # section, and must not loop back on itself
    sections = definition.sections_by_id
    unknown_sections = [section_id for section_id in response.path if section_id not in sections]
    if unknown_sections:
        raise ValueError(f"Path references unknown sections: {unknown_sections}")
    if response.path[0] != definition.sections[0].id:
        raise ValueError(f"Path must start at section '{definition.sections[0].id}'")
    if len(response.path) != len(set(response.path)):
        raise ValueError("Path visits a section more than once")

    # Each hop of the path must match the routing the answers imply
    _validate_path_transitions(response, sections)

    # Answers may only reference questions in visited sections — a respondent
    # can't answer questions on branches they didn't take
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

    # Required questions on the path must be answered, and every given answer
    # must match its question's type
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
    """Check that each step of the path follows the section routing rules.

    For every section on the path, the next section is determined by:
    - the goToSection of the selected option of the section's conditional
      multiple choice question, if there is one and it was answered with a
      routing option;
    - otherwise the section's defaultNext.

    Every hop in the path must match that expectation, and the final section
    must be terminal (its expected next section is None).
    """
    for index, section_id in enumerate(response.path):
        section = sections[section_id]

        # Start from the section's default and let an answered routing
        # question override it
        expected_next = section.default_next
        routing_question = section.routing_question
        if routing_question is not None:
            answer = response.answers.get(routing_question.id)
            if isinstance(answer, str) and answer:
                option = next(
                    (opt for opt in routing_question.options or [] if opt.id == answer),
                    None,
                )
                # An invalid option id is reported by answer validation, and an
                # option without goToSection falls back to defaultNext
                if option is not None and option.go_to_section is not None:
                    expected_next = option.go_to_section

        if index == len(response.path) - 1:
            # The path may only end where the form ends
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
    """Return an error message if the answer does not match the question type.

    Expected answer formats by question type:
    - checkboxes: list of the question's option ids, no duplicates
    - multiple_choice: one of the question's option ids
    - email: string matching a basic email pattern
    - date: "YYYY-MM-DD"
    - time: "HH:MM" (24-hour)
    - short_answer / paragraph: any non-empty string

    Only called for answered questions; empty answers are handled by the
    required check in validate_form_response.
    """
    # Checkboxes are the only list-valued answer
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

    # Every other type answers with a single string
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

    # short_answer and paragraph accept any string
    return None

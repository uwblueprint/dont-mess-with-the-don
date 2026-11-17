"""Business-rule validation of a form response against a form definition.

Shape-only validation of the stored JSON columns lives with the schemas in
app.models.form (validate_form_json / validate_response_json).
"""

import re
from datetime import datetime

from app.models.enum import QuestionTypeEnum
from app.models.form import FormDefinition, FormQuestion, FormResponse

_EMAIL_REGEX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# strptime also accepts non-zero-padded values ("2000-1-1", "9:30"), so the
# exact shape is checked first
_DATE_REGEX = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIME_REGEX = re.compile(r"[0-9]{2}:[0-9]{2}")


def validate_form_response(definition: FormDefinition, response_json: dict) -> FormResponse:
    """Validate a response against a form definition; raises ValueError on failure.

    Checks, in order:
    1. The response is shaped like a FormResponse (via model parsing).
    2. The response was written for this exact form (formId and formVersion match).
    3. Answers only reference questions that exist in the form.
    4. Every required question is answered ("", a whitespace-only string, []
       and a missing key all count as unanswered).
    5. Each given answer matches its question's type (see _validate_answer).
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

    # Answers may only reference questions in the form
    questions = definition.questions_by_id
    unknown_questions = [
        question_id for question_id in response.answers if question_id not in questions
    ]
    if unknown_questions:
        raise ValueError(f"Answers reference unknown questions: {unknown_questions}")

    # Required questions must be answered, and every given answer must match
    # its question's type
    for question in definition.questions:
        answer = response.answers.get(question.id)
        if answer is None or answer == [] or (isinstance(answer, str) and not answer.strip()):
            if question.required:
                raise ValueError(f"Question '{question.id}' is required")
            continue
        error = _validate_answer(question, answer)
        if error:
            raise ValueError(error)

    return response


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
        if not _EMAIL_REGEX.fullmatch(answer):
            return f"Question '{question.id}' expects a valid email address"
    elif question.type == QuestionTypeEnum.DATE:
        if not _is_formatted(answer, _DATE_REGEX, "%Y-%m-%d"):
            return f"Question '{question.id}' expects a date in YYYY-MM-DD format"
    elif question.type == QuestionTypeEnum.TIME:
        if not _is_formatted(answer, _TIME_REGEX, "%H:%M"):
            return f"Question '{question.id}' expects a time in HH:MM format"

    # short_answer and paragraph accept any string
    return None


def _is_formatted(answer: str, shape: re.Pattern[str], strptime_format: str) -> bool:
    """Return whether the answer has the exact shape and is a real date/time."""
    if not shape.fullmatch(answer):
        return False
    try:
        datetime.strptime(answer, strptime_format)
    except ValueError:
        return False
    return True

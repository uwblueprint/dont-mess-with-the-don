import copy
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.enum import QuestionTypeEnum
from app.models.form import FormDefinition, validate_form_json, validate_response_json
from app.utilities.form_validation import validate_form_response

# Covers every question type
WORKSHOP_FORM = {
    "formId": "frm_workshop_signup",
    "version": 1,
    "title": "Workshop Registration",
    "questions": [
        {"id": "q_name", "type": "short_answer", "label": "Name", "required": True},
        {"id": "q_email", "type": "email", "label": "Email", "required": True},
        {"id": "q_why", "type": "paragraph", "label": "Why are you joining?", "required": False},
        {
            "id": "q_dietary",
            "type": "multiple_choice",
            "label": "Dietary restrictions",
            "required": True,
            "options": [
                {"id": "opt_none", "label": "None"},
                {"id": "opt_veg", "label": "Vegetarian"},
            ],
        },
        {
            "id": "q_food",
            "type": "checkboxes",
            "label": "What food do you want during the event",
            "required": False,
            "options": [
                {"id": "opt_pizza", "label": "pizza"},
                {"id": "opt_cookies", "label": "cookies"},
                {"id": "opt_pretzels", "label": "pretzels"},
            ],
        },
        {"id": "q_birthday", "type": "date", "label": "Birthday", "required": False},
        {"id": "q_arrival", "type": "time", "label": "Arrival time", "required": False},
    ],
}

VALID_RESPONSE = {
    "formId": "frm_workshop_signup",
    "formVersion": 1,
    "answers": {
        "q_name": "Ben Ng",
        "q_email": "ben@example.com",
        "q_why": "I love the Don Valley",
        "q_dietary": "opt_veg",
        "q_food": ["opt_pizza", "opt_cookies"],
        "q_birthday": "2000-11-29",
        "q_arrival": "",
    },
}


def workshop_form():
    return copy.deepcopy(WORKSHOP_FORM)


def valid_response():
    return copy.deepcopy(VALID_RESPONSE)


def workshop_definition():
    return FormDefinition.model_validate(workshop_form())


# --- Form definition validation ---


def test_valid_definition_parses():
    definition = workshop_definition()
    assert definition.form_id == "frm_workshop_signup"
    assert [question.id for question in definition.questions] == [
        "q_name",
        "q_email",
        "q_why",
        "q_dietary",
        "q_food",
        "q_birthday",
        "q_arrival",
    ]


def test_validate_form_json_none_and_empty_pass_through():
    assert validate_form_json(None) is None
    assert validate_form_json({}) == {}


def test_validate_form_json_normalizes():
    normalized = validate_form_json(workshop_form())
    assert normalized["formId"] == "frm_workshop_signup"
    assert normalized["questions"][0]["type"] == "short_answer"
    # Defaults are filled in on normalization
    assert normalized["questions"][0]["options"] is None


def test_form_with_no_questions_rejected():
    form = workshop_form()
    form["questions"] = []
    with pytest.raises(ValidationError):
        FormDefinition.model_validate(form)


def test_sections_key_rejected():
    form = workshop_form()
    form["sections"] = []
    with pytest.raises(ValidationError):
        FormDefinition.model_validate(form)


def test_duplicate_question_ids_rejected():
    form = workshop_form()
    form["questions"][1]["id"] = "q_name"
    with pytest.raises(ValidationError, match="duplicate question ids"):
        FormDefinition.model_validate(form)


def test_unknown_question_type_rejected():
    form = workshop_form()
    form["questions"][0]["type"] = "slider"
    with pytest.raises(ValidationError):
        FormDefinition.model_validate(form)


def test_options_required_for_choice_questions():
    for question_index in (3, 4):  # multiple_choice, checkboxes
        form = workshop_form()
        del form["questions"][question_index]["options"]
        with pytest.raises(ValidationError, match="must define options"):
            FormDefinition.model_validate(form)


def test_options_forbidden_for_text_questions():
    form = workshop_form()
    form["questions"][0]["options"] = [{"id": "opt_a", "label": "A"}]
    with pytest.raises(ValidationError, match="cannot have options"):
        FormDefinition.model_validate(form)


def test_duplicate_option_ids_rejected():
    form = workshop_form()
    form["questions"][3]["options"].append({"id": "opt_veg", "label": "Vegan"})
    with pytest.raises(ValidationError, match="duplicate option ids"):
        FormDefinition.model_validate(form)


def test_go_to_section_on_option_rejected():
    form = workshop_form()
    form["questions"][3]["options"][0]["goToSection"] = "sec_other"
    with pytest.raises(ValidationError):
        FormDefinition.model_validate(form)


def test_unknown_question_attribute_rejected():
    form = workshop_form()
    form["questions"][0]["colour"] = "red"
    with pytest.raises(ValidationError):
        FormDefinition.model_validate(form)


# --- Response shape validation ---


def test_validate_response_json_none_and_empty_pass_through():
    assert validate_response_json(None) is None
    assert validate_response_json({}) == {}


def test_validate_response_json_normalizes():
    normalized = validate_response_json(valid_response())
    assert normalized["formId"] == "frm_workshop_signup"
    assert normalized["responseVersion"] == 1


def test_validate_response_json_rejects_malformed_shape():
    with pytest.raises(ValidationError):
        validate_response_json({"answers": {"q_name": "Ben"}})  # missing formId/formVersion
    with pytest.raises(ValidationError):
        validate_response_json({**valid_response(), "unexpected": True})
    with pytest.raises(ValidationError):
        validate_response_json({**valid_response(), "path": ["sec_intro"]})  # sections removed
    with pytest.raises(ValidationError):
        validate_response_json({**valid_response(), "answers": {"q_name": 5}})


# --- Response validation against a definition ---


def test_valid_response_passes():
    response = validate_form_response(workshop_definition(), valid_response())
    assert response.answers["q_dietary"] == "opt_veg"


def test_wrong_form_id_rejected():
    response_json = valid_response()
    response_json["formId"] = "frm_other"
    with pytest.raises(ValueError, match="frm_other"):
        validate_form_response(workshop_definition(), response_json)


def test_wrong_form_version_rejected():
    response_json = valid_response()
    response_json["formVersion"] = 2
    with pytest.raises(ValueError, match="version 2"):
        validate_form_response(workshop_definition(), response_json)


def test_missing_required_answer_rejected():
    for empty in ("", None):
        response_json = valid_response()
        if empty is None:
            del response_json["answers"]["q_dietary"]
        else:
            response_json["answers"]["q_dietary"] = empty
        with pytest.raises(ValueError, match="'q_dietary' is required"):
            validate_form_response(workshop_definition(), response_json)


def test_optional_answer_may_be_empty_or_omitted():
    response_json = valid_response()
    del response_json["answers"]["q_why"]
    response_json["answers"]["q_food"] = []
    response_json["answers"]["q_arrival"] = ""
    validate_form_response(workshop_definition(), response_json)


def test_unknown_question_id_rejected():
    response_json = valid_response()
    response_json["answers"]["q_mystery"] = "hello"
    with pytest.raises(ValueError, match="q_mystery"):
        validate_form_response(workshop_definition(), response_json)


def test_invalid_option_id_rejected():
    response_json = valid_response()
    response_json["answers"]["q_dietary"] = "opt_bogus"
    with pytest.raises(ValueError, match="invalid selection 'opt_bogus'"):
        validate_form_response(workshop_definition(), response_json)


def test_list_for_multiple_choice_rejected():
    response_json = valid_response()
    response_json["answers"]["q_dietary"] = ["opt_veg"]
    with pytest.raises(ValueError, match="single string"):
        validate_form_response(workshop_definition(), response_json)


def test_invalid_email_rejected():
    response_json = valid_response()
    response_json["answers"]["q_email"] = "not-an-email"
    with pytest.raises(ValueError, match="valid email address"):
        validate_form_response(workshop_definition(), response_json)


def test_invalid_time_rejected():
    response_json = valid_response()
    response_json["answers"]["q_arrival"] = "9 o'clock"
    with pytest.raises(ValueError, match="HH:MM"):
        validate_form_response(workshop_definition(), response_json)


def test_valid_time_accepted():
    response_json = valid_response()
    response_json["answers"]["q_arrival"] = "18:30"
    validate_form_response(workshop_definition(), response_json)


def test_invalid_date_rejected():
    response_json = valid_response()
    response_json["answers"]["q_birthday"] = "Nov 29th, 2025"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_form_response(workshop_definition(), response_json)


def test_checkbox_answers():
    definition = workshop_definition()

    bad_selection = valid_response()
    bad_selection["answers"]["q_food"] = ["opt_pizza", "opt_bogus"]
    with pytest.raises(ValueError, match="invalid selections"):
        validate_form_response(definition, bad_selection)

    duplicate_selection = valid_response()
    duplicate_selection["answers"]["q_food"] = ["opt_pizza", "opt_pizza"]
    with pytest.raises(ValueError, match="duplicate selections"):
        validate_form_response(definition, duplicate_selection)

    string_for_checkboxes = valid_response()
    string_for_checkboxes["answers"]["q_food"] = "opt_pizza"
    with pytest.raises(ValueError, match="expects a list"):
        validate_form_response(definition, string_for_checkboxes)


# --- README example ---


def readme_form_examples() -> tuple[dict, dict]:
    """Return the (definition, response) JSON examples from the README.

    The README sits at the repository root, which is not mounted into the
    backend container, so the tests using it are skipped when it is missing.
    """
    readme = next(
        (
            parent / "README.md"
            for parent in Path(__file__).resolve().parents
            if (parent / "README.md").is_file() and (parent / "backend").is_dir()
        ),
        None,
    )
    if readme is None:
        # Raised rather than called so mypy narrows `readme` even where pytest
        # is not installed (the lint job), and so sees pytest.skip as untyped.
        raise pytest.skip.Exception("Repository README is not available")
    section = readme.read_text(encoding="utf-8").split("## Registration Forms", 1)[1]
    section = section.split("\n## ", 1)[0]
    definition, response = re.findall(r"```json\n(.*?)```", section, flags=re.DOTALL)
    return json.loads(definition), json.loads(response)


def test_readme_example_is_valid():
    definition_json, response_json = readme_form_examples()

    definition = FormDefinition.model_validate(definition_json)
    validate_form_response(definition, response_json)


def test_readme_example_covers_every_question_type():
    definition_json, _ = readme_form_examples()

    definition = FormDefinition.model_validate(definition_json)
    assert {question.type for question in definition.questions} == set(QuestionTypeEnum)

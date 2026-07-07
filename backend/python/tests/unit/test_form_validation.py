import copy

import pytest
from pydantic import ValidationError

from app.models.form import (
    FormDefinition,
    validate_form_json,
    validate_form_response,
    validate_response_json,
)

WORKSHOP_FORM = {
    "formId": "frm_workshop_signup",
    "version": 1,
    "title": "Workshop Registration",
    "sections": [
        {
            "id": "sec_intro",
            "title": "About you",
            "questions": [
                {"id": "q_name", "type": "short_answer", "label": "Name", "required": True},
                {"id": "q_email", "type": "email", "label": "Email", "required": True},
                {
                    "id": "q_attending",
                    "type": "multiple_choice",
                    "label": "Will you attend in person or virtually?",
                    "required": True,
                    "options": [
                        {"id": "opt_inperson", "label": "In person", "goToSection": "sec_inperson"},
                        {"id": "opt_virtual", "label": "Virtually", "goToSection": "sec_virtual"},
                    ],
                },
            ],
            "defaultNext": "sec_inperson",
        },
        {
            "id": "sec_inperson",
            "title": "In-person details",
            "questions": [
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
                {"id": "q_arrival", "type": "time", "label": "Arrival time", "required": False},
            ],
            "defaultNext": "sec_final",
        },
        {
            "id": "sec_virtual",
            "title": "Virtual details",
            "questions": [
                {
                    "id": "q_zoom_email",
                    "type": "email",
                    "label": "Email for the Zoom invite",
                    "required": True,
                }
            ],
            "defaultNext": "sec_final",
        },
        {
            "id": "sec_final",
            "title": "Confirmation",
            "questions": [
                {
                    "id": "q_ack",
                    "type": "multiple_choice",
                    "label": "I agree to the terms",
                    "required": True,
                    "options": [{"id": "opt_agree", "label": "I agree"}],
                }
            ],
            "defaultNext": None,
        },
    ],
}

VALID_INPERSON_RESPONSE = {
    "formId": "frm_workshop_signup",
    "formVersion": 1,
    "path": ["sec_intro", "sec_inperson", "sec_final"],
    "answers": {
        "q_name": "Ben Ng",
        "q_email": "ben@example.com",
        "q_attending": "opt_inperson",
        "q_dietary": "opt_veg",
        "q_arrival": "",
        "q_ack": "opt_agree",
    },
}


def workshop_form():
    return copy.deepcopy(WORKSHOP_FORM)


def inperson_response():
    return copy.deepcopy(VALID_INPERSON_RESPONSE)


# --- Form definition validation ---


def test_valid_definition_parses():
    definition = FormDefinition.model_validate(workshop_form())
    assert definition.form_id == "frm_workshop_signup"
    assert len(definition.sections) == 4


def test_validate_form_json_none_and_empty_pass_through():
    assert validate_form_json(None) is None
    assert validate_form_json({}) == {}


def test_validate_form_json_normalizes():
    normalized = validate_form_json(workshop_form())
    assert normalized["formId"] == "frm_workshop_signup"
    assert normalized["sections"][0]["questions"][0]["type"] == "short_answer"


def test_duplicate_section_ids_rejected():
    form = workshop_form()
    form["sections"][1]["id"] = "sec_intro"
    with pytest.raises(ValidationError, match="duplicate section ids"):
        FormDefinition.model_validate(form)


def test_duplicate_question_ids_rejected():
    form = workshop_form()
    form["sections"][2]["questions"][0]["id"] = "q_name"
    with pytest.raises(ValidationError, match="duplicate question ids"):
        FormDefinition.model_validate(form)


def test_multiple_conditional_multiple_choice_in_section_rejected():
    form = workshop_form()
    form["sections"][0]["questions"].append(
        {
            "id": "q_second_router",
            "type": "multiple_choice",
            "label": "Another router",
            "options": [{"id": "opt_x", "label": "X", "goToSection": "sec_final"}],
        }
    )
    with pytest.raises(ValidationError, match="at most one is allowed per section"):
        FormDefinition.model_validate(form)


def test_non_conditional_multiple_choice_questions_can_share_a_section():
    form = workshop_form()
    form["sections"][1]["questions"].append(
        {
            "id": "q_tshirt",
            "type": "multiple_choice",
            "label": "T-shirt size",
            "options": [{"id": "opt_s", "label": "S"}, {"id": "opt_m", "label": "M"}],
        }
    )
    FormDefinition.model_validate(form)


def test_go_to_section_on_checkboxes_rejected():
    form = workshop_form()
    form["sections"][1]["questions"].append(
        {
            "id": "q_snacks",
            "type": "checkboxes",
            "label": "Snacks",
            "options": [{"id": "opt_pizza", "label": "Pizza", "goToSection": "sec_final"}],
        }
    )
    with pytest.raises(ValidationError, match="only multiple choice options may set goToSection"):
        FormDefinition.model_validate(form)


def test_unknown_section_reference_rejected():
    form = workshop_form()
    form["sections"][0]["defaultNext"] = "sec_missing"
    with pytest.raises(ValidationError, match="unknown section 'sec_missing'"):
        FormDefinition.model_validate(form)


def test_routing_cycle_rejected():
    form = workshop_form()
    form["sections"][3]["defaultNext"] = "sec_intro"
    with pytest.raises(ValidationError, match="cycle"):
        FormDefinition.model_validate(form)


def test_options_required_for_choice_questions():
    form = workshop_form()
    del form["sections"][0]["questions"][2]["options"]
    with pytest.raises(ValidationError, match="must define options"):
        FormDefinition.model_validate(form)


def test_options_forbidden_for_text_questions():
    form = workshop_form()
    form["sections"][0]["questions"][0]["options"] = [{"id": "opt_a", "label": "A"}]
    with pytest.raises(ValidationError, match="cannot have options"):
        FormDefinition.model_validate(form)


def test_duplicate_option_ids_rejected():
    form = workshop_form()
    form["sections"][1]["questions"][0]["options"][1]["id"] = "opt_none"
    with pytest.raises(ValidationError, match="duplicate option ids"):
        FormDefinition.model_validate(form)


# --- Response shape validation (definition-independent) ---


def test_validate_response_json_none_and_empty_pass_through():
    assert validate_response_json(None) is None
    assert validate_response_json({}) == {}


def test_validate_response_json_normalizes():
    normalized = validate_response_json(inperson_response())
    assert normalized["formId"] == "frm_workshop_signup"
    assert normalized["responseVersion"] == 1


def test_validate_response_json_rejects_malformed_shape():
    with pytest.raises(ValidationError):
        validate_response_json({"answers": {"q_name": "Ben"}})  # missing formId/version/path
    with pytest.raises(ValidationError):
        validate_response_json({**inperson_response(), "path": []})
    with pytest.raises(ValidationError):
        validate_response_json({**inperson_response(), "unexpected": True})


# --- Form response validation ---


def test_valid_inperson_response_passes():
    definition = FormDefinition.model_validate(workshop_form())
    response = validate_form_response(definition, inperson_response())
    assert response.answers["q_name"] == "Ben Ng"


def test_valid_virtual_response_passes():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = {
        "formId": "frm_workshop_signup",
        "formVersion": 1,
        "path": ["sec_intro", "sec_virtual", "sec_final"],
        "answers": {
            "q_name": "Ben Ng",
            "q_email": "ben@example.com",
            "q_attending": "opt_virtual",
            "q_zoom_email": "ben@example.com",
            "q_ack": "opt_agree",
        },
    }
    validate_form_response(definition, response_json)


def test_wrong_form_id_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["formId"] = "frm_other"
    with pytest.raises(ValueError, match="Response is for form 'frm_other'"):
        validate_form_response(definition, response_json)


def test_wrong_form_version_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["formVersion"] = 2
    with pytest.raises(ValueError, match="version"):
        validate_form_response(definition, response_json)


def test_path_not_matching_conditional_answer_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    # Answered "in person" but path goes to the virtual section
    response_json["path"] = ["sec_intro", "sec_virtual", "sec_final"]
    with pytest.raises(ValueError, match="Invalid path"):
        validate_form_response(definition, response_json)


def test_path_must_start_at_first_section():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["path"] = ["sec_inperson", "sec_final"]
    with pytest.raises(ValueError, match="must start at section 'sec_intro'"):
        validate_form_response(definition, response_json)


def test_path_ending_early_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["path"] = ["sec_intro", "sec_inperson"]
    with pytest.raises(ValueError, match="Path ends at section 'sec_inperson'"):
        validate_form_response(definition, response_json)


def test_missing_required_answer_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_dietary"] = ""
    with pytest.raises(ValueError, match="'q_dietary' is required"):
        validate_form_response(definition, response_json)


def test_optional_answer_may_be_empty_or_omitted():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    del response_json["answers"]["q_arrival"]
    validate_form_response(definition, response_json)


def test_answer_off_path_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_zoom_email"] = "ben@example.com"
    with pytest.raises(ValueError, match="not on the response path"):
        validate_form_response(definition, response_json)


def test_unknown_question_id_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_mystery"] = "hello"
    with pytest.raises(ValueError, match="q_mystery"):
        validate_form_response(definition, response_json)


def test_invalid_option_id_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_dietary"] = "opt_bogus"
    with pytest.raises(ValueError, match="invalid selection 'opt_bogus'"):
        validate_form_response(definition, response_json)


def test_invalid_email_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_email"] = "not-an-email"
    with pytest.raises(ValueError, match="valid email address"):
        validate_form_response(definition, response_json)


def test_invalid_time_rejected():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_arrival"] = "9 o'clock"
    with pytest.raises(ValueError, match="HH:MM"):
        validate_form_response(definition, response_json)


def test_valid_time_accepted():
    definition = FormDefinition.model_validate(workshop_form())
    response_json = inperson_response()
    response_json["answers"]["q_arrival"] = "18:30"
    validate_form_response(definition, response_json)


def test_checkboxes_and_date_answers():
    form = {
        "formId": "frm_snacks",
        "version": 1,
        "title": "Snacks",
        "sections": [
            {
                "id": "sec_main",
                "title": "Main",
                "questions": [
                    {
                        "id": "q_food",
                        "type": "checkboxes",
                        "label": "What food do you want during the event",
                        "options": [
                            {"id": "opt_pizza", "label": "pizza"},
                            {"id": "opt_cookies", "label": "cookies"},
                            {"id": "opt_pretzels", "label": "pretzels"},
                        ],
                    },
                    {"id": "q_birthday", "type": "date", "label": "Birthday", "required": True},
                ],
                "defaultNext": None,
            }
        ],
    }
    definition = FormDefinition.model_validate(form)

    valid = {
        "formId": "frm_snacks",
        "formVersion": 1,
        "path": ["sec_main"],
        "answers": {"q_food": ["opt_pizza", "opt_cookies"], "q_birthday": "2000-11-29"},
    }
    validate_form_response(definition, valid)

    bad_selection = copy.deepcopy(valid)
    bad_selection["answers"]["q_food"] = ["opt_pizza", "opt_bogus"]
    with pytest.raises(ValueError, match="invalid selections"):
        validate_form_response(definition, bad_selection)

    duplicate_selection = copy.deepcopy(valid)
    duplicate_selection["answers"]["q_food"] = ["opt_pizza", "opt_pizza"]
    with pytest.raises(ValueError, match="duplicate selections"):
        validate_form_response(definition, duplicate_selection)

    string_for_checkboxes = copy.deepcopy(valid)
    string_for_checkboxes["answers"]["q_food"] = "opt_pizza"
    with pytest.raises(ValueError, match="expects a list"):
        validate_form_response(definition, string_for_checkboxes)

    bad_date = copy.deepcopy(valid)
    bad_date["answers"]["q_birthday"] = "Nov 29th, 2025"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_form_response(definition, bad_date)

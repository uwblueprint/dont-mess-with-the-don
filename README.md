# Don't Mess With The Don

Don't Mess With The Don (DMWTD) is a non-profit organization based in the GTA that focuses on environmental and community initiatives. DMWTD connects volunteers, residents, and local partners and hosts events, educational programs, and fundraising initiatives related to sustainability.

## The Problem

A lot of people register for volunteering events online but don't show up. This is a recurring problem — the actual output of volunteer efforts isn't living up to its potential.

## Our Solution

This project is built by [UW Blueprint](https://uwblueprint.org) to address this with a centralized event management portal. The platform streamlines event discovery, attendee registration and vetting, attendance tracking, and data reporting for both staff and community members.

## Stack

- **Backend:** Python (FastAPI + SQLModel)
- **Frontend:** React (TypeScript)
- **Database:** PostgreSQL
- **Infrastructure:** Docker

## Environment Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Node.js 18+ (install directly from [nodejs.org](https://nodejs.org/) or via [nvm](https://github.com/nvm-sh/nvm))

### Initial Setup

1. Clone this repository and `cd` into the project folder
2. Set up environment files:

   **Ask PL** To share `.env` (root) and `frontend/.env` and place them in the repo root and `frontend/` respectively.

3. Start all services:
```bash
docker-compose up --build
```

The backend runs at http://localhost:8080 and the frontend at http://localhost:3000.

### Python Backend

The backend uses **FastAPI** with **SQLModel** (SQLAlchemy + Pydantic). Database migrations are managed with Alembic and run automatically on container startup.

#### Generating a new migration

After modifying a model in `backend/python/app/models/`, generate a migration:

```bash
docker exec -it don-backend alembic revision --autogenerate -m "describe your change"
```

Alembic diffs your models against the current DB schema and writes the migration file to `backend/python/migrations/versions/`.

#### Running migrations manually

```bash
docker exec -it don-backend alembic upgrade head
```

### Useful Commands

```bash
# List running containers
docker ps

# Open a shell in the backend container
docker exec -it don-backend /bin/bash

# Open a psql shell in the database container
docker exec -it don-db psql -U postgres -d postgres

# Lint Python code (check only)
docker exec don-backend ruff check .

# Auto-fix lint issues
docker exec don-backend ruff check --fix .

# Format Python code
docker exec don-backend ruff format .

# Check formatting without applying
docker exec don-backend ruff format --check .

# Type check
docker exec don-backend mypy .

# Run Python tests
docker exec -it don-backend pytest
```

## Registration Forms

Events can require a registration form. The form definition is stored as JSON on `event_types.form_json` (the template for a recurring event) and can be overridden per event on `events.form_json`. A user's answers are stored as JSON on `form_submissions.response_json`. Both formats are validated by the Pydantic schemas in `backend/python/app/models/form.py`; a submitted response is additionally validated against its event's form definition by `backend/python/app/utilities/form_validation.py`.

### Design decisions

| Question | Decision |
| --- | --- |
| Do we need multiple routes in the form? | Yes — conditional logic via `goToSection` on multiple choice options |
| Can a user respond multiple times to the same form? | No — submitting again edits their existing submission (enforced by a unique constraint on `(user_id, event_instance_id)`) |
| Can a question be repeated multiple times in the same form? | Yes — questions are referenced by an implicitly generated id, not by their label |

### Form JSON definition

A form is a list of ordered **sections**, each containing **questions**. The first section is the entry point.

```json
{
  "formId": "frm_workshop_signup",
  "version": 1,
  "title": "Workshop Registration",
  "sections": [
    {
      "id": "sec_intro",
      "title": "About you",
      "questions": [
        { "id": "q_name", "type": "short_answer", "label": "Name", "required": true },
        { "id": "q_email", "type": "email", "label": "Email", "required": true },
        {
          "id": "q_attending",
          "type": "multiple_choice",
          "label": "Will you attend in person or virtually?",
          "required": true,
          "options": [
            { "id": "opt_inperson", "label": "In person", "goToSection": "sec_inperson" },
            { "id": "opt_virtual", "label": "Virtually", "goToSection": "sec_virtual" }
          ]
        }
      ],
      "defaultNext": "sec_inperson"
    },
    {
      "id": "sec_inperson",
      "title": "In-person details",
      "questions": [
        {
          "id": "q_dietary",
          "type": "multiple_choice",
          "label": "Dietary restrictions",
          "required": true,
          "options": [
            { "id": "opt_none", "label": "None" },
            { "id": "opt_veg", "label": "Vegetarian" }
          ]
        },
        { "id": "q_arrival", "type": "time", "label": "Arrival time", "required": false }
      ],
      "defaultNext": "sec_final"
    },
    {
      "id": "sec_virtual",
      "title": "Virtual details",
      "questions": [
        { "id": "q_zoom_email", "type": "email", "label": "Email for the Zoom invite", "required": true }
      ],
      "defaultNext": "sec_final"
    },
    {
      "id": "sec_final",
      "title": "Confirmation",
      "questions": [
        {
          "id": "q_ack",
          "type": "multiple_choice",
          "label": "I agree to the terms",
          "required": true,
          "options": [{ "id": "opt_agree", "label": "I agree" }]
        }
      ],
      "defaultNext": null
    }
  ]
}
```

#### Question types

| Type | Answer format |
| --- | --- |
| `short_answer` | string |
| `paragraph` | string |
| `multiple_choice` | an option id (e.g. `"opt_veg"`) |
| `checkboxes` | list of option ids (e.g. `["opt_pizza", "opt_cookies"]`) |
| `date` | `"YYYY-MM-DD"` |
| `time` | `"HH:MM"` (24-hour) |
| `email` | string, must be a valid email address |

A **yes/no question should be a multiple choice question** with two options.

#### Conditional logic

- Routing is expressed with `goToSection` on multiple choice options. If the selected option has a `goToSection`, the form jumps there; otherwise (or if the routing question is unanswered) the section's `defaultNext` is used. `"defaultNext": null` marks the end of the form.
- **Each section can contain at most one conditional multiple choice question** (a multiple choice question with `goToSection` on any of its options). This is enforced at validation time.
- Only multiple choice options may set `goToSection` (checkboxes cannot route).

#### Validation rules

Enforced whenever a `form_json` is created or updated:

- Section ids and question ids must be unique across the form; option ids must be unique within their question.
- `defaultNext` and `goToSection` must reference existing sections, and the routing graph must not contain a cycle.
- `multiple_choice` and `checkboxes` questions must define `options`; other question types must not.

### Form JSON response

A submission records which sections the respondent traversed (`path`) and their answers keyed by question id. `""` / `[]` / an omitted key mean "did not answer".

```json
{
  "formId": "frm_workshop_signup",
  "formVersion": 1,
  "responseVersion": 2,
  "path": ["sec_intro", "sec_inperson", "sec_final"],
  "answers": {
    "q_name": "Ben Ng",
    "q_email": "ben@example.com",
    "q_attending": "opt_inperson",
    "q_dietary": "opt_veg",
    "q_arrival": "",
    "q_ack": "opt_agree"
  }
}
```

- `formId` / `formVersion` must match the event's form.
- `path` must start at the first section and follow the conditional routing implied by the answers, ending at a terminal section.
- Required questions in visited sections must be answered; answers are only allowed for questions on the path, and must match their question type.
- `responseVersion` is managed by the server and increments on every edit. The submission row's `updated_at` records when; `updatedBy` will be added once auth exists.

### Submitting

`POST /form-submissions/` validates the response against the event's form (`events.form_json`, falling back to the event type's template) and **upserts**: the first submission returns `201`, and submitting again for the same user and event edits the existing submission and returns `200`. The submission is automatically linked to the user's registration via `registrations.response_id`.

## Version Control Guide

- Branch off `main` for all feature work. Use the format `your-name/short-description` (e.g. `pranav/readme-update`)
- Rebase onto `main` to integrate upstream changes (do not merge)
- Commits should be atomic and written in imperative tense (e.g. "Add volunteer registration endpoint")

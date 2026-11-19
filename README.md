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
- Node.js 24+ (install directly from [nodejs.org](https://nodejs.org/) or via [nvm](https://github.com/nvm-sh/nvm))

### Initial Setup

1. Clone this repository and `cd` into the project folder
2. Set up environment files:

   **Ask PL** To share `.env` (root) and `frontend/.env` and place them in the repo root and `frontend/` respectively.

   Optional `frontend/.env` variables for the map POC (`/mapPOC`):

   | Variable | Purpose |
   | --- | --- |
   | `REACT_APP_GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key. Without it, the Google tab renders in watermarked development mode. |
   | `REACT_APP_GOOGLE_MAPS_MAP_ID` | Google Cloud map ID for advanced markers and cloud styling. Defaults to Google's `DEMO_MAP_ID`. |

   The Leaflet and MapLibre tabs need no keys. Restart the frontend after editing `.env`.

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

### Seeding sample data (development & testing)

Sample data lives as plain CSV files in `backend/python/seeds/` — one file per
table (`event_types.csv`, `users.csv`, `events.csv`, `form_submissions.csv`,
`registrations.csv`, `attendance.csv`). To change what gets seeded, just edit
the CSVs; the header row of each file matches the model's field names.

Run the seeder against the running dev database (via the `make` shortcuts, with
the raw commands shown for reference):

```bash
# Seed only if the database is empty (safe to run anytime)
make seed          # docker exec -it don-backend python -m app.seed

# Wipe the seeded tables and reload them from the CSVs
make seed-reset    # docker exec -it don-backend python -m app.seed --reset

# Wipe and seed the test database instead of the dev database
make seed-test     # docker exec -it -e APP_ENV=testing don-backend python -m app.seed --reset
```

Run `make help` to see all available shortcuts (start/stop, migrations, linting,
tests, DB shell, etc.).

To seed automatically when the backend container starts, set `SEED_DB=true` in
the root `.env`. Startup seeding is off by default and idempotent — it skips if
the database already has data, so it is safe to leave enabled across restarts.

**CSV notes:**
- Blank cells fall back to the model default (usually `NULL`) — leave optional
  columns empty.
- Rows are inserted in file order, so list parents before children in
  `users.csv` (the `guardian_id` self-reference).
- JSON/array columns (`form_json`, `response_json`, `post_event_photo_keys`, `notes`) must
  contain valid JSON, e.g. `{"formId": "frm_beach_cleanup"}` or `["a", "b"]`.
  Wrap those cells in double quotes and double any internal quotes (standard
  CSV quoting).
- `form_json` and `response_json` must follow the registration form schema: a
  response's `formId`, `formVersion` and answers have to match the form of the
  event it points to (the event's own `form_json`, or its event type's when
  that is blank).

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

Events can have a registration form. The form definition is stored as JSON on `event_types.form_json` (the template for an event type) and can be overridden per event on `events.form_json`. A user's answers are stored as JSON on `form_submissions.response_json`. Both formats are defined by the Pydantic schemas in `backend/python/app/models/form.py` and validated whenever an event, event type or form submission is created or updated through the API. When a form submission is created or its response is updated, the response is also checked against the event's form (the event's own `form_json`, falling back to its event type's) with `validate_form_response` in `backend/python/app/utilities/form_validation.py`; a response that does not match returns a 422.

`None` or `{}` means "no form" / "no response". Unknown keys are rejected everywhere.

### Form JSON definition

A form is an ordered list of **questions**; they render in list order. Questions are referenced by `id`, never by their label, so two questions may share a label.

```json
{
  "formId": "frm_workshop_signup",
  "version": 1,
  "title": "Workshop Registration",
  "questions": [
    { "id": "q_name", "type": "short_answer", "label": "Name", "required": true },
    { "id": "q_email", "type": "email", "label": "Email", "required": true },
    { "id": "q_why", "type": "paragraph", "label": "Why are you joining?" },
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
    {
      "id": "q_food",
      "type": "checkboxes",
      "label": "What food do you want during the event",
      "options": [
        { "id": "opt_pizza", "label": "pizza" },
        { "id": "opt_cookies", "label": "cookies" }
      ]
    },
    { "id": "q_birthday", "type": "date", "label": "Birthday" },
    { "id": "q_arrival", "type": "time", "label": "Arrival time" }
  ]
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `formId` | yes | Non-empty string identifying the form |
| `version` | no (default `1`) | Integer ≥ 1; bump it when the questions change |
| `title` | yes | Display title |
| `questions` | yes | At least one question; `id`s must be unique within the form |
| `questions[].id` | yes | Stable key used in `answers` |
| `questions[].type` | yes | One of the types below |
| `questions[].label` | yes | Display text |
| `questions[].required` | no (default `false`) | |
| `questions[].options` | choice types only | List of `{ "id", "label" }`; option `id`s must be unique within the question |

| Type | UI input | Answer format |
| --- | --- | --- |
| `short_answer` | single-line text | string |
| `paragraph` | multi-line text | string |
| `email` | email input | string matching a basic email pattern |
| `date` | date picker | `"YYYY-MM-DD"` |
| `time` | time picker | `"HH:MM"` (24-hour) |
| `multiple_choice` | radio buttons | one option `id` (string) |
| `checkboxes` | checkboxes | list of option `id`s, no duplicates |

### Form JSON response

```json
{
  "formId": "frm_workshop_signup",
  "formVersion": 1,
  "answers": {
    "q_name": "Ben Ng",
    "q_email": "ben@example.com",
    "q_dietary": "opt_veg",
    "q_food": ["opt_pizza", "opt_cookies"],
    "q_birthday": "2000-11-29",
    "q_arrival": ""
  },
  "responseVersion": 1
}
```

`answers` maps question `id` to its answer. An unanswered question may be omitted or given as `""` / `[]`; a whitespace-only string also counts as unanswered. `responseVersion` defaults to `1`.

To be accepted for an event that has a form, a response must use the form's `formId` and `version`, answer only questions that exist in the form, answer every required question, and match each question's answer format. An empty response is rejected. Events without a form are not checked beyond the response's shape.

### Design decisions

- **Questions are identified by `id`, not `key`.** The `id` is the stable key used in `answers`; it never changes when a label is edited.
- **Options are `{ "id", "label" }`, not `{ "value", "label" }`.** Answers store option `id`s, so an option's label can be reworded without invalidating existing responses.
- **Order is list position.** Questions and options render in the order they appear in their lists; there is no `order` field to keep in sync.
- **No sections.** A form is a flat list of questions. `sections`, `goToSection` and a response `path` are rejected as unknown keys.

### Feedback forms

Reusable forms that aren't tied to one event, such as a post-event feedback form, live in the `forms` table (`id` + `form_json`, same format as above) and are managed through `/forms`.

- A submission to one of these forms sets `form_id` on the form submission. Its response is checked against that form instead of the event's registration form. Submissions without a `form_id` are registration responses, as before.
- `GET /events/{event_id}/feedback` returns every submission for that event that has a `form_id`. `GET /form_submissions/?form_id=...` filters by form.
- A form can't be deleted while submissions still use it (409).

## Object storage (Cloudflare R2)

File uploads go to Cloudflare R2 (S3-compatible, accessed with boto3) through `R2StorageService` (`backend/python/app/services/implementations/storage_service.py`, get it with `get_storage_service()`). Config is read from the root `.env` through `app/config.py`:

| Variable | Required | Notes |
|---|---|---|
| `R2_ENDPOINT_URL` | yes | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `R2_PUBLIC_BUCKET_NAME` | yes | `dmwtd-public-{env}`. Public access enabled on this bucket only |
| `R2_PRIVATE_BUCKET_NAME` | yes | `dmwtd-private-{env}`. Never public |
| `R2_PUBLIC_BASE_URL` | yes | Public URL of the public bucket (r2.dev subdomain or custom domain) |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | yes | From an R2 API token with access to both buckets |
| `R2_KEY_PREFIX` | no | e.g. `dev/` or `prod/` if environments share a bucket |
| `SIGNED_URL_TTL_MEDIA_SECONDS` | no | Default `3600` (profile pics, post-event photos) |
| `SIGNED_URL_TTL_WAIVER_SIGNED_SECONDS` | no | Default `300` (completed/signed waivers) |

The R2 settings are required in production, where missing ones fail the deploy. In development and testing you can leave all of them unset: the app then uses `UnconfiguredStorageService`, which returns placeholder URLs (`https://r2-not-configured.invalid/...`) and raises on upload or delete. Setting only some of them is an error in every environment.

R2 enables public access per bucket, so each environment has two buckets: a public one for objects anyone may fetch and a private one reachable only through short-lived signed URLs. `url_for(key, visibility)` builds either: a permanent public URL, or a signed URL (signing is local, no network call). `upload_file` and `delete_file` take a `BucketVisibility` to pick the bucket. Keys are UUID-based (`events/{event_id}/{uuid}.jpg`, from `build_key`), never the uploaded filename, and the environment's key prefix is applied by the service, so the same key works in every environment.

### Access model: public-read vs signed URLs

The database stores **object keys only** (never URLs, never a signed URL). Serializers in `app/serializers/` build each response from its row and call `url_for` on the storage service for the URL fields; routes return `event_read(event, storage)` and so on, and the ORM models know nothing about storage.

| Type | Column | Bucket / access | Lifetime |
|---|---|---|---|
| Event / series / type headline image | `events.headline_image_key`, `event_series.headline_image_key`, `event_types.headline_image_key` | public; permanent URL | n/a |
| Waiver template (blank PDF) | `waiver_template.document_key` | public; permanent URL | n/a |
| Profile pic | `users.profile_pic_key` | private; signed URL | ~1 hour |
| Post-event photos (events only) | `events.post_event_photo_keys[]` | private; signed URL, admins and the event's attendees only | ~1 hour |
| Completed waivers | `waiver_signed.document_key` | private; signed URL, owner / guardian / admin only | ~5 minutes |

Why: headline images and blank templates are promotional or contain no personal data, so a public URL is fine (and cacheable). Photos of identifiable people (often minors) and signed waivers are private, so deleting the object makes every link stop working within the URL lifetime. Signing is local (no network call).

API responses return resolved URLs only (never keys), in the fields `headline_image_url`, `post_event_photo_urls`, `profile_pic_url` and `document_url`. **Frontend:** treat them as opaque strings, and refetch the record when an image returns 403 or the URL has expired. `post_event_photo_urls` (post-event photos) are filled only for admins and the event's attendees: anyone with an accepted registration or a check-in for that event, and the guardian of such a child (`app/utilities/photo_access.py`). Everyone else, including anonymous callers, gets an empty list. Event series have no post-event photos. Completed waivers are fetched with `GET /waiver-signed/{id}/url`, which checks authorization and returns a fresh 5-minute URL.

## Frontend URL

The backend builds some links that point at the frontend (for example event check-in links). It reads the frontend's base URL from `FRONTEND_URL` in the root `.env`, defaulting to `http://localhost:3000`. Set it in every deployed environment, e.g. `FRONTEND_URL=https://<frontend domain>`.

## Email (Resend)

Emails are sent through [Resend](https://resend.com) by `ResendEmailService` (`backend/python/app/services/implementations/email_service.py`). Get it with `get_email_service()` and call `await send_email(to, subject, html, text=..., idempotency_key=...)`. It returns Resend's email id, or raises `EmailSendError` (with `status_code`, e.g. `429` when rate limited). Pass an `idempotency_key` from scheduled jobs (e.g. `reminder/<registration id>`) so a retried run can't send the same email twice.

| Variable | Required | Notes |
|---|---|---|
| `RESEND_API_KEY` | in production | From Resend's API keys page. Without it, development and testing log emails instead of sending them (`LoggingEmailService`). |
| `EMAIL_FROM` | with the key | Sender, e.g. `Don't Mess With The Don <noreply@yourdomain>`. The domain must be verified in Resend (DNS records). Before that, `onboarding@resend.dev` only delivers to the Resend account owner's own address; `delivered@resend.dev` is a safe test recipient. |

Resend allows 10 requests per second by default.

## Strikes

People get strikes for missing events. They're stored in the `strikes` table and expire after a set time. Settings, all optional, in the root `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `STRIKE_NO_SHOW_GRACE_MINUTES` | `60` | How long after an event ends, with no check-in, before a no-show strike is given |
| `STRIKE_LATE_CANCELLATION_HOURS` | `48` | Cancelling less than this many hours before the start gives a strike |
| `STRIKE_EXPIRY_MONTHS` | `6` | Strikes expire this many months after the event's start |
| `STRIKE_NO_SHOW_START` | unset | Only events ending at or after this time (e.g. `2026-12-01T00:00:00`) give no-show strikes. Unset means no-show strikes are off. Set it to when check-in goes live, since attendance wasn't recorded before that. |

## Auth

Logins are handled by Firebase Auth (the dev project is `dmwtd-dev`). The frontend signs people in with the Firebase SDK (`frontend/src/firebase.ts`) and sends their Firebase ID token on every request as `Authorization: Bearer <token>`. The backend checks it in `backend/python/app/dependencies/auth.py` and only needs `FIREBASE_PROJECT_ID` in the root `.env` (no service-account key).

- Right after signing up with Firebase, the frontend calls `POST /auth/register` once to create the profile. People under 16 are rejected (a guardian registers them), and an email or phone number already on a profile gets a 409. `GET /users/me` returns the profile, including `role` (`attendee` or `admin`).
- 401 means the token is missing or invalid. 403 means the account has no profile yet, or isn't allowed to do that.
- Browsing events, event types and event series is public. Anyone logged in can register themselves or their children for an event and submit forms for them. Everything else is admin-only.
- Nobody can make themselves an admin through the API. To make your local account one:
  `docker exec -it don-db psql -U postgres -d dmwtd -c "UPDATE users SET role='admin' WHERE email='you@example.com';"`
- To call protected routes from Swagger (`/docs`):
  1. Get an ID token (the API key is `REACT_APP_FIREBASE_API_KEY` from `frontend/.env`). The first time, `accounts:signUp` creates your test account; after that, use `accounts:signInWithPassword` with the same body.
     ```bash
     curl -s "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=<API_KEY>" \
       -H "Content-Type: application/json" \
       -d '{"email": "you@example.com", "password": "...", "returnSecureToken": true}'
     ```
  2. Copy the `idToken` from the response (it lasts an hour) and paste it into **Authorize** in Swagger.
  3. The first time, call `POST /auth/register`, then make yourself an admin with the command above.
- Tests are logged in as a fake admin by default (`tests/functional/conftest.py`); `tests/functional/test_auth_routes.py` shows how to test as someone else.

## Version Control Guide

- Branch off `main` for all feature work. Use the format `your-name/short-description` (e.g. `pranav/readme-update`)
- Rebase onto `main` to integrate upstream changes (do not merge)
- Commits should be atomic and written in imperative tense (e.g. "Add volunteer registration endpoint")

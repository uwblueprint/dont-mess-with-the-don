"""Database seeding for development and testing.

Reads sample data from the CSV files in ``backend/python/seeds`` and inserts it
into the database. Each table has its own CSV file whose header row matches the
model's field names, so adding or editing sample data is just editing a CSV.

Usage (from inside the backend container)::

    # Seed the current environment's database (only if it is empty)
    python -m app.seed

    # Wipe the seeded tables and reload them from the CSVs
    python -m app.seed --reset

    # Seed the test database instead of the dev database
    APP_ENV=testing python -m app.seed --reset

The target database is chosen the same way the app chooses it: ``APP_ENV``
(``development`` -> dev DB, ``testing`` -> test DB).

Notes on the CSV format:
  * Blank cells are treated as "not provided" and fall back to the model default
    (usually ``NULL``), so you can leave optional columns empty.
  * JSON and array columns (e.g. ``form_json``, ``image_urls``) must contain
    valid JSON, e.g. ``{"waiver_required": true}`` or ``["a", "b"]``. Standard
    CSV quoting applies, so wrap those cells in double quotes and double any
    internal quotes.
  * Rows are inserted in file order, so within a self-referencing table (users)
    list parents before children.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import types as satypes
from sqlmodel import Session, SQLModel, create_engine, text

load_dotenv()

from app.models import get_database_url  # noqa: E402
from app.models.attendance import Attendance  # noqa: E402
from app.models.event import Event  # noqa: E402
from app.models.event_type import EventType  # noqa: E402
from app.models.form_submission import FormSubmission  # noqa: E402
from app.models.registration import Registration  # noqa: E402
from app.models.user import User  # noqa: E402

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"

# (csv filename, model). Order matters: parents before children so foreign keys
# resolve. Truncation happens in reverse order.
SEED_TABLES: list[tuple[str, type[SQLModel]]] = [
    ("event_types.csv", EventType),
    ("users.csv", User),
    ("events.csv", Event),
    ("form_submissions.csv", FormSubmission),
    ("registrations.csv", Registration),
    ("attendance.csv", Attendance),
]


def _json_and_array_columns(model: type[SQLModel]) -> set[str]:
    """Column names whose CSV cells should be parsed as JSON (JSON/JSONB/ARRAY)."""
    parsed: set[str] = set()
    for column in model.__table__.columns:  # type: ignore[attr-defined]
        if isinstance(column.type, (satypes.JSON, satypes.ARRAY)):
            parsed.add(column.name)
    return parsed


def _rows_from_csv(csv_path: Path, model: type[SQLModel]) -> list[SQLModel]:
    """Build (unpersisted) model instances from a CSV file."""
    parse_as_json = _json_and_array_columns(model)
    instances: list[SQLModel] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line_no, row in enumerate(reader, start=2):  # line 1 is the header
            data: dict = {}
            for key, raw in row.items():
                if key is None or raw is None:
                    continue
                value = raw.strip()
                if value == "":
                    continue  # fall back to the model's default
                if key in parse_as_json:
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"{csv_path.name} line {line_no}: column '{key}' is not "
                            f"valid JSON: {error}"
                        ) from error
                data[key] = value
            try:
                # The model coerces scalar strings (ints, bools, datetimes, UUIDs,
                # enums) via pydantic validation.
                instances.append(model(**data))
            except Exception as error:
                raise ValueError(
                    f"{csv_path.name} line {line_no}: could not build {model.__name__}: {error}"
                ) from error
    return instances


def _reset_sequence(session: Session, table_name: str) -> None:
    """Advance an integer-PK table's sequence past the largest seeded id."""
    sequence = session.execute(
        text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": table_name}
    ).scalar()
    if not sequence:
        return  # UUID primary key or no sequence
    session.execute(
        text(
            f"SELECT setval('{sequence}', "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), "
            f"(SELECT MAX(id) FROM {table_name}) IS NOT NULL)"
        )
    )


def _truncate(session: Session) -> None:
    """Empty every seeded table and reset identity sequences."""
    names = ", ".join(model.__tablename__ for _, model in SEED_TABLES)  # type: ignore[attr-defined]
    session.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    session.commit()


def _has_data(session: Session) -> bool:
    """True if any seeded table already contains rows."""
    for _, model in SEED_TABLES:
        count = session.execute(
            text(f"SELECT COUNT(*) FROM {model.__tablename__}")  # type: ignore[attr-defined]
        ).scalar()
        if count:
            return True
    return False


def seed(reset: bool = False) -> None:
    sync_url = get_database_url().replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        if reset:
            print("Truncating seeded tables ...")
            _truncate(session)
        elif _has_data(session):
            print("Database already contains data; skipping seed. Use --reset to wipe and reload.")
            return

        for filename, model in SEED_TABLES:
            csv_path = SEEDS_DIR / filename
            if not csv_path.exists():
                print(f"  {filename}: not found, skipping")
                continue
            instances = _rows_from_csv(csv_path, model)
            session.add_all(instances)
            session.commit()  # commit per table so later foreign keys resolve
            _reset_sequence(session, model.__tablename__)  # type: ignore[attr-defined]
            print(f"  {model.__tablename__}: inserted {len(instances)} rows")

        session.commit()

    print("Seeding complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with sample data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate the seeded tables before loading (wipe and reload).",
    )
    args = parser.parse_args()

    try:
        seed(reset=args.reset)
    except Exception as error:
        print(f"Seeding failed: {error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()

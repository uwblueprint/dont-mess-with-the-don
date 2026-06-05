from __future__ import with_statement

import logging
import os
import sys
from logging.config import fileConfig
from typing import Any

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from alembic import context  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

# Import all models to ensure they're registered with SQLModel
from app.models.entity import Entity  # noqa: E402, F401
from app.models.simple_entity import SimpleEntity  # noqa: E402, F401
from app.models.attendance import Attendance

# Alembic Config object
config = context.config

# Set up loggers
if config.config_file_name:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_database_url() -> str:
    if os.getenv("APP_ENV") == "production":
        return os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    else:
        return "postgresql://{username}:{password}@{host}:5432/{db}".format(
            username=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("DB_HOST"),
            db=(
                os.getenv("POSTGRES_DB_TEST")
                if os.getenv("APP_ENV") == "testing"
                else os.getenv("POSTGRES_DB_DEV")
            ),
        )


config.set_main_option("sqlalchemy.url", get_database_url())
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    def process_revision_directives(context: Any, revision: Any, directives: Any) -> None:
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    from sqlalchemy import create_engine

    connectable = create_engine(get_database_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from fastapi import FastAPI

from . import entity_routes, form_submission_routes, simple_entity_routes, user_routes


def init_app(app: FastAPI) -> None:
    """Initialize all routers with the FastAPI app"""
    app.include_router(entity_routes.router)
    app.include_router(form_submission_routes.router)
    app.include_router(simple_entity_routes.router)
    app.include_router(user_routes.router)

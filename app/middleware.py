"""Small helpers that run around every request."""

from fastapi import Request

from app.settings import settings


async def add_instance_header(request: Request, call_next):
    """Stamp every response with the name of the server copy that sent it.

    With two copies running, this proves which one answered each request.
    """
    response = await call_next(request)
    response.headers["X-Served-By"] = settings.instance_id
    return response

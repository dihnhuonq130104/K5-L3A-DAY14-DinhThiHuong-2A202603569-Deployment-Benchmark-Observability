"""API key authentication."""
import secrets
from fastapi import Header, HTTPException
from app.config import settings

def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not x_api_key or not settings.agent_api_key or not secrets.compare_digest(
        x_api_key.encode(), settings.agent_api_key.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

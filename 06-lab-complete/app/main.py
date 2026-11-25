"""Production agent with Redis-backed controls and JSON request logs."""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from redis.exceptions import RedisError
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                           "lvl": record.levelname, "event": record.getMessage(),
                           **getattr(record, "fields", {})}, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    # Uvicorn drains in-flight requests before this shutdown hook (SIGTERM).
    r.close()
    logger.info("shutdown")

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value

@app.middleware("http")
async def request_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info("request", extra={"fields": {"path": request.url.path,
                "status": response.status_code, "ms": round((time.perf_counter()-start)*1000, 3)}})
    return response

@app.exception_handler(RedisError)
async def redis_error(request: Request, exc: RedisError):
    logger.warning("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "State store unavailable"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("internal_error", extra={"fields": {"type": type(exc).__name__}})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}

@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    check_budget()
    answer = llm_ask(body.question)
    # Mock token estimate: approximately four characters per token.
    cost = record_cost(max(1, len(body.question)//4), max(1, len(answer)//4))
    return {"question": body.question, "answer": answer, "cost_usd": cost}

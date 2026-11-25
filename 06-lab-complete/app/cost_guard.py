"""Track shared daily and monthly mock token costs in Redis."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

def budget_keys():
    now = datetime.now(timezone.utc)
    return ["cost:day:" + now.strftime("%Y-%m-%d"),
            "cost:month:" + now.strftime("%Y-%m")]

def check_budget() -> None:
    daily, monthly = (float(v or 0) for v in r.mget(budget_keys()))
    if daily >= settings.daily_budget_usd or monthly >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="LLM budget exhausted")

def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = input_tokens / 1000 * PRICE_INPUT_PER_1K + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    pipe = r.pipeline(transaction=True)
    for key, ttl in zip(budget_keys(), (172800, 5356800)):
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, ttl)
    pipe.execute()
    return cost

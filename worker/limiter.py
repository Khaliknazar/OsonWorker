import asyncio
import time
from typing import Optional

LUA_ACQUIRE = r"""
-- KEYS[1] = rpm zset key
-- KEYS[2] = semaphore key
-- ARGV[1] = now (seconds)
-- ARGV[2] = window_s
-- ARGV[3] = rpm_limit (-1 means disabled)
-- ARGV[4] = conc_limit (-1 means disabled)
-- ARGV[5] = sem_ttl_ms

local rpm_key = KEYS[1]
local sem_key = KEYS[2]

local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local rpm = tonumber(ARGV[3])
local conc = tonumber(ARGV[4])
local sem_ttl = tonumber(ARGV[5])

-- Concurrency check (if enabled)
if conc > 0 then
  local current = tonumber(redis.call("GET", sem_key) or "0")
  if current >= conc then
    return {0, "concurrency"}
  end
end

-- RPM check (if enabled)
if rpm > 0 then
  local cutoff = now - window
  redis.call("ZREMRANGEBYSCORE", rpm_key, 0, cutoff)
  local count = tonumber(redis.call("ZCARD", rpm_key) or "0")
  if count >= rpm then
    return {0, "rpm"}
  end
end

-- Acquire semaphore (if enabled)
if conc > 0 then
  redis.call("INCR", sem_key)
  redis.call("PEXPIRE", sem_key, sem_ttl)
end

-- Consume RPM token (if enabled)
if rpm > 0 then
  local member = tostring(now) .. "-" .. tostring(redis.call("INCR", rpm_key .. ":seq"))
  redis.call("ZADD", rpm_key, now, member)
  redis.call("EXPIRE", rpm_key, math.ceil(window * 2))
end

return {1, "ok"}
"""

LUA_RELEASE = r"""
-- KEYS[1] = semaphore key
local sem_key = KEYS[1]
local current = tonumber(redis.call("GET", sem_key) or "0")
if current > 0 then
  redis.call("DECR", sem_key)
end
return 1
"""

class RateLimiter:
    def __init__(self, redis):
        self.redis = redis

    async def acquire(
        self,
        model_key: str,
        rpm: Optional[int],
        concurrency: Optional[int],
        window_s: int = 60,
        sem_ttl_ms: int = 10 * 60 * 1000,
        poll_s: float = 0.25,
        max_wait_s: float = 120.0,
    ):
        rpm_key = f"lim:rpm:{model_key}"
        sem_key = f"lim:sem:{model_key}"

        rpm_arg = int(rpm) if rpm and rpm > 0 else -1
        conc_arg = int(concurrency) if concurrency and concurrency > 0 else -1

        start = time.monotonic()
        while True:
            now = time.time()
            ok, reason = await self.redis.eval(
                LUA_ACQUIRE,
                keys=[rpm_key, sem_key],
                args=[now, window_s, rpm_arg, conc_arg, sem_ttl_ms],
            )
            if int(ok) == 1:
                return

            if time.monotonic() - start > max_wait_s:
                raise TimeoutError(f"Budget wait timeout: {model_key} ({reason})")

            await asyncio.sleep(poll_s)

    async def release(self, model_key: str):
        sem_key = f"lim:sem:{model_key}"
        await self.redis.eval(LUA_RELEASE, keys=[sem_key], args=[])

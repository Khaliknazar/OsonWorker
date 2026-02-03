import os
import asyncio
import logging

from worker.policies import POLICIES
from worker.limiter import RateLimiter
from worker.telegram import TelegramClient, OsonIntelektServer, TelegramTokenFilter
from worker.handlers import HANDLERS

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").addFilter(TelegramTokenFilter())

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

tg = TelegramClient(BOT_TOKEN)
oson = OsonIntelektServer()


async def generate_and_send(ctx, payload: dict, user_id: int):
    redis = ctx["redis"]

    model_key = payload["model_key"]
    if model_key not in POLICIES:
        await tg.send_text(user_id, f"Unknown model: <code>{model_key}</code>")
        return
    if model_key not in HANDLERS:
        await tg.send_text(user_id, f"No handler for model: <code>{model_key}</code>")
        return

    policy = POLICIES[model_key]
    handler = HANDLERS[model_key]
    limiter = RateLimiter(redis)

    # ✅ LIMITS HERE (global across all VPS)
    try:
        await limiter.acquire(
            model_key=model_key,
            rpm=policy.rpm,
            concurrency=policy.concurrency,
            max_wait_s=120,  # if queue is huge, fail fast
        )
    except TimeoutError:
        await tg.send_text(user_id, f"Navbat ko'p, Iltimos keginroq qayta urinib ko'ring\n\nPrompt:\n<code>{payload.get('prompt', '')}</code>")
        return

    try:
        result = await asyncio.wait_for(handler(payload), timeout=policy.timeout_s)

        if not result.get("ok"):
            await tg.send_text(
                user_id,
                f"Yaratishda xatolik! Qayta urinib ko'ring\n{result.get('error')}.\n\nPrompt:\n"
                f"<code>{payload.get('prompt', '')}</code>"
            )
            await oson.send_job_status(payload['job_id'], 'FAILED')
            return

        mime = result["mime"]
        ext = mime.split("/")[-1]
        filename = f"OsonIntelektBot.{ext}"

        await tg.send_document(user_id, filename, result["bytes"], mime, caption="@OsonIntelektBot")
        await tg.send_text(user_id, f"✅ Yakunlandi!\n\nPrompt:\n<blockquote expandable>{payload.get('prompt', '')}</blockquote>")
        await oson.send_job_status(payload['job_id'], 'FINISHED')
    except Exception:
        log.exception("Generation failed")
        try:
            await oson.send_job_status(payload['job_id'], 'FAILED')
        except Exception as e:
            log.error(f"Error sending status to server! job_id: {payload['job_id']} error: {e}")

        try:
            await tg.send_text(user_id, f"Xato, Iltimos keginroq qayta urinib ko'ring.\n\nPrompt:\n<code>{payload.get('prompt', '')}</code>")
        except:
            pass
        raise
    finally:
        # ✅ release concurrency slot
        await limiter.release(model_key)

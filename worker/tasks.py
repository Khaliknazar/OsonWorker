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


async def get_prompt(data: dict) -> str | None:
    return (
            data.get("body", {}).get("prompt")
            or data.get("body", {}).get("input", {}).get("prompt")
    )


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
            window_s=policy.window_s,
            concurrency=policy.concurrency,
            max_wait_s=120,  # if queue is huge, fail fast
        )
    except TimeoutError:
        await tg.send_text(user_id,
                           f"<tg-emoji emoji-id='5258474669769497337'>⚠️</tg-emoji>️ Navbat ko'p, Iltimos keginroq qayta urinib ko'ring\n\nPrompt:\n<code>{payload.get('prompt', '')}</code>")
        return

    prompt = await get_prompt(payload)
    try:
        result = await asyncio.wait_for(handler(payload), timeout=policy.timeout_s)
        logging.info(result)

        if not result.get("ok"):
            await tg.send_text(
                user_id,
                f"<tg-emoji emoji-id='5258474669769497337'>⚠️</tg-emoji>️ Yaratishda xatolik! Qayta urinib ko'ring\n{result.get('error')}.\n\nPrompt:\n"
                f"<blockquote expandable>{prompt}</blockquote>"
            )
            await oson.send_job_status(payload['job_id'], 'FAILED')
            return

        if result.get('task_id', False):
            await tg.send_text(user_id,
                               f"<tg-emoji emoji-id='5283112212792121487'>©️</tg-emoji>️ {payload['media_type']} tayyornalmoqda!\n\n"
                               f"<tg-emoji emoji-id='5249231689695115145'>©️</tg-emoji>️ Prompt:\n<blockquote expandable>{prompt}</blockquote>")
            await oson.send_job_status(payload['job_id'], 'PROCESSING', task_id=result.get('task_id'))
            return

        mime = result["mime"]
        ext = mime.split("/")[-1]
        filename = f"OsonIntelektBot.{ext}"

        await tg.send_document(user_id, filename, result["bytes"], mime, caption="@OsonIntelektBot")
        await tg.send_text(user_id, f"<tg-emoji emoji-id='5260416304224936047'>©️</tg-emoji>️ Yakunlandi!\n\n"
                                    f"<tg-emoji emoji-id='5249231689695115145'>©️</tg-emoji>️ Prompt:\n<blockquote expandable>{prompt}</blockquote>")
        await oson.send_job_status(payload['job_id'], 'FINISHED')
    except Exception:
        log.exception("Generation failed")
        try:
            await oson.send_job_status(payload['job_id'], 'FAILED')
        except Exception as e:
            log.error(f"Error sending status to server! job_id: {payload['job_id']} error: {e}")

        try:
            await tg.send_text(user_id,
                               f"<tg-emoji emoji-id='5258474669769497337'>⚠️</tg-emoji>️ Xato, Iltimos keginroq qayta urinib ko'ring.\n\n<tg-emoji emoji-id='5249231689695115145'>©️</tg-emoji>️ Prompt:\n<blockquote expandable>{prompt}</blockquote>")
        except:
            pass
        raise
    finally:
        # ✅ release concurrency slot
        await limiter.release(model_key)

import os
import time
import asyncio
import logging

from worker.policies import POLICIES
from worker.limiter import RateLimiter
from worker.telegram import TelegramClient, OsonIntelektServer, TelegramTokenFilter
from worker.handlers import HANDLERS, POLL_HANDLERS  # <-- добавь POLL_HANDLERS в handlers/__init__.py

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").addFilter(TelegramTokenFilter())

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

tg = TelegramClient(BOT_TOKEN)
oson = OsonIntelektServer()

DEFAULT_POLL_EVERY = int(os.getenv("KLING_POLL_EVERY", "5"))


async def poll_and_send(ctx, payload: dict, user_id: int):
    """
    Универсальный polling-job для async моделей (Kling и т.п.)
    payload должен содержать:
      - model_key
      - job_id
      - task_id
      - started_at (unix seconds)
      - poll_after (seconds)
      - timeout_s (seconds)
    """
    arq = ctx["arq_redis"]

    model_key = payload["model_key"]
    job_id = payload["job_id"]
    task_id = payload["task_id"]

    started_at = int(payload.get("started_at") or int(time.time()))
    timeout_s = int(payload.get("timeout_s") or 900)
    poll_after = int(payload.get("poll_after") or DEFAULT_POLL_EVERY)

    poller = POLL_HANDLERS.get(model_key)
    if not poller:
        await tg.send_text(user_id, f"No poll handler for model: <code>{model_key}</code>")
        await oson.send_job_status(job_id, "FAILED")
        return

    # общий таймаут ожидания
    if int(time.time()) - started_at > timeout_s:
        await tg.send_text(user_id, "⏰ Video juda uzoq tayyor bo'lyapti (timeout).")
        await oson.send_job_status(job_id, "FAILED")
        return

    # один poll-запрос
    try:
        st = await poller(payload, task_id)  # poll(payload, task_id) -> {"ok", "done", "url"/"error"}
    except Exception as e:
        log.warning("poll error model=%s task_id=%s err=%s", model_key, task_id, e)
        await arq.enqueue_job("poll_and_send", payload, user_id, _defer_by=poll_after)
        return

    # FAIL (готово, но с ошибкой)
    if not st.get("ok") and st.get("done"):
        await tg.send_text(user_id, f"❌ Xato: {st.get('error')}")
        await oson.send_job_status(job_id, "FAILED")
        return

    # DONE (есть url)
    if st.get("ok") and st.get("done"):
        url = st.get("url")
        await tg.send_text(user_id, f"✅ Tayyor!\n{url}")
        await oson.send_job_status(job_id, "FINISHED")
        return

    # NOT DONE -> запланировать следующий poll
    await arq.enqueue_job("poll_and_send", payload, user_id, _defer_by=poll_after)


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
    limit_key = policy.limit_key or model_key
    try:
        await limiter.acquire(
            model_key=limit_key,
            rpm=policy.rpm,
            concurrency=policy.concurrency,
            max_wait_s=120,  # if queue is huge, fail fast
        )
    except TimeoutError:
        await tg.send_text(
            user_id,
            f"Navbat ko'p, Iltimos keginroq qayta urinib ko'ring\n\nPrompt:\n<code>{payload.get('prompt', '')}</code>",
        )
        return

    try:
        result = await asyncio.wait_for(handler(payload), timeout=policy.timeout_s)

        if not result.get("ok"):
            await tg.send_text(
                user_id,
                f"Yaratishda xatolik! Qayta urinib ko'ring\n{result.get('error')}.\n\nPrompt:\n"
                f"<code>{payload.get('prompt', '')}</code>",
            )
            await oson.send_job_status(payload["job_id"], "FAILED")
            return

        # ✅ async models (Kling): handler вернул task_id, дальше poll отдельным job
        if result.get("type") == "async":
            arq = ctx["arq_redis"]

            poll_after = int(result.get("poll_after", DEFAULT_POLL_EVERY))
            timeout_s = int(result.get("timeout_s", policy.timeout_s))

            poll_payload = {
                **payload,
                "task_id": result["task_id"],
                "started_at": int(time.time()),
                "poll_after": poll_after,
                "timeout_s": timeout_s,
            }

            await tg.send_text(user_id, "🎬 Video generatsiya boshlandi, kuting...")
            await arq.enqueue_job("poll_and_send", poll_payload, user_id, _defer_by=poll_after)
            return

        # ✅ обычный режим: bytes/mime -> отправляем документом
        mime = result["mime"]
        ext = mime.split("/")[-1]
        filename = f"OsonIntelektBot.{ext}"

        await tg.send_document(user_id, filename, result["bytes"], mime, caption="@OsonIntelektBot")
        await tg.send_text(
            user_id,
            f"✅ Yakunlandi!\n\nPrompt:\n<blockquote expandable>{payload.get('prompt', '')}</blockquote>",
        )
        await oson.send_job_status(payload["job_id"], "FINISHED")

    except Exception:
        log.exception("Generation failed")
        try:
            await oson.send_job_status(payload["job_id"], "FAILED")
        except Exception as e:
            log.error(f"Error sending status to server! job_id: {payload['job_id']} error: {e}")

        try:
            await tg.send_text(
                user_id,
                f"Xato, Iltimos keginroq qayta urinib ko'ring.\n\nPrompt:\n<code>{payload.get('prompt', '')}</code>",
            )
        except Exception:
            pass
        raise
    finally:
        # ✅ release concurrency slot
        await limiter.release(limit_key)

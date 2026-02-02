import asyncio
import httpx
from handlers import gemini2
from handlers.registry import MODEL_CONFIGS
from config import BOT_TOKEN

SEND_MESSAGE = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
SEND_DOC = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
ACTION = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"

HANDLERS = {
    "gemini_flash_image": gemini2.run,
    # "my_video_model": my_video_model.run,
    # "flux": flux.run,
}


async def send_text(user_id: int, text: str):
    async with httpx.AsyncClient(timeout=30) as s:
        await s.post(SEND_MESSAGE, data={"chat_id": user_id, "text": text, "parse_mode": "HTML"})


async def send_document(user_id: int, filename: str, file_bytes: bytes, mime_type: str, caption: str = ""):
    async with httpx.AsyncClient(timeout=120) as s:
        await s.post(ACTION, data={"chat_id": user_id, "action": "upload_document"})
        files = {"document": (filename, file_bytes, mime_type)}
        await s.post(SEND_DOC, data={"chat_id": user_id, "caption": caption}, files=files)


async def generate_and_send(ctx, payload: dict, user_id: int):
    model_key = payload["model_key"]
    cfg = MODEL_CONFIGS[model_key]
    handler = HANDLERS[model_key]

    # (Optional) global rate/concurrency control goes here (Redis-based)

    result = await asyncio.wait_for(handler(payload), timeout=cfg.timeout_s)

    if not result["ok"]:
        await send_text(user_id, "Xatolik! Qayta urinib ko'ring.\n\nPrompt:\n"
                                 f"<code>{payload.get('prompt', '')}</code>")
        return

    mime = result["mime"]
    ext = mime.split("/")[-1]
    await send_document(user_id, f"OsonIntelektBot.{ext}", result["bytes"], mime, "@OsonIntelektBot")

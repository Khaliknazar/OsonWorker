import os

import httpx

class TelegramClient:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base = f"https://api.telegram.org/bot{bot_token}"

    async def send_text(self, chat_id: int, text: str):
        async with httpx.AsyncClient(timeout=30) as s:
            await s.post(
                f"{self.base}/sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )

    async def send_action(self, chat_id: int, action: str):
        async with httpx.AsyncClient(timeout=10) as s:
            await s.post(f"{self.base}/sendChatAction", data={"chat_id": chat_id, "action": action})

    async def send_document(self, chat_id: int, filename: str, file_bytes: bytes, mime_type: str, caption: str = ""):
        async with httpx.AsyncClient(timeout=180) as s:
            await self.send_action(chat_id, "upload_document")
            files = {"document": (filename, file_bytes, mime_type)}
            data = {"chat_id": chat_id, "caption": caption}
            await s.post(f"{self.base}/sendDocument", data=data, files=files)


class OsonIntelektServer:
    def __init__(self):
        self.base = os.getenv("BASE_URL")

    async def send_job_status(self, job_id: int, status: str):
        async with httpx.AsyncClient(timeout=30) as s:
            data = {'job_id': job_id, 'status': status}
            await s.post(f"{self.base}/api/job-status", data=data)


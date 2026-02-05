import time
import jwt
import httpx
from worker import config

BASE = "https://api-singapore.klingai.com"

def make_jwt() -> str:
    now = int(time.time())
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {"iss": config.KLING_ACCESS_KEY, "exp": now + 60, "nbf": now - 5}
    return jwt.encode(payload, config.KLING_SECRET_KEY, headers=headers)

async def post_json(path: str, body: dict) -> dict:
    token = make_jwt()
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.post(
            f"{BASE}{path}",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            json=body,
        )
        r.raise_for_status()
        return r.json()

async def get_json(path: str) -> dict:
    token = make_jwt()
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.get(
            f"{BASE}{path}",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()

def parse_status(data_json: dict) -> dict:
    # под твой формат
    data = data_json.get("data") or {}
    task_status = data.get("task_status")
    if task_status == "succeed":
        videos = (data.get("task_result") or {}).get("videos") or []
        url = videos[0].get("url") if videos else None
        if not url:
            return {"ok": False, "done": True, "error": "done but url missing"}
        return {"ok": True, "done": True, "url": url}

    if task_status == "failed":
        return {"ok": False, "done": True, "error": data.get("task_status_msg") or "failed"}

    # submitted / processing / etc
    return {"ok": True, "done": False, "status": task_status}

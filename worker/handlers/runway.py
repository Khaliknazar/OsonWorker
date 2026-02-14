import time

import httpx

from worker import config

BASE = 'https://api.dev.runwayml.com'


async def post_json(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as s:
        r = await s.post(
            f"{BASE}{path}",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.RUNWAY_API_KEY}",
                     "X-Runway-Version": "2024-11-06"},
            json=body,
        )
        r.raise_for_status()
        js = await r.json()
        if r.status_code != 200:
            return {'code': r.status_code, 'error': js['error']}
        return js


async def create_task(payload: dict):
    j = await post_json(payload["request_url"], payload['body'])
    task_id = j.get("id")
    if not task_id:
        return {"ok": False, "error": f"create failed: {j}"}

    return {"ok": True, "task_id": task_id}


async def get_task(job_data: dict):
    """
    Poll AI server until job is done
    """

    task_id = job_data["task_id"]
    started_at = job_data["started_at"]

    # timeout protection
    if time.time() - started_at > 10 * 60:  # 10 minutes
        raise RuntimeError("Generation timeout")

    j = await post_json(f'/v1/tasks/{task_id}')

    status = j["status"]

    if status == "SUCCEEDED":
        result_url = j["result_url"]

        # ✅ FINAL RESULT
        return {
            "status": status,
            "ok": True,
            "result_url": result_url,
        }

    if status == "FAILED":
        return {"ok": False, "error": j["failure"], 'status': status}

    return {'ok': True, 'status': status, 'progress': j['progress']}




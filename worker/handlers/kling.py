import logging
import os
import asyncio
import time

import httpx
import jwt
from pydantic import BaseModel, Field

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


async def image_to_video(payload: dict) -> dict:
    request_url = '/v1/videos/text2video'
    body = {
        "model_name": "kling-v2-6",
        "mode": "pro",
        "duration": payload['duration'],
        "prompt": payload['prompt'],
        'sound': payload['sound'],
        "callback_url": f'{config.BASE_URL}/kling/status'
    }
    if payload['image']:
        body['image'] = payload['image']

        if payload['image_tail']:
            body['image_tail'] = payload['image_tail']
        request_url = '/v1/videos/image2video'
    else:
        body['aspect_ratio'] = payload['aspect_ratio']

    j = await post_json(request_url, body)
    data = j.get("data") or {}
    task_id = data.get("task_id")
    if not task_id:
        return {"ok": False, "error": f"create failed: {j}"}

    return {'ok': True, 'task_id': task_id}


async def motion_control(payload: dict):
    pass


async def run(payload: dict) -> dict:
    if bool(payload["is_test"]):
        return {'ok': False, 'error': "Fake error"}

    try:
        handlers = {'image2video': image_to_video,
                    'motion-control': motion_control}

        r = await handlers[payload["generation_type"]](payload)
        if not r.get('ok'):
            return {'ok': False, 'error': r.get('error')}

        task_id = r.get('task_id')

    except Exception as e:
        logging.exception(e)
        return {'ok': False, 'error': 'Error when creating image'}

    return {
        "ok": True,
        "task_id": task_id
    }

import logging

import httpx

from worker import config


class KieApi:
    def __init__(self):
        self.base = "https://api.kie.ai"
        self.headers = {
            "Authorization": f"Bearer {config.KIE_API_KEY}",
            "Content-Type": "application/json"
        }

    async def create_task(self, payload: dict, request_url: str):
        async with httpx.AsyncClient(timeout=30) as s:
            r = await s.post(self.base + request_url, headers=self.headers, json=payload)
            r.raise_for_status()
            data = r.json()
            if data.get('code', 0) == 200:
                return {'ok': True, 'task_id': data['data']['taskId']}

            logging.error(data['msg'])
            return {'ok': False, 'error': data['msg']}


async def run(payload: dict) -> dict:
    if bool(payload["is_test"]):
        return {'ok': False, 'error': "Fake error"}

    kie_api = KieApi()
    try:

        body = payload.get('body')
        request_url = payload.get('request_url')
        s = await kie_api.create_task(body, request_url)
    except Exception as e:
        logging.error(e)
        return {'ok': False, 'error': str(e)}

    if not s.get('ok'):
        return {'ok': False, 'error': s.get('error')}

    return {'ok': True, 'task_id': s.get('task_id')}

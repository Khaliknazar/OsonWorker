import logging

import httpx

from worker import config


class KieApi:
    def __init__(self):
        self.base = "https://api.kie.ai/api/v1/jobs/createTask"
        self.api_key = config.KIE_API_KEY

    async def create_task(self, payload: dict):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=30) as s:
            r = await s.post(self.base, headers=headers, json=payload)
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
        s = await kie_api.create_task(body)
    except Exception as e:
        logging.error(e)
        return {'ok': False, 'error': str(e)}

    if not s.get('ok'):
        return {'ok': False, 'error': s.get('error')}

    return {'ok': True, 'task_id': s.get('task_id')}

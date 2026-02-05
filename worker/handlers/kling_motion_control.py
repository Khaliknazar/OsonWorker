from .kling_common import post_json, get_json, parse_status

async def run(payload: dict) -> dict:
    # TODO: подставь правильный endpoint и поля из motionControl API
    body = {
        "model_name": "kling-v2-6",
        "mode": payload.get("mode", "pro"),
        "duration": str(payload.get("duration", 5)),
        "image": payload["image"],
        "prompt": payload.get("prompt"),
        # motion control параметры:
        # "motion_control": payload["motion_control"],
        # или reference видео, или trajectory — как в их доке
    }

    j = await post_json("/v1/videos/motion-control", body)
    data = j.get("data") or {}
    task_id = data.get("task_id")
    if not task_id:
        return {"ok": False, "error": f"create failed: {j}"}

    return {"ok": True, "type": "async", "task_id": task_id, "poll_after": 5, "timeout_s": 900}

async def poll(payload: dict, task_id: str) -> dict:
    j = await get_json(f"/v1/videos/motion-control/{task_id}")  # <-- поправишь
    return parse_status(j)

from .kling_common import post_json, get_json, parse_status


async def run(payload: dict) -> dict:
    # imageToVideo
    body = {
        "model_name": "kling-v2-6",
        "mode": payload.get("mode", "pro"),
        "duration": str(payload.get("duration", 5)),
        "image": payload["image"],
        "prompt": payload.get("prompt"),
    }
    if payload.get("image_tail"):
        body["image_tail"] = payload["image_tail"]

    j = await post_json("/v1/videos/image2video", body)
    data = j.get("data") or {}
    task_id = data.get("task_id")
    if not task_id:
        return {"ok": False, "error": f"create failed: {j}"}

    return {"ok": True, "type": "async", "task_id": task_id, "poll_after": 5, "timeout_s": 900}


async def poll(payload: dict, task_id: str) -> dict:
    j = await get_json(f"/v1/videos/image2video/{task_id}")
    return parse_status(j)

import logging
import os
import asyncio
import mimetypes
import requests
from google.genai.types import Part, GenerateContentConfig, FinishReason, ImageConfig

from worker.config import client

DOWNLOAD_SEM = asyncio.Semaphore(int(os.getenv("DOWNLOAD_CONCURRENCY", "20")))


def _download_sync(url: str) -> bytes:
    return requests.get(url, timeout=30).content


async def _download(url: str) -> bytes:
    async with DOWNLOAD_SEM:
        return await asyncio.to_thread(_download_sync, url)


async def run(payload: dict) -> dict:
    if bool(payload["is_test"]):
        return {'ok': False, 'error': "Fake error"}
    contents = [payload["prompt"]]

    for img_url in payload.get("images", []):
        image_bytes = await _download(img_url)
        mime_type = mimetypes.guess_type(img_url)[0] or "image/jpeg"
        contents.append(Part.from_bytes(data=image_bytes, mime_type=mime_type))

    try:

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=GenerateContentConfig(response_modalities=["Image"],
                                         image_config=ImageConfig(
                                             aspect_ratio=payload["aspect_ratio"],
                                             image_size=payload["quality"],
                                         )),
        )
    except Exception as e:
        logging.exception(e)
        return {'ok': False, 'error': 'Error when creating image'}

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return {'ok': False, 'error': 'No images in response found'}

    cand0 = candidates[0]
    finish_reason = getattr(cand0, "finish_reason", None)
    if finish_reason is not None and finish_reason != FinishReason.STOP:
        return {'ok': False, 'error': "Finish reason doesn't match"}

    image_part = next(p.inline_data for p in response.candidates[0].content.parts if p.inline_data)

    return {
        "ok": True,
        "bytes": image_part.data,
        "mime": image_part.mime_type or "image/png",
    }

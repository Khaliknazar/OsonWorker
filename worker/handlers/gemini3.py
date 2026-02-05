import logging
import os
import asyncio
import mimetypes
import requests
from google import genai
from google.genai.types import Part, GenerateContentConfig, FinishReason, ImageConfig

from worker.config import client

DOWNLOAD_SEM = asyncio.Semaphore(int(os.getenv("DOWNLOAD_CONCURRENCY", "20")))


def _download_sync(url: str) -> bytes:
    return requests.get(url, timeout=30).content


async def _download(url: str) -> bytes:
    async with DOWNLOAD_SEM:
        return await asyncio.to_thread(_download_sync, url)


def _make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


async def run(payload: dict) -> dict:
    if bool(payload["is_test"]):
        return {'ok': False, 'error': "Fake error"}
    try:
        contents = [payload["prompt"]]

        for img_url in payload.get("images", []):
            image_bytes = await _download(img_url)
            mime_type = mimetypes.guess_type(img_url)[0] or "image/jpeg"
            contents.append(Part.from_bytes(data=image_bytes, mime_type=mime_type))

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
        if not response.candidates:
            logging.error("No candidates in response: %s", response)
            return {"ok": False, "error": "No response candidates from model"}

        candidate = response.candidates[0]
        if candidate.finish_reason != FinishReason.STOP:
            logging.error(response)
            return {"ok": False, "error": f"finish reason {candidate.finish_reason}"}

        parts_with_data = [p for p in (candidate.content.parts or []) if p.inline_data]
        if not parts_with_data:
            logging.error("No image in response: %s", response)
            return {"ok": False, "error": "No image in response"}

        image_part = parts_with_data[0].inline_data
        return {
            "ok": True,
            "bytes": image_part.data,
            "mime": image_part.mime_type or "image/png",
        }
    except Exception as e:
        logging.exception("Image generation failed")
        return {"ok": False, "error": str(e)}

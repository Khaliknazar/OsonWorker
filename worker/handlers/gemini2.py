import os
import asyncio
import mimetypes
import requests
from google import genai
from google.genai.types import Part, GenerateContentConfig, FinishReason

from worker.config import client

DOWNLOAD_SEM = asyncio.Semaphore(int(os.getenv("DOWNLOAD_CONCURRENCY", "10")))

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

    contents = [payload["prompt"]]

    for img_url in payload.get("images", []):
        image_bytes = await _download(img_url)
        mime_type = mimetypes.guess_type(img_url)[0] or "image/jpeg"
        contents.append(Part.from_bytes(data=image_bytes, mime_type=mime_type))

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash-image",
        contents=contents,
        config=GenerateContentConfig(response_modalities=["Image"]),
    )

    if response.candidates[0].finish_reason == FinishReason.NO_IMAGE:
        return {"ok": False, "error": "NO_IMAGE"}

    image_part = next(p.inline_data for p in response.candidates[0].content.parts if p.inline_data)

    return {
        "ok": True,
        "bytes": image_part.data,
        "mime": image_part.mime_type or "image/png",
    }

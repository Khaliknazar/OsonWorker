from typing import Literal, Union, List

from pydantic import BaseModel, Field
import config


class NanoBananaImageEditInputModel(BaseModel):
    prompt: str = Field(..., max_length=5000)
    image_url: List[str] = Field(..., max_length=10)
    output_format: Literal['png', 'jpeg'] = 'png'
    image_size: Literal["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"] = "auto"


class NanoBananaImageEditRequest(BaseModel):
    model: Literal['google/nano-banana-edit'] = 'google/nano-banana-edit'
    callBackUrl: str
    input: NanoBananaImageEditInputModel


class NanoBananaImageInputModel(BaseModel):
    prompt: str = Field(..., max_length=5000)
    output_format: Literal['png', 'jpeg'] = 'png'
    image_size: Literal["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"] = "auto"


class NanoBananaImageRequest(BaseModel):
    model: Literal['google/nano-banana'] = 'google/nano-banana'
    callBackUrl: str
    input: NanoBananaImageInputModel


class NanoBananaProInputModel(BaseModel):
    prompt: str = Field(..., max_length=5000)
    image_url: List[str] = Field(..., max_length=8)
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"] = "auto"
    resolution: Literal['1K', '2K', '4K'] = '1K'


class NanoBananaProRequest(BaseModel):
    model: Literal['nano-banana-pro'] = 'nano-banana-pro'
    callBackUrl: str
    input: NanoBananaProInputModel


class KlingTextToVideoInputModel(BaseModel):
    prompt: str = Field(..., max_length=1000)
    sound: bool
    aspect_ratio: Literal['1:1', '16:9', '9:16']
    duration: Literal['5', '10']


class KlingTextToVideoRequest(BaseModel):
    model: Literal['kling-2.6/text-to-video'] = 'kling-2.6/text-to-video'
    callBackUrl: str
    input: KlingTextToVideoInputModel


class KlingImageToVideoInputModel(BaseModel):
    prompt: str = Field(..., max_length=1000)
    image_urls: List[str] = Field(..., min_length=1, max_length=1)
    sound: bool
    duration: Literal['5', '10']


class KlingImageToVideoRequest(BaseModel):
    model: Literal['kling-2.6/image-to-video'] = 'kling-2.6/image-to-video'
    callBackUrl: str
    input: KlingImageToVideoInputModel


class KlingMotionControlInputModel(BaseModel):
    prompt: str = Field(..., max_length=2500)
    input_urls: List[str] = Field(..., min_length=1, max_length=1)
    video_urls: List[str] = Field(..., min_length=1, max_length=1)
    character_orientation: Literal['image', 'video'] = 'video'
    mode: Literal['720p', '1080p']


class KlingMotionControlRequest(BaseModel):
    model: Literal['kling-2.6/motion-control'] = 'kling-2.6/motion-control'
    callBackUrl: str
    input: KlingMotionControlInputModel

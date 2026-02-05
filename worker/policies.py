from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelPolicy:
    rpm: Optional[int] = None
    concurrency: Optional[int] = None
    timeout_s: int = 600
    limit_key: Optional[str] = None


POLICIES: dict[str, ModelPolicy] = {
    # image
    "gemini_2_5_image": ModelPolicy(rpm=500, concurrency=50),
    "gemini_3_image": ModelPolicy(rpm=20, concurrency=4),
    "kling_image_to_video": ModelPolicy(rpm=60, concurrency=1, timeout_s=900, limit_key="kling"),
    "kling_motion_control": ModelPolicy(rpm=60, concurrency=1, timeout_s=900, limit_key="kling"),

    # # examples: local/other providers
    # "sdxl_api": ModelPolicy(rpm=60, concurrency=10),
    # "flux_api": ModelPolicy(rpm=10, concurrency=2),
    #
    # # only concurrency ограничение (пример)
    # "video_model_x": ModelPolicy(rpm=None, concurrency=1),
    #
    # # если реально без лимитов (не советую)
    # "unlimited": ModelPolicy(),
}

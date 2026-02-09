from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelPolicy:
    rpm: Optional[int] = None,
    window_s: int = 60
    concurrency: Optional[int] = None
    timeout_s: int = 600


POLICIES: dict[str, ModelPolicy] = {
    "gemini_2_5_image": ModelPolicy(rpm=500, concurrency=50),
    "gemini_3_image": ModelPolicy(rpm=20, concurrency=4),
    "kling_2_6_video": ModelPolicy(concurrency=3),
    'kieapi': ModelPolicy(concurrency=10, rpm=20, window_s=20),

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

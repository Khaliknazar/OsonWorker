from . import gemini2, gemini3, kling_image_to_video, kling_motion_control

HANDLERS = {
    "gemini_2_5_image": gemini2.run,
    "gemini_3_image": gemini3.run,
    "kling_image_to_video": kling_image_to_video.run,
    "kling_motion_control": kling_motion_control.run,
}

POLL_HANDLERS = {
    "kling_image_to_video": kling_image_to_video.poll,
    "kling_motion_control": kling_motion_control.poll,
}

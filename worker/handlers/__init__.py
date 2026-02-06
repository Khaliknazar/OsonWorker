from . import gemini2, gemini3, kling

HANDLERS = {
    "gemini_2_5_image": gemini2.run,
    "gemini_3_image": gemini3.run,
    "kling_2_6_video": kling.run,
}

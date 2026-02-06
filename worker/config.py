import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


BOT_TOKEN = os.getenv("BOT_TOKEN")
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")
SERVER_KEY = os.getenv("SERVER_KEY")

import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
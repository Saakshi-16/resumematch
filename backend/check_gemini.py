"""
Run this to check your Gemini API key works:   python check_gemini.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
key = os.environ.get("GEMINI_API_KEY", "").strip()
model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

if not key:
    print("❌ No GEMINI_API_KEY found. Create backend/.env (copy .env.example) and paste your key.")
    raise SystemExit(1)

print(f"Key found (starts with {key[:6]}...). Testing model '{model}'...")
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)  # keep a reference so the connection stays open
    reply = client.models.generate_content(
        model=model,
        contents="Reply with exactly: Gemini is working",
        config=types.GenerateContentConfig(automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)),
    )
    print("✅ Success! Gemini replied:", reply.text.strip())
except Exception as e:  # noqa: BLE001
    print("❌ Gemini error:", str(e)[:400])
    print("\nIf it says the model is not found, try changing GEMINI_MODEL in .env to gemini-3.8-flash or gemini-3.1-flash-lite")

"""
STEP 6 of RAG: the "Generation" part. Sends a prompt to Google Gemini and returns the answer.
"""
import json
import re

from django.conf import settings

_client = None


class LLMError(Exception):
    pass


def configured():
    return bool(settings.GEMINI_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def friendly_error(e):
    msg = str(e)
    low = msg.lower()
    if "api key not valid" in low or "api_key_invalid" in low:
        return "The Gemini API key is not valid. Check GEMINI_API_KEY."
    if "403" in msg or "permission" in low:
        return "Gemini refused the request (403). Check the API key is copied correctly and the Gemini API is enabled for it."
    if "429" in msg or "quota" in low or "resource_exhausted" in low:
        return "Gemini free-tier limit reached. Wait a minute and try again."
    if "not found" in low and "model" in low:
        return f"Gemini model '{settings.GEMINI_MODEL}' was not found. Change GEMINI_MODEL."
    return f"Gemini request failed: {msg[:200]}"


def generate(prompt, system=None, as_json=False, temperature=0.2):
    if not configured():
        raise LLMError("No GEMINI_API_KEY configured.")
    from google.genai import types
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json" if as_json else None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    try:
        resp = _get_client().models.generate_content(model=settings.GEMINI_MODEL, contents=prompt, config=config)
        text = (resp.text or "").strip()
    except Exception as e:  # noqa: BLE001
        raise LLMError(friendly_error(e)) from e
    if not as_json:
        return text
    return parse_json(text)


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise LLMError("The AI returned an unexpected format. Please try again.")

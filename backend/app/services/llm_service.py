from __future__ import annotations

import json
from google import genai
from app.config import get_settings


class LLMService:
    """Gemini LLM service using the new google-genai SDK with forced stable models."""

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.gemini_api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)

    def _ensure_client(self):
        if self.client is None:
            raise RuntimeError("GEMINI_API_KEY is not set in environment.")

    def generate_text(self, prompt: str) -> str:
        self._ensure_client()
        
        # Güncel ve kararlı çalışan model ismini doğrudan geçiyoruz
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text

    def generate_json(self, prompt: str) -> dict:
        self._ensure_client()
        
        # Güncel ve kararlı çalışan model ismini doğrudan geçiyoruz
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            cleaned = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)
import os
import random
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    def __init__(self):
        self.keys = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
        self.current_key_index = 0
        self._configure_genai()

    def _configure_genai(self):
        if not self.keys:
            raise ValueError("No Gemini API keys found in environment variables.")
        
        # Rotation logic: Pick a random key or use round-robin
        # For simplicity in this implementation, we pick the "next" one
        key = self.keys[self.current_key_index]
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def rotate_key(self):
        if self.keys:
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            self._configure_genai()

    async def generate_content(self, prompt: str, attempt: int = 0):
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            # If rate limited or other API error, try rotating up to len(keys) times
            if attempt >= len(self.keys):
                print(f"All Gemini keys exhausted. Failed to generate content.")
                raise e
            print(f"Error with key {self.current_key_index}: {e}. Rotating...")
            self.rotate_key()
            return await self.generate_content(prompt, attempt + 1)

gemini_service = GeminiService()

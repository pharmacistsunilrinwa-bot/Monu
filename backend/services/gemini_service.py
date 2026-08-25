import google.generativeai as genai
from services.api_key_manager import api_key_manager, execute_with_failover

class GeminiService:
    def __init__(self):
        self.model = None
        self._recreate_model()

    def _recreate_model(self):
        """Callback to recreate the model instance when API keys are failover-rotated."""
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_content(self, prompt: str):
        """Generates content using Gemini with automatic failover key-rotation."""
        async def _call():
            response = await self.model.generate_content_async(prompt)
            return response.text
            
        return await execute_with_failover(
            service_name="GeminiService",
            api_call_fn=_call,
            model_creator_fn=self._recreate_model
        )

gemini_service = GeminiService()

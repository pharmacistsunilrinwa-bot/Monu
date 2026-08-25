import google.generativeai as genai
from sqlalchemy.future import select
from models import ChatHistory
from sqlalchemy.ext.asyncio import AsyncSession
from services.api_key_manager import api_key_manager, execute_with_failover

class GeminiLogicService:
    def __init__(self):
        self.system_instruction = (
            "You are a highly logical Personal AI Assistant. "
            "You excel at pattern recognition, logical reasoning, and step-by-step problem solving. "
            "When presented with data, look for underlying trends. "
            "Always maintain a professional and efficient tone."
        )
        self.model = None
        self._recreate_model()

    def _recreate_model(self):
        """Callback to recreate the model instance when API keys are failover-rotated."""
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=self.system_instruction
        )

    async def get_context(self, db: AsyncSession, user_id: str, limit: int = 5):
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.timestamp.desc())
            .limit(limit)
        )
        history = result.scalars().all()
        context = ""
        for entry in reversed(history):
            context += f"User: {entry.message}\nAssistant: {entry.response}\n"
        return context

    async def reasoned_chat(self, prompt: str, context: str = ""):
        """Generates reasoned response using Gemini with automatic failover key-rotation."""
        full_prompt = f"Previous conversation:\n{context}\n\nCurrent message: {prompt}" if context else prompt
        
        async def _call():
            response = await self.model.generate_content_async(full_prompt)
            return response.text
            
        return await execute_with_failover(
            service_name="GeminiLogicService",
            api_call_fn=_call,
            model_creator_fn=self._recreate_model
        )

gemini_logic_service = GeminiLogicService()

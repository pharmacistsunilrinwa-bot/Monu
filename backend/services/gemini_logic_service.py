import google.generativeai as genai
from sqlalchemy.future import select
from models import ChatHistory
from sqlalchemy.ext.asyncio import AsyncSession
from services.api_key_manager import api_key_manager, execute_with_failover
from typing import Optional

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
            model_name='gemini-3.1-pro',
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

    async def reasoned_chat(
        self, 
        prompt: str, 
        context: str = "", 
        attachment_bytes: Optional[bytes] = None, 
        attachment_mime: Optional[str] = None
    ):
        """Generates reasoned response using Gemini with automatic failover key-rotation, codebase context if needed, and optional multimodal attachment."""
        # 1. Check if this is a query about the codebase
        is_codebase_query = any(keyword in prompt.lower() for keyword in [
            "codebase", "source file", "source code", "your code", "improve yourself", 
            "optimize speech-to-text", "optimize your", "refactor your", "architecture",
            "main.py", "main.dart", "gemini_logic_service", "voice_service", "advisory"
        ])
        
        full_prompt = ""
        if is_codebase_query:
            from services.codebase_advisory_service import codebase_advisory_service
            codebase_content = codebase_advisory_service.scan_codebase()
            full_prompt += (
                "You have been asked a question regarding your own codebase. "
                "Here is the complete codebase source file context for your analysis:\n\n"
                f"{codebase_content}\n\n"
                "Please analyze the codebase carefully. When asked for improvements or optimization ideas, "
                "suggest accurate, step-by-step code enhancements, referencing specific lines and file paths.\n\n"
            )
            
        if context:
            full_prompt += f"Previous conversation:\n{context}\n\n"
            
        full_prompt += f"Current message: {prompt}"
        
        async def _call():
            content_parts = []
            if attachment_bytes and attachment_mime:
                content_parts.append({
                    "mime_type": attachment_mime,
                    "data": attachment_bytes
                })
            content_parts.append(full_prompt)
            
            response = await self.model.generate_content_async(content_parts)
            return response.text
            
        return await execute_with_failover(
            service_name="GeminiLogicService",
            api_call_fn=_call,
            model_creator_fn=self._recreate_model
        )

gemini_logic_service = GeminiLogicService()

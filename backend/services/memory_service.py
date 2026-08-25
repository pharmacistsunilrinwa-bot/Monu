import json
import re
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import ChatHistory
from services.gemini_service import gemini_service

class MemoryService:
    @staticmethod
    async def forget_semantic(db: AsyncSession, user_id: str, forget_query: str) -> str:
        """
        Uses Gemini to analyze chat history and selectively delete entries 
        matching the semantic intent of the forget request.
        """
        # 1. Fetch all chat history for the user
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.timestamp.desc())
        )
        history = result.scalars().all()
        
        if not history:
            return "Your history is already empty."
            
        # 2. Format history for Gemini
        history_list = []
        for entry in history:
            history_list.append({
                "id": entry.id,
                "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "message": entry.message,
                "response": entry.response
            })
            
        history_json = json.dumps(history_list, indent=2)
        
        # 3. Request Gemini to identify IDs to delete
        prompt = (
            f"You are the memory manager of a personal AI assistant.\n"
            f"The user wants to delete specific memories/history entries based on this query:\n"
            f"\"{forget_query}\"\n\n"
            f"Here is the user's conversation history (JSON format, newest first):\n"
            f"{history_json}\n\n"
            f"Identify all entries (by 'id') that are relevant to the user's request. "
            f"For example, if they say 'forget about Python', identify any entries discussing Python. "
            f"If they say 'forget the last message', identify the most recent entry.\n"
            f"If they say 'forget yesterday's conversation', identify entries with yesterday's date (today is Wednesday, August 26, 2026).\n\n"
            f"Return ONLY a JSON list of integers representing the IDs to delete. Do not include markdown blocks or any conversational text. "
            f"Example: [3, 7, 12]\n"
            f"If nothing matches, return: []"
        )
        
        try:
            response_text = await gemini_service.generate_content(prompt)
            # Parse the response text for JSON list
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_text)
                cleaned_text = re.sub(r"\n?```$", "", cleaned_text)
            cleaned_text = cleaned_text.strip()
            
            ids_to_delete = json.loads(cleaned_text)
            if isinstance(ids_to_delete, list):
                # Filter to only valid integers
                ids_to_delete = [int(i) for i in ids_to_delete if isinstance(i, (int, float))]
                
                if ids_to_delete:
                    # 4. Perform the deletion
                    await db.execute(
                        delete(ChatHistory)
                        .where(ChatHistory.id.in_(ids_to_delete))
                    )
                    await db.commit()
                    return f"Successfully deleted {len(ids_to_delete)} context entries matching '{forget_query}'."
                else:
                    return f"No context entries matched the query: '{forget_query}'."
            else:
                return "Failed to parse memory deletion plan. No entries deleted."
        except Exception as e:
            print(f"Error in forget_semantic: {e}")
            return f"Error executing memory forget request: {str(e)}"

memory_service = MemoryService()

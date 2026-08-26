import os
import asyncio
import google.generativeai as genai
from services.api_key_manager import api_key_manager, execute_with_failover

class SearchService:
    @staticmethod
    async def web_search(query: str):
        model_container = {"model": None}
        
        def _recreate_model():
            """Callback to recreate the model instance when API keys are failover-rotated."""
            model_container["model"] = genai.GenerativeModel(
                model_name='gemini-3-flash', 
                tools='google_search'
            )
            
        async def _call():
            response = await model_container["model"].generate_content_async(
                f"Perform a Google Search and provide highly accurate, current information on: {query}"
            )
            return response

        try:
            response = await execute_with_failover(
                service_name="SearchService",
                api_call_fn=_call,
                model_creator_fn=_recreate_model
            )
            
            results = []
            
            # Extract structured grounding metadata from the response if available
            try:
                candidate = response.candidates[0]
                metadata = getattr(candidate, 'grounding_metadata', None)
                if metadata:
                    chunks = getattr(metadata, 'grounding_chunks', [])
                    for i, chunk in enumerate(chunks):
                        web = getattr(chunk, 'web', None)
                        if web:
                            results.append({
                                "title": getattr(web, 'title', f"Search Result {i+1}"),
                                "url": getattr(web, 'uri', "https://google.com"),
                                "content": response.text if i == 0 else ""  # standard fallback content
                            })
            except Exception as meta_err:
                print(f"Grounding metadata extraction failed: {meta_err}")
                
            # Fallback if no structured web results could be extracted
            if not results:
                results.append({
                    "title": "Gemini Search Grounding Result",
                    "url": "https://google.com",
                    "content": response.text
                })
                
            return {"results": results}
        except Exception as e:
            print(f"Gemini search grounding service failed: {e}")
            return {"results": [], "error": str(e)}

search_service = SearchService()

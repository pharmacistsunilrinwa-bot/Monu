import os
import asyncio
import google.generativeai as genai

class SearchService:
    @staticmethod
    async def web_search(query: str):
        # Configure Gemini using available keys safely
        keys = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
        if keys:
            genai.configure(api_key=keys[0])
        else:
            print("Warning: No Gemini API keys found in environment for Search Service.")
            
        # Use Google Search grounding in Gemini 1.5
        model = genai.GenerativeModel(model_name='gemini-1.5-flash', tools='google_search')
        try:
            # We run the async call to generate content with search grounding
            response = await model.generate_content_async(
                f"Perform a Google Search and provide highly accurate, current information on: {query}"
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

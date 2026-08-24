import os
import asyncio
import mimetypes
import google.generativeai as genai
from gtts import gTTS
import tempfile

class VoiceService:
    @staticmethod
    async def speech_to_text(audio_file_path: str) -> str:
        # Determine the file's mime type
        mime_type, _ = mimetypes.guess_type(audio_file_path)
        if not mime_type:
            # Fallback mappings for standard extensions
            ext = os.path.splitext(audio_file_path)[1].lower()
            if ext == '.m4a':
                mime_type = 'audio/m4a'
            elif ext == '.mp3':
                mime_type = 'audio/mp3'
            elif ext == '.wav':
                mime_type = 'audio/wav'
            elif ext == '.ogg':
                mime_type = 'audio/ogg'
            elif ext == '.aac':
                mime_type = 'audio/aac'
            elif ext == '.flac':
                mime_type = 'audio/flac'
            else:
                mime_type = 'audio/mp3'  # default fallback

        # Configure Gemini using available keys safely
        keys = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
        if keys:
            genai.configure(api_key=keys[0])
        else:
            print("Warning: No Gemini API keys found in environment for Voice Service.")

        model = genai.GenerativeModel('gemini-1.5-flash')

        # Read audio file bytes
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()

        # Build transcription prompt
        prompt = (
            "Please transcribe the following audio recording accurately. "
            "Do not add any preamble, explanation, introduction, or commentary. "
            "Output only the transcribed text."
        )

        # Query Gemini model with the audio file as inline data
        response = await model.generate_content_async([
            {
                "mime_type": mime_type,
                "data": audio_bytes
            },
            prompt
        ])

        return response.text.strip()

    @staticmethod
    async def text_to_speech(text: str) -> str:
        # gTTS is synchronous, run in thread to avoid blocking.
        # This uses Google TTS, which is local and keyless.
        def _save_tts():
            tts = gTTS(text=text, lang='en')
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(temp_file.name)
            return temp_file.name
            
        return await asyncio.to_thread(_save_tts)

voice_service = VoiceService()

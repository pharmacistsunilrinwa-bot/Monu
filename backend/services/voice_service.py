import os
import asyncio
import mimetypes
import google.generativeai as genai
from gtts import gTTS
import tempfile
from services.api_key_manager import api_key_manager, execute_with_failover

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

        # Read audio file bytes
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()

        # Build transcription prompt
        prompt = (
            "Please transcribe the following audio recording accurately. "
            "Do not add any preamble, explanation, introduction, or commentary. "
            "Output only the transcribed text."
        )

        model_container = {"model": None}
        def _recreate_model():
            model_container["model"] = genai.GenerativeModel('gemini-3-flash')

        async def _call():
            response = await model_container["model"].generate_content_async([
                {
                    "mime_type": mime_type,
                    "data": audio_bytes
                },
                prompt
            ])
            return response.text.strip()

        return await execute_with_failover(
            service_name="VoiceService",
            api_call_fn=_call,
            model_creator_fn=_recreate_model
        )

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

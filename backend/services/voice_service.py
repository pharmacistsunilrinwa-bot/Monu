import os
from openai import AsyncOpenAI
from gtts import gTTS
import tempfile
import asyncio

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class VoiceService:
    @staticmethod
    async def speech_to_text(audio_file_path: str) -> str:
        with open(audio_file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text

    @staticmethod
    async def text_to_speech(text: str) -> str:
        # gTTS is synchronous, run in thread to avoid blocking
        def _save_tts():
            tts = gTTS(text=text, lang='en')
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(temp_file.name)
            return temp_file.name
            
        return await asyncio.to_thread(_save_tts)

voice_service = VoiceService()

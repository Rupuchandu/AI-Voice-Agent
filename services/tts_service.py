import os, httpx
from utils.logger import logger

MURF_API_KEY = os.getenv("MURF_API_KEY")

async def synthesize_speech(text):
    if not text:
        return []
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
    audio_urls = []
    for chunk in chunks:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.murf.ai/v1/speech/generate",
                headers={"api-key": MURF_API_KEY, "Content-Type": "application/json"},
                json={"text": chunk, "voice_id": "en-IN-alia", "audio_format": "mp3"}
            )
        if resp.status_code != 200:
            logger.error(f"TTS API failed: {resp.status_code}")
            continue
        data = resp.json()
        url = data.get("audioFile") or data.get("audio_url")
        if url:
            audio_urls.append(url)
    logger.info("TTS synthesis complete")
    return audio_urls

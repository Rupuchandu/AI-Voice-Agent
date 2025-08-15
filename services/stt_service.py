import os, asyncio, httpx
from utils.logger import logger

STT_API_KEY = os.getenv("STT_API_KEY")

async def transcribe_audio(file):
    audio_bytes = await file.read()
    async with httpx.AsyncClient() as client:
        up = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": STT_API_KEY},
            data=audio_bytes
        )
    if up.status_code != 200:
        logger.error("Audio upload failed.")
        return ""
    audio_url = up.json()["upload_url"]
    async with httpx.AsyncClient() as client:
        tr = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": STT_API_KEY},
            json={"audio_url": audio_url}
        )
    tr_id = tr.json()["id"]
    status = "processing"
    text = ""
    while status not in ("completed", "error"):
        await asyncio.sleep(1)
        async with httpx.AsyncClient() as client:
            poll = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{tr_id}",
                headers={"authorization": STT_API_KEY}
            )
        pdata = poll.json()
        status = pdata["status"]
        if status == "completed":
            text = pdata.get("text", "")
        elif status == "error":
            logger.error(f"Transcription error: {pdata}")
            return ""
    logger.info("Transcription complete")
    return text.strip()

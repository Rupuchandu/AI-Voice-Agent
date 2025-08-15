from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from services.stt_service import transcribe_audio
from services.llm_service import get_llm_reply
from services.tts_service import synthesize_speech
from models.schemas import TextChatRequest, TextChatResponse, VoiceChatResponse
from utils.logger import logger
from pathlib import Path
import json

app = FastAPI()
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

HISTORY_FILE = Path("chat_history.json")
if HISTORY_FILE.exists():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        chat_histories = json.load(f)
else:
    chat_histories = {}

def save_histories():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_histories, f, indent=2)

@app.get("/", response_class=FileResponse)
def serve_index():
    return STATIC_DIR / "index.html"

@app.post("/agent/chat/{session_id}/text", response_model=TextChatResponse)
async def text_chat(session_id: str, body: TextChatRequest):
    logger.info(f"Received text from {session_id}: {body.text}")
    chat_histories.setdefault(session_id, []).append({"role": "user", "text": body.text})
    reply = await get_llm_reply(chat_histories[session_id])
    chat_histories[session_id].append({"role": "assistant", "text": reply})
    save_histories()
    audio_urls = await synthesize_speech(reply)
    return TextChatResponse(
        transcript=body.text,
        llm_response=reply,
        audio_urls=audio_urls,
        history=chat_histories[session_id],
    )

@app.post("/agent/chat/{session_id}", response_model=VoiceChatResponse)
async def voice_chat(session_id: str, audio: UploadFile = File(...)):
    transcript = await transcribe_audio(audio)
    if not transcript:
        return VoiceChatResponse(
            transcript="",
            llm_response="Sorry, could not transcribe audio.",
            audio_urls=[],
            history=chat_histories.get(session_id, []),
        )
    logger.info(f"Received voice input (transcribed: {transcript}) from {session_id}")
    chat_histories.setdefault(session_id, []).append({"role": "user", "text": transcript})
    reply = await get_llm_reply(chat_histories[session_id])
    chat_histories[session_id].append({"role": "assistant", "text": reply})
    save_histories()
    audio_urls = await synthesize_speech(reply)
    return VoiceChatResponse(
        transcript=transcript,
        llm_response=reply,
        audio_urls=audio_urls,
        history=chat_histories[session_id],
    )

# Only needed for direct python run; can use "uvicorn main:app --reload"
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

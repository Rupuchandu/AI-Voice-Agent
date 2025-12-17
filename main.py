import os
import json
import asyncio
import base64
import textwrap
import re
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import websockets

from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
)
from groq import Groq

# --- Initialization ---
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

assert ASSEMBLYAI_API_KEY and GROQ_API_KEY and MURF_API_KEY and OPENWEATHER_API_KEY

# Groq Client (Replaces Gemini for ultra-low latency)
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

MURF_WS_URL = "wss://api.murf.ai/v1/speech/stream-input"
MURF_CONTEXT = "session-1"

HITMAAN_PERSONA = """
You are HitmAAN, a witty, helpful AI assistant. 
Keep responses under 2 sentences. Be warm and conversational.
"""

# --- Skills ---

async def search_web(query: str) -> str:
    async with httpx.AsyncClient() as client:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        try:
            resp = await client.get(url, timeout=5.0)
            data = resp.json()
            return data.get("AbstractText") or "I couldn't find a quick summary for that."
        except: return "Search failed."

async def get_weather(city: str) -> str:
    async with httpx.AsyncClient() as client:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        try:
            resp = await client.get(url, timeout=5.0)
            data = resp.json()
            return f"{data['weather'][0]['description']}, {data['main']['temp']}°C in {city}."
        except: return f"Couldn't get weather for {city}."

# --- Core Logic ---

async def call_groq_llm(text: str) -> str:
    """Uses Groq for sub-second inference."""
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": HITMAAN_PERSONA},
            {"role": "user", "content": text}
        ],
        model="llama-3.1-8b-instant", # Extremely fast model
        max_tokens=100
    )
    return chat_completion.choices[0].message.content

async def murf_tts_stream(text: str, websocket: WebSocket):
    try:
        async with websockets.connect(
            f"{MURF_WS_URL}?api_key={MURF_API_KEY}&sample_rate=44100&channel_type=MONO&format=WAV",
            ping_interval=20
        ) as murf_ws:
            await murf_ws.send(json.dumps({"voice_config": {"voiceId": "en-US-amara", "style": "Conversational"}}))
            await murf_ws.send(json.dumps({"context_id": MURF_CONTEXT, "text": text, "end": True}))
            
            async for msg in murf_ws:
                data = json.loads(msg)
                if audio_b64 := data.get("audio"):
                    await websocket.send_text(json.dumps({"type": "murf_audio_chunk", "audio_b64": audio_b64}))
                if data.get("final") or data.get("type") == "finalOutput":
                    await websocket.send_text(json.dumps({"type": "audio_done"}))
                    break
    except Exception as e:
        print(f"[Murf Error] {e}")

@app.websocket("/ws/voice-agent")
async def ws_voice_agent(ws: WebSocket):
    await ws.accept()
    loop = asyncio.get_running_loop()
    
    # AssemblyAI Client
    client = StreamingClient(StreamingClientOptions(api_key=ASSEMBLYAI_API_KEY))

    async def handle_logic(text: str):
        lowered = text.lower()
        response_text = ""

        # Routing Logic
        if "weather in" in lowered:
            match = re.search(r"weather in ([a-zA-Z\s]+)", lowered)
            city = match.group(1).strip().title() if match else "London"
            response_text = await get_weather(city)
        elif "search the web" in lowered:
            query = lowered.split("search the web")[-1].strip()
            response_text = await search_web(query)
        else:
            # Fast LLM path
            response_text = await call_groq_llm(text)

        await ws.send_text(json.dumps({"type": "llm_response", "text": response_text}))
        asyncio.create_task(murf_tts_stream(response_text, ws))

    def on_turn(_c, event):
        if not (text := event.transcript): return
        
        # Send partials to UI, but only trigger LLM on Final
        if getattr(event, "end_of_turn", False):
            asyncio.run_coroutine_threadsafe(ws.send_text(json.dumps({"type": "final", "text": text})), loop)
            asyncio.run_coroutine_threadsafe(handle_logic(text), loop)
        else:
            asyncio.run_coroutine_threadsafe(ws.send_text(json.dumps({"type": "partial", "text": text})), loop)

    client.on(StreamingEvents.Turn, on_turn)

    # Connect AssemblyAI (Optimized for Voice Agents)
    await loop.run_in_executor(None, lambda: client.connect(StreamingParameters(
        sample_rate=16000,
        end_of_turn_confidence_threshold=0.7, # Lower = faster response
        max_turn_silence=300 # Wait only 300ms of silence
    )))

    try:
        while True:
            pcm = await ws.receive_bytes()
            client.stream(pcm)
    except WebSocketDisconnect:
        client.disconnect(terminate=True)

@app.get("/")
async def index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

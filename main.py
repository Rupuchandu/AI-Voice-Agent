import os
import json
import asyncio
import base64
import textwrap
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
)
import google.generativeai as genai
import websockets

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load environment variables for fallback
ASSEMBLYAI_API_KEY_ENV = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY_ENV = os.getenv("GEMINI_API_KEY")
MURF_API_KEY_ENV = os.getenv("MURF_API_KEY")
OPENWEATHER_API_KEY_ENV = os.getenv("OPENWEATHER_API_KEY")

HITMAAN_PERSONA_PROMPT = """
You are HitmAAN, an engaging, witty, and helpful AI assistant with a friendly, approachable style. 
Keep your responses conversational and personable. Add a touch of humor and warmth 
to make the user feel like they are talking to a smart, fun companion.
"""

MURF_WS_URL = "wss://api.murf.ai/v1/speech/stream-input"
MURF_CONTEXT = "session-1"

genai.configure(api_key=None)  # Will be set per connection

@app.get("/")
async def index():
    return FileResponse("static/index.html")

async def search_web(query: str) -> str:
    async with httpx.AsyncClient() as client:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        try:
            resp = await client.get(url, timeout=8.0)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("AbstractText") or data.get("Answer") or ""
            related_topics = data.get("RelatedTopics", [])
            if not answer and related_topics:
                answer = related_topics[0].get("Text", "")
            return answer or "Sorry, couldn't find relevant web results."
        except Exception as e:
            print("[Web Search Error]", e)
            return f"Web search failed: {str(e)}"

async def murf_tts_stream(text: str, websocket: WebSocket, murf_api_key: str):
    try:
        async with websockets.connect(
            f"{MURF_WS_URL}?api_key={murf_api_key}&sample_rate=44100&channel_type=MONO&format=WAV",
            ping_interval=20, ping_timeout=20,
        ) as murf_ws:
            await murf_ws.send(json.dumps({
                "voice_config": {
                    "voiceId": "en-US-amara",
                    "style": "Conversational",
                    "rate": 0, "pitch": 0, "variation": 1,
                }
            }))
            await murf_ws.send(json.dumps({
                "context_id": MURF_CONTEXT,
                "text": text,
                "end": True
            }))

            print("[Murf] TTS streaming started...")
            async for msg in murf_ws:
                if isinstance(msg, bytes):
                    # If Murf sends binary data, encode and send to frontend
                    audio_b64 = base64.b64encode(msg).decode()
                    await websocket.send_text(json.dumps({
                        "type": "murf_audio_chunk",
                        "audio_b64": audio_b64
                    }))
                else:
                    data = json.loads(msg)
                    audio_b64 = data.get("audio")
                    if audio_b64:
                        await websocket.send_text(json.dumps({
                            "type": "murf_audio_chunk",
                            "audio_b64": audio_b64
                        }))
                    if data.get("final") or data.get("type") in {"finalOutput"}:
                        await websocket.send_text(json.dumps({"type": "audio_done"}))
                        print("[Murf] TTS streaming done.")
                        break
    except Exception as e:
        print("[Murf Error]", e)
        if websocket.application_state == 1:
            try:
                await websocket.send_text(json.dumps({"type": "audio_error", "error": str(e)}))
            except Exception:
                pass

async def get_weather(city: str, openweather_api_key: str) -> str:
    async with httpx.AsyncClient() as client:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={openweather_api_key}&units=metric"
        )
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            weather_desc = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            result = (
                f"Current weather in {city}:\n"
                f"{weather_desc}, temperature {temp:.1f}°C, feels like {feels_like:.1f}°C.\n"
                f"Humidity: {humidity}%. Wind speed: {wind_speed} m/s."
            )
            return result
        except Exception as e:
            print("[Weather API Error]", e)
            return f"Sorry, I couldn't get the weather for {city} right now."

@app.websocket("/ws/voice-agent")
async def ws_voice_agent(
    ws: WebSocket,
    assemblyKey: str = Query(None),
    geminiKey: str = Query(None),
    murfKey: str = Query(None),
    openweatherKey: str = Query(None),
):
    # Use keys from query if present, else fallback env
    assembly_key = assemblyKey or ASSEMBLYAI_API_KEY_ENV
    gemini_key = geminiKey or GEMINI_API_KEY_ENV
    murf_key = murfKey or MURF_API_KEY_ENV
    openweather_key = openweatherKey or OPENWEATHER_API_KEY_ENV

    # Validate keys
    missing_keys = []
    if not assembly_key: missing_keys.append("AssemblyAI")
    if not gemini_key: missing_keys.append("Gemini")
    if not murf_key: missing_keys.append("Murf")
    if not openweather_key: missing_keys.append("OpenWeather")
    if missing_keys:
        await ws.accept()
        await ws.send_text(json.dumps({
            "type": "llm_response",
            "text": f"Error: Missing API keys for: {', '.join(missing_keys)}. Please provide all keys to proceed."
        }))
        await ws.close()
        return

    await ws.accept()

    genai.configure(api_key=gemini_key)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    client = StreamingClient(StreamingClientOptions(api_key=assembly_key))

    loop = asyncio.get_running_loop()

    async def send_json(payload: dict):
        try:
            await ws.send_text(json.dumps(payload))
        except WebSocketDisconnect:
            print("[WebSocket] Disconnected on send.")

    async def handle_llm_and_tts(text: str):
        print(f"\n🎤 Final Transcript: {text}")

        lowered = text.lower()
        skill = None
        city = None
        web_search_query = None

        # Weather skill detection (simple regex)
        m = re.search(r'weather in ([a-zA-Z\s]+)', lowered)
        if not m:
            m = re.search(r'weather', lowered)
        if m and "weather" in lowered:
            city = m.group(1).strip().title() if m and len(m.groups()) > 0 else None
            skill = "weather"

        # Web search detection
        m = re.search(r'search (?:the )?web (?:for|about)?\s*(.*)', lowered)
        if m:
            web_search_query = m.group(1).strip()
            if web_search_query:
                skill = "web_search"

        if skill == "weather" and city:
            weather_report = await get_weather(city, openweather_key)
            final_response = f"🌤️ Here is the weather update:\n{weather_report}"
            await send_json({"type": "llm_response", "text": final_response})
            asyncio.create_task(murf_tts_stream(final_response, ws, murf_key))
            print("[Weather Skill] Responded with live weather.")
            return

        elif skill == "web_search" and web_search_query:
            web_search_result = await search_web(web_search_query)
            final_response = f"🔍 I searched the web and found:\n{web_search_result}"
            await send_json({"type": "llm_response", "text": final_response})
            asyncio.create_task(murf_tts_stream(final_response, ws, murf_key))
            print("[Web Search Skill] Responded with web results.")
            return

        # Default: Call Gemini LLM
        try:
            def call_gemini_sync(user_text: str) -> str:
                prompt = HITMAAN_PERSONA_PROMPT + "\n\nUser: " + user_text + "\nHitmAAN:"
                resp = gemini_model.generate_content(prompt)
                # Extract text safely
                if hasattr(resp, "text"):
                    return resp.text
                elif getattr(resp, "candidates", None):
                    return " ".join([c.text for c in resp.candidates if getattr(c, "text", None)])
                return str(resp)

            final_response = await loop.run_in_executor(None, call_gemini_sync, text)
            await send_json({"type": "llm_response", "text": final_response})

            # Logging base64 of output (optional)
            base64_llm = base64.b64encode(final_response.encode("utf-8")).decode()
            print("=========== HitmAAN (base64) ===========")
            for line in textwrap.wrap(base64_llm, 76):
                print(line)
            print("=======================================\n")

            asyncio.create_task(murf_tts_stream(final_response, ws, murf_key))

        except Exception as e:
            print("[Gemini Error]", e)
            await send_json({"type": "llm_response", "text": f"Error: {str(e)}"})

    def on_turn(_c, event):
        text = event.transcript or ""
        is_eot = getattr(event, "end_of_turn", False)
        if text:
            if not is_eot:
                asyncio.run_coroutine_threadsafe(
                    send_json({"type": "partial", "text": text}), loop
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    send_json({"type": "final", "text": text}), loop
                )
                asyncio.run_coroutine_threadsafe(
                    handle_llm_and_tts(text), loop
                )


    def on_begin(_c, e): print("[AssemblyAI] session started:", e.id)
    def on_term(_c, e):  print(f"[AssemblyAI] session ended after {e.audio_duration_seconds:.2f}s")
    def on_err(_c, e):   print("[AssemblyAI] Error:", e)

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_term)
    client.on(StreamingEvents.Error, on_err)

    # Run AssemblyAI streaming connect in executor (blocking)
    await loop.run_in_executor(None, lambda: client.connect(StreamingParameters(
        sample_rate=16000,
        formatted_finals=True,
        end_of_turn_confidence_threshold=0.7,
        min_end_of_turn_silence_when_confident=160,
        max_turn_silence=2400
    )))

    try:
        while True:
            pcm = await ws.receive_bytes()
            client.stream(pcm)
    except WebSocketDisconnect:
        print("[WebSocket] Disconnected by client.")
    finally:
        client.disconnect(terminate=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

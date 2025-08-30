🎤 HitmAAN Voice Agent
HitmAAN is a unique, friendly, and multi-talented AI voice assistant. Powered by FastAPI, it streams real-time speech-to-text, web search, weather info, voice synthesis, and Gemini LLM responses—accessible from a modern web frontend for everyone!

✨ Features
Engaging AI Persona: HitmAAN responds with wit, warmth, and humor, making every chat enjoyable.

Streaming Voice Input & Output: Full-duplex voice with live transcription (AssemblyAI) and natural-sounding replies (Murf TTS).

Skill Detection: Automatically answers queries about weather, web search, or conversation—with the right APIs invoked on demand.

Real-time WebSocket Updates: Instant feedback for user speech, partial/final transcriptions, and agent responses.

Web Search: DuckDuckGo API integration for live answers to broad questions.

Weather Integration: Fetches real-time weather via OpenWeather.

Modern Web UI: Responsive frontend with chat bubbles, key management, audio controls, and a downloadable chat log.

🗂️ Directory Structure

.
├── main.py           # FastAPI backend, streaming, API integrations
├── static/
│   └── index.html    # Stylish frontend: UI, chat, controls, audio
├── requirements.txt  # Python dependencies (see below)
└── README.md         # This file
⚡ Setup
Clone the Repository

git clone https://github.com/yourusername/hitmaan-voice-agent.git
cd hitmaan-voice-agent
Install Dependencies

pip install -r requirements.txt
Required Python packages include:

fastapi
uvicorn
httpx
assemblyai
google-generativeai
websockets
(and any others in your requirements.txt)


Prepare API Keys

AssemblyAI
Gemini (Google Generative AI)
Murf (TTS)
OpenWeather


You can set environment variables or enter keys in the web UI sidebar.

Run the App

uvicorn main:app --host 0.0.0.0 --port 8000
Then visit (http://localhost:8000) in your browser.


🌐 How It Works
Backend (main.py):

Accepts WebSocket connections (/ws/voice-agent)

Streams audio: transcribes speech in real time (AssemblyAI)

Detects user intent (weather, search, or chat)

Fetches:

Weather data (OpenWeather)

Web search results (DuckDuckGo)

AI-generated replies (Gemini LLM with persona prompt)

Sends replies both as text and streamed TTS (Murf), chunked as base64 over WebSocket

Frontend (static/index.html):

API key sidebar (with persistent local storage)

Voice controls: start/stop recording, status bar, chat bubbles

Receives and plays agent voice output in sync

Allows chat history download


🚀 Deployment
You can deploy publicly on Render.com or similar cloud services for free:

Push your code to GitHub.

Create a new Web Service at render.com and connect your repo.

Build command: pip install -r requirements.txt

Start command: uvicorn main:app --host 0.0.0.0 --port 10000

Add your API keys as environment variables or use the frontend sidebar after deploy.

Share your live app link!


👑 Unique Aspects
Custom HitmAAN persona prompt ensures lively, memorable agent replies.

Direct integration of four APIs, each with real-time skill recognition logic.

WebSocket-based streaming keeps the conversation fast and interactive.

Modern frontend with stylish gradient, key management, and voice controls.

Downloadable chat history for easy review or sharing.

No third-party frameworks for skill routing—everything built in Python and JavaScript.


📜 License
MIT — Have fun and keep the personality alive!



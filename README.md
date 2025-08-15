# AI Conversational Voice Assistant with Context Memory

## Overview

This project is a modular AI conversational assistant supporting both **text** and **voice interactions** with persistent context memory. Leveraging state-of-the-art APIs for speech-to-text, language models, and text-to-speech, it creates a seamless experience for smart, contextual conversations – all powered by FastAPI.

---

## Features

- **Text Chat:** Type messages and receive smart, contextual AI responses.
- **Voice Chat:** Speak your message and get transcribed, context-aware replies – both as text and natural-sounding audio.
- **Context Memory:** The assistant remembers per-session conversations for a personalized chat experience.
- **Session Management:** Each browser/user uses a session ID for their own continuous chat flow.
- **Elegant Glassmorphism UI:** Responsive, modern frontend (see `/static/index.html`) with an animated voice button.
- **Extensible & Clean Code:** All business logic and third-party APIs are modularized under `/services` for maintainability.

---

## Technologies Used

- **Backend**
    - [FastAPI](https://fastapi.tiangolo.com/) — for API and app logic
    - [AssemblyAI](https://www.assemblyai.com/) — Speech-to-Text Transcription (STT)
    - [Google Gemini](https://ai.google.dev/gemini-api/docs/get-started) — Conversational LLM API
    - [Murf.ai](https://murf.ai/) — Text-to-Speech Synthesis (TTS)
    - Python libraries: `httpx`, `python-dotenv`, `pydantic`, `uvicorn`

- **Frontend**
    - HTML, CSS (glassmorphism), JavaScript (vanilla)
    - Modern session-based chat UI

---

## Architecture

- **Frontend** sends text/voice to the API server.
- **Backend**:
    - Voice input → `/agent/chat/{session_id}`: STT → LLM → TTS → returns text+audio.
    - Text input  → `/agent/chat/{session_id}/text`: LLM → TTS → returns text+audio.
    - Context is managed and persisted by `chat_history.json`.
- **Services**: External calls (STT, LLM, TTS) are split into `/services` Python modules.
- **Settings**: Sensitive info (API keys) configured in `.env`.

---

## Project Structure

ai-assistant/
├── main.py
├── requirements.txt
├── .env
├── chat_history.json
├── README.md
├── services/
│ ├── stt_service.py
│ ├── tts_service.py
│ └── llm_service.py
├── models/
│ └── schemas.py
├── utils/
│ └── logger.py
└── static/
└── index.html

---

## Setup & Running

### 1. **Clone the Repository & Install Requirements**

git clone <your-repo-url>
cd ai-assistant
pip install -r requirements.txt

### 2. **Set Up Environment Variables**

Create a **`.env`** file in the project root:

MURF_API_KEY=your_murf_api_key
GEMINI_API_KEY=your_gemini_api_key
STT_API_KEY=your_assemblyai_api_key

> **Note:** Never commit API keys to public repos – keep `.env` in `.gitignore`.

### 3. **Run the Server**

python main.py

or (for auto-reload)
uvicorn main:app --reload


### 4. **Access the App**

Browse to:

http://localhost:8000

to use the modern AI conversational assistant with both text and voice input.

---

## API Endpoints

- **POST** `/agent/chat/{session_id}/text`  
  Request body: `{ "text": "<Your message here>" }`

- **POST** `/agent/chat/{session_id}`  
  Form-data: `audio` (webm) file

Both endpoints return the reply, TTS audio URL(s), and full session history.

---

## Environment Variables

| Variable        | Description                                 |
|-----------------|---------------------------------------------|
| MURF_API_KEY    | Murf.ai API key for speech synthesis        |
| GEMINI_API_KEY  | Google Gemini LLM API key                   |
| STT_API_KEY     | AssemblyAI API key for speech transcription |

---

## Screenshots

*(Paste a screenshot of your running UI or README for your LinkedIn post!)*

---

## Future Improvements

- Live chat bubble/conversation transcript UI
- Audio waveform visualization for mic feedback
- Google OAuth or user login support
- Dockerization for easy deployment
- Multi-language voice support

---

## License

[MIT](LICENSE) (or your preferred license)

---

## Contributing

PRs, feedback, and suggestions are always welcome!
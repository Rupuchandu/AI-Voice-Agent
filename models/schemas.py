from pydantic import BaseModel
from typing import List, Dict

class TextChatRequest(BaseModel):
    text: str

class TextChatResponse(BaseModel):
    transcript: str
    llm_response: str
    audio_urls: List[str]
    history: List[Dict]

class VoiceChatResponse(BaseModel):
    transcript: str
    llm_response: str
    audio_urls: List[str]
    history: List[Dict]

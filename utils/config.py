import os
import json
from pathlib import Path

APP_NAME = "LocalDataForge"
APP_DIR = Path.home() / ".localdataforge"
DATA_DIR = APP_DIR / "data"
CACHE_DIR = APP_DIR / "cache"
DB_PATH = DATA_DIR / "localdataforge.db"
MODEL_DIR = APP_DIR / "models"
UPLOAD_DIR = APP_DIR / "uploads"

for d in [APP_DIR, DATA_DIR, CACHE_DIR, MODEL_DIR, UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM_MODEL = "llama3"
EMBED_MODEL = "nomic-embed-text"

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
MAX_AUDIO_SIZE_MB = 50
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma"}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "A concise title for the content"},
        "document_type": {
            "type": "string",
            "enum": ["meeting", "lecture", "note", "memo", "interview", "voice_memo", "other"],
            "description": "The type of content"
        },
        "participants": {
            "type": "array",
            "items": {"type": "string"},
            "description": "People mentioned or involved"
        },
        "date": {
            "type": "string",
            "description": "Date mentioned in the content or date of recording"
        },
        "key_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "detail": {"type": "string"}
                }
            },
            "description": "Main topics and their details discussed"
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "assignee": {"type": "string"},
                    "deadline": {"type": "string"}
                }
            },
            "description": "Tasks or action items identified"
        },
        "summary": {
            "type": "string",
            "description": "A concise 2-3 sentence summary of the content"
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral", "mixed"],
            "description": "Overall sentiment of the content"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relevant tags or keywords"
        }
    },
    "required": ["title", "document_type", "summary", "sentiment", "tags"]
}

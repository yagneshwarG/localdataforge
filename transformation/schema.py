import json
from datetime import datetime, timezone


STRUCTURED_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "document_type": {
            "type": "string",
            "enum": ["meeting", "lecture", "note", "memo", "interview", "voice_memo", "other"]
        },
        "participants": {
            "type": "array",
            "items": {"type": "string"}
        },
        "date": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "detail": {"type": "string"}
                }
            }
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
            }
        },
        "summary": {"type": "string"},
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral", "mixed"]
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["title", "document_type", "summary", "sentiment", "tags"]
}


def record_to_dict(record, structured_json: str | None = None) -> dict:
    result = {
        "id": record["id"],
        "source_type": record["source_type"],
        "source_name": record["source_name"],
        "checksum": record["checksum"],
        "created_at": record["created_at"],
        "processed_at": record["processed_at"],
    }

    if record["source_type"] == "audio":
        result["transcript"] = record.get("raw_text", "")
    else:
        result["raw_text"] = record.get("raw_text", "")

    if structured_json:
        try:
            result["structured"] = json.loads(structured_json)
        except (json.JSONDecodeError, TypeError):
            result["structured"] = None
    else:
        result["structured"] = None

    return result


def make_id() -> str:
    import uuid
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

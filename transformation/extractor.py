import json
import time
from utils.config import LLM_MODEL

SYSTEM_PROMPT = """You are a structured data extraction assistant. Your task is to analyze the given text and extract structured information according to the specified JSON schema.

Rules:
1. ONLY output valid JSON - no explanations, no markdown, no code blocks
2. If information is not present in the text, use null or empty arrays
3. Be concise but accurate
4. The "summary" field must be 2-3 sentences maximum
5. "key_points" should capture the main topics discussed (max 5 items)
6. "action_items" should capture tasks, assignments, or next steps
7. "tags" should be 3-8 relevant keywords
8. For "sentiment", classify the overall tone as "positive", "negative", "neutral", or "mixed"

Output ONLY the JSON object, nothing else."""

USER_TEMPLATE = """Extract structured data from the following text:

{text}

Return a JSON object with these fields:
- title: string (concise title)
- document_type: one of ["meeting", "lecture", "note", "memo", "interview", "voice_memo", "other"]
- participants: array of strings (people mentioned)
- date: string (any date mentioned)
- key_points: array of {{topic, detail}} objects
- action_items: array of {{task, assignee, deadline}} objects
- summary: string (2-3 sentences)
- sentiment: one of ["positive", "negative", "neutral", "mixed"]
- tags: array of strings (3-8 keywords)

JSON:"""


def _call_ollama(prompt: str, model: str | None = None) -> str | None:
    try:
        import ollama
    except ImportError:
        return None

    model = model or LLM_MODEL

    try:
        result = ollama.generate(
            model=model,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            stream=False,
            options={
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 2048,
            }
        )
        return result.get("response", "")
    except Exception:
        return None


def _fallback_extract(text: str) -> dict:
    import re

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    first_line = lines[0] if lines else text[:80]

    participants = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    participants = list(dict.fromkeys(p for p in participants if len(p) > 2))[:5]

    lower = text.lower()
    if any(w in lower for w in ["meeting", "standup", "sync", "discussion"]):
        doc_type = "meeting"
    elif any(w in lower for w in ["lecture", "class", "lesson", "tutorial"]):
        doc_type = "lecture"
    elif any(w in lower for w in ["note", "notes"]):
        doc_type = "note"
    elif any(w in lower for w in ["interview"]):
        doc_type = "interview"
    else:
        doc_type = "other"

    positive = sum(lower.count(w) for w in ["good", "great", "positive", "happy", "success", "excellent", "well"])
    negative = sum(lower.count(w) for w in ["bad", "issue", "bug", "problem", "error", "fail", "negative", "difficult"])
    if positive > negative:
        sentiment = "positive"
    elif negative > positive:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    action_items = re.findall(
        r'(?:to|need to|must|should|will)\s+(.+?)(?:by|before|\.|$)',
        text, re.IGNORECASE
    )
    action_items_deduped = []
    for a in action_items:
        task = a.strip().rstrip(".")
        if task and len(task) > 5:
            deadline_match = re.search(r'\b(\w+day|\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2})\b', task)
            deadline = deadline_match.group(1) if deadline_match else ""
            clean_task = re.sub(r'\s+by\s+\w+day.*', '', task).strip()
            action_items_deduped.append({"task": clean_task[:80], "assignee": "", "deadline": deadline})

    sentences = re.split(r'[.!?\n]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    summary = " ".join(sentences[:2]) if sentences else text[:150]

    kp_match = re.findall(r'(?:discussed|covered|talked about|topic|point|item)\s*:\s*(.+?)(?:\.|$)', text, re.IGNORECASE)
    key_points = [{"topic": kp.strip()[:60], "detail": kp.strip()[:200]} for kp in kp_match[:5]]

    if not key_points:
        parts = [s.strip() for s in sentences[:3] if len(s.strip()) > 30]
        key_points = [{"topic": p[:50], "detail": p[:200]} for p in parts]
        if not key_points:
            key_points = [{"topic": first_line[:50], "detail": first_line[:200]}]

    first_sentence = re.split(r'[.!?\n]', text)[0] if text else text
    title = first_sentence[:80] if len(first_sentence) > 10 else first_line[:80]

    tags = [doc_type.replace("_", " ").title()]
    for w in ["meeting", "update", "report", "planning", "review", "technical", "design", "api", "ui", "bug"]:
        if w in lower:
            tags.append(w.title())
    tags = list(dict.fromkeys(tags))[:8]

    return {
        "title": title,
        "document_type": doc_type,
        "participants": participants,
        "date": "",
        "key_points": key_points,
        "action_items": action_items_deduped,
        "summary": summary[:300],
        "sentiment": sentiment,
        "tags": tags,
    }


def extract_structured(text: str, model: str | None = None) -> dict:
    if not text or not text.strip():
        return {
            "title": "Empty input",
            "document_type": "other",
            "participants": [],
            "date": "",
            "key_points": [],
            "action_items": [],
            "summary": "No content provided.",
            "sentiment": "neutral",
            "tags": ["empty"],
        }

    text = text.strip()
    prompt = USER_TEMPLATE.format(text=text)

    start = time.time()
    response = _call_ollama(prompt, model=model)
    elapsed = time.time() - start

    if response is None:
        result = _fallback_extract(text)
        result["_processing_time"] = round(elapsed, 2)
        result["_model"] = "fallback"
        return result

    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                result = json.loads(cleaned[start_idx:end_idx + 1])
            else:
                raise
        except (json.JSONDecodeError, ValueError):
            result = _fallback_extract(text)
            result["_raw"] = cleaned[:500]

    result["_processing_time"] = round(elapsed, 2)
    result["_model"] = model or LLM_MODEL

    return result

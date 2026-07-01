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


def _call_ollama(prompt: str, model: str | None = None) -> str:
    import ollama

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
    except ollama.ResponseError as e:
        raise RuntimeError(f"Ollama API error {e.status_code}: {e.error}")
    except Exception as e:
        raise RuntimeError(
            f"Ollama connection failed. Is Ollama running? Error: {e}"
        )


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
            result = {
                "title": "Parsing error",
                "document_type": "other",
                "participants": [],
                "date": "",
                "key_points": [{"topic": "raw_output", "detail": cleaned[:500]}],
                "action_items": [],
                "summary": cleaned[:300],
                "sentiment": "neutral",
                "tags": ["parse_error"],
            }

    result["_processing_time"] = round(elapsed, 2)
    result["_model"] = model or LLM_MODEL

    return result

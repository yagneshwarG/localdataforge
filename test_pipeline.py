import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.config import DB_PATH, LLM_MODEL, OLLAMA_BASE_URL
from storage.database import init_db, count_sources
from transformation.extractor import extract_structured
from processing.normalizer import normalize_text

def main():
    init_db()
    print(f"DB initialized. Records: {count_sources()}")

    text = (
        "Team standup meeting on June 15. John discussed the API integration progress - "
        "80% complete. Sarah needs the UI mockups by Friday. Alice reported a bug in the "
        "login flow. Action items: John to finish API by Tuesday, Sarah to deliver mockups "
        "by Friday, Alice to fix login bug by Thursday. Overall sentiment is positive."
    )
    normalized = normalize_text(text)
    print(f"Normalized ({len(normalized)} chars): {normalized[:120]}...")

    print("Calling Ollama (llama3) for structured extraction...")
    result = extract_structured(normalized)

    print(f"Title: {result.get('title')}")
    print(f"Type: {result.get('document_type')}")
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Tags: {result.get('tags')}")
    print(f"Processing time: {result.get('_processing_time')}s")
    print(f"Key Points: {len(result.get('key_points', []))}")
    print(f"Action Items: {len(result.get('action_items', []))}")
    print(f"Summary: {result.get('summary')}")

    print("\nSUCCESS: End-to-end pipeline works!")

if __name__ == "__main__":
    main()

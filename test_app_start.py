import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from storage.database import init_db, count_sources
from utils.config import DB_PATH

init_db()
print(f"DB OK at {DB_PATH}, count={count_sources()}")

from transformation.extractor import extract_structured
import ollama

# Quick health check
models = ollama.list()
model_names = [m.model for m in models.get("models", [])]
print(f"Ollama models: {model_names}")

# Test a tiny extraction
result = extract_structured("Quick test. John said hello. Sentiment is positive.")
print(f"Quick test OK: {result.get('title')} - {result.get('summary', '')[:60]}")

print("ALL CHECKS PASSED")

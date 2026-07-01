# LocalDataForge — Hackathon Submission

## Overview
An offline-first, CPU-optimized application that transforms unstructured data (audio + text) into highly structured JSON datasets using local AI models.

## Architecture

```
Audio Upload ──▶ faster-whisper ──▶ Text Normalization ──▶ Ollama (llama3) ──▶ Structured JSON ──▶ SQLite
Text Paste   ────────────────────┘                                                    │
                                                                                     └──▶ Cache (SHA256)
```

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audio Model | faster-whisper (base, INT8) | CTranslate2-based, CPU-optimized via int8 quantization |
| LLM | llama3 via Ollama (4.7B, GGUF) | CPU-first inference, quantized for edge hardware |
| Storage | SQLite (WAL mode) | Zero-dependency, offline-first, reliable |
| Caching | Content-addressable (SHA256) | Avoids redundant LLM calls on identical inputs |
| UI | Streamlit | Lightweight Python-based, works fully offline |
| Vector Search | nomic-embed-text | Local embeddings via Ollama for semantic retrieval |

## CPU Optimization Details
- **faster-whisper**: Uses CTranslate2 with INT8 quantization, 4 CPU threads, 2 workers
- **llama3**: GGUF quantization via Ollama, runs 100% on CPU with 4096 context
- **Ollama settings**: temperature=0.1 (deterministic), num_predict=2048

## Project Structure
```
localdataforge/
├── app.py                     # Streamlit UI (3 tabs: Ingest, Browse, Schema)
├── ingestion/
│   └── audio.py               # faster-whisper transcription (base model, INT8)
├── processing/
│   └── normalizer.py          # Text normalization (whitespace, dedup, chunking)
├── transformation/
│   ├── extractor.py           # Ollama LLM → structured JSON extraction
│   └── schema.py              # JSON schema definitions & helpers
├── storage/
│   └── database.py            # SQLite persistence (WAL mode, indexed)
├── utils/
│   ├── cache.py               # SHA256 content-addressable cache
│   └── config.py              # App configuration & constants
├── requirements.txt
└── AGENTS.md
```

## Output Schema
Every unstructured input produces:
```json
{
  "title": "string",
  "document_type": "meeting|lecture|note|memo|interview|voice_memo|other",
  "participants": ["string"],
  "date": "string",
  "key_points": [{"topic": "string", "detail": "string"}],
  "action_items": [{"task": "string", "assignee": "string", "deadline": "string"}],
  "summary": "string (2-3 sentences)",
  "sentiment": "positive|negative|neutral|mixed",
  "tags": ["string (3-8 keywords)"]
}
```

## How to Run
```bash
# 1. Start Ollama
ollama serve

# 2. In another terminal, pull models (if not already)
ollama pull llama3
ollama pull nomic-embed-text

# 3. Install deps
pip install -r requirements.txt

# 4. Launch app
streamlit run app.py
```

## Validation Against Criteria
1. **Model Performance**: llama3 + faster-whisper provides high-quality extraction from both audio and text
2. **Resource Efficiency**: INT8 quantization, GGUF format, 4 CPU threads — all optimized for low-power CPU
3. **Offline Resiliency**: Zero external API calls; Ollama, SQLite, Streamlit all run locally; SHA256 caching prevents redundant LLM calls
4. **Data Schema Alignment**: Unstructured input → structured JSON with clear relational schema stored in SQLite

## Graceful Failure & Caching
- Checksum-based dedup: identical content skips LLM inference entirely
- File-based cache (`~/.localdataforge/cache/`) persists across sessions
- Graceful fallback if faster-whisper not installed (text mode still works)
- Ollama connectivity check prevents cryptic errors
- SQLite WAL mode ensures data integrity during crashes

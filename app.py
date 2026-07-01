import json
import time
import sys
from pathlib import Path

import streamlit as st

from utils.config import DB_PATH, LLM_MODEL, SUPPORTED_AUDIO_FORMATS
from utils.cache import compute_checksum, read_cache, write_cache, clear_cache
from processing.normalizer import normalize_text
from transformation.schema import make_id, now_iso, record_to_dict
from transformation.extractor import extract_structured
from storage.database import (
    init_db, source_exists_by_checksum, insert_source, insert_extraction,
    get_source_by_checksum, get_extraction_by_source, list_sources, count_sources, delete_source
)

DEMO_TEXT = """Team standup meeting on June 15. John discussed the API integration progress - 80% complete. Sarah needs the UI mockups by Friday. Alice reported a bug in the login flow. Action items: John to finish API by Tuesday, Sarah to deliver mockups by Friday, Alice to fix login bug by Thursday. Overall sentiment is positive."""

st.set_page_config(
    page_title="LocalDataForge",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #888; margin-top: 0; }
    .stat-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #1a73e8; }
    .stat-label { font-size: 0.8rem; color: #666; }
    .success-box { background: #d4edda; color: #155724; padding: 0.75rem; border-radius: 6px; }
    .error-box { background: #f8d7da; color: #721c24; padding: 0.75rem; border-radius: 6px; }
    .info-box { background: #d1ecf1; color: #0c5460; padding: 0.75rem; border-radius: 6px; }
    .json-output { background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 6px; font-family: monospace; font-size: 0.85rem; overflow-x: auto; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)


def check_ollama() -> bool:
    try:
        import httpx
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1)
        return resp.status_code == 200
    except Exception:
        return False


def process_audio(file_path: Path) -> dict:
    from ingestion.audio import transcribe
    with st.spinner("Transcribing audio..."):
        try:
            result = transcribe(str(file_path))
            return result
        except ImportError as e:
            st.error(f"faster-whisper not installed: {e}")
            st.info("Install with: pip install faster-whisper")
            return {}
        except Exception as e:
            st.error(f"Transcription failed: {e}")
            return {}


def process_text(text: str) -> dict:
    normalized = normalize_text(text)
    return {
        "transcript": "",
        "segments": [],
        "language": "text",
        "duration": 0,
        "processing_time": 0,
        "model": "none",
        "normalized_text": normalized,
    }


def run_extraction(text: str, progress_bar) -> dict:
    progress_bar.progress(0.3, text="Calling local LLM...")
    start = time.time()
    try:
        structured = extract_structured(text, model=LLM_MODEL)
        elapsed = time.time() - start
        structured["_total_time"] = round(elapsed, 2)
        progress_bar.progress(1.0, text="Done!")
        return structured
    except RuntimeError as e:
        st.error(f"LLM extraction failed: {e}")
        progress_bar.progress(0, text="Failed")
        return {}


def main():
    init_db()

    with st.sidebar:
        st.markdown('<p class="main-header">🔨 LocalDataForge</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Offline-First Data Structuring</p>', unsafe_allow_html=True)
        st.divider()

        ollama_ok = check_ollama()
        if ollama_ok:
            st.success(f"✅ Ollama ({LLM_MODEL}) online")
        else:
            st.warning("⚠️ Ollama offline — using fallback extraction")

        db_count = count_sources()
        st.info(f"📦 Database: {db_count} records")

        st.divider()
        st.markdown("### ⚙️ Settings")
        model_name = st.text_input("LLM Model", value=LLM_MODEL)
        st.caption(f"Audio: {len(SUPPORTED_AUDIO_FORMATS)} formats supported")

        if st.button("🗑️ Clear Cache", use_container_width=True):
            cleared = clear_cache()
            st.toast(f"Cleared {cleared} cache entries")

    tab1, tab2, tab3 = st.tabs(["📥 Ingest", "📊 Browse", "📋 Schema"])

    with tab1:
        st.markdown('<p class="main-header">Ingest Unstructured Data</p>', unsafe_allow_html=True)
        st.markdown("Upload audio or paste text to extract structured information.")

        input_mode = st.radio(
            "Input mode",
            ["🎤 Audio Upload", "📝 Text Paste"],
            horizontal=True,
            label_visibility="collapsed",
        )

        raw_text = ""
        source_type = "text"
        source_name = ""
        ingestion_result = {}
        text_for_extraction = ""

        if input_mode == "🎤 Audio Upload":
            uploaded_file = st.file_uploader(
                "Choose an audio file",
                type=[fmt.lstrip(".") for fmt in SUPPORTED_AUDIO_FORMATS],
            )

            if uploaded_file is not None:
                source_name = uploaded_file.name
                source_type = "audio"

                temp_dir = Path(__file__).parent / "temp"
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / uploaded_file.name

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                checksum = compute_checksum(uploaded_file.name)

                existing = get_source_by_checksum(checksum)
                if existing:
                    st.info("🔄 Previously processed (cached)")
                    ingestion_result = {"transcript": existing["raw_text"]}
                    text_for_extraction = existing["raw_text"]
                else:
                    ingestion_result = process_audio(temp_path)
                    if ingestion_result:
                        text_for_extraction = ingestion_result.get("transcript", "")
                        if text_for_extraction:
                            st.success(f"Transcribed ({ingestion_result['language']}, {ingestion_result['duration']}s)")

                if text_for_extraction:
                    with st.expander("📄 Transcript", expanded=False):
                        st.text(text_for_extraction)
        else:
            demo_hint = ""
            if not check_ollama():
                demo_hint = DEMO_TEXT
            pasted = st.text_area(
                "Paste your text",
                height=200,
                value=demo_hint,
                placeholder="Paste meeting notes, lecture content, voice memo transcription, or any unstructured text..."
            )
            if pasted:
                source_name = "pasted_text"
                source_type = "text"
                checksum = compute_checksum(pasted)
                existing = get_source_by_checksum(checksum)
                if existing:
                    st.info("🔄 Previously processed (cached)")
                    text_for_extraction = existing["raw_text"]
                else:
                    proc = process_text(pasted)
                    text_for_extraction = proc.get("normalized_text", pasted)

        if text_for_extraction:
            st.divider()
            st.markdown("### 🔄 Extract Structured Data")

            progress_bar = st.progress(0, text="Starting...")

            checksum = compute_checksum(text_for_extraction)
            cached = read_cache(checksum)

            if cached:
                progress_bar.progress(1.0, text="Loaded from cache")
                structured = cached
                st.info("✅ Loaded from cache (same content processed before)")
            else:
                structured = run_extraction(text_for_extraction, progress_bar)

            if structured and structured.get("title"):
                source_id = make_id()
                extraction_id = make_id()

                insert_source(
                    id=source_id,
                    source_type=source_type,
                    source_name=source_name,
                    checksum=checksum,
                    raw_text=text_for_extraction,
                )

                insert_extraction(
                    id=extraction_id,
                    source_id=source_id,
                    structured=structured,
                    model=structured.get("_model", LLM_MODEL),
                    proc_time=structured.get("_processing_time", 0),
                )

                write_cache(checksum, structured)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("⏱️ LLM Time", f"{structured.get('_processing_time', 0):.1f}s")
                with col2:
                    st.metric("📄 Type", structured.get("document_type", "?").replace("_", " ").title())
                with col3:
                    st.metric("😊 Sentiment", structured.get("sentiment", "?").title())
                with col4:
                    tags = structured.get("tags", [])
                    st.metric("🏷️ Tags", str(len(tags)))

                st.divider()
                col_a, col_b = st.columns([1, 1])

                with col_a:
                    st.markdown("#### 📋 Extracted Fields")
                    st.markdown(f"**Title:** {structured.get('title', 'N/A')}")
                    st.markdown(f"**Type:** {structured.get('document_type', 'N/A')}")
                    st.markdown(f"**Date:** {structured.get('date', 'N/A')}")
                    st.markdown(f"**Participants:** {', '.join(structured.get('participants', [])) or 'None'}")
                    st.markdown(f"**Sentiment:** {structured.get('sentiment', 'N/A')}")
                    st.markdown(f"**Tags:** {', '.join(structured.get('tags', []))}")

                    st.markdown("**Summary:**")
                    st.markdown(f"> {structured.get('summary', 'N/A')}")

                with col_b:
                    st.markdown("#### 🔑 Key Points")
                    for kp in structured.get("key_points", []):
                        topic = kp.get("topic", "")
                        detail = kp.get("detail", "")
                        st.markdown(f"- **{topic}**: {detail}")

                    if structured.get("action_items"):
                        st.markdown("#### ✅ Action Items")
                        for ai in structured.get("action_items", []):
                            task = ai.get("task", "")
                            assignee = ai.get("assignee", "")
                            deadline = ai.get("deadline", "")
                            parts = [f"**{task}**"]
                            if assignee:
                                parts.append(f"👤 {assignee}")
                            if deadline:
                                parts.append(f"📅 {deadline}")
                            st.markdown(f"- {' · '.join(parts)}")

                st.divider()
                with st.expander("📦 Full JSON Output", expanded=False):
                    st.markdown(
                        f'<div class="json-output">{json.dumps(structured, indent=2, ensure_ascii=False)}</div>',
                        unsafe_allow_html=True
                    )
            elif structured:
                st.warning("LLM returned empty or partial data. Check Ollama logs.")

    with tab2:
        st.markdown('<p class="main-header">Browse Extractions</p>', unsafe_allow_html=True)

        records = list_sources(limit=100)
        if not records:
            st.info("No records yet. Start by ingesting data in the **Ingest** tab.")
        else:
            st.markdown(f"**{len(records)} records found**")

            for r in records:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{r.get('source_name', 'Unknown')}**")
                        st.caption(f"Type: {r.get('source_type', '?')} · Created: {r.get('created_at', '?')[:19]}")
                    with col2:
                        if st.button("View", key=f"view_{r['id']}", use_container_width=True):
                            st.session_state["selected_id"] = r["id"]

                    if st.session_state.get("selected_id") == r["id"]:
                        extraction = get_extraction_by_source(r["id"])
                        if extraction and extraction.get("structured_json"):
                            try:
                                data = json.loads(extraction["structured_json"])
                                st.markdown(f"**Title:** {data.get('title', 'N/A')}")
                                st.markdown(f"**Summary:** {data.get('summary', 'N/A')}")
                                st.markdown(f"**Sentiment:** {data.get('sentiment', 'N/A')} · **Tags:** {', '.join(data.get('tags', []))}")
                                with st.expander("Full JSON"):
                                    st.json(data)
                            except json.JSONDecodeError:
                                st.text(extraction["structured_json"][:500])
                        else:
                            st.caption("No structured extraction yet.")

                        if st.button("🗑️ Delete", key=f"del_{r['id']}"):
                            delete_source(r["id"])
                            st.rerun()

    with tab3:
        st.markdown('<p class="main-header">Output Schema</p>', unsafe_allow_html=True)
        st.markdown("""
        Every unstructured input is transformed into this JSON schema:

        ```json
        {
          "title": "string",
          "document_type": "meeting|lecture|note|memo|interview|voice_memo|other",
          "participants": ["string"],
          "date": "string (ISO date or natural language)",
          "key_points": [
            {"topic": "string", "detail": "string"}
          ],
          "action_items": [
            {"task": "string", "assignee": "string", "deadline": "string"}
          ],
          "summary": "string (2-3 sentences)",
          "sentiment": "positive|negative|neutral|mixed",
          "tags": ["string (3-8 keywords)"]
        }
        ```
        """)

        st.divider()
        st.markdown("### 🏗️ Architecture")
        st.markdown("""
        ```
        ┌────────────┐     ┌──────────┐     ┌───────────┐     ┌────────┐
        │  Audio     │────▶│ faster-  │────▶│  Text     │────▶│ SQLite │
        │  Upload    │     │ whisper  │     │           │     │  DB    │
        └────────────┘     └──────────┘     └───────────┘     └────────┘
                                               │
        ┌────────────┐                         │
        │  Text      │────────────────────────▶│
        │  Paste     │                         │
        └────────────┘                         ▼
                                        ┌───────────┐
                                        │  Ollama   │
                                        │  llama3   │
                                        └───────────┘
                                               │
                                               ▼
                                        ┌───────────┐
                                        │ Structured │
                                        │   JSON     │
                                        └───────────┘
        ```""")


if __name__ == "__main__":
    main()

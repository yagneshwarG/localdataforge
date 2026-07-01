import sys, os, json, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.config import OLLAMA_BASE_URL, LLM_MODEL

text = "Team standup meeting on June 15. John discussed the API integration progress - 80% complete. Sarah needs the UI mockups by Friday."

prompt = f"""Extract structured data from the following text:

{text}

Return a JSON object with these fields:
- title: string
- document_type: one of ["meeting", "lecture", "note", "memo", "interview", "voice_memo", "other"]
- participants: array of strings
- date: string
- key_points: array of topic/detail objects
- action_items: array of task/assignee/deadline objects
- summary: string (2-3 sentences)
- sentiment: one of ["positive", "negative", "neutral", "mixed"]
- tags: array of strings (3-8 keywords)

JSON:"""

system_prompt = "You are a structured data extraction assistant. Output ONLY valid JSON, no explanations."

url = f"{OLLAMA_BASE_URL}/api/generate"
payload = json.dumps({
    "model": LLM_MODEL,
    "prompt": prompt,
    "system": system_prompt,
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 2048}
}).encode("utf-8")

req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

print(f"Calling {LLM_MODEL}...")
start = time.time()
with urllib.request.urlopen(req, timeout=300) as resp:
    result = json.loads(resp.read().decode("utf-8"))
elapsed = time.time() - start
print(f"Response time: {elapsed:.2f}s")
print(f"Response: {result['response'][:300]}")

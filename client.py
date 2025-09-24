
# import os
# import re
# import json
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# if not OPENROUTER_API_KEY:
#     raise ValueError("OpenRouter API key not found. Please check your .env file.")

# # Allowed enum values
# NODE_TYPES = {"TOPIC", "SUBTOPIC", "EXERCISE", "CHECKPOINT", "RESOURCE"}

# def _extract_json_from_text(text: str) -> str | None:
#     """
#     Try to extract a JSON object substring from `text`. Returns the JSON string or None.
#     This helps when the model outputs an explanation before/after the JSON.
#     """
#     # First try to find the first { ... } block that parses as JSON
#     # Greedy find from first { to last }
#     start = text.find("{")
#     end = text.rfind("}")
#     if start != -1 and end != -1 and end > start:
#         candidate = text[start:end+1]
#         # Quick sanity check: balanced braces
#         # Attempt to parse
#         try:
#             json.loads(candidate)
#             return candidate
#         except Exception:
#             pass

#     # If naive approach fails, try to find all {...} like blocks and test each
#     braces_stack = []
#     candidates = []
#     for i, ch in enumerate(text):
#         if ch == "{":
#             braces_stack.append(i)
#         elif ch == "}" and braces_stack:
#             start_idx = braces_stack.pop()
#             # Only consider top-level-ish slices (length reasonable)
#             candidate = text[start_idx:i+1]
#             candidates.append(candidate)

#     for c in candidates:
#         try:
#             json.loads(c)
#             return c
#         except Exception:
#             continue

#     return None

# def _validate_and_repair(obj: dict) -> dict:
#     """
#     Ensure the parsed object matches the schema:
#     {
#       "node_type": one of NODE_TYPES,
#       "title": str,
#       "description": str,
#       optional: "extra": any
#     }
#     Returns a repaired dict. If unrecoverable, raises ValueError.
#     """
#     repaired = {}

#     # node_type
#     node_type = obj.get("node_type") or obj.get("type") or obj.get("nodeType")
#     if isinstance(node_type, str):
#         node_type_up = node_type.strip().upper()
#         # If value contains whitespace or extra chars, try to extract a valid token
#         if node_type_up in NODE_TYPES:
#             repaired["node_type"] = node_type_up
#         else:
#             # Attempt fuzzy match: pick the first NODE_TYPES member that is substring
#             matched = None
#             for nt in NODE_TYPES:
#                 if nt in node_type_up:
#                     matched = nt
#                     break
#             if matched:
#                 repaired["node_type"] = matched
#             else:
#                 # try exact uppercase words only
#                 token = re.findall(r"[A-Z]{3,}", node_type_up)
#                 if token:
#                     for t in token:
#                         if t in NODE_TYPES:
#                             repaired["node_type"] = t
#                             break
#                 # fallback: set RESOURCE
#                 if "node_type" not in repaired:
#                     repaired["node_type"] = "RESOURCE"
#     else:
#         repaired["node_type"] = "RESOURCE"

#     # title
#     title = obj.get("title") or obj.get("name") or obj.get("heading")
#     if isinstance(title, str) and title.strip():
#         repaired["title"] = title.strip()
#     else:
#         # If no title provided, create a short one using node_type
#         repaired["title"] = f"{repaired['node_type'].title()}"

#     # description
#     description = obj.get("description") or obj.get("desc") or obj.get("details")
#     if isinstance(description, str) and description.strip():
#         repaired["description"] = description.strip()
#     else:
#         repaired["description"] = ""

#     # collect any other fields under "extra"
#     extras = {}
#     for k, v in obj.items():
#         if k not in {"node_type", "nodeType", "type", "title", "name", "heading", "description", "desc", "details"}:
#             extras[k] = v
#     if extras:
#         repaired["extra"] = extras

#     return repaired

# def generate_api_response(context: str, query: str, model: str = "openai/gpt-3.5-turbo") -> dict:
#     """
#     Generate a response using OpenRouter API (chat completions) and return a validated JSON dict.
#     The returned dict will contain at least: TOPIC, SUBTOPIC
#     If the model returns invalid JSON, we attempt to extract and repair it. If repair is required,
#     the returned dict will include a key "repaired_from_raw": <raw text>.
#     """

#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     # Strong system prompt forcing strict JSON output
#     system_prompt = (
#         "You are a strict teaching assistant that MUST output JSON objects and NOTHING else on the topic the user gives, to create a roadmap to learn that subject "
#         "The JSON must follow this schema exactly:\n\n"
#         "array of topics, each topic is a array of subtopics\n\n"
#         "Output JSON object schema (required keys):\n"
#         "{\n"
#         '  "TOPIC":"The topic to be studied",\n'
#         '  "SUBTOPIC": "SubTopic of the topic if any",\n'
#         "}\n\n"
#         "Rules:\n"
#         "1) MUST output valid JSON parsable by a JSON parser (no trailing commas, no comments, no markdown).\n"
#         "2) Make an array of jsons, each having a valid TOPIC AND SUBTOPIC.\n"
#         "3) Do NOT output any explanation, commentary, or text before/after the JSON.\n"
#         "4) If you cannot answer, still return a JSON object using TOPIC RESOURCE and set SUBTOPIC to a short explanation.\n"
        
#     )

#     user_prompt = f"Context:\n{context}\n\nQuestion:\n{query}\n\nReturn the JSON object only."

#     payload = {
#         "model": model,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         "temperature": 0.0,
#         "max_tokens": 800
#     }

#     try:
#         response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
#         response.raise_for_status()
#     except requests.exceptions.RequestException as e:
#         return {"error": "Request failed", "details": str(e)}

#     try:
#         data = response.json()
#     except Exception as e:
#         return {"error": "Invalid JSON from OpenRouter response", "details": str(e), "raw_response_text": response.text}

#     # Extract the assistant message content
#     try:
#         assistant_text = data["choices"][0]["message"]["content"]
#         if assistant_text is None:
#             assistant_text = ""
#     except Exception:
#         # fallback
#         assistant_text = data.get("choices", [{}])[0].get("text", "") if isinstance(data.get("choices"), list) else ""

#     assistant_text = assistant_text.strip()

#     # Try parsing directly
#     try:
#         parsed = json.loads(assistant_text)
#         # validate/repair
#         validated = _validate_and_repair(parsed)
#         return validated
#     except json.JSONDecodeError:
#         # attempt to extract JSON substring
#         json_candidate = _extract_json_from_text(assistant_text)
#         if json_candidate:
#             try:
#                 parsed = json.loads(json_candidate)
#                 validated = _validate_and_repair(parsed)
#                 # include raw output for traceability
#                 validated["repaired_from_raw"] = assistant_text
#                 return validated
#             except json.JSONDecodeError:
#                 return {"error": "Model returned malformed JSON that couldn't be parsed", "raw_output": assistant_text}
#         else:
#             # As last resort return a safe RESOURCE response with raw text included
#             safe = {
#                 "node_type": "RESOURCE",
#                 "title": "Auto-generated resource",
#                 "description": assistant_text if len(assistant_text) <= 1000 else assistant_text[:997] + "...",
#                 "note": "Model did not return JSON; returned raw content in description"
#             }
#             return safe


# src/api/client.py
import os
import json
import re
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OpenRouter API key not found. Please check your .env file.")

# ---- Helpers for extraction + validation ----

def _extract_json(text: str) -> Optional[str]:
    """Try to find and return the largest JSON array/object substring that parses."""
    text = text.strip()
    # quick direct parse
    try:
        json.loads(text)
        return text
    except Exception:
        pass

    # find candidate brackets/braces spans and test them (prefer long)
    candidates = []
    stack = []
    pairs = {"{": "}", "[": "]"}
    opens = set(pairs.keys())
    closes = set(pairs.values())

    for i, ch in enumerate(text):
        if ch in opens:
            stack.append((ch, i))
        elif ch in closes and stack:
            open_ch, start_idx = stack.pop()
            # ensure matching pair
            if pairs[open_ch] == ch:
                candidate = text[start_idx:i+1]
                candidates.append(candidate)

    candidates.sort(key=len, reverse=True)
    for c in candidates:
        try:
            json.loads(c)
            return c
        except Exception:
            continue

    return None

def _validate_and_repair_topic(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure returned topic object has exactly:
      - type: "TOPIC"
      - name: str
      - subtopics: list of { type: "SUBTOPIC", name: str }
    Light repairs applied when possible.
    """
    repaired: Dict[str, Any] = {}

    # type: prefer "type" else fallback to "TYPE" or provided value -> uppercase and validate
    t = obj.get("type") or obj.get("TYPE") or obj.get("node_type") or "TOPIC"
    t = (t or "TOPIC").strip().upper()
    if t != "TOPIC":
        # If user accidentally returned SUBTOPIC or others, force TOPIC at the outer level
        t = "TOPIC"
    repaired["type"] = t

    # name
    name = obj.get("name") or obj.get("title") or obj.get("topic") or ""
    if not isinstance(name, str) or not name.strip():
        name = "Untitled Topic"
    repaired["name"] = name.strip()

    # subtopics: expect list of dicts with type SUBTOPIC and name
    subtopics_raw = obj.get("subtopics") or obj.get("SUBTOPICS") or obj.get("children") or []
    repaired_subs: List[Dict[str, str]] = []

    # If subtopics is a single string separated by newlines, convert
    if isinstance(subtopics_raw, str):
        lines = [l.strip() for l in subtopics_raw.splitlines() if l.strip()]
        for ln in lines:
            repaired_subs.append({"type": "SUBTOPIC", "name": ln[:200]})
    elif isinstance(subtopics_raw, list):
        for s in subtopics_raw:
            if isinstance(s, dict):
                s_name = s.get("name") or s.get("title") or s.get("subtopic") or ""
                if not isinstance(s_name, str) or not s_name.strip():
                    continue
                repaired_subs.append({"type": "SUBTOPIC", "name": s_name.strip()})
            elif isinstance(s, str) and s.strip():
                repaired_subs.append({"type": "SUBTOPIC", "name": s.strip()})
            else:
                # skip non-usable item
                continue
    else:
        # unknown shape -> empty list
        repaired_subs = []

    repaired["subtopics"] = repaired_subs
    return repaired

def _validate_parsed(parsed: Any, raw_text: str) -> List[Dict[str, Any]]:
    """
    Accept either list or dict. Return list of validated topic objects.
    """
    if isinstance(parsed, list):
        out = []
        for elem in parsed:
            if isinstance(elem, dict):
                out.append(_validate_and_repair_topic(elem))
            elif isinstance(elem, str) and elem.strip():
                out.append({"type": "TOPIC", "name": elem.strip()[:200], "subtopics": []})
            else:
                # fallback
                out.append({"type": "TOPIC", "name": "RESOURCE", "subtopics": []})
        return out

    if isinstance(parsed, dict):
        return [_validate_and_repair_topic(parsed)]

    # fallback: embed raw text as single RESOURCE topic
    snippet = raw_text.strip()
    if len(snippet) > 1000:
        snippet = snippet[:997] + "..."
    return [{"type": "TOPIC", "name": "RESOURCE", "subtopics": [{"type": "SUBTOPIC", "name": snippet}]}]

# ---- Main function that talks to OpenRouter ----

def generate_api_response(context: str, query: str, model: str = "openai/gpt-3.5-turbo") -> List[Dict[str, Any]]:
    """
    Call OpenRouter and return a validated List[TopicObjects] exactly matching the structure:
    [
      {
        "type": "TOPIC",
        "name": "...",
        "subtopics": [
          {"type":"SUBTOPIC","name":"..."},
          ...
        ]
      },
      ...
    ]
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Strict instruction to force the format you provided
    system_prompt = (
        "You are an assistant that MUST output only valid JSON (no markdown, no explanations). "
        "Output a JSON ARRAY. Each array element must be an OBJECT with exactly these keys:\n\n"
        '  "type": "TOPIC",\n'
        '  "name": "Short topic name",\n'
        '  "subtopics": [ { "type": "SUBTOPIC", "name": "Short subtopic name" }, ... ]\n\n'
        "Rules:\n"
        "1) Top-level value MUST be an ARRAY even if it contains one element.\n"
        "2) Each object must have type exactly 'TOPIC' and subtopics must be objects with type 'SUBTOPIC'.\n"
        "3) Do NOT include any additional top-level keys other than type, name, subtopics.\n"
        "4) Keep names concise. Do not output explanations or text outside the JSON.\n"
        "5)Give atleast 5 TOPICS with their respective SubTopic Arrays\n"
    )

    user_prompt = f"Subject: {query}\n\nContext (optional):\n{context}\n\nReturn an ARRAY of topic objects only."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 900
    }

    try:
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Always return a list so callers don't break
        return [{"type": "TOPIC", "name": "RESOURCE", "subtopics": [{"type": "SUBTOPIC", "name": f"Request failed: {str(e)}"}]}]

    # get assistant text
    try:
        data = resp.json()
    except Exception:
        return [{"type": "TOPIC", "name": "RESOURCE", "subtopics": [{"type": "SUBTOPIC", "name": f"Invalid JSON response from API: {resp.text[:500]}"}]}]

    assistant_text = ""
    try:
        assistant_text = data["choices"][0]["message"]["content"] or ""
    except Exception:
        try:
            assistant_text = data["choices"][0]["text"] or ""
        except Exception:
            assistant_text = ""

    assistant_text = assistant_text.strip()

    # direct parse
    try:
        parsed = json.loads(assistant_text)
        validated = _validate_parsed(parsed, assistant_text)
        return validated
    except json.JSONDecodeError:
        # try to extract JSON substring
        candidate = _extract_json(assistant_text)
        if candidate:
            try:
                parsed = json.loads(candidate)
                validated = _validate_parsed(parsed, assistant_text)
                return validated
            except json.JSONDecodeError:
                return [{"type": "TOPIC", "name": "RESOURCE", "subtopics": [{"type": "SUBTOPIC", "name": f"Malformed JSON: {assistant_text[:500]}"}]}]
        # fallback: return raw as RESOURCE
        snippet = assistant_text if len(assistant_text) <= 1000 else assistant_text[:997] + "..."
        return [{"type": "TOPIC", "name": "RESOURCE", "subtopics": [{"type": "SUBTOPIC", "name": snippet}]}]

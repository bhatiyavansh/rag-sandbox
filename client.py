
import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OpenRouter API key not found. Please check your .env file.")

# Allowed enum values
NODE_TYPES = {"TOPIC", "SUBTOPIC", "EXERCISE", "CHECKPOINT", "RESOURCE"}

def _extract_json_from_text(text: str) -> str | None:
    """
    Try to extract a JSON object substring from `text`. Returns the JSON string or None.
    This helps when the model outputs an explanation before/after the JSON.
    """
    # First try to find the first { ... } block that parses as JSON
    # Greedy find from first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        # Quick sanity check: balanced braces
        # Attempt to parse
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass

    # If naive approach fails, try to find all {...} like blocks and test each
    braces_stack = []
    candidates = []
    for i, ch in enumerate(text):
        if ch == "{":
            braces_stack.append(i)
        elif ch == "}" and braces_stack:
            start_idx = braces_stack.pop()
            # Only consider top-level-ish slices (length reasonable)
            candidate = text[start_idx:i+1]
            candidates.append(candidate)

    for c in candidates:
        try:
            json.loads(c)
            return c
        except Exception:
            continue

    return None

def _validate_and_repair(obj: dict) -> dict:
    """
    Ensure the parsed object matches the schema:
    {
      "node_type": one of NODE_TYPES,
      "title": str,
      "description": str,
      optional: "extra": any
    }
    Returns a repaired dict. If unrecoverable, raises ValueError.
    """
    repaired = {}

    # node_type
    node_type = obj.get("node_type") or obj.get("type") or obj.get("nodeType")
    if isinstance(node_type, str):
        node_type_up = node_type.strip().upper()
        # If value contains whitespace or extra chars, try to extract a valid token
        if node_type_up in NODE_TYPES:
            repaired["node_type"] = node_type_up
        else:
            # Attempt fuzzy match: pick the first NODE_TYPES member that is substring
            matched = None
            for nt in NODE_TYPES:
                if nt in node_type_up:
                    matched = nt
                    break
            if matched:
                repaired["node_type"] = matched
            else:
                # try exact uppercase words only
                token = re.findall(r"[A-Z]{3,}", node_type_up)
                if token:
                    for t in token:
                        if t in NODE_TYPES:
                            repaired["node_type"] = t
                            break
                # fallback: set RESOURCE
                if "node_type" not in repaired:
                    repaired["node_type"] = "RESOURCE"
    else:
        repaired["node_type"] = "RESOURCE"

    # title
    title = obj.get("title") or obj.get("name") or obj.get("heading")
    if isinstance(title, str) and title.strip():
        repaired["title"] = title.strip()
    else:
        # If no title provided, create a short one using node_type
        repaired["title"] = f"{repaired['node_type'].title()}"

    # description
    description = obj.get("description") or obj.get("desc") or obj.get("details")
    if isinstance(description, str) and description.strip():
        repaired["description"] = description.strip()
    else:
        repaired["description"] = ""

    # collect any other fields under "extra"
    extras = {}
    for k, v in obj.items():
        if k not in {"node_type", "nodeType", "type", "title", "name", "heading", "description", "desc", "details"}:
            extras[k] = v
    if extras:
        repaired["extra"] = extras

    return repaired

def generate_api_response(context: str, query: str, model: str = "openai/gpt-3.5-turbo") -> dict:
    """
    Generate a response using OpenRouter API (chat completions) and return a validated JSON dict.
    The returned dict will contain at least: TOPIC, SUBTOPIC
    If the model returns invalid JSON, we attempt to extract and repair it. If repair is required,
    the returned dict will include a key "repaired_from_raw": <raw text>.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Strong system prompt forcing strict JSON output
    system_prompt = (
        "You are a strict teaching assistant that MUST output JSON objects and NOTHING else on the topic the user gives, to create a roadmap to learn that subject "
        "The JSON must follow this schema exactly:\n\n"
        "array of topics, each topic is a array of subtopics\n\n"
        "Output JSON object schema (required keys):\n"
        "{\n"
        '  "TOPIC":"The topic to be studied",\n'
        '  "SUBTOPIC": "SubTopic of the topic if any",\n'
        "}\n\n"
        "Rules:\n"
        "1) MUST output valid JSON parsable by a JSON parser (no trailing commas, no comments, no markdown).\n"
        "2) Make an array of jsons, each having a valid TOPIC AND SUBTOPIC.\n"
        "3) Do NOT output any explanation, commentary, or text before/after the JSON.\n"
        "4) If you cannot answer, still return a JSON object using TOPIC RESOURCE and set SUBTOPIC to a short explanation.\n"
        
    )

    user_prompt = f"Context:\n{context}\n\nQuestion:\n{query}\n\nReturn the JSON object only."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 800
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": "Request failed", "details": str(e)}

    try:
        data = response.json()
    except Exception as e:
        return {"error": "Invalid JSON from OpenRouter response", "details": str(e), "raw_response_text": response.text}

    # Extract the assistant message content
    try:
        assistant_text = data["choices"][0]["message"]["content"]
        if assistant_text is None:
            assistant_text = ""
    except Exception:
        # fallback
        assistant_text = data.get("choices", [{}])[0].get("text", "") if isinstance(data.get("choices"), list) else ""

    assistant_text = assistant_text.strip()

    # Try parsing directly
    try:
        parsed = json.loads(assistant_text)
        # validate/repair
        validated = _validate_and_repair(parsed)
        return validated
    except json.JSONDecodeError:
        # attempt to extract JSON substring
        json_candidate = _extract_json_from_text(assistant_text)
        if json_candidate:
            try:
                parsed = json.loads(json_candidate)
                validated = _validate_and_repair(parsed)
                # include raw output for traceability
                validated["repaired_from_raw"] = assistant_text
                return validated
            except json.JSONDecodeError:
                return {"error": "Model returned malformed JSON that couldn't be parsed", "raw_output": assistant_text}
        else:
            # As last resort return a safe RESOURCE response with raw text included
            safe = {
                "node_type": "RESOURCE",
                "title": "Auto-generated resource",
                "description": assistant_text if len(assistant_text) <= 1000 else assistant_text[:997] + "...",
                "note": "Model did not return JSON; returned raw content in description"
            }
            return safe


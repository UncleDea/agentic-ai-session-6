"""Read a JSON object from a model reply."""

import json

from studymaster.agents.errors import ModelResponseError


def read_model_json(raw: str) -> dict:
    """Return the JSON object in a model reply."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if "```" in cleaned:
            cleaned = cleaned[: cleaned.rfind("```")]
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ModelResponseError("The model reply was not readable JSON.") from exc
    if not isinstance(payload, dict):
        raise ModelResponseError("The model reply was not readable JSON.")
    return payload


def complete_json(complete, *, instructions: str, prompt: str) -> dict:
    """Read one JSON object. A reply that is not JSON is requested once more."""
    raw = complete(instructions=instructions, prompt=prompt)
    try:
        return read_model_json(raw)
    except ModelResponseError:
        retry = f"{prompt}\n\nReply with one JSON object only."
        return read_model_json(complete(instructions=instructions, prompt=retry))


def object_list(payload: dict, key: str) -> list[dict]:
    """Return a list of JSON objects, or raise when the shape is wrong."""
    items = payload.get(key, [])
    if not isinstance(items, list):
        raise ModelResponseError("The model reply was not readable JSON.")
    objects = []
    for item in items:
        if not isinstance(item, dict):
            raise ModelResponseError("The model reply was not readable JSON.")
        objects.append(item)
    return objects

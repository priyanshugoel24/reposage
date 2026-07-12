import json
import logging

from reposage.rag.synthesize import client

logger = logging.getLogger(__name__)

TOUR_SYSTEM_INSTRUCTION = """You are guiding a developer who has never seen this codebase before through a
step-by-step tour of its modules, in the exact order given.

For each module, given its file path, architecture tier, function names, and dependency/dependent counts,
produce:
- title: a short human-readable heading for this tour stop
- narration: 2-4 sentences explaining what this module does and why it matters at this point in the tour,
  written for someone new to the codebase, referencing concrete function names where relevant

Respond with ONLY a valid JSON array, no markdown code fences, no commentary. The array must have exactly
one object per module, in the same order as the input, each with exactly the keys "title" and "narration".
"""


def _placeholder_step(module: dict) -> dict:
    function_names = module.get("functions", [])
    preview = ", ".join(function_names[:3])
    return {
        "title": module["file_path"],
        "narration": f"This module contains {module.get('function_count', 0)} functions including {preview}.",
    }


def generate_tour_narration(ordered_modules: list[dict]) -> list[dict]:
    """One Gemini call: given ordered module summaries, return {title, narration} per module,
    in the same order. Falls back to a generated placeholder per module if the response can't
    be parsed as a JSON array of matching length."""
    if not ordered_modules:
        return []

    prompt = "Modules in tour order:\n" + json.dumps(ordered_modules, indent=2)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"system_instruction": TOUR_SYSTEM_INSTRUCTION},
    )

    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.removeprefix("json").strip()

    try:
        parsed = json.loads(raw_text)
        if not isinstance(parsed, list) or len(parsed) != len(ordered_modules):
            raise ValueError("Response was not a JSON array matching the module count.")
        for entry in parsed:
            if not isinstance(entry, dict) or "title" not in entry or "narration" not in entry:
                raise ValueError("Response entry missing required keys.")
        return [{"title": entry["title"], "narration": entry["narration"]} for entry in parsed]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Falling back to placeholder tour narration: %s", exc)
        return [_placeholder_step(module) for module in ordered_modules]

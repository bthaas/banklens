"""Categorization helpers backed by the OpenAI API."""

import json
import os
from typing import List

from openai import OpenAI


CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Entertainment",
    "Bills",
    "Health",
    "Other",
]


def _strip_markdown_fence(text: str) -> str:
    """Remove optional ```json fences if the model returns wrapped content."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        return stripped

    inner = lines[1:-1]
    if inner and inner[0].strip().lower() == "json":
        inner = inner[1:]

    return "\n".join(inner).strip()


def categorize_transactions(descriptions: List[str]) -> List[str]:
    """Categorize transaction descriptions in a single batched model call."""
    if not descriptions:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    prompt_payload = {
        "allowed_categories": CATEGORIES,
        "descriptions": descriptions,
        "instructions": (
            "Return only a JSON array of category names in the same order as descriptions. "
            "Each category must be exactly one of the allowed categories."
        ),
    }

    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You categorize bank transactions. "
                        "Respond with strict JSON only, no markdown and no extra text."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_payload),
                },
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to categorize transactions: {exc}") from exc

    if not response.choices:
        raise RuntimeError("AI categorization returned no choices.")

    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI categorization returned an empty response.")

    try:
        parsed = json.loads(_strip_markdown_fence(content))
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI categorization returned invalid JSON.") from exc

    categories = parsed.get("categories") if isinstance(parsed, dict) else parsed
    if not isinstance(categories, list) or len(categories) != len(descriptions):
        raise RuntimeError("AI categorization returned an invalid number of categories.")

    category_lookup = {category.lower(): category for category in CATEGORIES}
    validated: List[str] = []
    for category in categories:
        if not isinstance(category, str):
            validated.append("Other")
            continue

        canonical = category_lookup.get(category.strip().lower())
        validated.append(canonical if canonical else "Other")

    return validated

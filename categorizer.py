"""Categorization helpers backed by the OpenAI API.

This module handles:
1.  Validating descriptions.
2.  Batching requests to avoid OpenAI token limits.
3.  Cleaning and validating the JSON response from the LLM.
4.  Providing a mock mode for demos without API keys.
"""

import json
import os
from typing import List

from openai import OpenAI


# Allowed categories for strict classification.
CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Entertainment",
    "Bills",
    "Health",
    "Other",
]

# Batch size prevents hitting token limits or timeouts on large CSVs.
BATCH_SIZE = 50


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


def _mock_categorize(descriptions: List[str]) -> List[str]:
    """Deterministic mock categorizer for demos/testing without API keys."""
    # Seed random so the same description always gets the same category.
    # This simulates a consistent "model" behavior.
    mock_categories = []
    for desc in descriptions:
        # Simple hash-based selection ensures consistency across runs.
        seed_val = sum(ord(c) for c in desc)
        category = CATEGORIES[seed_val % len(CATEGORIES)]
        mock_categories.append(category)
    return mock_categories


def _categorize_batch(client: OpenAI, model_name: str, descriptions: List[str]) -> List[str]:
    """Send a single batch of descriptions to the OpenAI API."""
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
            temperature=0,  # Deterministic output is preferred
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
        # Catch network errors, rate limits, or API errors.
        raise RuntimeError(f"Failed to categorize batch: {exc}") from exc

    if not response.choices:
        raise RuntimeError("AI categorization returned no choices.")

    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI categorization returned an empty response.")

    try:
        parsed = json.loads(_strip_markdown_fence(content))
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI categorization returned invalid JSON.") from exc

    # Handle cases where the model returns {"categories": [...]} or just [...]
    categories = parsed.get("categories") if isinstance(parsed, dict) else parsed

    if not isinstance(categories, list) or len(categories) != len(descriptions):
        # Fallback: If the model hallucinates the length, we can't trust the alignment.
        # In a real production app, we might retry or return "Unknown" for all.
        raise RuntimeError(
            f"AI returned {len(categories) if isinstance(categories, list) else 'invalid'} categories "
            f"for {len(descriptions)} descriptions."
        )

    # Normalize and validate against the allowlist
    category_lookup = {category.lower(): category for category in CATEGORIES}
    validated: List[str] = []
    for category in categories:
        if not isinstance(category, str):
            validated.append("Other")
            continue

        canonical = category_lookup.get(category.strip().lower())
        validated.append(canonical if canonical else "Other")

    return validated


def categorize_transactions(descriptions: List[str]) -> List[str]:
    """Categorize a list of transaction descriptions using batching."""
    if not descriptions:
        return []

    # Check for Mock Mode (useful for demos without internet/API keys)
    if os.getenv("BANKLENS_MOCK_MODE"):
        return _mock_categorize(descriptions)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    all_categories: List[str] = []

    # Process in chunks to respect token limits and improve reliability
    for i in range(0, len(descriptions), BATCH_SIZE):
        batch = descriptions[i : i + BATCH_SIZE]
        batch_categories = _categorize_batch(client, model_name, batch)
        all_categories.extend(batch_categories)

    return all_categories

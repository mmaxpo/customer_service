"""Shared parsing for JSON returned by model-backed services."""

from __future__ import annotations

import json
import re


def parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(cleaned[start : end + 1])

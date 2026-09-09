import json
import os

from google import genai
from google.genai import types

from .ai_insights import (
    AI_INSIGHT_RESPONSE_SCHEMA,
    AIInsightValidationError,
    build_ai_insight_messages,
    validate_ai_insight_response,
)


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

GEMINI_TIMEOUT_MS = 30_000

UNSUPPORTED_GEMINI_SCHEMA_KEYS = {
    "minLength",
    "maxLength",
}


class GeminiInsightProviderError(RuntimeError):
    pass


def _remove_unsupported_schema_rules(value):
    if isinstance(value, dict):
        return {
            key: _remove_unsupported_schema_rules(item)
            for key, item in value.items()
            if key not in UNSUPPORTED_GEMINI_SCHEMA_KEYS
        }

    if isinstance(value, list):
        return [
            _remove_unsupported_schema_rules(item)
            for item in value
        ]

    return value


def build_gemini_response_schema():
    return _remove_unsupported_schema_rules(
        AI_INSIGHT_RESPONSE_SCHEMA
    )


def generate_gemini_insights(
    analytics_summary,
    *,
    client=None,
    model=None,
):
    messages = build_ai_insight_messages(
        analytics_summary
    )

    prompt = (
        "SYSTEM INSTRUCTIONS:\n"
        f"{messages[0]['content']}\n\n"
        "USER REQUEST:\n"
        f"{messages[1]['content']}"
    )

    selected_model = (
        model
        or os.getenv(
            "GEMINI_MODEL",
            DEFAULT_GEMINI_MODEL,
        )
    )

    try:
        provider_client = client or genai.Client(
            http_options=types.HttpOptions(
                timeout=GEMINI_TIMEOUT_MS,
            )
        )

        response = provider_client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": (
                    build_gemini_response_schema()
                ),
            },
        )
    except Exception as error:
        raise GeminiInsightProviderError(
            "The Gemini request failed."
        ) from error

    output_text = getattr(
        response,
        "text",
        None,
    )

    if not isinstance(output_text, str) or not output_text.strip():
        raise GeminiInsightProviderError(
            "Gemini returned an empty response."
        )

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise GeminiInsightProviderError(
            "Gemini returned invalid JSON."
        ) from error

    try:
        return validate_ai_insight_response(payload)
    except AIInsightValidationError as error:
        raise GeminiInsightProviderError(
            "Gemini returned an invalid insight response."
        ) from error

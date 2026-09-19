import copy
import json


AI_INSIGHT_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "executive_summary",
        "important_findings",
        "risks_and_warnings",
        "recommended_actions",
        "areas_for_investigation",
    ],
    "properties": {
        "executive_summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1000,
        },
        "important_findings": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
            "minItems": 1,
            "maxItems": 5,
        },
        "risks_and_warnings": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
            "minItems": 0,
            "maxItems": 5,
        },
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
            "minItems": 1,
            "maxItems": 5,
        },
        "areas_for_investigation": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
            "minItems": 0,
            "maxItems": 5,
        },
    },
}


class AIInsightValidationError(ValueError):
    pass


class AIInsightRequestError(ValueError):
    pass


def _validate_text(
    value,
    *,
    field_name,
    maximum_length,
):
    if not isinstance(value, str):
        raise AIInsightValidationError(
            f"{field_name} must be text."
        )

    normalized_value = value.strip()

    if not normalized_value:
        raise AIInsightValidationError(
            f"{field_name} cannot be empty."
        )

    if len(normalized_value) > maximum_length:
        raise AIInsightValidationError(
            f"{field_name} is too long."
        )

    return normalized_value


def _validate_text_list(
    value,
    *,
    field_name,
    minimum_items,
    maximum_items,
):
    if not isinstance(value, list):
        raise AIInsightValidationError(
            f"{field_name} must be a list."
        )

    if not minimum_items <= len(value) <= maximum_items:
        raise AIInsightValidationError(
            f"{field_name} must contain between "
            f"{minimum_items} and {maximum_items} items."
        )

    return [
        _validate_text(
            item,
            field_name=f"{field_name} item",
            maximum_length=500,
        )
        for item in value
    ]


def validate_ai_insight_response(payload):
    if not isinstance(payload, dict):
        raise AIInsightValidationError(
            "The AI insight response must be an object."
        )

    expected_fields = set(
        AI_INSIGHT_RESPONSE_SCHEMA["required"]
    )
    received_fields = set(payload)

    if received_fields != expected_fields:
        missing_fields = sorted(
            expected_fields - received_fields
        )
        unexpected_fields = sorted(
            received_fields - expected_fields
        )

        details = []

        if missing_fields:
            details.append(
                "missing: " + ", ".join(missing_fields)
            )

        if unexpected_fields:
            details.append(
                "unexpected: "
                + ", ".join(unexpected_fields)
            )

        raise AIInsightValidationError(
            "Invalid AI insight response fields ("
            + "; ".join(details)
            + ")."
        )

    return {
        "executive_summary": _validate_text(
            payload["executive_summary"],
            field_name="executive_summary",
            maximum_length=1000,
        ),
        "important_findings": _validate_text_list(
            payload["important_findings"],
            field_name="important_findings",
            minimum_items=1,
            maximum_items=5,
        ),
        "risks_and_warnings": _validate_text_list(
            payload["risks_and_warnings"],
            field_name="risks_and_warnings",
            minimum_items=0,
            maximum_items=5,
        ),
        "recommended_actions": _validate_text_list(
            payload["recommended_actions"],
            field_name="recommended_actions",
            minimum_items=1,
            maximum_items=5,
        ),
        "areas_for_investigation": (
            _validate_text_list(
                payload["areas_for_investigation"],
                field_name="areas_for_investigation",
                minimum_items=0,
                maximum_items=5,
            )
        ),
    }

AI_INSIGHT_SYSTEM_PROMPT = """
You are Vendilume's business analytics assistant.

Use the supplied trusted analytics summary as your only source
of business facts.

Follow these rules:
- Never recalculate, replace, or contradict Vendilume's metrics.
- Preserve monetary values and their stated currency.
- Use comma thousands separators for monetary values and
  quantities with four or more integer digits.
- Keep calendar years and ISO dates unchanged.
- Do not invent missing products, customers, causes, or trends.
- Do not claim that correlation proves causation.
- Clearly distinguish observed facts from recommendations.
- Treat unavailable values as unavailable, not as zero.
- Make recommendations specific, cautious, and measurable.
- Mention uncertainty when the supplied evidence is limited.
- Return only the requested structured response.
- A null filter means no filter was applied; it does not mean
  that the underlying dimension is unavailable.
- Determine field availability only from data_availability.
- If data_availability is absent, do not make claims about
  whether a field is available.
- Do not recommend adding fields solely because a filter is null.
""".strip()


def build_ai_safe_summary(analytics_summary):
    safe_summary = copy.deepcopy(analytics_summary)

    dataset_details = safe_summary.get("dataset")

    if isinstance(dataset_details, dict):
        dataset_details.pop("id", None)
        dataset_details.pop("name", None)

    filters = safe_summary.get("filters")

    if (
        isinstance(filters, dict)
        and filters.get("customer")
    ):
        filters["customer"] = "selected"

    return safe_summary


def build_ai_insight_messages(analytics_summary):
    if not isinstance(analytics_summary, dict):
        raise AIInsightRequestError(
            "The analytics summary must be an object."
        )

    if analytics_summary.get("schema_version") != 1:
        raise AIInsightRequestError(
            "Unsupported analytics summary version."
        )

    if not analytics_summary.get("has_data"):
        raise AIInsightRequestError(
            "AI insights cannot be generated without "
            "matching sales data."
        )

    safe_summary = build_ai_safe_summary(
        analytics_summary
    )

    serialized_summary = json.dumps(
        safe_summary,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    user_prompt = (
        "Interpret the following trusted Vendilume analytics "
        "summary.\n\n"
        "Produce:\n"
        "1. A concise executive summary.\n"
        "2. One to five important findings.\n"
        "3. Up to five risks and warnings.\n"
        "4. One to five recommended actions.\n"
        "5. Up to five areas requiring further investigation."
        "\n\n"
        "Trusted analytics summary:\n"
        f"{serialized_summary}"
    )

    return [
        {
            "role": "system",
            "content": AI_INSIGHT_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

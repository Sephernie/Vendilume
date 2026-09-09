from .ai_insights import AIInsightRequestError
from .gemini_provider import (
    GeminiInsightProviderError,
    generate_gemini_insights,
)


AI_UNAVAILABLE_NOTICE = (
    "AI-enhanced insights are temporarily unavailable. "
    "Showing verified Smart Insights instead."
)

NO_MATCHING_DATA_NOTICE = (
    "AI-enhanced insights require matching sales data."
)


def generate_business_insights(
    analytics_summary,
    *,
    ai_generator=generate_gemini_insights,
):
    rule_based_insights = analytics_summary.get(
        "rule_based_insights",
        [],
    )

    if not analytics_summary.get("has_data"):
        return {
            "source": "rule_based",
            "ai_insights": None,
            "rule_based_insights": rule_based_insights,
            "notice": NO_MATCHING_DATA_NOTICE,
        }

    try:
        ai_insights = ai_generator(analytics_summary)
    except (
        GeminiInsightProviderError,
        AIInsightRequestError,
    ):
        return {
            "source": "rule_based",
            "ai_insights": None,
            "rule_based_insights": rule_based_insights,
            "notice": AI_UNAVAILABLE_NOTICE,
        }

    return {
        "source": "gemini",
        "ai_insights": ai_insights,
        "rule_based_insights": rule_based_insights,
        "notice": None,
    }
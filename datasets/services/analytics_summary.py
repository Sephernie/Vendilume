from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from .analytics_insights import (
    generate_sales_insights,
    get_filtered_sales_lines,
)

from datetime import timedelta


def _format_decimal(value):
    if value is None:
        return None

    return f"{value:,.2f}"


def _build_ranking(sales_lines, field_name, ordering):
    rows = (
        sales_lines
        .values(field_name)
        .annotate(
            net_revenue=Sum("net_revenue"),
            total_quantity=Sum("quantity"),
            order_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by(ordering, field_name)[:5]
    )

    return [
        {
            "name": row[field_name],
            "net_revenue": _format_decimal(
                row["net_revenue"]
            ),
            "total_quantity": row["total_quantity"],
            "order_count": row["order_count"],
        }
        for row in rows
    ]


def _build_monthly_trend(sales_lines):
    rows = (
        sales_lines
        .annotate(
            month=TruncMonth("order__order_date")
        )
        .values("month")
        .annotate(
            net_revenue=Sum("net_revenue"),
            total_quantity=Sum("quantity"),
            order_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by("month")
    )

    return [
        {
            "month": row["month"].strftime("%Y-%m"),
            "net_revenue": _format_decimal(
                row["net_revenue"]
            ),
            "total_quantity": row["total_quantity"],
            "order_count": row["order_count"],
        }
        for row in rows
    ]


def _percentage_change(current_value, previous_value):
    if not previous_value:
        return None

    change = (
        (
            Decimal(current_value)
            - Decimal(previous_value)
        )
        / Decimal(previous_value)
    ) * Decimal("100")

    return _format_decimal(change)


def _build_period_comparison(
    *,
    dataset,
    start_date,
    end_date,
    current_net_revenue,
    current_order_count,
    current_total_quantity,
    product="",
    category="",
    region="",
    sales_channel="",
    customer="",
):
    period_length = end_date - start_date
    previous_end_date = start_date - timedelta(days=1)
    previous_start_date = (
        previous_end_date - period_length
    )

    previous_sales_lines = get_filtered_sales_lines(
        dataset=dataset,
        start_date=previous_start_date,
        end_date=previous_end_date,
        product=product,
        category=category,
        region=region,
        sales_channel=sales_channel,
        customer=customer,
    )

    previous_totals = previous_sales_lines.aggregate(
        order_count=Count("order_id", distinct=True),
        total_quantity=Sum("quantity"),
        net_revenue=Sum("net_revenue"),
    )

    previous_order_count = previous_totals[
        "order_count"
    ]
    previous_total_quantity = (
        previous_totals["total_quantity"] or 0
    )
    previous_net_revenue = (
        previous_totals["net_revenue"]
        or Decimal("0.00")
    )

    return {
        "previous_period": {
            "start_date": (
                previous_start_date.isoformat()
            ),
            "end_date": previous_end_date.isoformat(),
        },
        "previous_has_data": (
            previous_sales_lines.exists()
        ),
        "previous_metrics": {
            "order_count": previous_order_count,
            "total_quantity": previous_total_quantity,
            "net_revenue": _format_decimal(
                previous_net_revenue
            ),
        },
        "percentage_changes": {
            "order_count": _percentage_change(
                current_order_count,
                previous_order_count,
            ),
            "total_quantity": _percentage_change(
                current_total_quantity,
                previous_total_quantity,
            ),
            "net_revenue": _percentage_change(
                current_net_revenue,
                previous_net_revenue,
            ),
        },
    }


def build_analytics_summary(
    *,
    dataset,
    start_date,
    end_date,
    product="",
    category="",
    region="",
    sales_channel="",
    customer="",
):
    sales_lines = get_filtered_sales_lines(
        dataset=dataset,
        start_date=start_date,
        end_date=end_date,
        product=product,
        category=category,
        region=region,
        sales_channel=sales_channel,
        customer=customer,
    )

    totals = sales_lines.aggregate(
        order_count=Count("order_id", distinct=True),
        total_quantity=Sum("quantity"),
        gross_revenue=Sum("gross_revenue"),
        discount_amount=Sum("discount_amount"),
        net_revenue=Sum("net_revenue"),
    )

    order_count = totals["order_count"]
    total_quantity = totals["total_quantity"] or 0
    gross_revenue = (
        totals["gross_revenue"] or Decimal("0.00")
    )
    discount_amount = (
        totals["discount_amount"] or Decimal("0.00")
    )
    net_revenue = (
        totals["net_revenue"] or Decimal("0.00")
    )

    average_order_value = None

    if order_count:
        average_order_value = net_revenue / order_count

    discount_rate_percent = None

    if dataset.has_discount and gross_revenue:
        discount_rate_percent = (
            discount_amount / gross_revenue
        ) * Decimal("100")

    total_cost = None
    profit = None
    profit_margin_percent = None

    if dataset.has_complete_unit_cost:
        cost_totals = sales_lines.aggregate(
            total_cost=Sum("total_cost"),
            profit=Sum("profit"),
        )

        total_cost = (
            cost_totals["total_cost"] or Decimal("0.00")
        )
        profit = (
            cost_totals["profit"] or Decimal("0.")
        )

        if net_revenue:
            profit_margin_percent = (
                profit / net_revenue
            ) * Decimal("100")

    rankings = {
        "top_products_by_net_revenue": _build_ranking(
            sales_lines,
            "product_name",
            "-net_revenue",
        ),
        "lowest_products_by_net_revenue": (
            _build_ranking(
                sales_lines,
                "product_name",
                "net_revenue",
            )
        ),
        "top_categories_by_net_revenue": (
            _build_ranking(
                sales_lines,
                "category",
                "-net_revenue",
            )
        ),
        "lowest_categories_by_net_revenue": (
            _build_ranking(
                sales_lines,
                "category",
                "net_revenue",
            )
        ),
    }

    monthly_trend = _build_monthly_trend(
        sales_lines
    )

    period_comparison = _build_period_comparison(
        dataset=dataset,
        start_date=start_date,
        end_date=end_date,
        current_net_revenue=net_revenue,
        current_order_count=order_count,
        current_total_quantity=total_quantity,
        product=product,
        category=category,
        region=region,
        sales_channel=sales_channel,
        customer=customer,
    )

    rule_based_insights = generate_sales_insights(
        dataset=dataset,
        start_date=start_date,
        end_date=end_date,
        product=product,
        category=category,
        region=region,
        sales_channel=sales_channel,
        customer=customer,
    )

    return {
        "schema_version": 1,
        "has_data": sales_lines.exists(),
        "dataset": {
            "id": dataset.pk,
            "name": dataset.name,
            "currency": dataset.currency,
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "filters": {
            "product": product or None,
            "category": category or None,
            "region": region or None,
            "sales_channel": sales_channel or None,
            "customer": customer or None,
        },
        "data_availability": {
            "discount": dataset.has_discount,
            "unit_cost": dataset.has_unit_cost,
            "complete_unit_cost": (
                dataset.has_complete_unit_cost
            ),
        },
        "metrics": {
            "line_count": sales_lines.count(),
            "order_count": order_count,
            "total_quantity": total_quantity,
            "gross_revenue": _format_decimal(
                gross_revenue
            ),
            "discount_amount": (
                _format_decimal(discount_amount)
                if dataset.has_discount
                else None
            ),
            "net_revenue": _format_decimal(
                net_revenue
            ),
            "average_order_value": _format_decimal(
                average_order_value
            ),
            "total_cost": _format_decimal(total_cost),
            "profit": _format_decimal(profit),
            "profit_margin_percent": _format_decimal(
                profit_margin_percent
            ),
            "discount_rate_percent": _format_decimal(
                discount_rate_percent
            ),
        },
        "rankings": rankings,
        "monthly_trend": monthly_trend,
        "period_comparison": period_comparison,
        "rule_based_insights": rule_based_insights,
    }

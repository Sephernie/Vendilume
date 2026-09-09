from django.db.models import Sum
from django.db.models.functions import TruncMonth

from ..models import SalesLine


def get_filtered_sales_lines(
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
    sales_lines = SalesLine.objects.filter(
        order__dataset=dataset,
        order__order_date__range=(start_date, end_date),
    )

    if product:
        sales_lines = sales_lines.filter(
            product_name=product
        )

    if category:
        sales_lines = sales_lines.filter(
            category=category
        )

    if region:
        sales_lines = sales_lines.filter(
            order__region=region
        )

    if sales_channel:
        sales_lines = sales_lines.filter(
            order__sales_channel=sales_channel
        )

    if customer:
        sales_lines = sales_lines.filter(
            order__customer_id=customer
        )

    return sales_lines


def generate_sales_insights(
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

    if not sales_lines.exists():
        return [
            "No sales data matches the selected filters."
        ]

    insights = []

    highest_revenue_product = (
        sales_lines
        .values("product_name")
        .annotate(total_revenue=Sum("net_revenue"))
        .order_by("-total_revenue", "product_name")
        .first()
    )

    if highest_revenue_product:
        insights.append(
            f'{highest_revenue_product["product_name"]} generated '
            "the highest net revenue at "
            f'{highest_revenue_product["total_revenue"]:,.2f} '
            f"{dataset.currency}."
        )

    strongest_category = (
        sales_lines
        .values("category")
        .annotate(total_revenue=Sum("net_revenue"))
        .order_by("-total_revenue", "category")
        .first()
    )

    if strongest_category:
        insights.append(
            f'{strongest_category["category"]} was the '
            "strongest-performing category, generating "
            f'{strongest_category["total_revenue"]:,.2f} '
            f"{dataset.currency} in net revenue."
        )

    best_selling_product = (
        sales_lines
        .values("product_name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity", "product_name")
        .first()
    )

    if best_selling_product:
        insights.append(
            f'{best_selling_product["product_name"]} sold the '
            "most units, with "
            f'{best_selling_product["total_quantity"]:,} '
            "items sold."
        )

    strongest_month = (
        sales_lines
        .annotate(month=TruncMonth("order__order_date"))
        .values("month")
        .annotate(total_revenue=Sum("net_revenue"))
        .order_by("-total_revenue", "month")
        .first()
    )

    if strongest_month:
        month_name = strongest_month["month"].strftime(
            "%B %Y"
        )

        insights.append(
            f"{month_name} recorded the highest monthly "
            "net revenue at "
            f'{strongest_month["total_revenue"]:,.2f} '
            f"{dataset.currency}."
        )

    return insights

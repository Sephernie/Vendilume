from pathlib import Path

from django.db import transaction

from ..models import (
    Dataset,
    DatasetWarning,
    SalesLine,
    SalesOrder,
)


def _nullable_text(value):
    return value or None


@transaction.atomic
def persist_processed_dataset(
    *,
    result,
    name,
    original_filename,
    currency,
):
    dataframe = result.dataframe
    source_columns = set(result.source_columns)

    safe_filename = Path(
        original_filename.replace("\\", "/")
    ).name

    dataset_name = name.strip() or Path(
        safe_filename
    ).stem

    dataset = Dataset.objects.create(
        name=dataset_name,
        original_filename=safe_filename,
        currency=currency,
        status=Dataset.Status.PROCESSING,
        has_product_id=(
            "product_id" in source_columns
        ),
        has_customer_id=(
            "customer_id" in source_columns
        ),
        has_region=(
            "region" in source_columns
        ),
        has_sales_channel=(
            "sales_channel" in source_columns
        ),
        has_discount=(
            "discount_percent" in source_columns
        ),
        has_unit_cost=(
            "unit_cost" in source_columns
        ),
        has_complete_unit_cost=(
            "unit_cost" in source_columns
            and bool(
                dataframe["unit_cost"].notna().all()
            )
        ),
    )

    order_data = {}

    for _, row in dataframe.iterrows():
        order_key = row["order_id"].casefold()

        if order_key not in order_data:
            order_data[order_key] = {
                "source_order_id": row["order_id"],
                "order_date": row["order_date"],
                "customer_id": None,
                "region": None,
                "sales_channel": None,
            }

        stored_order = order_data[order_key]

        for column in (
            "customer_id",
            "region",
            "sales_channel",
        ):
            if column not in source_columns:
                continue

            value = _nullable_text(row[column])

            if (
                stored_order[column] is None
                and value is not None
            ):
                stored_order[column] = value

    orders = [
        SalesOrder(
            dataset=dataset,
            **values,
        )
        for values in order_data.values()
    ]

    SalesOrder.objects.bulk_create(
        orders,
        batch_size=1000,
    )

    orders_by_key = {
        order.source_order_id.casefold(): order
        for order in orders
    }

    lines = []

    for index, row in dataframe.iterrows():
        lines.append(
            SalesLine(
                order=orders_by_key[
                    row["order_id"].casefold()
                ],
                source_row_number=index + 2,
                source_product_id=(
                    _nullable_text(
                        row["product_id"]
                    )
                    if "product_id" in source_columns
                    else None
                ),
                product_name=row["product_name"],
                category=row["category"],
                quantity=row["quantity"],
                unit_price=row["unit_price"],
                discount_percent=row[
                    "discount_percent"
                ],
                unit_cost=row["unit_cost"],
                gross_revenue=row[
                    "gross_revenue"
                ],
                discount_amount=row[
                    "discount_amount"
                ],
                net_revenue=row["net_revenue"],
                total_cost=row["total_cost"],
                profit=row["profit"],
            )
        )

    SalesLine.objects.bulk_create(
        lines,
        batch_size=1000,
    )

    DatasetWarning.objects.bulk_create(
        [
            DatasetWarning(
                dataset=dataset,
                code=warning.code,
                message=warning.message,
                affected_row_count=(
                    warning.affected_row_count
                ),
                details=warning.details,
            )
            for warning in result.warnings
        ],
        batch_size=1000,
    )

    dataset.row_count = len(dataframe)
    dataset.order_count = len(orders)
    dataset.start_date = dataframe[
        "order_date"
    ].min()
    dataset.end_date = dataframe[
        "order_date"
    ].max()
    dataset.status = Dataset.Status.READY

    dataset.save(
        update_fields=[
            "row_count",
            "order_count",
            "start_date",
            "end_date",
            "status",
        ]
    )

    return dataset

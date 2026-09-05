from django.db import migrations


CREATE_ANALYTICS_SALES_VIEW = """
CREATE VIEW analytics_sales AS
SELECT
    d.id AS dataset_id,
    d.name AS dataset_name,
    d.currency,
    o.id AS internal_order_id,
    o.source_order_id,
    o.order_date,
    o.customer_id,
    o.region,
    o.sales_channel,
    l.id AS sales_line_id,
    l.source_row_number,
    l.source_product_id,
    l.product_name,
    l.category,
    l.quantity,
    l.unit_price,
    l.discount_percent,
    l.unit_cost,
    l.gross_revenue,
    l.discount_amount,
    l.net_revenue,
    l.total_cost,
    l.profit
FROM vendilume_dataset AS d
JOIN vendilume_sales_order AS o
    ON o.dataset_id = d.id
JOIN vendilume_sales_line AS l
    ON l.order_id = o.id
WHERE d.status = 'READY';
"""


DROP_ANALYTICS_SALES_VIEW = """
DROP VIEW analytics_sales;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_ANALYTICS_SALES_VIEW,
            reverse_sql=DROP_ANALYTICS_SALES_VIEW,
        ),
    ]

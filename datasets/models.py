from django.db import models
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


def validate_not_future_date(value):
    if value > timezone.localdate():
        raise ValidationError("Order date cannot be in the future.")

class Dataset(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    name = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.READY,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    row_count = models.PositiveIntegerField(default=0)
    order_count = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    has_product_id = models.BooleanField(default=False)
    has_customer_id = models.BooleanField(default=False)
    has_region = models.BooleanField(default=False)
    has_sales_channel = models.BooleanField(default=False)
    has_discount = models.BooleanField(default=False)
    has_unit_cost = models.BooleanField(default=False)
    has_complete_unit_cost = models.BooleanField(default=False)

    class Meta:
        db_table = "vendilume_dataset"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(
                fields=["-uploaded_at"],
                name="dataset_uploaded_desc_idx",
            ),
            models.Index(
                fields=["status"],
                name="dataset_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"),
                name="dataset_name_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(original_filename__regex=r"\S"),
                name="dataset_filename_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(currency__regex=r"^[A-Z]{3}$"),
                name="dataset_currency_format",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "PROCESSING",
                        "READY",
                        "FAILED",
                    ]
                ),
                name="dataset_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(row_count__gte=0),
                name="dataset_row_count_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(order_count__gte=0),
                name="dataset_order_count_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status="READY")
                    | (
                        Q(row_count__gt=0)
                        & Q(order_count__gt=0)
                        & Q(start_date__isnull=False)
                        & Q(end_date__isnull=False)
                    )
                ),
                name="dataset_ready_summary_complete",
            ),
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(end_date__isnull=True)
                    | Q(start_date__lte=F("end_date"))
                ),
                name="dataset_valid_date_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(has_complete_unit_cost=False)
                    | Q(has_unit_cost=True)
                ),
                name="dataset_complete_cost_requires_cost",
            ),
        ]

    def __str__(self):
        return self.name

class DatasetWarning(models.Model):
    class Code(models.TextChoices):
        UNSUPPORTED_COLUMNS = (
            "UNSUPPORTED_COLUMNS",
            "Unsupported columns",
        )
        DUPLICATE_ROWS = (
            "DUPLICATE_ROWS",
            "Duplicate rows",
        )
        INCOMPLETE_OPTIONAL_DATA = (
            "INCOMPLETE_OPTIONAL_DATA",
            "Incomplete optional data",
        )

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="warnings",
    )
    code = models.CharField(
        max_length=50,
        choices=Code.choices,
    )
    message = models.TextField()
    affected_row_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    details = models.JSONField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendilume_dataset_warning"
        constraints = [
            models.CheckConstraint(
                condition=Q(code__regex=r"\S"),
                name="warning_code_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(message__regex=r"\S"),
                name="warning_message_not_blank",
            ),
            models.CheckConstraint(
                condition=(
                    Q(affected_row_count__isnull=True)
                    | Q(affected_row_count__gt=0)
                ),
                name="warning_affected_rows_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(details__isnull=True)
                    | Q(details__contains={})
                ),
                name="warning_details_object",
            ),
        ]

    def __str__(self):
        return self.code

class SalesOrder(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    source_order_id = models.CharField(max_length=255)
    order_date = models.DateField(
        validators=[validate_not_future_date],
    )
    customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    region = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    sales_channel = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "vendilume_sales_order"
        indexes = [
            models.Index(
                fields=["dataset", "order_date"],
                name="order_dataset_date_idx",
            ),
            models.Index(
                fields=["dataset", "customer_id"],
                name="order_dataset_customer_idx",
            ),
            models.Index(
                fields=["dataset", "region"],
                name="order_dataset_region_idx",
            ),
            models.Index(
                fields=["dataset", "sales_channel"],
                name="order_dataset_channel_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(source_order_id__regex=r"\S"),
                name="order_source_id_not_blank",
            ),
            models.CheckConstraint(
                condition=(
                    Q(customer_id__isnull=True)
                    | Q(customer_id__regex=r"\S")
                ),
                name="order_customer_null_or_text",
            ),
            models.CheckConstraint(
                condition=(
                    Q(region__isnull=True)
                    | Q(region__regex=r"\S")
                ),
                name="order_region_null_or_text",
            ),
            models.CheckConstraint(
                condition=(
                    Q(sales_channel__isnull=True)
                    | Q(sales_channel__regex=r"\S")
                ),
                name="order_channel_null_or_text",
            ),
            models.UniqueConstraint(
                fields=["dataset", "source_order_id"],
                name="order_dataset_source_uniq",
            ),
        ]

    def __str__(self):
        return self.source_order_id

class SalesLine(models.Model):
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    source_row_number = models.PositiveIntegerField()
    source_product_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    gross_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    discount_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    net_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    total_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    profit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "vendilume_sales_line"
        indexes = [
            models.Index(
                fields=["source_product_id"],
                name="line_product_source_idx",
            ),
            models.Index(
                fields=["product_name"],
                name="line_product_name_idx",
            ),
            models.Index(
                fields=["category"],
                name="line_category_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(source_row_number__gt=1),
                name="line_source_row_gt_header",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source_product_id__isnull=True)
                    | Q(source_product_id__regex=r"\S")
                ),
                name="line_product_id_null_or_text",
            ),
            models.CheckConstraint(
                condition=Q(product_name__regex=r"\S"),
                name="line_product_name_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(category__regex=r"\S"),
                name="line_category_not_blank",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="line_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="line_unit_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discount_percent__gte=0)
                    & Q(discount_percent__lte=100)
                ),
                name="line_discount_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(unit_cost__isnull=True)
                    | Q(unit_cost__gte=0)
                ),
                name="line_unit_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(gross_revenue__gte=0),
                name="line_gross_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=0),
                name="line_discount_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(net_revenue__gte=0),
                name="line_net_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(total_cost__isnull=True)
                    | Q(total_cost__gte=0)
                ),
                name="line_total_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        Q(unit_cost__isnull=True)
                        & Q(total_cost__isnull=True)
                        & Q(profit__isnull=True)
                    )
                    | (
                        Q(unit_cost__isnull=False)
                        & Q(total_cost__isnull=False)
                        & Q(profit__isnull=False)
                    )
                ),
                name="line_cost_values_consistent",
            ),
            models.UniqueConstraint(
                fields=["order", "source_row_number"],
                name="line_order_source_row_uniq",
            ),
        ]

    def __str__(self):
        return (
            f"{self.product_name} "
            f"(source row {self.source_row_number})"
        )

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    Dataset,
    DatasetWarning,
    SalesLine,
    SalesOrder,
)


class DatasetRelationshipTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="January Sales",
            original_filename="january_sales.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=1,
            order_count=1,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
            has_product_id=True,
            has_customer_id=True,
            has_region=True,
            has_sales_channel=True,
            has_discount=True,
            has_unit_cost=True,
            has_complete_unit_cost=True,
        )

        self.order = SalesOrder.objects.create(
            dataset=self.dataset,
            source_order_id="ORDER-001",
            order_date=date(2026, 1, 10),
            customer_id="CUSTOMER-001",
            region="Berlin",
            sales_channel="Online",
        )

        self.line = SalesLine.objects.create(
            order=self.order,
            source_row_number=2,
            source_product_id="PRODUCT-001",
            product_name="Desk Lamp",
            category="Home",
            quantity=2,
            unit_price=Decimal("10.00"),
            discount_percent=Decimal("10.00"),
            unit_cost=Decimal("6.00"),
            gross_revenue=Decimal("20.00"),
            discount_amount=Decimal("2.00"),
            net_revenue=Decimal("18.00"),
            total_cost=Decimal("12.00"),
            profit=Decimal("6.00"),
        )

        self.warning = DatasetWarning.objects.create(
            dataset=self.dataset,
            code=DatasetWarning.Code.DUPLICATE_ROWS,
            message="One duplicate row was retained.",
            affected_row_count=1,
            details={"source_rows": [2]},
        )

    def test_dataset_graph_can_be_created_and_retrieved(self):
        stored_dataset = Dataset.objects.get(pk=self.dataset.pk)

        self.assertEqual(stored_dataset.name, "January Sales")
        self.assertEqual(stored_dataset.orders.get(), self.order)
        self.assertEqual(stored_dataset.warnings.get(), self.warning)
        self.assertEqual(self.order.lines.get(), self.line)
        self.assertEqual(
            self.line.net_revenue,
            Decimal("18.00"),
        )

    def test_deleting_dataset_cascades_to_children(self):
        self.dataset.delete()

        self.assertEqual(Dataset.objects.count(), 0)
        self.assertEqual(DatasetWarning.objects.count(), 0)
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(SalesLine.objects.count(), 0)

class DatabaseConstraintTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="Constraint Test Dataset",
            original_filename="constraint_test.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=1,
            order_count=1,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
        )

        self.order = SalesOrder.objects.create(
            dataset=self.dataset,
            source_order_id="ORDER-001",
            order_date=date(2026, 1, 10),
        )

    def create_valid_line(self, **overrides):
        values = {
            "order": self.order,
            "source_row_number": 2,
            "source_product_id": "PRODUCT-001",
            "product_name": "Desk Lamp",
            "category": "Home",
            "quantity": 2,
            "unit_price": Decimal("10.00"),
            "discount_percent": Decimal("10.00"),
            "unit_cost": Decimal("6.00"),
            "gross_revenue": Decimal("20.00"),
            "discount_amount": Decimal("2.00"),
            "net_revenue": Decimal("18.00"),
            "total_cost": Decimal("12.00"),
            "profit": Decimal("6.00"),
        }
        values.update(overrides)
        return SalesLine.objects.create(**values)

    def test_ready_dataset_requires_positive_summaries(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dataset.objects.create(
                    name="Invalid Ready Dataset",
                    original_filename="invalid.csv",
                    currency="EUR",
                    status=Dataset.Status.READY,
                    row_count=0,
                    order_count=0,
                    start_date=date(2026, 1, 10),
                    end_date=date(2026, 1, 10),
                )

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dataset.objects.create(
                    name="Invalid Currency Dataset",
                    original_filename="invalid_currency.csv",
                    currency="eur",
                    status=Dataset.Status.READY,
                    row_count=1,
                    order_count=1,
                    start_date=date(2026, 1, 10),
                    end_date=date(2026, 1, 10),
                )

    def test_duplicate_order_id_in_dataset_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SalesOrder.objects.create(
                    dataset=self.dataset,
                    source_order_id="ORDER-001",
                    order_date=date(2026, 1, 10),
                )

    def test_duplicate_source_row_in_order_is_rejected(self):
        self.create_valid_line()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_valid_line()

    def test_cost_fields_must_be_consistent(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_valid_line(
                    unit_cost=None,
                    total_cost=Decimal("12.00"),
                    profit=Decimal("6.00"),
                )

    def test_warning_details_must_be_json_object(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DatasetWarning.objects.create(
                    dataset=self.dataset,
                    code=DatasetWarning.Code.DUPLICATE_ROWS,
                    message="Invalid JSON details.",
                    affected_row_count=1,
                    details=["source row 2"],
                )

    def test_future_order_date_fails_django_validation(self):
        future_order = SalesOrder(
            dataset=self.dataset,
            source_order_id="FUTURE-ORDER",
            order_date=timezone.localdate() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            future_order.full_clean()

    def test_same_order_id_is_allowed_in_different_datasets(self):
        second_dataset = Dataset.objects.create(
            name="Second Dataset",
            original_filename="second.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=1,
            order_count=1,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
        )

        second_order = SalesOrder.objects.create(
            dataset=second_dataset,
            source_order_id="ORDER-001",
            order_date=date(2026, 1, 10),
        )

        self.assertEqual(second_order.source_order_id, "ORDER-001")
        self.assertEqual(
            SalesOrder.objects.filter(
                source_order_id="ORDER-001",
            ).count(),
            2,
        )

    def test_duplicate_business_rows_with_different_row_numbers_are_allowed(
        self,
    ):
        first_line = self.create_valid_line()
        second_line = self.create_valid_line(
            source_row_number=3,
        )

        self.assertNotEqual(
            first_line.source_row_number,
            second_line.source_row_number,
        )
        self.assertEqual(SalesLine.objects.count(), 2)

    def test_negative_profit_is_allowed(self):
        line = self.create_valid_line(
            unit_cost=Decimal("12.00"),
            total_cost=Decimal("24.00"),
            profit=Decimal("-6.00"),
        )

        self.assertEqual(line.profit, Decimal("-6.00"))

    def test_failed_atomic_operation_leaves_no_partial_dataset(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                atomic_dataset = Dataset.objects.create(
                    name="Atomic Rollback Dataset",
                    original_filename="atomic.csv",
                    currency="EUR",
                    status=Dataset.Status.READY,
                    row_count=1,
                    order_count=1,
                    start_date=date(2026, 1, 10),
                    end_date=date(2026, 1, 10),
                )

                atomic_order = SalesOrder.objects.create(
                    dataset=atomic_dataset,
                    source_order_id="ATOMIC-ORDER",
                    order_date=date(2026, 1, 10),
                )

                SalesLine.objects.create(
                    order=atomic_order,
                    source_row_number=2,
                    product_name="Invalid Product",
                    category="Test",
                    quantity=0,
                    unit_price=Decimal("10.00"),
                    discount_percent=Decimal("0.00"),
                    gross_revenue=Decimal("0.00"),
                    discount_amount=Decimal("0.00"),
                    net_revenue=Decimal("0.00"),
                )

        self.assertFalse(
            Dataset.objects.filter(
                name="Atomic Rollback Dataset",
            ).exists()
        )
        self.assertFalse(
            SalesOrder.objects.filter(
                source_order_id="ATOMIC-ORDER",
            ).exists()
        )

class DatasetViewTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="Interface Test Dataset",
            original_filename="interface_test.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=25,
            order_count=10,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            has_product_id=True,
            has_customer_id=True,
            has_region=True,
            has_sales_channel=True,
            has_discount=True,
            has_unit_cost=True,
            has_complete_unit_cost=True,
        )

    def test_upload_page_loads_successfully(self):
        response = self.client.get(
            reverse("datasets:upload"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "datasets/upload.html",
        )

    def test_history_page_displays_dataset(self):
        response = self.client.get(
            reverse("datasets:history"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "datasets/history.html",
        )
        self.assertContains(
            response,
            self.dataset.name,
        )

    def test_detail_page_displays_dataset(self):
        response = self.client.get(
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "datasets/detail.html",
        )
        self.assertContains(
            response,
            self.dataset.name,
        )
        self.assertContains(
            response,
            self.dataset.original_filename,
        )

    def test_missing_dataset_detail_returns_404(self):
        response = self.client.get(
            reverse(
                "datasets:detail",
                args=[999999],
            ),
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_confirmation_does_not_delete_dataset(self):
        response = self.client.get(
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "datasets/delete_confirm.html",
        )
        self.assertTrue(
            Dataset.objects.filter(
                pk=self.dataset.pk,
            ).exists()
        )

    def test_post_request_deletes_dataset(self):
        response = self.client.post(
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("datasets:history"),
        )
        self.assertFalse(
            Dataset.objects.filter(
                pk=self.dataset.pk,
            ).exists()
        )
        self.assertContains(
            response,
            "&quot;Interface Test Dataset&quot; was deleted successfully.",
        )

from datetime import date, timedelta
from decimal import Decimal

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from .services.csv_processor import (
    CsvValidationError,
    read_and_validate_csv,
)
from .services.dataset_importer import (
    persist_processed_dataset,
)
from .forms import DatasetUploadForm, MAX_UPLOAD_SIZE
from .models import (
    Dataset,
    DatasetWarning,
    SalesLine,
    SalesOrder,
)


class CsvStructureValidationTests(SimpleTestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.csv_path = (
            Path(self.temporary_directory.name)
            / "sales.csv"
        )

    def write_csv(self, content):
        self.csv_path.write_text(
            content,
            encoding="utf-8",
            newline="",
        )

        return self.csv_path

    def test_valid_csv_is_loaded_and_unsupported_columns_are_removed(
        self,
    ):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,notes\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,Featured\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            list(result.dataframe.columns),
            [
                "order_id",
                "order_date",
                "product_name",
                "category",
                "quantity",
                "unit_price",
                "discount_percent",
                "unit_cost",
                "gross_revenue",
                "discount_amount",
                "net_revenue",
                "total_cost",
                "profit",
            ],
        )
        self.assertEqual(
            result.unsupported_columns,
            ("notes",),
        )
        self.assertEqual(
            result.dataframe.iloc[0]["order_id"],
            "ORDER-001",
        )

    def test_column_names_are_normalized(self):
        csv_path = self.write_csv(
            " ORDER_ID , ORDER_DATE , PRODUCT_NAME ,"
            " CATEGORY , QUANTITY , UNIT_PRICE \n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            list(result.dataframe.columns),
            [
                "order_id",
                "order_date",
                "product_name",
                "category",
                "quantity",
                "unit_price",
                "discount_percent",
                "unit_cost",
                "gross_revenue",
                "discount_amount",
                "net_revenue",
                "total_cost",
                "profit",
            ],
        )

    def test_missing_required_columns_are_rejected(self):
        csv_path = self.write_csv(
            "order_id,product_name\n"
            "ORDER-001,Desk Lamp\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            "Missing required columns: "
            "order_date, category, quantity, unit_price.",
            context.exception.errors,
        )

    def test_duplicate_normalized_columns_are_rejected(self):
        csv_path = self.write_csv(
            "order_id, ORDER_ID ,order_date,"
            "product_name,category,quantity,unit_price\n"
            "ORDER-001,ORDER-001,2026-01-10,"
            "Desk Lamp,Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            "Duplicate columns after normalization: "
            "order_id.",
            context.exception.errors,
        )

    def test_header_without_data_rows_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,"
            "category,quantity,unit_price\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            "The CSV file must contain at least one data row.",
            context.exception.errors,
        )

    def test_non_comma_separator_is_rejected(self):
        csv_path = self.write_csv(
            "order_id;order_date;product_name;"
            "category;quantity;unit_price\n"
            "ORDER-001;2026-01-10;Desk Lamp;"
            "Home;2;10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            "The CSV file must use commas as separators.",
            context.exception.errors,
        )

    def test_non_utf8_file_is_rejected(self):
        self.csv_path.write_bytes(
            b"order_id,order_date,product_name,"
            b"category,quantity,unit_price\n"
            b"\xff\xfe\xfa\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(self.csv_path)

        self.assertIn(
            "The CSV file must use UTF-8 encoding.",
            context.exception.errors,
        )

    @patch(
        "datasets.services.csv_processor.MAX_DATA_ROWS",
        1,
    )
    def test_row_limit_is_enforced(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,"
            "category,quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
            "ORDER-002,2026-01-11,Chair,"
            "Furniture,1,50.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertTrue(
            any(
                "must not contain more than"
                in error
                for error in context.exception.errors
            )
        )

    def test_malformed_csv_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,"
            "category,quantity,unit_price\n"
            'ORDER-001,2026-01-10,"Desk Lamp,'
            "Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            "The CSV file could not be parsed correctly.",
            context.exception.errors,
        )

    def test_text_values_are_trimmed(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,customer_id\n"
            "  ORDER-001  ,2026-01-10,  Desk Lamp  ,"
            "  Home  ,2,10.00,  CUSTOMER-001  \n"
        )

        result = read_and_validate_csv(csv_path)
        row = result.dataframe.iloc[0]

        self.assertEqual(row["order_id"], "ORDER-001")
        self.assertEqual(row["product_name"], "Desk Lamp")
        self.assertEqual(row["category"], "Home")
        self.assertEqual(
            row["customer_id"],
            "CUSTOMER-001",
        )

    def test_empty_required_text_values_are_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "   ,2026-01-10,   ,Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "order_id", '
            'value "": A value is required.',
            context.exception.errors,
        )
        self.assertIn(
            'Row 2, column "product_name", '
            'value "": A value is required.',
            context.exception.errors,
        )

    def test_empty_optional_text_values_are_allowed(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,customer_id\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,   \n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.dataframe.iloc[0]["customer_id"],
            "",
        )

    def test_valid_order_date_is_converted_to_date(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.dataframe.iloc[0]["order_date"],
            date(2026, 1, 10),
        )

    def test_order_date_requires_iso_format(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,10/01/2026,Desk Lamp,"
            "Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "order_date", '
            'value "10/01/2026": Expected the '
            "YYYY-MM-DD format.",
            context.exception.errors,
        )

    def test_invalid_calendar_date_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-02-30,Desk Lamp,"
            "Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "order_date", '
            'value "2026-02-30": This is not a valid '
            "calendar date.",
            context.exception.errors,
        )

    def test_empty_order_date_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,,Desk Lamp,Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "order_date", '
            'value "": A value is required.',
            context.exception.errors,
        )

    def test_future_order_date_is_rejected(self):
        future_date = (
            timezone.localdate() + timedelta(days=1)
        ).isoformat()

        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            f"ORDER-001,{future_date},Desk Lamp,"
            "Home,2,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            f'Row 2, column "order_date", '
            f'value "{future_date}": Order date cannot '
            "be in the future.",
            context.exception.errors,
        )

    def test_required_numbers_are_converted(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.125\n"
        )

        result = read_and_validate_csv(csv_path)
        row = result.dataframe.iloc[0]

        self.assertEqual(row["quantity"], 2)
        self.assertEqual(
            row["unit_price"],
            Decimal("10.13"),
        )

    def test_empty_quantity_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "quantity", '
            'value "": A value is required.',
            context.exception.errors,
        )

    def test_decimal_quantity_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2.5,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "quantity", '
            'value "2.5": Quantity must be a whole number.',
            context.exception.errors,
        )

    def test_zero_quantity_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,0,10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "quantity", '
            'value "0": Quantity must be greater than zero.',
            context.exception.errors,
        )

    def test_empty_unit_price_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "unit_price", '
            'value "": A value is required.',
            context.exception.errors,
        )

    def test_unit_price_with_symbol_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,€10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "unit_price", '
            'value "€10.00": Unit price must be a plain '
            "number without symbols or separators.",
            context.exception.errors,
        )

    def test_negative_unit_price_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,-10.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "unit_price", '
            'value "-10.00": Unit price cannot be negative.',
            context.exception.errors,
        )

    def test_empty_discount_is_converted_to_zero(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,discount_percent\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.dataframe.iloc[0]["discount_percent"],
            Decimal("0.00"),
        )

    def test_optional_numbers_are_converted_and_rounded(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,discount_percent,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,10.125,6.125\n"
        )

        result = read_and_validate_csv(csv_path)
        row = result.dataframe.iloc[0]

        self.assertEqual(
            row["discount_percent"],
            Decimal("10.13"),
        )
        self.assertEqual(
            row["unit_cost"],
            Decimal("6.13"),
        )

    def test_discount_above_one_hundred_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,discount_percent\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,100.01\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "discount_percent", '
            'value "100.01": Discount percent must be '
            "from 0 through 100.",
            context.exception.errors,
        )

    def test_negative_discount_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,discount_percent\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,-1\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "discount_percent", '
            'value "-1": Discount percent must be '
            "from 0 through 100.",
            context.exception.errors,
        )

    def test_empty_unit_cost_is_converted_to_none(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertIsNone(
            result.dataframe.iloc[0]["unit_cost"]
        )

    def test_negative_unit_cost_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,-5.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "unit_cost", '
            'value "-5.00": Unit cost cannot be negative.',
            context.exception.errors,
        )

    def test_optional_number_with_symbol_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,€5.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 2, column "unit_cost", '
            'value "€5.00": Unit cost must be a plain '
            "number without symbols or separators.",
            context.exception.errors,
        )

    def test_consistent_multi_line_order_is_allowed(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,product_id,customer_id,"
            "region,sales_channel\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,PRODUCT-001,CUSTOMER-001,"
            "Berlin,Online\n"
            "ORDER-001,2026-01-10,Chair,Furniture,"
            "1,50.00,PRODUCT-002,CUSTOMER-001,"
            "Berlin,Online\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(len(result.dataframe), 2)

    def test_exact_duplicate_rows_are_detected_and_retained(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(len(result.dataframe), 2)
        self.assertEqual(
            result.duplicate_row_numbers,
            (3,),
        )


    def test_different_rows_are_not_reported_as_duplicates(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,3,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.duplicate_row_numbers,
            (),
        )


    def test_unsupported_columns_do_not_affect_duplicate_detection(
        self,
    ):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,notes\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,First note\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,Second note\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.unsupported_columns,
            ("notes",),
        )
        self.assertEqual(
            result.duplicate_row_numbers,
            (3,),
        )
        self.assertEqual(len(result.dataframe), 2)


    def test_inconsistent_order_date_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
            "ORDER-001,2026-01-11,Chair,"
            "Furniture,1,50.00\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 3, column "order_date", '
            'value "2026-01-11": Must match value '
            '"2026-01-10" used for order_id '
            '"ORDER-001" on row 2.',
            context.exception.errors,
        )


    def test_inconsistent_order_information_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,customer_id,region,"
            "sales_channel\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,CUSTOMER-001,Berlin,Online\n"
            "ORDER-001,2026-01-10,Chair,Furniture,"
            "1,50.00,CUSTOMER-002,Berlin,Online\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 3, column "customer_id", '
            'value "CUSTOMER-002": Must match value '
            '"CUSTOMER-001" used for order_id '
            '"ORDER-001" on row 2.',
            context.exception.errors,
        )


    def test_empty_optional_order_value_is_allowed(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,customer_id\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,CUSTOMER-001\n"
            "ORDER-001,2026-01-10,Chair,"
            "Furniture,1,50.00,\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(len(result.dataframe), 2)


    def test_inconsistent_product_information_is_rejected(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,product_id\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,PRODUCT-001\n"
            "ORDER-002,2026-01-11,Standing Lamp,"
            "Home,1,25.00,PRODUCT-001\n"
        )

        with self.assertRaises(
            CsvValidationError
        ) as context:
            read_and_validate_csv(csv_path)

        self.assertIn(
            'Row 3, column "product_name", '
            'value "Standing Lamp": Must match value '
            '"Desk Lamp" used for product_id '
            '"PRODUCT-001" on row 2.',
            context.exception.errors,
        )

    def test_unsupported_column_warning_is_created(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,notes\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00,Featured\n"
        )

        result = read_and_validate_csv(csv_path)

        warning = next(
            warning
            for warning in result.warnings
            if warning.code == "UNSUPPORTED_COLUMNS"
        )

        self.assertEqual(
            warning.message,
            "Unsupported columns were ignored: notes.",
        )
        self.assertIsNone(warning.affected_row_count)
        self.assertEqual(
            warning.details,
            {"columns": ["notes"]},
        )


    def test_duplicate_row_warning_is_created(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        warning = next(
            warning
            for warning in result.warnings
            if warning.code == "DUPLICATE_ROWS"
        )

        self.assertEqual(
            warning.message,
            "1 exact duplicate row was retained.",
        )
        self.assertEqual(warning.affected_row_count, 1)
        self.assertEqual(
            warning.details,
            {"source_rows": [3]},
        )


    def test_missing_optional_columns_create_warning(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        warning = next(
            warning
            for warning in result.warnings
            if warning.code == "INCOMPLETE_OPTIONAL_DATA"
        )

        self.assertEqual(
            warning.affected_row_count,
            1,
        )
        self.assertEqual(
            warning.details["missing_columns"],
            [
                "product_id",
                "customer_id",
                "region",
                "sales_channel",
                "discount_percent",
                "unit_cost",
            ],
        )


    def test_empty_optional_values_create_warning(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,product_id,customer_id,"
            "region,sales_channel,discount_percent,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,PRODUCT-001,,Berlin,Online,0,\n"
        )

        result = read_and_validate_csv(csv_path)

        warning = next(
            warning
            for warning in result.warnings
            if warning.code == "INCOMPLETE_OPTIONAL_DATA"
        )

        self.assertEqual(
            warning.details["missing_columns"],
            [],
        )
        self.assertEqual(
            warning.details["empty_value_rows"],
            {
                "customer_id": [2],
                "unit_cost": [2],
            },
        )
        self.assertEqual(
            warning.affected_row_count,
            1,
        )


    def test_complete_optional_data_creates_no_incomplete_warning(
        self,
    ):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,product_id,customer_id,"
            "region,sales_channel,discount_percent,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,PRODUCT-001,CUSTOMER-001,"
            "Berlin,Online,10,6.00\n"
        )

        result = read_and_validate_csv(csv_path)

        warning_codes = {
            warning.code
            for warning in result.warnings
        }

        self.assertNotIn(
            "INCOMPLETE_OPTIONAL_DATA",
            warning_codes,
        )
    def test_financial_values_are_calculated(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,discount_percent,unit_cost\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,3,19.99,12.5,11.111\n"
        )

        result = read_and_validate_csv(csv_path)
        row = result.dataframe.iloc[0]

        self.assertEqual(
            row["gross_revenue"],
            Decimal("59.97"),
        )
        self.assertEqual(
            row["discount_amount"],
            Decimal("7.50"),
        )
        self.assertEqual(
            row["net_revenue"],
            Decimal("52.47"),
        )
        self.assertEqual(
            row["total_cost"],
            Decimal("33.33"),
        )
        self.assertEqual(
            row["profit"],
            Decimal("19.14"),
        )


    def test_missing_financial_options_use_safe_defaults(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)
        row = result.dataframe.iloc[0]

        self.assertEqual(
            row["discount_percent"],
            Decimal("0.00"),
        )
        self.assertIsNone(row["unit_cost"])
        self.assertEqual(
            row["gross_revenue"],
            Decimal("20.00"),
        )
        self.assertEqual(
            row["discount_amount"],
            Decimal("0.00"),
        )
        self.assertEqual(
            row["net_revenue"],
            Decimal("20.00"),
        )
        self.assertIsNone(row["total_cost"])
        self.assertIsNone(row["profit"])

    def test_source_columns_exclude_generated_columns(self):
        csv_path = self.write_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        result = read_and_validate_csv(csv_path)

        self.assertEqual(
            result.source_columns,
            (
                "order_id",
                "order_date",
                "product_name",
                "category",
                "quantity",
                "unit_price",
            ),
        )

        self.assertNotIn(
            "discount_percent",
            result.source_columns,
        )
        self.assertNotIn(
            "gross_revenue",
            result.source_columns,
        )


class DatasetImportServiceTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.csv_path = (
            Path(self.temporary_directory.name)
            / "sales.csv"
        )

    def process_csv(self, content):
        self.csv_path.write_text(
            content,
            encoding="utf-8",
            newline="",
        )

        return read_and_validate_csv(
            self.csv_path
        )

    def test_processed_dataset_is_persisted(self):
        result = self.process_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price,product_id,customer_id,"
            "region,sales_channel,discount_percent,"
            "unit_cost,notes\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,PRODUCT-001,CUSTOMER-001,"
            "Berlin,Online,10,6.00,First note\n"
            "ORDER-001,2026-01-10,Desk Lamp,Home,"
            "2,10.00,PRODUCT-001,CUSTOMER-001,"
            "Berlin,Online,10,6.00,Second note\n"
            "ORDER-002,2026-01-11,Chair,Furniture,"
            "1,50.00,PRODUCT-002,CUSTOMER-002,"
            "Hamburg,Retail,0,,Third note\n"
        )

        dataset = persist_processed_dataset(
            result=result,
            name="January Sales",
            original_filename="january-sales.csv",
            currency="EUR",
        )

        dataset.refresh_from_db()

        self.assertEqual(
            dataset.status,
            Dataset.Status.READY,
        )
        self.assertEqual(dataset.row_count, 3)
        self.assertEqual(dataset.order_count, 2)
        self.assertEqual(
            dataset.start_date,
            date(2026, 1, 10),
        )
        self.assertEqual(
            dataset.end_date,
            date(2026, 1, 11),
        )

        self.assertTrue(dataset.has_product_id)
        self.assertTrue(dataset.has_customer_id)
        self.assertTrue(dataset.has_region)
        self.assertTrue(
            dataset.has_sales_channel
        )
        self.assertTrue(dataset.has_discount)
        self.assertTrue(dataset.has_unit_cost)
        self.assertFalse(
            dataset.has_complete_unit_cost
        )

        self.assertEqual(
            dataset.orders.count(),
            2,
        )
        self.assertEqual(
            SalesLine.objects.count(),
            3,
        )

        first_order = dataset.orders.get(
            source_order_id="ORDER-001"
        )

        self.assertEqual(
            first_order.lines.count(),
            2,
        )
        self.assertEqual(
            list(
                first_order.lines.order_by(
                    "source_row_number"
                ).values_list(
                    "source_row_number",
                    flat=True,
                )
            ),
            [2, 3],
        )

        first_line = first_order.lines.get(
            source_row_number=2
        )

        self.assertEqual(
            first_line.gross_revenue,
            Decimal("20.00"),
        )
        self.assertEqual(
            first_line.discount_amount,
            Decimal("2.00"),
        )
        self.assertEqual(
            first_line.net_revenue,
            Decimal("18.00"),
        )
        self.assertEqual(
            first_line.total_cost,
            Decimal("12.00"),
        )
        self.assertEqual(
            first_line.profit,
            Decimal("6.00"),
        )

        self.assertEqual(
            set(
                dataset.warnings.values_list(
                    "code",
                    flat=True,
                )
            ),
            {
                DatasetWarning.Code.UNSUPPORTED_COLUMNS,
                DatasetWarning.Code.DUPLICATE_ROWS,
                DatasetWarning.Code.INCOMPLETE_OPTIONAL_DATA,
            },
        )

    def test_blank_name_is_derived_from_filename(self):
        result = self.process_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        dataset = persist_processed_dataset(
            result=result,
            name="   ",
            original_filename="january-sales.csv",
            currency="USD",
        )

        self.assertEqual(
            dataset.name,
            "january-sales",
        )
        self.assertEqual(
            dataset.original_filename,
            "january-sales.csv",
        )
        self.assertFalse(dataset.has_product_id)
        self.assertFalse(dataset.has_discount)
        self.assertFalse(dataset.has_unit_cost)
        self.assertFalse(
            dataset.has_complete_unit_cost
        )

        line = SalesLine.objects.get()

        self.assertEqual(
            line.discount_percent,
            Decimal("0.00"),
        )
        self.assertIsNone(line.unit_cost)
        self.assertIsNone(line.total_cost)
        self.assertIsNone(line.profit)

    @patch(
        "datasets.services.dataset_importer."
        "SalesLine.objects.bulk_create"
    )
    def test_failure_rolls_back_complete_import(
        self,
        mocked_bulk_create,
    ):
        mocked_bulk_create.side_effect = RuntimeError(
            "Simulated persistence failure."
        )

        result = self.process_csv(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        with self.assertRaises(RuntimeError):
            persist_processed_dataset(
                result=result,
                name="Rollback Test",
                original_filename="rollback.csv",
                currency="EUR",
            )

        self.assertEqual(Dataset.objects.count(), 0)
        self.assertEqual(
            DatasetWarning.objects.count(),
            0,
        )
        self.assertEqual(
            SalesOrder.objects.count(),
            0,
        )
        self.assertEqual(
            SalesLine.objects.count(),
            0,
        )


class DatasetUploadFormTests(TestCase):
    def make_csv_file(
        self,
        name="sales.csv",
        content=b"order_id\nORDER-001",
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type="text/csv",
        )

    def test_valid_form_normalizes_currency(self):
        form = DatasetUploadForm(
            data={
                "name": "January Sales",
                "currency": " eur ",
            },
            files={
                "csv_file": self.make_csv_file(),
            },
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(
            form.cleaned_data["currency"],
            "EUR",
        )

    def test_dataset_name_is_optional(self):
        form = DatasetUploadForm(
            data={
                "name": "",
                "currency": "USD",
            },
            files={
                "csv_file": self.make_csv_file(),
            },
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data["name"], "")

    def test_currency_must_use_ascii_letters(self):
        form = DatasetUploadForm(
            data={
                "name": "Invalid Currency",
                "currency": "EU1",
            },
            files={
                "csv_file": self.make_csv_file(),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Enter a valid three-letter currency code using A–Z.",
            form.errors["currency"],
        )

    def test_file_must_have_csv_extension(self):
        form = DatasetUploadForm(
            data={
                "name": "Wrong File Type",
                "currency": "EUR",
            },
            files={
                "csv_file": self.make_csv_file(
                    name="sales.txt",
                ),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The uploaded file must use the .csv extension.",
            form.errors["csv_file"],
        )

    def test_empty_csv_file_is_rejected(self):
        form = DatasetUploadForm(
            data={
                "name": "Empty Dataset",
                "currency": "EUR",
            },
            files={
                "csv_file": self.make_csv_file(content=b""),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The uploaded CSV file is empty.",
            form.errors["csv_file"],
        )

    def test_file_larger_than_limit_is_rejected(self):
        oversized_content = b"x" * (MAX_UPLOAD_SIZE + 1)

        form = DatasetUploadForm(
            data={
                "name": "Oversized Dataset",
                "currency": "EUR",
            },
            files={
                "csv_file": self.make_csv_file(
                    content=oversized_content,
                ),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The uploaded CSV file must not exceed 10 MB.",
            form.errors["csv_file"],
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

class DatasetUploadWorkflowTests(TestCase):
    def make_csv_file(
        self,
        content,
        name="sales.csv",
    ):
        return SimpleUploadedFile(
            name=name,
            content=content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_valid_csv_is_imported_and_redirects_to_detail(
        self,
    ):
        csv_file = self.make_csv_file(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        response = self.client.post(
            reverse("datasets:upload"),
            data={
                "name": "January Sales",
                "currency": "eur",
                "csv_file": csv_file,
            },
        )

        dataset = Dataset.objects.get(
            name="January Sales"
        )

        self.assertRedirects(
            response,
            reverse(
                "datasets:detail",
                args=[dataset.pk],
            ),
        )
        self.assertEqual(
            dataset.status,
            Dataset.Status.READY,
        )
        self.assertEqual(dataset.currency, "EUR")
        self.assertEqual(dataset.row_count, 1)
        self.assertEqual(dataset.order_count, 1)
        self.assertEqual(
            SalesOrder.objects.count(),
            1,
        )
        self.assertEqual(
            SalesLine.objects.count(),
            1,
        )

    def test_invalid_csv_is_redisplayed_with_errors(self):
        csv_file = self.make_csv_file(
            "order_id,product_name\n"
            "ORDER-001,Desk Lamp\n"
        )

        response = self.client.post(
            reverse("datasets:upload"),
            data={
                "name": "Invalid Dataset",
                "currency": "EUR",
                "csv_file": csv_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "datasets/upload.html",
        )
        self.assertContains(
            response,
            "Missing required columns: "
            "order_date, category, quantity, unit_price.",
        )
        self.assertEqual(
            Dataset.objects.count(),
            0,
        )
        self.assertEqual(
            SalesOrder.objects.count(),
            0,
        )
        self.assertEqual(
            SalesLine.objects.count(),
            0,
        )

    def test_success_message_is_displayed(self):
        csv_file = self.make_csv_file(
            "order_id,order_date,product_name,category,"
            "quantity,unit_price\n"
            "ORDER-001,2026-01-10,Desk Lamp,"
            "Home,2,10.00\n"
        )

        response = self.client.post(
            reverse("datasets:upload"),
            data={
                "name": "Message Test",
                "currency": "USD",
                "csv_file": csv_file,
            },
            follow=True,
        )

        self.assertContains(
            response,
            "&quot;Message Test&quot; was imported successfully.",
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

    def test_upload_page_displays_upload_form(self):
        response = self.client.get(
            reverse("datasets:upload"),
        )

        self.assertIsInstance(
            response.context["form"],
            DatasetUploadForm,
            )
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="currency"')
        self.assertContains(response, 'name="csv_file"')


class AnalyticsSalesViewTests(TestCase):
    def create_dataset_with_sale(self, name, status):
        dataset = Dataset.objects.create(
            name=name,
            original_filename=f"{name.lower()}.csv",
            currency="EUR",
            status=status,
            row_count=1,
            order_count=1,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
        )

        order = SalesOrder.objects.create(
            dataset=dataset,
            source_order_id="ORDER-001",
            order_date=date(2026, 1, 10),
            customer_id="CUSTOMER-001",
            region="Berlin",
            sales_channel="Online",
        )

        SalesLine.objects.create(
            order=order,
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

        return dataset

    def setUp(self):
        self.ready_dataset = self.create_dataset_with_sale(
            name="Ready Dataset",
            status=Dataset.Status.READY,
        )

        self.processing_dataset = self.create_dataset_with_sale(
            name="Processing Dataset",
            status=Dataset.Status.PROCESSING,
        )

    def test_view_returns_ready_sales_data(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM analytics_sales
                WHERE dataset_id = %s
                """,
                [self.ready_dataset.id],
            )

            columns = [
                column[0]
                for column in cursor.description
            ]
            row = cursor.fetchone()

        self.assertIsNotNone(row)

        result = dict(zip(columns, row))

        self.assertEqual(
            result["dataset_name"],
            "Ready Dataset",
        )
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(
            result["source_order_id"],
            "ORDER-001",
        )
        self.assertEqual(
            result["product_name"],
            "Desk Lamp",
        )
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(
            result["net_revenue"],
            Decimal("18.00"),
        )
        self.assertEqual(
            result["profit"],
            Decimal("6.00"),
        )

    def test_view_excludes_non_ready_datasets(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT dataset_id
                FROM analytics_sales
                ORDER BY dataset_id
                """
            )

            dataset_ids = [
                row[0]
                for row in cursor.fetchall()
            ]

        self.assertEqual(
            dataset_ids,
            [self.ready_dataset.id],
        )
        self.assertNotIn(
            self.processing_dataset.id,
            dataset_ids,
        )

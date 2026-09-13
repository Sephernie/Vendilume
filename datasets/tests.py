import json
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO


from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import URLError

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command

from .services.csv_processor import (
    CsvValidationError,
    read_and_validate_csv,
)
from .services.dataset_importer import (
    persist_processed_dataset,
)
from .services.analytics_insights import (
    generate_sales_insights,
)
from .services.analytics_summary import (
    build_analytics_summary,
)
from .services.ai_insights import (
    AIInsightRequestError,
    AIInsightValidationError,
    build_ai_insight_messages,
    validate_ai_insight_response,
)
from .services.gemini_provider import (
    DEFAULT_GEMINI_MODEL,
    GeminiInsightProviderError,
    build_gemini_response_schema,
    generate_gemini_insights,
)
from .services.business_insights import (
    AI_UNAVAILABLE_NOTICE,
    NO_MATCHING_DATA_NOTICE,
    generate_business_insights,
)
from .forms import AnalyticsFilterForm, DatasetUploadForm, MAX_UPLOAD_SIZE
from .models import (
    Dataset,
    DatasetWarning,
    SalesLine,
    SalesOrder,
)
from accounts.roles import (
    ADMINISTRATORS,
    MANAGERS,
    SALES_ANALYSTS,
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
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="upload.analyst",
            password="TestPassword123!",
        )
        self.client.force_login(self.user)

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

    def test_currency_uses_dropdown_with_supported_choices(self):
        form = DatasetUploadForm()

        self.assertEqual(
            form.fields["currency"].widget.input_type,
            "select",
        )
        self.assertIn(
            ("EUR", "EUR — Euro"),
            form.fields["currency"].choices,
        )
        self.assertIn(
            ("IRR", "IRR — Iranian Rial"),
            form.fields["currency"].choices,
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
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="upload.analyst",
            password="TestPassword123!",
        )
        permissions = Permission.objects.filter(
            content_type__app_label="datasets",
            codename__in=[
                "add_dataset",
                "view_dataset",
            ],
        )
        self.user.user_permissions.add(*permissions)

        self.client.force_login(self.user)

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

    def test_upload_page_links_to_downloadable_csv_template(self):
        response = self.client.get(
            reverse("datasets:upload")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Download CSV template",
        )
        self.assertContains(
            response,
            "core/files/vendilume-sales-template.csv",
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

class AnalyticsFilterFormTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="Filter Dataset",
            original_filename="filters.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=1,
            order_count=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            has_customer_id=True,
            has_region=True,
            has_sales_channel=True,
        )

        order = SalesOrder.objects.create(
            dataset=self.dataset,
            source_order_id="ORDER-001",
            order_date=date(2026, 1, 10),
            customer_id="CUSTOMER-001",
            region="Berlin",
            sales_channel="Online",
        )

        SalesLine.objects.create(
            order=order,
            source_row_number=2,
            product_name="Keyboard",
            category="Electronics",
            quantity=2,
            unit_price=Decimal("50.00"),
            gross_revenue=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            net_revenue=Decimal("100.00"),
        )

    def test_choices_are_scoped_to_selected_dataset(self):
        form = AnalyticsFilterForm(
            dataset=self.dataset
        )

        self.assertEqual(
            list(form.fields["product"].choices),
            [
                ("", "All products"),
                ("Keyboard", "Keyboard"),
            ],
        )
        self.assertEqual(
            list(form.fields["category"].choices),
            [
                ("", "All categories"),
                ("Electronics", "Electronics"),
            ],
        )
        self.assertEqual(
            list(form.fields["region"].choices),
            [
                ("", "All regions"),
                ("Berlin", "Berlin"),
            ],
        )

    def test_optional_fields_are_removed_when_unsupported(self):
        self.dataset.has_customer_id = False
        self.dataset.has_region = False
        self.dataset.has_sales_channel = False
        self.dataset.save(
            update_fields=[
                "has_customer_id",
                "has_region",
                "has_sales_channel",
            ]
        )

        form = AnalyticsFilterForm(
            dataset=self.dataset
        )

        self.assertNotIn("customer", form.fields)
        self.assertNotIn("region", form.fields)
        self.assertNotIn("sales_channel", form.fields)

    def test_invalid_filter_values_are_rejected(self):
        form = AnalyticsFilterForm(
            data={
                "start_date": "2025-12-31",
                "end_date": "2026-02-01",
                "product": "Unknown Product",
                "category": "",
                "region": "",
                "sales_channel": "",
                "customer": "",
            },
            dataset=self.dataset,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)
        self.assertIn("end_date", form.errors)
        self.assertIn("product", form.errors)


class AIInsightResponseValidationTests(SimpleTestCase):
    def valid_payload(self):
        return {
            "executive_summary": (
                "Revenue increased during the period."
            ),
            "important_findings": [
                "Furniture generated the most revenue.",
            ],
            "risks_and_warnings": [],
            "recommended_actions": [
                "Review the strongest furniture products.",
            ],
            "areas_for_investigation": [
                "Investigate changes in customer demand.",
            ],
        }

    def test_valid_response_is_normalized(self):
        payload = self.valid_payload()
        payload["executive_summary"] = (
            "  Revenue increased during the period.  "
        )

        result = validate_ai_insight_response(payload)

        self.assertEqual(
            result["executive_summary"],
            "Revenue increased during the period.",
        )

    def test_response_must_be_an_object(self):
        with self.assertRaises(
            AIInsightValidationError
        ):
            validate_ai_insight_response([])

    def test_response_rejects_missing_fields(self):
        payload = self.valid_payload()
        del payload["recommended_actions"]

        with self.assertRaises(
            AIInsightValidationError
        ):
            validate_ai_insight_response(payload)

    def test_response_rejects_invalid_list_items(self):
        payload = self.valid_payload()
        payload["important_findings"] = [""]

        with self.assertRaises(
            AIInsightValidationError
        ):
            validate_ai_insight_response(payload)

    def valid_summary(self):
        return {
            "schema_version": 1,
            "has_data": True,
            "dataset": {
                "id": 1,
                "name": "Test Dataset",
                "currency": "EUR",
            },
            "metrics": {
                "net_revenue": "450.00",
            },
        }

    def test_prompt_contains_trusted_summary(self):
        summary = self.valid_summary()

        messages = build_ai_insight_messages(summary)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

        self.assertIn(
            '"net_revenue": "450.00"',
            messages[1]["content"],
        )
        self.assertIn(
            '"currency": "EUR"',
            messages[1]["content"],
        )

    def test_prompt_prohibits_recalculating_metrics(self):
        messages = build_ai_insight_messages(
            self.valid_summary()
        )

        self.assertIn(
            "Never recalculate",
            messages[0]["content"],
        )
        self.assertIn(
            "Do not invent",
            messages[0]["content"],
        )

    def test_prompt_rejects_summary_without_data(self):
        summary = self.valid_summary()
        summary["has_data"] = False

        with self.assertRaises(AIInsightRequestError):
            build_ai_insight_messages(summary)

    def test_prompt_removes_sensitive_identifiers(self):
        summary = self.valid_summary()
        summary["dataset"]["id"] = 42
        summary["dataset"]["name"] = (
            "Confidential Customer Dataset"
        )
        summary["filters"] = {
            "customer": "customer-123",
        }

        messages = build_ai_insight_messages(summary)
        prompt = messages[1]["content"]

        self.assertNotIn(
            '"id": 42',
            prompt,
        )
        self.assertNotIn(
            "Confidential Customer Dataset",
            prompt,
        )
        self.assertNotIn(
            "customer-123",
            prompt,
        )
        self.assertIn(
            '"customer": "selected"',
            prompt,
        )

    def test_prompt_explains_null_filters(self):
        messages = build_ai_insight_messages(
            self.valid_summary()
        )

        system_prompt = messages[0]["content"]

        self.assertIn(
            "A null filter means no filter was applied",
            system_prompt,
        )
        self.assertIn(
            "Determine field availability only from "
            "data_availability",
            system_prompt,
        )


class GeminiInsightProviderTests(SimpleTestCase):
    def valid_payload(self):
        return {
            "executive_summary": (
                "Revenue increased during the period."
            ),
            "important_findings": [
                "Furniture generated the most revenue.",
            ],
            "risks_and_warnings": [],
            "recommended_actions": [
                "Review the strongest furniture products.",
            ],
            "areas_for_investigation": [
                "Investigate changes in customer demand.",
            ],
        }

    def valid_summary(self):
        return {
            "schema_version": 1,
            "has_data": True,
            "dataset": {
                "id": 1,
                "name": "Test Dataset",
                "currency": "EUR",
            },
            "metrics": {
                "net_revenue": "450.00",
            },
        }

    def test_generates_validated_insights(self):
        client = Mock()
        client.models.generate_content.return_value.text = (
            json.dumps(self.valid_payload())
        )

        result = generate_gemini_insights(
            self.valid_summary(),
            client=client,
        )

        self.assertEqual(
            result["executive_summary"],
            "Revenue increased during the period.",
        )

        request = (
            client.models.generate_content.call_args.kwargs
        )

        self.assertEqual(
            request["model"],
            DEFAULT_GEMINI_MODEL,
        )
        self.assertEqual(
            request["config"]["response_mime_type"],
            "application/json",
        )

    def test_schema_removes_unsupported_string_limits(self):
        schema = build_gemini_response_schema()
        serialized_schema = json.dumps(schema)

        self.assertNotIn(
            "minLength",
            serialized_schema,
        )
        self.assertNotIn(
            "maxLength",
            serialized_schema,
        )
        self.assertIn(
            "maxItems",
            serialized_schema,
        )

    def test_invalid_json_raises_provider_error(self):
        client = Mock()
        client.models.generate_content.return_value.text = (
            "not valid JSON"
        )

        with self.assertRaises(
            GeminiInsightProviderError
        ):
            generate_gemini_insights(
                self.valid_summary(),
                client=client,
            )

    def test_timeout_raises_provider_error(self):
        client = Mock()
        client.models.generate_content.side_effect = (
            TimeoutError("The request timed out.")
        )

        with self.assertRaises(
            GeminiInsightProviderError
        ) as context:
            generate_gemini_insights(
                self.valid_summary(),
                client=client,
            )

        self.assertEqual(
            str(context.exception),
            "The Gemini request failed.",
        )


class BusinessInsightServiceTests(SimpleTestCase):
    def summary(self):
        return {
            "schema_version": 1,
            "has_data": True,
            "rule_based_insights": [
                "Verified rule-based finding.",
            ],
        }

    def ai_response(self):
        return {
            "executive_summary": "Revenue remained healthy.",
            "important_findings": [
                "Revenue reached its expected level.",
            ],
            "risks_and_warnings": [],
            "recommended_actions": [
                "Continue monitoring revenue.",
            ],
            "areas_for_investigation": [],
        }

    def test_returns_gemini_insights_when_available(self):
        ai_generator = Mock(
            return_value=self.ai_response()
        )

        result = generate_business_insights(
            self.summary(),
            ai_generator=ai_generator,
        )

        self.assertEqual(result["source"], "gemini")
        self.assertEqual(
            result["ai_insights"],
            self.ai_response(),
        )
        self.assertIsNone(result["notice"])
        ai_generator.assert_called_once()

    def test_falls_back_when_gemini_fails(self):
        ai_generator = Mock(
            side_effect=GeminiInsightProviderError(
                "Gemini failed."
            )
        )

        result = generate_business_insights(
            self.summary(),
            ai_generator=ai_generator,
        )

        self.assertEqual(
            result["source"],
            "rule_based",
        )
        self.assertIsNone(result["ai_insights"])
        self.assertEqual(
            result["rule_based_insights"],
            ["Verified rule-based finding."],
        )
        self.assertEqual(
            result["notice"],
            AI_UNAVAILABLE_NOTICE,
        )

    def test_does_not_call_gemini_without_data(self):
        summary = self.summary()
        summary["has_data"] = False

        ai_generator = Mock()

        result = generate_business_insights(
            summary,
            ai_generator=ai_generator,
        )

        self.assertEqual(
            result["source"],
            "rule_based",
        )
        self.assertEqual(
            result["notice"],
            NO_MATCHING_DATA_NOTICE,
        )
        ai_generator.assert_not_called()


class SalesInsightTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="Insight Dataset",
            original_filename="insights.csv",
            currency="EUR",
            status=Dataset.Status.READY,
            row_count=3,
            order_count=3,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
            has_customer_id=True,
            has_region=True,
            has_sales_channel=True,
        )

        self.create_sale(
            order_id="ORDER-001",
            order_date=date(2026, 1, 10),
            product="Keyboard",
            category="Electronics",
            quantity=2,
            revenue="100.00",
            region="Berlin",
            channel="Online",
            customer="CUSTOMER-001",
        )
        self.create_sale(
            order_id="ORDER-002",
            order_date=date(2026, 2, 10),
            product="Chair",
            category="Furniture",
            quantity=5,
            revenue="250.00",
            region="Munich",
            channel="Retail",
            customer="CUSTOMER-002",
        )
        self.create_sale(
            order_id="ORDER-003",
            order_date=date(2026, 2, 15),
            product="Mouse",
            category="Electronics",
            quantity=10,
            revenue="100.00",
            region="Berlin",
            channel="Online",
            customer="CUSTOMER-001",
        )

    def create_sale(
        self,
        *,
        order_id,
        order_date,
        product,
        category,
        quantity,
        revenue,
        region,
        channel,
        customer,
    ):
        order = SalesOrder.objects.create(
            dataset=self.dataset,
            source_order_id=order_id,
            order_date=order_date,
            customer_id=customer,
            region=region,
            sales_channel=channel,
        )

        SalesLine.objects.create(
            order=order,
            source_row_number=2,
            product_name=product,
            category=category,
            quantity=quantity,
            unit_price=Decimal(revenue),
            gross_revenue=Decimal(revenue),
            discount_amount=Decimal("0.00"),
            net_revenue=Decimal(revenue),
        )

    def test_insights_identify_strongest_results(self):
        insights = generate_sales_insights(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
        )

        self.assertIn(
            "Chair generated the highest net revenue at "
            "250.00 EUR.",
            insights,
        )
        self.assertIn(
            "Furniture was the strongest-performing category, "
            "generating 250.00 EUR in net revenue.",
            insights,
        )
        self.assertIn(
            "Mouse sold the most units, with 10 items sold.",
            insights,
        )
        self.assertIn(
            "February 2026 recorded the highest monthly "
            "net revenue at 350.00 EUR.",
            insights,
        )

    def test_optional_filters_limit_insight_data(self):
        insights = generate_sales_insights(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
            region="Munich",
            sales_channel="Retail",
            customer="CUSTOMER-002",
        )

        self.assertIn(
            "Chair generated the highest net revenue at "
            "250.00 EUR.",
            insights,
        )
        self.assertTrue(
            all("Keyboard" not in insight for insight in insights)
        )
        self.assertTrue(
            all("Mouse" not in insight for insight in insights)
        )

    def test_no_matching_sales_returns_clear_message(self):
        insights = generate_sales_insights(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
            product="Chair",
            region="Berlin",
        )

        self.assertEqual(
            insights,
            [
                "No sales data matches the selected filters."
            ],
        )

    def test_analytics_summary_contains_trusted_metrics(self):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
        )

        self.assertEqual(summary["schema_version"], 1)
        self.assertTrue(summary["has_data"])

        self.assertEqual(
            summary["dataset"],
            {
                "id": self.dataset.pk,
                "name": "Insight Dataset",
                "currency": "EUR",
            },
        )

        self.assertEqual(
            summary["period"],
            {
                "start_date": "2026-01-01",
                "end_date": "2026-02-28",
            },
        )

        self.assertEqual(summary["metrics"]["line_count"], 3)
        self.assertEqual(summary["metrics"]["order_count"], 3)
        self.assertEqual(
            summary["metrics"]["total_quantity"],
            17,
        )
        self.assertEqual(
            summary["metrics"]["gross_revenue"],
            "450.00",
        )
        self.assertEqual(
            summary["metrics"]["net_revenue"],
            "450.00",
        )
        self.assertEqual(
            summary["metrics"]["average_order_value"],
            "150.00",
        )

        self.assertIsNone(
            summary["metrics"]["total_cost"]
        )
        self.assertIsNone(
            summary["metrics"]["profit"]
        )
        self.assertIsNone(
            summary["metrics"]["profit_margin_percent"]
        )

    def test_analytics_summary_uses_selected_filters(self):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
            region="Berlin",
            sales_channel="Online",
        )

        self.assertTrue(summary["has_data"])

        self.assertEqual(
            summary["filters"]["region"],
            "Berlin",
        )
        self.assertEqual(
            summary["filters"]["sales_channel"],
            "Online",
        )

        self.assertEqual(summary["metrics"]["line_count"], 2)
        self.assertEqual(summary["metrics"]["order_count"], 2)
        self.assertEqual(
            summary["metrics"]["total_quantity"],
            12,
        )
        self.assertEqual(
            summary["metrics"]["net_revenue"],
            "200.00",
        )
        self.assertEqual(
            summary["metrics"]["average_order_value"],
            "100.00",
        )

    def test_analytics_summary_handles_no_matching_data(self):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
            product="Unknown Product",
        )

        self.assertFalse(summary["has_data"])
        self.assertEqual(summary["metrics"]["line_count"], 0)
        self.assertEqual(summary["metrics"]["order_count"], 0)
        self.assertEqual(
            summary["metrics"]["total_quantity"],
            0,
        )
        self.assertEqual(
            summary["metrics"]["gross_revenue"],
            "0.00",
        )
        self.assertEqual(
            summary["metrics"]["net_revenue"],
            "0.00",
        )
        self.assertIsNone(
            summary["metrics"]["average_order_value"]
        )
    def test_analytics_summary_contains_rankings_and_trend(
        self,
    ):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
        )

        self.assertEqual(
            summary["rankings"][
                "top_products_by_net_revenue"
            ][0],
            {
                "name": "Chair",
                "net_revenue": "250.00",
                "total_quantity": 5,
                "order_count": 1,
            },
        )

        self.assertEqual(
            summary["rankings"][
                "lowest_products_by_net_revenue"
            ][0]["name"],
            "Keyboard",
        )

        self.assertEqual(
            summary["rankings"][
                "top_categories_by_net_revenue"
            ][0]["name"],
            "Furniture",
        )

        self.assertEqual(
            summary["monthly_trend"],
            [
                {
                    "month": "2026-01",
                    "net_revenue": "100.00",
                    "total_quantity": 2,
                    "order_count": 1,
                },
                {
                    "month": "2026-02",
                    "net_revenue": "350.00",
                    "total_quantity": 15,
                    "order_count": 2,
                },
            ],
        )

    def test_analytics_summary_compares_previous_period(
        self,
    ):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )

        comparison = summary["period_comparison"]

        self.assertEqual(
            comparison["previous_period"],
            {
                "start_date": "2026-01-04",
                "end_date": "2026-01-31",
            },
        )
        self.assertTrue(
            comparison["previous_has_data"]
        )
        self.assertEqual(
            comparison["previous_metrics"],
            {
                "order_count": 1,
                "total_quantity": 2,
                "net_revenue": "100.00",
            },
        )
        self.assertEqual(
            comparison["percentage_changes"],
            {
                "order_count": "100.00",
                "total_quantity": "650.00",
                "net_revenue": "250.00",
            },
        )

    def test_analytics_summary_includes_rule_based_insights(
        self,
    ):
        summary = build_analytics_summary(
            dataset=self.dataset,
            start_date=self.dataset.start_date,
            end_date=self.dataset.end_date,
        )

        self.assertEqual(
            summary["rule_based_insights"],
            [
                "Chair generated the highest net revenue "
                "at 250.00 EUR.",
                "Furniture was the strongest-performing "
                "category, generating 250.00 EUR in net "
                "revenue.",
                "Mouse sold the most units, with 10 items "
                "sold.",
                "February 2026 recorded the highest monthly "
                "net revenue at 350.00 EUR.",
            ],
        )

class DatasetAuthenticationTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(
            name="Protected Dataset",
            original_filename="protected.csv",
            currency="EUR",
            status=Dataset.Status.PROCESSING,
        )

    def test_anonymous_user_is_redirected_from_dataset_pages(self):
        protected_urls = [
            reverse("datasets:history"),
            reverse("datasets:upload"),
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            ),
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
            reverse(
                "datasets:analytics",
                args=[self.dataset.pk],
            ),
        ]

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                )

class DatasetRoleAccessTests(TestCase):
    def setUp(self):
        call_command(
            "setup_roles",
            stdout=StringIO(),
        )

        self.dataset = Dataset.objects.create(
            name="Role Access Dataset",
            original_filename="role-access.csv",
            currency="EUR",
            status=Dataset.Status.PROCESSING,
        )

        user_model = get_user_model()

        self.administrator = user_model.objects.create_user(
            username="administrator",
            password="TestPassword123!",
        )
        self.administrator.groups.add(
            Group.objects.get(name=ADMINISTRATORS)
        )

        self.sales_analyst = user_model.objects.create_user(
            username="sales.analyst",
            password="TestPassword123!",
        )
        self.sales_analyst.groups.add(
            Group.objects.get(name=SALES_ANALYSTS)
        )

        self.manager = user_model.objects.create_user(
            username="manager",
            password="TestPassword123!",
        )
        self.manager.groups.add(
            Group.objects.get(name=MANAGERS)
        )

    def test_all_roles_can_view_shared_dataset_pages(self):
        view_urls = [
            reverse("datasets:history"),
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            ),
            reverse(
                "datasets:analytics",
                args=[self.dataset.pk],
            ),
        ]

        for user in (
            self.administrator,
            self.sales_analyst,
            self.manager,
        ):
            self.client.force_login(user)

            for url in view_urls:
                with self.subTest(
                    username=user.username,
                    url=url,
                ):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)

    def test_administrator_and_analyst_can_access_upload(self):
        upload_url = reverse("datasets:upload")

        for user in (
            self.administrator,
            self.sales_analyst,
        ):
            self.client.force_login(user)

            with self.subTest(username=user.username):
                response = self.client.get(upload_url)
                self.assertEqual(response.status_code, 200)

    def test_manager_cannot_access_upload_or_delete(self):
        self.client.force_login(self.manager)

        forbidden_urls = [
            reverse("datasets:upload"),
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
        ]

        for url in forbidden_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_administrator_and_analyst_can_delete(self):
        delete_url = reverse(
            "datasets:delete",
            args=[self.dataset.pk],
        )

        expected_statuses = (
            (self.administrator, 200),
            (self.sales_analyst, 200),
            (self.manager, 403),
        )

        for user, expected_status in expected_statuses:
            self.client.force_login(user)

            with self.subTest(username=user.username):
                response = self.client.get(delete_url)
                self.assertEqual(
                    response.status_code,
                    expected_status,
                )

    def test_manager_interface_hides_upload_and_delete(self):
        self.client.force_login(self.manager)

        history_response = self.client.get(
            reverse("datasets:history")
        )
        detail_response = self.client.get(
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            )
        )

        self.assertNotContains(
            history_response,
            reverse("datasets:upload"),
        )
        self.assertNotContains(
            detail_response,
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
        )

    def test_analyst_interface_shows_upload_and_delete(self):
        self.client.force_login(self.sales_analyst)

        history_response = self.client.get(
            reverse("datasets:history")
        )
        detail_response = self.client.get(
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            )
        )

        self.assertContains(
            history_response,
            reverse("datasets:upload"),
        )
        self.assertContains(
            detail_response,
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
        )

    def test_administrator_interface_shows_upload_and_delete(self):
        self.client.force_login(self.administrator)

        history_response = self.client.get(
            reverse("datasets:history")
        )
        detail_response = self.client.get(
            reverse(
                "datasets:detail",
                args=[self.dataset.pk],
            )
        )

        self.assertContains(
            history_response,
            reverse("datasets:upload"),
        )
        self.assertContains(
            detail_response,
            reverse(
                "datasets:delete",
                args=[self.dataset.pk],
            ),
        )

    def test_permission_denied_page_is_clear(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("datasets:upload")
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Access denied",
            status_code=403,
        )

class DatasetViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dataset.employee",
            password="TestPassword123!",
        )
        self.client.force_login(self.user)
        permissions = Permission.objects.filter(
            content_type__app_label="datasets",
            codename__in=[
                "add_dataset",
                "delete_dataset",
                "view_dataset",
            ],
        )
        self.user.user_permissions.add(*permissions)
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

    @override_settings(
        GRAFANA_BASE_URL="http://grafana.test",
        GRAFANA_DASHBOARD_UID="test-dashboard-uid",
    )
    @patch("datasets.views.urlopen")
    def test_ready_dataset_analytics_embeds_dashboard(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 200

        response = self.client.get(
            reverse("datasets:analytics", args=[self.dataset.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datasets/analytics.html")
        self.assertTrue(response.context["grafana_available"])

        dashboard_url = response.context["dashboard_url"]

        self.assertIn(
            "http://grafana.test/d/test-dashboard-uid/"
            "vendilume-sales-overview?",
            dashboard_url,
        )
        self.assertIn(
            f"var-dataset_id={self.dataset.pk}",
            dashboard_url,
        )
        self.assertIn(
            "var-product=%24__all",
            dashboard_url,
        )
        self.assertIn(
            "var-category=%24__all",
            dashboard_url,
        )
        self.assertIn(
            "var-region=%24__all",
            dashboard_url,
        )
        self.assertIn(
            "var-sales_channel=%24__all",
            dashboard_url,
        )
        self.assertIn(
            "var-customer=%24__all",
            dashboard_url,
        )
        self.assertIn("from=", dashboard_url)
        self.assertIn("to=", dashboard_url)

        mock_urlopen.assert_called_once_with(
            "http://grafana.test/api/health",
            timeout=2,
        )


    @override_settings(
        GRAFANA_BASE_URL="http://grafana.test",
        GRAFANA_DASHBOARD_UID="test-dashboard-uid",
    )
    @patch("datasets.views.urlopen")
    def test_analytics_shows_message_when_grafana_is_unavailable(
        self,
        mock_urlopen,
    ):
        mock_urlopen.side_effect = URLError("Grafana unavailable")

        response = self.client.get(
            reverse("datasets:analytics", args=[self.dataset.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["grafana_available"])
        self.assertIsNone(response.context["dashboard_url"])
        self.assertContains(response, "Grafana is unavailable")


    @patch("datasets.views.urlopen")
    def test_non_ready_dataset_does_not_load_grafana(
        self,
        mock_urlopen,
    ):
        self.dataset.status = Dataset.Status.PROCESSING
        self.dataset.save(update_fields=["status"])

        response = self.client.get(
            reverse("datasets:analytics", args=[self.dataset.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["grafana_available"])
        self.assertIsNone(response.context["dashboard_url"])
        self.assertContains(
            response,
            "Analytics are only available after this dataset has finished",
        )
        mock_urlopen.assert_not_called()


    def test_unknown_dataset_analytics_returns_404(self):
        response = self.client.get(
            reverse("datasets:analytics", args=[999999])
        )

        self.assertEqual(response.status_code, 404)


    def test_ready_dataset_detail_links_to_analytics(self):
        response = self.client.get(
            reverse("datasets:detail", args=[self.dataset.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("datasets:analytics", args=[self.dataset.pk]),
        )
        self.assertContains(response, "View Analytics")

    @override_settings(
        GRAFANA_BASE_URL="http://grafana.test",
        GRAFANA_DASHBOARD_UID="test-dashboard-uid",
    )
    @patch("datasets.views.urlopen")
    def test_analytics_applies_filters_to_dashboard_and_insights(
        self,
        mock_urlopen,
    ):
        mock_urlopen.return_value.__enter__.return_value.status = 200

        order = SalesOrder.objects.create(
            dataset=self.dataset,
            source_order_id="FILTERED-ORDER",
            order_date=date(2026, 1, 10),
            customer_id="CUSTOMER-001",
            region="Berlin",
            sales_channel="Online",
        )

        SalesLine.objects.create(
            order=order,
            source_row_number=2,
            product_name="Keyboard",
            category="Electronics",
            quantity=2,
            unit_price=Decimal("50.00"),
            gross_revenue=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            net_revenue=Decimal("100.00"),
        )

        response = self.client.get(
            reverse(
                "datasets:analytics",
                args=[self.dataset.pk],
            ),
            data={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "product": "Keyboard",
                "category": "Electronics",
                "region": "Berlin",
                "sales_channel": "Online",
                "customer": "CUSTOMER-001",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.context["filter_form"].is_valid()
        )

        dashboard_url = response.context["dashboard_url"]

        self.assertIn(
            "var-product=Keyboard",
            dashboard_url,
        )
        self.assertIn(
            "var-category=Electronics",
            dashboard_url,
        )
        self.assertIn(
            "var-region=Berlin",
            dashboard_url,
        )
        self.assertIn(
            "var-sales_channel=Online",
            dashboard_url,
        )
        self.assertIn(
            "var-customer=CUSTOMER-001",
            dashboard_url,
        )

        self.assertContains(
            response,
            "Keyboard generated the highest net revenue at "
            "100.00 EUR.",
        )


    @patch("datasets.views.generate_business_insights")
    @patch("datasets.views.build_analytics_summary")
    @patch("datasets.views.urlopen")
    def test_analytics_does_not_generate_ai_automatically(
        self,
        mock_urlopen,
        mock_build_summary,
        mock_generate_business_insights,
    ):
        mock_urlopen.side_effect = URLError(
            "Grafana unavailable"
        )

        mock_build_summary.return_value = {
            "has_data": False,
            "rule_based_insights": [],
        }

        response = self.client.get(
            reverse(
                "datasets:analytics",
                args=[self.dataset.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            response.context["business_insight_result"]
        )
        mock_generate_business_insights.assert_not_called()

    @patch("datasets.views.generate_business_insights")
    @patch("datasets.views.build_analytics_summary")
    @patch("datasets.views.urlopen")
    def test_explicit_request_generates_ai_insights(
        self,
        mock_urlopen,
        mock_build_summary,
        mock_generate_business_insights,
    ):
        mock_urlopen.side_effect = URLError(
            "Grafana unavailable"
        )

        summary = {
            "has_data": True,
            "rule_based_insights": [
                "Verified Smart Insight.",
            ],
        }

        mock_build_summary.return_value = summary

        mock_generate_business_insights.return_value = {
            "source": "gemini",
            "notice": None,
            "rule_based_insights": [
                "Verified Smart Insight.",
            ],
            "ai_insights": {
                "executive_summary": (
                    "Revenue increased."
                ),
                "important_findings": [
                    "Furniture performed strongly.",
                ],
                "risks_and_warnings": [],
                "recommended_actions": [
                    "Review furniture inventory.",
                ],
                "areas_for_investigation": [],
            },
        }

        response = self.client.get(
            reverse(
                "datasets:analytics",
                args=[self.dataset.pk],
            ),
            data={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "generate_ai": "1",
            },
        )

        self.assertEqual(response.status_code, 200)

        mock_generate_business_insights.assert_called_once_with(
            summary
        )

        self.assertContains(
            response,
            "AI-enhanced insights",
        )
        self.assertContains(
            response,
            "Revenue increased.",
        )
        self.assertContains(
            response,
            "Review furniture inventory.",
        )


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

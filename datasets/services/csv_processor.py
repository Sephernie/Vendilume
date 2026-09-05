import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


REQUIRED_COLUMNS = (
    "order_id",
    "order_date",
    "product_name",
    "category",
    "quantity",
    "unit_price",
)

OPTIONAL_COLUMNS = (
    "product_id",
    "customer_id",
    "region",
    "sales_channel",
    "discount_percent",
    "unit_cost",
)

REQUIRED_TEXT_COLUMNS = (
    "order_id",
    "product_name",
    "category",
)

OPTIONAL_TEXT_COLUMNS = (
    "product_id",
    "customer_id",
    "region",
    "sales_channel",
)

ORDER_OPTIONAL_COLUMNS = (
    "customer_id",
    "region",
    "sales_channel",
)

SUPPORTED_COLUMNS = frozenset(
    REQUIRED_COLUMNS + OPTIONAL_COLUMNS
)

MAX_DATA_ROWS = 100_000

DATE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}$",
    flags=re.ASCII,
)

QUANTITY_PATTERN = re.compile(
    r"^\d+$",
    flags=re.ASCII,
)

DECIMAL_PATTERN = re.compile(
    r"^-?(?:\d+(?:\.\d*)?|\.\d+)$",
    flags=re.ASCII,
)

TWO_DECIMAL_PLACES = Decimal("0.01")

UNSUPPORTED_COLUMNS_WARNING = "UNSUPPORTED_COLUMNS"
DUPLICATE_ROWS_WARNING = "DUPLICATE_ROWS"
INCOMPLETE_OPTIONAL_DATA_WARNING = (
    "INCOMPLETE_OPTIONAL_DATA"
)


class CsvValidationError(Exception):
    def __init__(self, errors):
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))


@dataclass
class CsvProcessingWarning:
    code: str
    message: str
    affected_row_count: int | None
    details: dict


@dataclass
class CsvStructureResult:
    dataframe: pd.DataFrame
    source_columns: tuple[str, ...]
    unsupported_columns: tuple[str, ...]
    duplicate_row_numbers: tuple[int, ...]
    warnings: tuple[CsvProcessingWarning, ...]


def read_and_validate_csv(file_path):
    file_path = Path(file_path)

    try:
        header, data_row_count = _read_csv_shape(file_path)
    except UnicodeDecodeError as error:
        raise CsvValidationError(
            ["The CSV file must use UTF-8 encoding."]
        ) from error
    except csv.Error as error:
        raise CsvValidationError(
            ["The CSV file could not be parsed correctly."]
        ) from error

    if header is None or not any(
        column.strip() for column in header
    ):
        raise CsvValidationError(
            ["The CSV file must contain a header row."]
        )

    if len(header) == 1 and any(
        separator in header[0]
        for separator in (";", "\t", "|")
    ):
        raise CsvValidationError(
            ["The CSV file must use commas as separators."]
        )

    normalized_columns = [
        column.strip().lower()
        for column in header
    ]

    duplicate_columns = sorted(
        column
        for column, count in Counter(
            normalized_columns
        ).items()
        if count > 1
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in normalized_columns
    ]

    errors = []

    if duplicate_columns:
        errors.append(
            "Duplicate columns after normalization: "
            + ", ".join(duplicate_columns)
            + "."
        )

    if missing_columns:
        errors.append(
            "Missing required columns: "
            + ", ".join(missing_columns)
            + "."
        )

    if data_row_count == 0:
        errors.append(
            "The CSV file must contain at least one data row."
        )

    if data_row_count > MAX_DATA_ROWS:
        errors.append(
            "The CSV file must not contain more than "
            f"{MAX_DATA_ROWS:,} data rows."
        )

    if errors:
        raise CsvValidationError(errors)

    try:
        dataframe = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            skip_blank_lines=False,
        )
    except UnicodeDecodeError as error:
        raise CsvValidationError(
            ["The CSV file must use UTF-8 encoding."]
        ) from error
    except EmptyDataError as error:
        raise CsvValidationError(
            ["The CSV file does not contain readable data."]
        ) from error
    except ParserError as error:
        raise CsvValidationError(
            ["The CSV file could not be parsed correctly."]
        ) from error

    dataframe.columns = normalized_columns

    unsupported_columns = tuple(
        column
        for column in normalized_columns
        if column not in SUPPORTED_COLUMNS
    )

    supported_columns = [
        column
        for column in normalized_columns
        if column in SUPPORTED_COLUMNS
    ]

    dataframe = dataframe[supported_columns].copy()

    dataframe = _clean_and_validate_text_values(
        dataframe
    )
    dataframe = _validate_and_transform_dates(
        dataframe
    )
    dataframe = _validate_and_transform_required_numbers(
        dataframe
    )
    dataframe = _validate_and_transform_optional_numbers(
        dataframe
    )
    dataframe = _validate_cross_row_consistency(
        dataframe
    )
    duplicate_row_numbers = (
        _find_exact_duplicate_rows(dataframe)
    )
    warnings = _build_csv_warnings(
        dataframe=dataframe,
        unsupported_columns=unsupported_columns,
        duplicate_row_numbers=duplicate_row_numbers,
    )
    dataframe = _calculate_financial_values(
        dataframe
    )

    return CsvStructureResult(
        dataframe=dataframe,
        source_columns=tuple(supported_columns),
        unsupported_columns=unsupported_columns,
        duplicate_row_numbers=duplicate_row_numbers,
        warnings=warnings,
    )


def _calculate_financial_values(dataframe):
    dataframe = dataframe.copy()

    if "discount_percent" not in dataframe.columns:
        dataframe["discount_percent"] = pd.Series(
            [Decimal("0.00")] * len(dataframe),
            index=dataframe.index,
            dtype=object,
        )

    if "unit_cost" not in dataframe.columns:
        dataframe["unit_cost"] = pd.Series(
            [None] * len(dataframe),
            index=dataframe.index,
            dtype=object,
        )

    calculated_columns = (
        "gross_revenue",
        "discount_amount",
        "net_revenue",
        "total_cost",
        "profit",
    )

    for column in calculated_columns:
        dataframe[column] = pd.Series(
            [None] * len(dataframe),
            index=dataframe.index,
            dtype=object,
        )

    for index, row in dataframe.iterrows():
        quantity = row["quantity"]
        unit_price = row["unit_price"]
        discount_percent = row["discount_percent"]
        unit_cost = row["unit_cost"]

        gross_revenue = (
            unit_price * quantity
        ).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )

        discount_amount = (
            gross_revenue
            * discount_percent
            / Decimal("100")
        ).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )

        net_revenue = (
            gross_revenue - discount_amount
        ).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )

        dataframe.at[
            index,
            "gross_revenue",
        ] = gross_revenue

        dataframe.at[
            index,
            "discount_amount",
        ] = discount_amount

        dataframe.at[
            index,
            "net_revenue",
        ] = net_revenue

        if unit_cost is None:
            continue

        total_cost = (
            unit_cost * quantity
        ).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )

        profit = (
            net_revenue - total_cost
        ).quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )

        dataframe.at[
            index,
            "total_cost",
        ] = total_cost

        dataframe.at[
            index,
            "profit",
        ] = profit

    return dataframe


def _build_csv_warnings(
    dataframe,
    unsupported_columns,
    duplicate_row_numbers,
):
    warnings = []

    if unsupported_columns:
        warnings.append(
            CsvProcessingWarning(
                code=UNSUPPORTED_COLUMNS_WARNING,
                message=(
                    "Unsupported columns were ignored: "
                    + ", ".join(unsupported_columns)
                    + "."
                ),
                affected_row_count=None,
                details={
                    "columns": list(unsupported_columns),
                },
            )
        )

    if duplicate_row_numbers:
        duplicate_count = len(
            duplicate_row_numbers
        )

        message = (
            "1 exact duplicate row was retained."
            if duplicate_count == 1
            else (
                f"{duplicate_count} exact duplicate "
                "rows were retained."
            )
        )

        warnings.append(
            CsvProcessingWarning(
                code=DUPLICATE_ROWS_WARNING,
                message=message,
                affected_row_count=duplicate_count,
                details={
                    "source_rows": list(
                        duplicate_row_numbers
                    ),
                },
            )
        )

    missing_columns = [
        column
        for column in OPTIONAL_COLUMNS
        if column not in dataframe.columns
    ]

    empty_value_rows = {}

    for column in OPTIONAL_TEXT_COLUMNS:
        if column not in dataframe.columns:
            continue

        rows = [
            index + 2
            for index in dataframe.index[
                dataframe[column] == ""
            ]
        ]

        if rows:
            empty_value_rows[column] = rows

    if "unit_cost" in dataframe.columns:
        rows = [
            index + 2
            for index in dataframe.index[
                dataframe["unit_cost"].isna()
            ]
        ]

        if rows:
            empty_value_rows["unit_cost"] = rows

    if missing_columns or empty_value_rows:
        if missing_columns:
            affected_rows = set(
                range(2, len(dataframe) + 2)
            )
        else:
            affected_rows = set()

        for rows in empty_value_rows.values():
            affected_rows.update(rows)

        warnings.append(
            CsvProcessingWarning(
                code=INCOMPLETE_OPTIONAL_DATA_WARNING,
                message=(
                    "Optional data is missing or incomplete, "
                    "so some analytics will be unavailable."
                ),
                affected_row_count=len(affected_rows),
                details={
                    "missing_columns": missing_columns,
                    "empty_value_rows": empty_value_rows,
                },
            )
        )

    return tuple(warnings)


def _find_exact_duplicate_rows(dataframe):
    duplicate_mask = dataframe.duplicated(
        keep="first"
    )

    return tuple(
        index + 2
        for index in dataframe.index[duplicate_mask]
    )


def _validate_cross_row_consistency(dataframe):
    errors = []
    known_orders = {}
    known_products = {}

    for index, row in dataframe.iterrows():
        row_number = index + 2

        order_id = row["order_id"]
        order_key = order_id.casefold()

        if order_key not in known_orders:
            known_orders[order_key] = {
                "order_id": order_id,
                "row_number": row_number,
                "order_date": row["order_date"],
                "optional_values": {},
            }

        known_order = known_orders[order_key]

        if row["order_date"] != known_order["order_date"]:
            errors.append(
                f'Row {row_number}, column "order_date", '
                f'value "{row["order_date"]}": Must match '
                f'value "{known_order["order_date"]}" used '
                f'for order_id "{known_order["order_id"]}" '
                f'on row {known_order["row_number"]}.'
            )

        for column in ORDER_OPTIONAL_COLUMNS:
            if column not in dataframe.columns:
                continue

            value = row[column]

            if value == "":
                continue

            normalized_value = value.casefold()

            known_value = known_order[
                "optional_values"
            ].get(column)

            if known_value is None:
                known_order["optional_values"][column] = {
                    "value": value,
                    "normalized_value": normalized_value,
                    "row_number": row_number,
                }
                continue

            if (
                normalized_value
                != known_value["normalized_value"]
            ):
                errors.append(
                    f'Row {row_number}, column "{column}", '
                    f'value "{value}": Must match value '
                    f'"{known_value["value"]}" used for '
                    f'order_id "{known_order["order_id"]}" '
                    f'on row {known_value["row_number"]}.'
                )

        if "product_id" not in dataframe.columns:
            continue

        product_id = row["product_id"]

        if product_id == "":
            continue

        product_key = product_id.casefold()

        if product_key not in known_products:
            known_products[product_key] = {
                "product_id": product_id,
                "row_number": row_number,
                "product_name": row["product_name"],
                "category": row["category"],
            }
            continue

        known_product = known_products[product_key]

        for column in ("product_name", "category"):
            value = row[column]
            known_value = known_product[column]

            if value.casefold() != known_value.casefold():
                errors.append(
                    f'Row {row_number}, column "{column}", '
                    f'value "{value}": Must match value '
                    f'"{known_value}" used for product_id '
                    f'"{known_product["product_id"]}" on row '
                    f'{known_product["row_number"]}.'
                )

    if errors:
        raise CsvValidationError(errors)

    return dataframe


def _validate_and_transform_optional_numbers(dataframe):
    dataframe = dataframe.copy()
    errors = []

    if "discount_percent" in dataframe.columns:
        dataframe["discount_percent"] = (
            dataframe["discount_percent"].astype(object)
        )

        for index, original_value in (
            dataframe["discount_percent"].items()
        ):
            value = original_value.strip()
            row_number = index + 2

            if value == "":
                dataframe.at[
                    index,
                    "discount_percent",
                ] = Decimal("0.00")
                continue

            if DECIMAL_PATTERN.fullmatch(value) is None:
                errors.append(
                    f'Row {row_number}, column '
                    f'"discount_percent", value "{value}": '
                    "Discount percent must be a plain "
                    "number without symbols or separators."
                )
                continue

            try:
                discount_percent = Decimal(value)
            except InvalidOperation:
                errors.append(
                    f'Row {row_number}, column '
                    f'"discount_percent", value "{value}": '
                    "Discount percent could not be processed."
                )
                continue

            if not Decimal("0") <= discount_percent <= Decimal("100"):
                errors.append(
                    f'Row {row_number}, column '
                    f'"discount_percent", value "{value}": '
                    "Discount percent must be from 0 "
                    "through 100."
                )
                continue

            try:
                discount_percent = discount_percent.quantize(
                    TWO_DECIMAL_PLACES,
                    rounding=ROUND_HALF_UP,
                )
            except InvalidOperation:
                errors.append(
                    f'Row {row_number}, column '
                    f'"discount_percent", value "{value}": '
                    "Discount percent is too precise "
                    "to process."
                )
                continue

            dataframe.at[
                index,
                "discount_percent",
            ] = discount_percent

    if "unit_cost" in dataframe.columns:
        dataframe["unit_cost"] = (
            dataframe["unit_cost"].astype(object)
        )

        for index, original_value in (
            dataframe["unit_cost"].items()
        ):
            value = original_value.strip()
            row_number = index + 2

            if value == "":
                dataframe.at[index, "unit_cost"] = None
                continue

            if DECIMAL_PATTERN.fullmatch(value) is None:
                errors.append(
                    f'Row {row_number}, column "unit_cost", '
                    f'value "{value}": Unit cost must be a '
                    "plain number without symbols or "
                    "separators."
                )
                continue

            try:
                unit_cost = Decimal(value)
            except InvalidOperation:
                errors.append(
                    f'Row {row_number}, column "unit_cost", '
                    f'value "{value}": Unit cost could not '
                    "be processed."
                )
                continue

            if unit_cost < 0:
                errors.append(
                    f'Row {row_number}, column "unit_cost", '
                    f'value "{value}": Unit cost cannot '
                    "be negative."
                )
                continue

            try:
                unit_cost = unit_cost.quantize(
                    TWO_DECIMAL_PLACES,
                    rounding=ROUND_HALF_UP,
                )
            except InvalidOperation:
                errors.append(
                    f'Row {row_number}, column "unit_cost", '
                    f'value "{value}": Unit cost is too '
                    "large or precise to process."
                )
                continue

            dataframe.at[index, "unit_cost"] = unit_cost

    if errors:
        raise CsvValidationError(errors)

    return dataframe


def _validate_and_transform_required_numbers(dataframe):
    dataframe = dataframe.copy()

    dataframe["quantity"] = (
        dataframe["quantity"].astype(object)
    )
    dataframe["unit_price"] = (
        dataframe["unit_price"].astype(object)
    )

    errors = []

    for index, row in dataframe.iterrows():
        row_number = index + 2

        quantity_text = row["quantity"].strip()

        if quantity_text == "":
            errors.append(
                f'Row {row_number}, column "quantity", '
                'value "": A value is required.'
            )
        elif QUANTITY_PATTERN.fullmatch(
            quantity_text
        ) is None:
            errors.append(
                f'Row {row_number}, column "quantity", '
                f'value "{quantity_text}": Quantity must '
                "be a whole number."
            )
        else:
            quantity = int(quantity_text)

            if quantity <= 0:
                errors.append(
                    f'Row {row_number}, column "quantity", '
                    f'value "{quantity_text}": Quantity must '
                    "be greater than zero."
                )
            else:
                dataframe.at[index, "quantity"] = quantity

        unit_price_text = row["unit_price"].strip()

        if unit_price_text == "":
            errors.append(
                f'Row {row_number}, column "unit_price", '
                'value "": A value is required.'
            )
        elif DECIMAL_PATTERN.fullmatch(
            unit_price_text
        ) is None:
            errors.append(
                f'Row {row_number}, column "unit_price", '
                f'value "{unit_price_text}": Unit price must '
                "be a plain number without symbols or "
                "separators."
            )
        else:
            try:
                unit_price = Decimal(
                    unit_price_text
                ).quantize(
                    TWO_DECIMAL_PLACES,
                    rounding=ROUND_HALF_UP,
                )
            except InvalidOperation:
                errors.append(
                    f'Row {row_number}, column "unit_price", '
                    f'value "{unit_price_text}": Unit price '
                    "is too large or precise to process."
                )
                continue

            if unit_price < 0:
                errors.append(
                    f'Row {row_number}, column "unit_price", '
                    f'value "{unit_price_text}": Unit price '
                    "cannot be negative."
                )
            else:
                dataframe.at[
                    index,
                    "unit_price",
                ] = unit_price

    if errors:
        raise CsvValidationError(errors)

    return dataframe


def _validate_and_transform_dates(dataframe):
    dataframe = dataframe.copy()

    dataframe["order_date"] = (
        dataframe["order_date"].astype(object)
    )

    errors = []

    for index, original_value in (
        dataframe["order_date"].items()
    ):
        value = original_value.strip()
        row_number = index + 2

        if value == "":
            errors.append(
                f'Row {row_number}, column "order_date", '
                'value "": A value is required.'
            )
            continue

        if DATE_PATTERN.fullmatch(value) is None:
            errors.append(
                f'Row {row_number}, column "order_date", '
                f'value "{value}": Expected the '
                "YYYY-MM-DD format."
            )
            continue

        try:
            parsed_date = date.fromisoformat(value)
        except ValueError:
            errors.append(
                f'Row {row_number}, column "order_date", '
                f'value "{value}": This is not a valid '
                "calendar date."
            )
            continue

        if parsed_date > timezone.localdate():
            errors.append(
                f'Row {row_number}, column "order_date", '
                f'value "{value}": Order date cannot '
                "be in the future."
            )
            continue

        dataframe.at[index, "order_date"] = parsed_date

    if errors:
        raise CsvValidationError(errors)

    return dataframe


def _clean_and_validate_text_values(dataframe):
    dataframe = dataframe.copy()
    errors = []

    for column in REQUIRED_TEXT_COLUMNS:
        dataframe[column] = dataframe[column].str.strip()

        empty_rows = dataframe.index[
            dataframe[column] == ""
        ]

        for index in empty_rows:
            row_number = index + 2

            errors.append(
                f'Row {row_number}, column "{column}", '
                'value "": A value is required.'
            )

    for column in OPTIONAL_TEXT_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = (
                dataframe[column].str.strip()
            )

    if errors:
        raise CsvValidationError(errors)

    return dataframe


def _read_csv_shape(file_path):
    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.reader(
            csv_file,
            delimiter=",",
            strict=True,
        )

        header = next(reader, None)
        data_row_count = sum(1 for _ in reader)

    return header, data_row_count

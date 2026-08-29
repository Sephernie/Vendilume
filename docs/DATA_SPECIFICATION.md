# Vendilume Data Specification

## 1. Purpose

This document defines the sales-data structure supported by Vendilume. It specifies the expected CSV format, required and optional fields, calculated values, validation rules, error-handling behavior, and MVP data limitations.

The specification acts as the data contract between uploaded CSV files, Pandas processing, PostgreSQL storage, and Grafana analytics.

---

## 2. Record Structure

Each CSV row represents one product line within a completed sales order.

An order may contain multiple product lines. Rows belonging to the same order are connected through the shared `order_id` value.

Example:

| order_id | order_date | product_name | category | quantity | unit_price |
| --- | --- | --- | --- | ---: | ---: |
| ORD-1001 | 2026-08-28 | Wireless Mouse | Electronics | 2 | 24.99 |
| ORD-1001 | 2026-08-28 | Keyboard | Electronics | 1 | 49.99 |

This structure supports order-level, product-level, category-level, and time-based analytics.

---

## 3. Required Columns

Every uploaded dataset must contain the following columns.

| Column | Data type | Example | Description |
| --- | --- | --- | --- |
| `order_id` | Text | `ORD-1001` | Identifier that groups product lines belonging to the same order |
| `order_date` | Date | `2026-08-28` | Date on which the order was completed |
| `product_name` | Text | `Wireless Mouse` | Name of the sold product |
| `category` | Text | `Electronics` | Product category used for grouped analysis |
| `quantity` | Positive whole number | `2` | Number of units sold on the order line |
| `unit_price` | Non-negative decimal | `24.99` | Selling price of one unit before discount |

These columns provide the minimum data required to calculate the core MVP metrics, including revenue, units sold, number of orders, average order value, product performance, category performance, and sales trends.

---

## 4. Optional Columns

The following columns are supported but are not required for a successful import.

| Column | Data type | Example | Analytics enabled |
| --- | --- | --- | --- |
| `product_id` | Text | `PRD-204` | Reliable product identification across rows |
| `customer_id` | Text | `CUS-109` | Unique-customer and customer-level statistics |
| `region` | Text | `Berlin` | Geographic comparisons and filtering |
| `sales_channel` | Text | `Online` | Channel comparisons such as online, retail, or wholesale |
| `discount_percent` | Decimal from 0 to 100 | `10` | Discount and net-revenue analysis |
| `unit_cost` | Non-negative decimal | `15.50` | Cost and profit analysis |

Missing optional columns or values do not block an import. Analytics that depend on unavailable optional data will not be shown.

When `discount_percent` is absent or empty, Vendilume treats the discount as zero. Profit-related calculations are available only for rows that provide `unit_cost`.

---

## 5. Example CSV

```csv
order_id,order_date,product_name,category,quantity,unit_price,product_id,customer_id,region,sales_channel,discount_percent,unit_cost
ORD-1001,2026-08-28,Wireless Mouse,Electronics,2,24.99,PRD-204,CUS-109,Berlin,Online,10,15.50
ORD-1001,2026-08-28,Keyboard,Electronics,1,49.99,PRD-205,CUS-109,Berlin,Online,0,31.00
ORD-1002,2026-08-29,Office Chair,Furniture,1,180.00,PRD-310,CUS-117,Hamburg,Retail,5,120.00
```

---

## 6. Dataset Metadata

Each dataset represents sales in one currency. The user selects the dataset currency as part of the upload process rather than repeating it in every CSV row.

Vendilume must not combine monetary results from datasets that use different currencies. Monetary fields in the CSV contain plain numeric values without currency symbols.

The application will also record system-managed dataset information, such as the uploaded filename and upload time. This metadata is not supplied as CSV columns.

---

## 7. Calculated Fields

Users do not include calculated fields in the uploaded CSV. Vendilume derives them during processing.

### 7.1 Gross Revenue

```text
gross_revenue = quantity × unit_price
```

### 7.2 Discount Amount

```text
discount_amount = gross_revenue × (discount_percent ÷ 100)
```

If `discount_percent` is absent or empty, it is treated as `0`.

### 7.3 Net Revenue

```text
net_revenue = gross_revenue − discount_amount
```

### 7.4 Total Cost

```text
total_cost = quantity × unit_cost
```

### 7.5 Profit

```text
profit = net_revenue − total_cost
```

`total_cost` and `profit` are calculated only when `unit_cost` is available.

---

## 8. File-Level Validation

| Rule | Result when violated |
| --- | --- |
| The uploaded file must use the `.csv` extension. | Reject the upload |
| The file must be readable as UTF-8. | Reject the upload |
| The file must use commas as field separators. | Reject the upload |
| The file must contain one header row. | Reject the upload |
| The file must contain at least one data row. | Reject the upload |
| The file must not exceed 10 MB. | Reject the upload |
| The file must not exceed 100,000 data rows. | Reject the upload |
| Every required column must be present. | Reject the upload |
| Column names must not be duplicated after normalization. | Reject the upload |
| Unsupported columns may be present. | Ignore those columns and display a warning |

---

## 9. Column-Name Validation

Vendilume performs the following safe normalization before validating column names:

1. Remove whitespace from the beginning and end of each column name.
2. Convert each column name to lowercase.
3. Check that the resulting name uses `snake_case`.

Examples:

| Uploaded name | Result |
| --- | --- |
| `ORDER_ID` | Normalized to `order_id` |
| ` order_date ` | Normalized to `order_date` |
| `Product Name` | Rejected because the expected name is `product_name` |

Vendilume will not guess the meaning of incorrectly named columns. If normalization produces two columns with the same name, the upload is rejected.

---

## 10. Required-Value Validation

The following fields must contain a value on every row:

- `order_id`
- `order_date`
- `product_name`
- `category`
- `quantity`
- `unit_price`

Optional values may be empty. However, when an optional value is provided, it must satisfy that column's validation rules.

For example, an empty `unit_cost` is permitted, but a `unit_cost` of `-20` is invalid.

---

## 11. Text Validation

| Column | Rule |
| --- | --- |
| `order_id` | Must contain non-empty text |
| `product_name` | Must contain non-empty text |
| `category` | Must contain non-empty text |
| `product_id` | May be empty; otherwise must contain text |
| `customer_id` | May be empty; otherwise must contain text |
| `region` | May be empty; otherwise must contain text |
| `sales_channel` | May be empty; otherwise must contain text |

Vendilume removes whitespace from the beginning and end of text values. It preserves the original capitalization for display while using case-insensitive comparisons for grouping and filtering.

---

## 12. Date Validation

Every `order_date` value must:

- Use the ISO `YYYY-MM-DD` format.
- Represent a real calendar date.
- Contain a date only, without a time value.
- Not represent a future date at the time of upload.

Examples:

| Value | Valid | Reason |
| --- | --- | --- |
| `2026-08-28` | Yes | Uses the required format and represents a real date |
| `28/08/2026` | No | Uses an unsupported format |
| `08-28-2026` | No | Uses an unsupported format |
| `2026-02-30` | No | Does not represent a real date |
| `2026-08-28 14:30` | No | Contains a time value |

---

## 13. Numerical Validation

| Column | Rule |
| --- | --- |
| `quantity` | Must be a whole number greater than zero |
| `unit_price` | Must be a number equal to or greater than zero |
| `discount_percent` | When provided, must be a number from 0 through 100 |
| `unit_cost` | When provided, must be a number equal to or greater than zero |

Numeric values must not contain currency symbols, percentage symbols, thousands separators, or text.

Examples:

| Value and context | Valid | Reason |
| --- | --- | --- |
| `3` as `quantity` | Yes | Positive whole number |
| `3.5` as `quantity` | No | Quantity must be a whole number |
| `24.99` as `unit_price` | Yes | Valid non-negative decimal |
| `€24.99` as `unit_price` | No | Contains a currency symbol |
| `1,250.00` as `unit_price` | No | Contains a thousands separator |
| `-10` as `unit_price` | No | Monetary values cannot be negative |
| `105` as `discount_percent` | No | Discount exceeds 100 percent |

---

## 14. Cross-Row Consistency

Rows sharing the same `order_id` must contain the same values for:

- `order_date`
- `customer_id`, when provided
- `region`, when provided
- `sales_channel`, when provided

For example, `ORD-1001` cannot use `2026-08-20` on one row and `2026-08-21` on another.

When `product_id` is provided, the same identifier must consistently refer to the same `product_name` and `category` within the dataset.

Violations of these consistency rules are validation errors and block the import.

---

## 15. Duplicate Rows

An exact duplicate exists when every supported value in two or more rows is identical.

Vendilume will:

- Report exact duplicates as warnings.
- Retain the rows instead of silently removing them.
- Include the rows in calculations if the dataset is imported.

Identical rows could represent legitimate separate sales lines. The warning allows the user to review the source data without Vendilume making an unsafe assumption.

---

## 16. Errors and Warnings

### 16.1 Errors

Errors prevent the entire dataset from being imported. They include:

- An unreadable, empty, oversized, or unsupported file.
- Missing required columns.
- Duplicate column names.
- Missing required values.
- Invalid dates or data types.
- Values outside their permitted ranges.
- Inconsistent order information.
- Inconsistent product identifiers.
- Exceeding the supported row limit.

### 16.2 Warnings

Warnings do not prevent an import. They include:

- Unsupported extra columns that Vendilume will ignore.
- Exact duplicate rows that Vendilume will retain.
- Missing or partially empty optional data that limits available analytics.

---

## 17. Validation and Import Workflow

Vendilume uses an all-or-nothing import process.

```text
Upload CSV
    ↓
Validate the complete file
    ↓
Were errors found?
    ├── Yes → Reject the complete import and show an error report
    └── No  → Process and store the complete dataset
```

Vendilume will not partially import only the valid rows. This prevents users from unknowingly viewing analytics based on an incomplete dataset.

If validation fails, no records from the uploaded file are written to the permanent sales tables.

---

## 18. Validation Feedback

The validation result must clearly state whether the dataset was accepted or rejected.

For each error, the report should identify:

- CSV row number
- Column name
- Problematic value
- Explanation of the problem

Example:

| Row | Column | Value | Problem |
| ---: | --- | --- | --- |
| 14 | `quantity` | `2.5` | Quantity must be a whole number |
| 27 | `order_date` | `28/08/2026` | Expected the `YYYY-MM-DD` format |
| 43 | `unit_price` | `-12` | Unit price cannot be negative |

Warnings should be presented separately from errors so the user can distinguish blocking problems from informational concerns.

---

## 19. MVP Limitations

The initial Vendilume data model does not support:

- Returns or refunds
- Cancelled orders
- Tax calculations
- Multiple currencies within one dataset
- Currency conversion
- Real-time sales integrations
- Inventory or stock movement records
- Payment-processing information

These capabilities may be considered after the core import and analytics workflow is complete.

---

## 20. Completion Criteria

The data specification is considered implemented when Vendilume can:

1. Accept CSV files that follow the defined structure.
2. Identify every missing required column.
3. Validate required and optional values using the defined rules.
4. Reject invalid datasets without partially storing their sales records.
5. Provide clear row-level error feedback.
6. Process and store valid datasets.
7. Calculate the defined revenue, cost, and profit fields when the required source values are available.
8. Preserve enough structured data for the planned PostgreSQL and Grafana components.
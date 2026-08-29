# Vendilume — Software Requirements

## 1. Purpose

This document defines the functional and non-functional requirements of Vendilume.

Requirements describe the expected behavior and quality of the application and will later provide a basis for implementation and testing.

---

## 2. Functional Requirements

### FR-01 — Dataset Upload

The system must allow users to upload sales datasets in CSV format through the web application.

### FR-02 — Dataset Validation

The system must validate uploaded datasets before importing them.

Validation should include:

* File format
* Empty files
* Required columns
* Invalid data types
* Missing or unusable values

Validation failures should produce understandable error messages.

Non-blocking issues should be reported as warnings and must not prevent an otherwise valid dataset from being imported.

If one or more blocking errors are found, the complete import must be rejected. The system must not partially store only the valid rows.

### FR-03 — Data Processing

Valid datasets must be cleaned and transformed into a consistent structure suitable for storage and analysis.

Processing may include data-type conversion, standardization, handling invalid values, and calculation of necessary derived values.

### FR-04 — Persistent Data Storage

Successfully processed sales records must be stored persistently in the application's database.

Records must remain associated with the dataset from which they originated.

Dataset metadata, orders, sales lines, calculated values, and retained warnings must be stored within one atomic database transaction. If persistence fails, the complete transaction must be rolled back.

### FR-05 — Dataset Management

The system should maintain information about imported datasets.

Users should be able to view information such as:

* Dataset name
* Original filename
* Dataset currency
* Upload date
* Number of records
* Number of orders
* Sales date range
* Available optional data
* Retained validation warnings
* Processing status

Users should be able to open dataset details and permanently delete a dataset together with its related sales records after confirming the action.

### FR-06 — Sales KPIs

The system must provide important sales performance indicators.

Planned KPIs include:

* Gross Revenue
* Net Revenue
* Total Orders
* Total Items Sold
* Average Order Value
* Best-Selling Product
* Top-Performing Category

Available KPIs may depend on the information contained in the uploaded dataset.

Cost, profit, and profit-margin analytics should be available only when complete unit-cost data exists for the relevant sales records. Region, sales-channel, customer, and discount analytics should appear only when their supporting optional data is available.

### FR-07 — Sales Visualizations

The system must provide visual representations of sales performance.

Planned visualizations include:

* Revenue Over Time
* Sales by Category
* Top Products

### FR-08 — Analytics Filtering

Users should be able to filter analytics using relevant dimensions such as:

* Dataset
* Date range
* Product
* Category

When supported by the selected dataset, additional filters may include:

* Region
* Sales channel
* Customer

Displayed analytics should update according to the selected filters.

The selected filter state must be applied consistently to dashboard KPIs, visualizations, and smart insights.

### FR-09 — Analytics Access

Users must be able to reach the sales analytics dashboard through the Vendilume application workflow.

### FR-10 — Smart Insights

The system should generate simple written observations based on calculated sales results.

For example:

```text
Electronics generated the highest revenue.

July recorded the highest monthly sales.

Product A was the best-selling product.
```

The core implementation should use deterministic, rule-based analysis.

### FR-11 — Error Handling

The system must handle common upload, validation, processing, and application errors without causing the application to become unusable.

Errors should be communicated using understandable messages.

---

## 3. Non-Functional Requirements

### NFR-01 — Usability

The standard application workflow should be understandable without requiring programming, database, or data-analysis knowledge.

### NFR-02 — Reliability

Valid datasets following the supported structure should produce consistent results.

### NFR-03 — Data Accuracy

Calculated KPIs, visualizations, and generated insights must accurately represent the processed sales data.

### NFR-04 — Performance

Datasets of the size expected for the project should be processed within a reasonable amount of time on the development environment.

Enterprise-scale performance is not required.

### NFR-05 — Maintainability

The source code should maintain clear separation between application functionality, data processing, storage, and analytics responsibilities.

### NFR-06 — Compatibility

Vendilume should be accessible through modern desktop web browsers.

### NFR-07 — Testability

Important application and data-processing logic should be structured so that its behavior can be tested.

---

## 4. Data Requirements

The input dataset must contain enough information to perform meaningful sales analysis.

A supported CSV row represents one product line within a completed sales order.

Every dataset must contain these required columns:

```text
order_id
order_date
product_name
category
quantity
unit_price
```

Vendilume also supports these optional columns:

```text
product_id
customer_id
region
sales_channel
discount_percent
unit_cost
```

The dataset currency is selected as upload metadata rather than repeated in every CSV row.

The complete field definitions, calculated values, validation rules, file limits, and error-handling behavior are defined in [`DATA_SPECIFICATION.md`](DATA_SPECIFICATION.md).

At minimum, the available information must make it possible to determine:

* What was sold
* When it was sold
* How much was sold
* The monetary value required for revenue calculations

---

## 5. Requirement Priorities

### Must Have

* Dataset upload
* Dataset validation
* Data processing
* Persistent storage
* Core sales KPIs
* Analytics dashboard
* Essential visualizations
* User-friendly validation error and warning reporting

### Should Have

* Dataset history, details, and confirmed deletion
* Dashboard filters
* Smart insights
* Automated testing of important logic
* Integrated dashboard experience

### Could Have

* Report export
* Additional analytics
* User accounts
* LLM-enhanced insights
* Sales forecasting
* Public deployment

---

## 6. Acceptance Criteria

The core Vendilume system will be considered functionally successful when:

1. A valid sales CSV following the supported structure can be uploaded.
2. A dataset containing blocking validation errors is rejected completely with understandable row-level feedback.
3. Non-blocking validation warnings are displayed without preventing an otherwise valid import.
4. Valid records, calculated values, dataset metadata, and retained warnings are stored within one atomic transaction.
5. A failed persistence operation leaves no partial dataset in permanent storage.
6. Users can view dataset history and the details of an imported dataset.
7. Users can delete a dataset and its related records only after confirming the action.
8. Stored data can be analyzed through the dashboard.
9. The dashboard displays accurate gross revenue, net revenue, order, item, product, category, and time-based analytics.
10. Analytics that depend on optional data appear only when the required source data is available and sufficiently complete.
11. The selected filters are applied consistently to KPIs, visualizations, and smart insights.
12. Common upload, processing, database, dashboard, and insight errors result in understandable feedback without making the application unusable.

These criteria define the expected behavior of the core application and will later be used as a basis for testing.

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

### FR-03 — Data Processing

Valid datasets must be cleaned and transformed into a consistent structure suitable for storage and analysis.

Processing may include data-type conversion, standardization, handling invalid values, and calculation of necessary derived values.

### FR-04 — Persistent Data Storage

Successfully processed sales records must be stored persistently in the application's database.

Records must remain associated with the dataset from which they originated.

### FR-05 — Dataset Management

The system should maintain information about imported datasets.

Users should be able to view information such as:

* Dataset name
* Upload date
* Number of records
* Processing status

### FR-06 — Sales KPIs

The system must provide important sales performance indicators.

Planned KPIs include:

* Total Revenue
* Total Orders
* Total Items Sold
* Average Order Value
* Best-Selling Product
* Top-Performing Category

Available KPIs may depend on the information contained in the uploaded dataset.

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

Displayed analytics should update according to the selected filters.

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

A typical sales record is expected to contain information equivalent to:

```text
Order ID
Date
Product
Category
Quantity
Unit Price
```

The final required schema will be established once the development dataset has been selected.

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
* User-friendly error handling

### Should Have

* Dataset history
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

1. A valid sales CSV can be uploaded.
2. Invalid datasets are appropriately rejected.
3. Valid records are processed successfully.
4. Processed records are stored persistently.
5. Stored data can be analyzed through the dashboard.
6. The dashboard displays accurate KPIs and visualizations.
7. Relevant analytics can be filtered.
8. Common errors result in understandable feedback.

These criteria define the expected behavior of the core application and will later be used as a basis for testing.
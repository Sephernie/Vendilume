# Vendilume — Project Overview

## 1. Introduction

**Vendilume** is a web-based sales analytics and business intelligence application designed to transform raw sales data into clear, structured, and understandable business information.

Businesses regularly collect sales records containing information such as transaction dates, products, categories, quantities, and prices. Although this data can provide valuable information about business performance, raw datasets are often difficult to interpret without additional processing, analysis, and visualization.

Vendilume aims to simplify this process by providing a centralized application where users can import sales datasets and explore their performance through an interactive analytics dashboard.

---

## 2. Problem Statement

Sales data can answer important business questions such as:

* How much revenue has been generated?
* How are sales changing over time?
* Which products sell the most units?
* Which products generate the most revenue?
* Which categories perform best?
* When are sales at their highest or lowest?

Obtaining these answers directly from raw sales files often requires several manual steps.

A user may need to clean the data, perform calculations, group and compare records, and create visualizations before useful conclusions can be drawn. These steps may also need to be repeated whenever new data becomes available.

This creates a gap between **collecting sales data** and **being able to understand and use that data effectively**.

Vendilume aims to reduce this gap by providing a structured workflow that converts uploaded sales data into accessible business analytics.

---

## 3. Proposed Solution

Vendilume will provide a web application through which users can upload sales datasets in CSV format.

The application will validate and process the uploaded data before storing the resulting structured sales information. The stored information can then be analyzed and presented through an interactive business intelligence dashboard.

From the user's perspective, the process should remain simple:

```text
Upload Sales Data
        ↓
Process Data
        ↓
View Analytics
        ↓
Understand Performance
```

The technical complexity behind processing, storing, querying, and visualizing the data is handled by Vendilume.

The objective is not to create a large enterprise business intelligence platform. Instead, Vendilume will provide a focused and complete system demonstrating the journey from raw sales data to useful business information.

---

## 4. Project Objectives

The primary objective of Vendilume is to develop a functional sales analytics system capable of transforming uploaded sales data into useful and understandable information.

The project aims to:

1. Provide a straightforward method for importing sales datasets.
2. Validate uploaded data before accepting it for analysis.
3. Clean and transform raw sales data into a consistent structure.
4. Store processed sales information for persistent use.
5. Provide meaningful sales performance indicators.
6. Present sales trends and comparisons through interactive visualizations.
7. Allow users to explore different portions of their sales data.
8. Identify and communicate notable sales patterns.
9. Provide a coherent workflow between data import, processing, storage, and analytics.
10. Apply software engineering principles throughout the design, implementation, testing, and documentation of the system.

---

## 5. Target Users

Vendilume is intended for users who have access to sales data but want a straightforward way to understand its performance.

Potential users include:

* Small business owners
* Store managers
* Sales managers
* Business analysts
* Data analysts
* Students learning business or data analytics

Users should not need programming, database, or business intelligence knowledge to perform the standard Vendilume workflow.

The intended experience can be summarized as:

> **Provide the data and receive understandable analytics.**

---

## 6. Core Application Concept

Vendilume is built around four main stages:

### Import

The user provides a sales dataset through the application.

### Process

The uploaded data is validated, cleaned, transformed, and prepared for analysis.

### Store

Processed sales information is stored persistently so that it can be queried and analyzed reliably.

### Analyze

Stored information is transformed into KPIs, visualizations, filters, and useful observations about sales performance.

Together, these stages form Vendilume's central concept:

```text
IMPORT → PROCESS → STORE → ANALYZE
```

---

## 7. Main Features

The planned application includes the following major features:

* CSV sales dataset import
* Dataset validation and processing
* Persistent sales-data storage
* Dataset history and management
* Sales KPIs
* Interactive analytics dashboard
* Product, category, date, and dataset filtering
* Sales trends and comparisons
* Automatically generated sales insights
* User-friendly error handling

The exact behavior and priority of these features are defined in [`REQUIREMENTS.md`](REQUIREMENTS.md).

---

## 8. Project Scope

Vendilume focuses specifically on the workflow between **sales-data import and sales-performance analysis**.

The project covers importing, processing, storing, managing, analyzing, and visualizing structured sales data.

It is intentionally not intended to become a complete ERP, e-commerce platform, or enterprise data warehouse.

Features such as real-time point-of-sale integrations, payment processing, advanced predictive analytics, large-scale cloud infrastructure, and a full conversational AI assistant are outside the initial project scope.

---

## 9. Expected Outcome

At the end of development, Vendilume should demonstrate a complete workflow for transforming raw sales records into accessible business intelligence.

Instead of manually inspecting and analyzing a sales CSV file, a user should be able to provide their data to Vendilume and explore the resulting analytics.

The completed project should also demonstrate practical experience with:

* Software requirements and design
* Web application development
* Data processing
* Relational databases
* Business intelligence
* Data visualization
* Component integration
* Input validation and error handling
* Software testing
* Version control
* Technical documentation

---

## 10. Project Vision

Vendilume is centered around one idea:

> **Transform raw sales data into clear and understandable business intelligence.**

The project prioritizes a focused, reliable, and complete analytics workflow rather than unnecessary complexity.

Further project details are separated into dedicated documents:

* [`REQUIREMENTS.md`](REQUIREMENTS.md) defines **what the system must do**.
* [`TECHNOLOGY_STACK.md`](TECHNOLOGY_STACK.md) defines **what the system will be built with and why**.
* [`PROJECT_PLAN.md`](PROJECT_PLAN.md) defines **how the system will be developed**.
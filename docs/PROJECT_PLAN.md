# Vendilume — Project Plan

## 1. Purpose

This document defines the planned development process for Vendilume.

Development will be divided into sequential phases. Each phase should produce a clear result before work begins on the next major stage.

The guiding principle is:

> **Build the core workflow first, verify that it works, and introduce additional complexity afterward.**

---

## 2. Development Roadmap

```text
Phase 1   Project Foundation
              ↓
Phase 2   Requirements & Software Design
              ↓
Phase 3   Django Foundation
              ↓
Phase 4   PostgreSQL & Data Models
              ↓
Phase 5   Django User Interface
              ↓
Phase 6   CSV Upload, Validation & Processing
              ↓
Phase 7   Grafana Foundation
              ↓
Phase 8   Sales Analytics Dashboard
              ↓
Phase 9   Django ↔ Grafana Integration
              ↓
Phase 10  Filters & Smart Insights
              ↓
Phase 11  Testing & Polish
              ↓
Phase 12  Final Documentation & Presentation
```

---

## Phase 1 — Project Foundation

### Goal

Clearly define the project before implementation begins.

### Tasks

* Finalize the project concept and scope.
* Define the major requirements.
* Finalize the technology stack.
* Establish the development roadmap.
* Create the initial repository documentation.
* Prepare the GitHub repository structure.

### Deliverables

```text
README.md

docs/
├── PROJECT_OVERVIEW.md
├── REQUIREMENTS.md
├── TECHNOLOGY_STACK.md
└── PROJECT_PLAN.md
```

### Completion

Phase 1 is complete when Vendilume's purpose, requirements, technologies, and development approach are clearly documented.

---

## Phase 2 — Requirements & Software Design

### Goal

Design how the major parts of Vendilume will behave and interact before implementing them.

### Tasks

* Review and finalize requirements.
* Define the supported sales-data structure.
* Design the system architecture.
* Design the initial database structure.
* Identify the major user interactions.
* Create useful software diagrams.

Potential diagrams include:

* Use Case Diagram
* Activity Diagram
* System Architecture Diagram
* Entity Relationship Diagram

Only diagrams that contribute to understanding the system should be created.

### Completion

The major system components, data structures, relationships, and user interactions are understood before implementation begins.

---

## Phase 3 — Django Foundation

### Goal

Create the first functioning Vendilume web application.

### Tasks

* Create the Python environment.
* Install Django.
* Create the Django project.
* Create the initial application structure.
* Configure project settings.
* Create the first URL and view.
* Run the development server.
* Verify the application in the browser.

### Completion

Vendilume successfully runs as a Django application and displays its first page.

---

## Phase 4 — PostgreSQL & Data Models

### Goal

Introduce persistent data storage.

### Tasks

* Set up PostgreSQL.
* Connect Django to PostgreSQL.
* Implement the initial Django models.
* Create and apply migrations.
* Verify database operations.
* Establish relationships between datasets and sales records.

### Completion

Django can successfully create, retrieve, and manage Vendilume data using PostgreSQL.

---

## Phase 5 — Django User Interface

### Goal

Create the main application pages and navigation.

### Tasks

* Configure Django templates.
* Add Bootstrap.
* Create the main layout.
* Build the home page.
* Build the dataset upload page.
* Build the dataset history page.
* Add application navigation.
* Add basic success and error messages.

### Completion

Vendilume has a usable web interface through which the main application areas can be accessed.

---

## Phase 6 — CSV Upload, Validation & Processing

### Goal

Build the data-ingestion pipeline.

### Tasks

* Implement CSV upload.
* Read uploaded files.
* Validate dataset structure.
* Validate required values and data types.
* Process data using Pandas.
* Transform records into the expected structure.
* Insert processed records into PostgreSQL.
* Record dataset metadata and processing status.
* Handle invalid datasets appropriately.

### Completion

A valid sales CSV can travel successfully through:

```text
Upload
  ↓
Validation
  ↓
Processing
  ↓
PostgreSQL
```

At this point, Vendilume has a functioning data pipeline.

---

## Phase 7 — Grafana Foundation

### Goal

Introduce the analytics platform.

### Tasks

* Install or configure Grafana.
* Connect Grafana to PostgreSQL.
* Verify database access.
* Create an initial dashboard.
* Test SQL queries against imported Vendilume data.
* Create the first working dashboard panel.

### Completion

Grafana can successfully retrieve and display Vendilume sales data from PostgreSQL.

---

## Phase 8 — Sales Analytics Dashboard

### Goal

Build the main business intelligence dashboard.

### Tasks

Create the core KPI panels and useful visualizations.

Potential KPIs include:

* Total Revenue
* Total Orders
* Total Items Sold
* Average Order Value
* Best-Selling Product
* Top-Performing Category

Potential visualizations include:

* Revenue Over Time
* Sales by Category
* Top Products

Dashboard design should prioritize clarity and usefulness rather than the number of panels.

### Completion

Imported sales data can be understood through a functional Grafana dashboard.

---

## Phase 9 — Django ↔ Grafana Integration

### Goal

Connect the web application and analytics experience.

### Tasks

* Add dashboard access to Vendilume.
* Investigate appropriate Grafana embedding.
* Embed the dashboard within Django where practical.
* Provide a fallback dashboard link if required.
* Ensure the transition from dataset management to analytics is understandable.

### Completion

A user can move naturally from Vendilume's application interface to the corresponding sales analytics.

---

## Phase 10 — Filters & Smart Insights

### Goal

Improve the user's ability to explore and understand sales performance.

### Tasks

Add relevant dashboard filters such as:

* Dataset
* Date range
* Product
* Category

Develop rule-based observations such as:

```text
Electronics generated the highest revenue.

July recorded the strongest sales performance.

Product A sold the most units.
```

Verify that filters update the relevant analytics correctly.

### Completion

Users can explore subsets of their data and receive useful automatically generated observations.

---

## Phase 11 — Testing & Polish

### Goal

Verify that Vendilume behaves reliably and improve the overall user experience.

### Tasks

Test important scenarios such as:

* Valid CSV upload
* Unsupported file
* Empty dataset
* Missing required columns
* Invalid values
* Correct sales calculations
* Database insertion
* Dashboard queries
* Dashboard filters

Additional work includes:

* Improve error messages.
* Improve navigation and layout.
* Fix identified bugs.
* Add automated tests where appropriate.
* Document testing results.

### Completion

Core requirements have been tested and common failures are handled appropriately.

---

## Phase 12 — Final Documentation & Presentation

### Goal

Prepare Vendilume for final submission and demonstration.

### Tasks

* Review repository structure.
* Update the README.
* Add installation instructions.
* Add usage instructions.
* Document environment setup.
* Add application and dashboard screenshots.
* Finalize technical documentation.
* Review diagrams.
* Prepare presentation material.
* Prepare a live demonstration.

The final demonstration should follow the core workflow:

```text
Upload Dataset
      ↓
Process Data
      ↓
View Dashboard
      ↓
Apply Filters
      ↓
View Insights
```

### Completion

Vendilume is documented, presentable, reproducible, and ready for university evaluation.

---

## 3. Development Priorities

Development should always prioritize the complete core workflow:

```text
Django
  ↓
CSV Upload
  ↓
Data Processing
  ↓
PostgreSQL
  ↓
Grafana
  ↓
Dashboard
```

Optional improvements should not delay completion of this workflow.

If development time becomes limited, the priority is to submit a smaller application that works reliably rather than a larger application containing incomplete features.
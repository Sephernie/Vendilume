# Vendilume

> **Transform raw sales data into clear and understandable business intelligence.**

Vendilume is a web-based **sales analytics and business intelligence application** that transforms uploaded sales data into structured, interactive, and understandable analytics.

Users provide sales data in CSV format, and Vendilume handles the workflow of validating, processing, storing, and analyzing that data before presenting the results through an interactive dashboard.

---

## Overview

Raw sales data can contain valuable information about revenue, product performance, category performance, sales volume, and trends over time. Extracting this information manually, however, often requires data cleaning, calculations, database operations, and visualization.

Vendilume aims to provide a simpler workflow:

```text
Upload Sales Data
        ↓
Validate & Process
        ↓
Store Data
        ↓
Analyze
        ↓
Explore Results
```

The goal is to allow users to move from a raw sales dataset to useful business analytics without requiring them to manually perform each technical step.

---

## Planned Features

Vendilume is planned to include:

* CSV sales dataset upload
* Dataset validation and cleaning
* Persistent sales-data storage
* Dataset history and management
* Sales KPI calculation
* Interactive analytics dashboard
* Sales trends and visualizations
* Dataset, date, product, and category filters
* Rule-based smart insights
* User-friendly validation and error handling

The project will prioritize completing the core analytics workflow before optional or advanced functionality is introduced.

---

## Technology Stack

| Technology           | Role                                      |
| -------------------- | ----------------------------------------- |
| **Python**           | Primary programming language              |
| **Django**           | Web application and backend               |
| **Pandas**           | Dataset processing and transformation     |
| **PostgreSQL**       | Persistent relational data storage        |
| **Grafana**          | Analytics dashboard and visualization     |
| **Django Templates** | Server-rendered web interface             |
| **Bootstrap**        | Interface styling                         |
| **Docker Compose**   | Local service management                  |
| **Git & GitHub**     | Version control and repository management |

Detailed information about the technology choices can be found in [`docs/TECHNOLOGY_STACK.md`](docs/TECHNOLOGY_STACK.md).

---

## System Concept

Vendilume separates the sales analytics workflow into components with clear responsibilities:

```text
                 ┌─────────────┐
                 │    User     │
                 └──────┬──────┘
                        │
                        ▼
                  ┌──────────┐
                  │  Django  │
                  └────┬─────┘
                       │
                       ▼
                  ┌──────────┐
                  │  Pandas  │
                  └────┬─────┘
                       │
                       ▼
                ┌────────────┐
                │ PostgreSQL │
                └─────┬──────┘
                      │
                      ▼
                 ┌─────────┐
                 │ Grafana │
                 └────┬────┘
                      │
                      ▼
               Sales Analytics
```

In short:

> **Django manages the application.
> Pandas processes the data.
> PostgreSQL stores the data.
> Grafana presents the analytics.**

---

## Documentation

Detailed project documentation is available in the [`docs`](docs/) directory.

| Document                                          | Description                                            |
| ------------------------------------------------- | ------------------------------------------------------ |
| [`PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | Project purpose, problem, objectives, users, and scope |
| [`REQUIREMENTS.md`](docs/REQUIREMENTS.md)         | Functional and non-functional system requirements      |
| [`TECHNOLOGY_STACK.md`](docs/TECHNOLOGY_STACK.md) | Selected technologies, responsibilities, and reasoning |
| [`PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)         | Development phases, tasks, and planned deliverables    |
| [`DATA_SPECIFICATION.md`](docs/DATA_SPECIFICATION.md) | Supported CSV structure, validation rules, and calculated fields |
| [`SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md)       | System architecture, component responsibilities, and user interactions |
| [`DATABASE_DESIGN.md`](docs/DATABASE_DESIGN.md)   | PostgreSQL schema, constraints, ERD, and analytics view |

Testing and implementation documentation will be added as development progresses.

---

## Development Roadmap

Vendilume is being developed incrementally across twelve phases:

```text
01  Project Foundation
 ↓
02  Requirements & Software Design
 ↓
03  Django Foundation
 ↓
04  PostgreSQL & Data Models
 ↓
05  Django User Interface
 ↓
06  CSV Upload, Validation & Processing
 ↓
07  Grafana Foundation
 ↓
08  Sales Analytics Dashboard
 ↓
09  Django ↔ Grafana Integration
 ↓
10  Filters & Smart Insights
 ↓
11  Testing & Polish
 ↓
12  Final Documentation & Presentation
```

See [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) for the complete development plan.

---

## Project Status

**Phase 1 — Project Foundation:** Complete

**Phase 2 — Requirements & Software Design:** Complete

**Phase 3 — Django Foundation:** Complete

**Phase 4 — PostgreSQL & Data Models:** Complete

**Phase 5 — Django User Interface:** Complete

**Phase 6 — CSV Upload, Validation & Processing:** Complete

**Phase 7 — Grafana Foundation:** Complete

**Phase 8 — Sales Analytics Dashboard:** Complete

**Current Stage:** Phase 9 — Django ↔ Grafana Integration

Phase 8 established:

* A dataset-scoped `Vendilume Sales Overview` dashboard
* A single-selection dataset variable for switching between imported datasets
* Currency-aware monetary panel titles and number formatting
* KPI panels for total net revenue, total orders, total items sold, and average order value
* A revenue-over-time time-series visualization
* Top-products and category-revenue bar charts
* Independent validation of the Phase 7 sample dataset's KPI results
* A portable, version-controlled Grafana dashboard export

All 82 automated tests pass successfully.

Vendilume can now turn each ready sales dataset into a clear set of KPIs and visualizations without mixing data between uploads. The project is ready to embed the dashboard in Django and connect application navigation to the corresponding dataset analytics.

---

## Repository Structure

The repository currently follows this structure:

```text
Vendilume/
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── core/
│   ├── migrations/
│   │   └── __init__.py
│   ├── templates/
│   │   └── core/
│   │       └── home.html
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── datasets/
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   └── 0002_create_analytics_sales_view.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_processor.py
│   │   └── dataset_importer.py
│   ├── templates/
│   │   └── datasets/
│   │       ├── delete_confirm.html
│   │       ├── detail.html
│   │       ├── history.html
│   │       └── upload.html
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   ├── REQUIREMENTS.md
│   ├── TECHNOLOGY_STACK.md
│   ├── PROJECT_PLAN.md
│   ├── DATA_SPECIFICATION.md
│   ├── SYSTEM_DESIGN.md
│   └── DATABASE_DESIGN.md
│
├── grafana/
│   └── dashboards/
│       └── vendilume-sales-overview.json
│
├── templates/
│   └── base.html
│
├── .env.example
├── .gitattributes
├── .gitignore
├── LICENSE
├── manage.py
├── README.md
└── requirements.txt
```

---

## Project Scope

Vendilume focuses specifically on the workflow between **sales-data import and sales-performance analysis**.

It is not intended to become a complete ERP, e-commerce platform, or enterprise business intelligence system.

The priority is to build a focused and reliable application that successfully performs its core workflow before considering more advanced functionality.

---

## Author

**Sepehr Bakhshivash**

Aspiring Data Analyst / Data Scientist
- [`LinkedIn`](https://linkedin.com/in/sepehr-bakhshivash-29121841a)
- [`GitHub`](https://github.com/Sephernie)

---

## License

This project is licensed under the terms provided in the [`LICENSE`](LICENSE) file.

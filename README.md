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
* AI-enhanced business interpretations and recommended actions
* Company user accounts with role-based access control
* A redesigned, consistent application interface
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
| **AI API**           | Business-insight interpretation (planned) |
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

Vendilume was originally planned as a twelve-phase project. The original MVP
was completed through Phase 10 and preserved in Git as `v0.1-mvp`. After that
checkpoint, the roadmap was expanded to fifteen phases so that three new
product-development stages could be completed before final testing and
submission.

The newly introduced phases are:

* Phase 11 — AI-Enhanced Business Insights
* Phase 12 — User Accounts & Role-Based Access Control
* Phase 13 — Vendilume UI/UX Redesign

The original Phase 11 — Testing & Polish became Phase 14, and the original
Phase 12 — Final Documentation & Presentation became Phase 15.

The revised roadmap is:

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
11  AI-Enhanced Business Insights [New]
 ↓
12  User Accounts & Role-Based Access Control [New]
 ↓
13  Vendilume UI/UX Redesign [New]
 ↓
14  Testing, Security & Final Polish [Originally Phase 11]
 ↓
15  Final Documentation & Presentation [Originally Phase 12]
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

**Phase 9 — Django ↔ Grafana Integration:** Complete

**Phase 10 — Filters & Smart Insights:** Complete

**Original MVP Checkpoint:** Completed through Phase 10 and tagged `v0.1-mvp`

**Current Stage:** Phase 11 — AI-Enhanced Business Insights

Phase 10 established:

* Django-controlled date-range, product, and category filters
* Conditional region, sales-channel, and customer filters when supported by the selected dataset
* Dataset-scoped filter choices and server-side validation
* Coordinated filter state across Django, Grafana, and Smart Insights
* Explicit Grafana All values that prevent saved dashboard selections from leaking into embedded analytics
* Updated queries for all seven Grafana panels
* Deterministic smart insights for top product revenue, strongest category, highest unit sales, and strongest month
* Clear feedback when no sales match the selected filters
* Smart Insights that remain available when Grafana is offline
* Automated coverage for filter validation, optional fields, insight calculations, empty results, and Django-to-Grafana integration

All 94 automated tests pass successfully.

Vendilume now allows users to explore a selected dataset through synchronized dashboard filters and rule-based sales observations. Phase 11 will preserve those trusted calculations while adding AI-generated explanations, risks, and recommended business actions. The rule-based insight system will remain available as a deterministic fallback if the AI service is unavailable or not configured.

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
│   │   ├── analytics_insights.py
│   │   ├── csv_processor.py
│   │   └── dataset_importer.py
│   ├── templates/
│   │   └── datasets/
│   │       ├── analytics.html
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

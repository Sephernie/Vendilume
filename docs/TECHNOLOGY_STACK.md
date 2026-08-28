# Vendilume — Technology Stack

## 1. Purpose

This document describes the primary technologies selected for Vendilume and the responsibility of each technology within the system.

The stack is designed to support the complete Vendilume workflow while keeping responsibilities clearly separated.

---

## 2. Technology Overview

| Technology       | Responsibility                            |
| ---------------- | ----------------------------------------- |
| Python           | Primary programming language              |
| Django           | Web application and backend               |
| Pandas           | Dataset processing and transformation     |
| PostgreSQL       | Persistent relational database            |
| Grafana          | Analytics and visualization               |
| Django Templates | Server-rendered web pages                 |
| Bootstrap        | Interface styling                         |
| Docker Compose   | Local service management                  |
| Git & GitHub     | Version control and repository management |

---

## 3. Python

**Python** is the primary programming language used by Vendilume.

Python was selected because it provides strong support for both web development and data analysis, allowing the application's backend and data-processing components to use the same language.

Python will primarily be used for:

* Django application logic
* Dataset validation
* Data transformation
* Sales calculations
* Smart-insight logic

---

## 4. Django

**Django** is the main web framework used to build Vendilume.

It is responsible for the application's primary workflow, including receiving requests, displaying pages, managing uploaded datasets, communicating with the database, and coordinating data processing.

Django was selected because it provides many important web-development features within a single structured framework, including:

* URL routing
* Views
* Templates
* Forms
* File uploads
* Database integration
* ORM support
* Application organization

Using Django also gives Vendilume a structured foundation that can be extended if the project grows.

---

## 5. Pandas

**Pandas** is used as Vendilume's main data-processing library.

Uploaded CSV files may contain values that need to be validated, converted, cleaned, or transformed before they are suitable for analysis.

Pandas will be responsible for operations such as:

* Reading CSV files
* Inspecting columns
* Handling missing values
* Converting data types
* Cleaning values
* Transforming records
* Preparing data for database insertion

This keeps dataset-processing logic separate from the visualization layer.

---

## 6. PostgreSQL

**PostgreSQL** is Vendilume's relational database.

Processed sales data will be stored in PostgreSQL rather than analyzed only from the original CSV files.

PostgreSQL provides Vendilume with:

* Persistent data storage
* Structured relational data
* SQL querying
* Data integrity
* Support for multiple imported datasets
* A shared data source for application and analytics functionality

Both Django and the analytics layer can therefore work with the same structured source of sales information.

---

## 7. Grafana

**Grafana** provides Vendilume's business intelligence and visualization layer.

Grafana will connect to PostgreSQL and use SQL queries to create dashboard panels based on the stored sales data.

It will primarily be responsible for:

* KPI panels
* Sales charts
* Time-series analysis
* Product comparisons
* Category comparisons
* Dashboard filters

Using Grafana avoids the need to manually implement an entire analytics dashboard inside the Django frontend while providing experience with a real business intelligence and monitoring platform.

Django remains responsible for the application workflow, while Grafana is responsible for presenting analytics.

---

## 8. Django Templates and Bootstrap

**Django Templates** will be used to create server-rendered application pages.

This avoids introducing a separate frontend framework when the project does not require one.

**Bootstrap** will provide reusable styling and layout components for elements such as:

* Navigation
* Forms
* Buttons
* Tables
* Alerts
* Responsive layouts

The objective is to create a clean and usable interface without making frontend development a major source of project complexity.

---

## 9. Docker Compose

Vendilume contains multiple services that need to work together, particularly the Django application, PostgreSQL, and Grafana.

**Docker Compose** is planned for managing these services within a consistent local development environment.

Conceptually:

```text
Docker Compose
│
├── Django
├── PostgreSQL
└── Grafana
```

This should make it easier to configure and start the application's supporting services consistently.

Docker will be introduced only when it becomes useful during development rather than adding unnecessary setup at the very beginning.

---

## 10. Git and GitHub

**Git** will be used for version control throughout development.

**GitHub** will host the Vendilume repository and project documentation.

They will provide:

* Development history
* Source-code versioning
* Commit tracking
* Documentation storage
* Repository backup
* A presentable record of the project's development

---

## 11. High-Level Technology Architecture

The technologies work together as follows:

```text
                 User
                   │
                   ▼
              ┌─────────┐
              │ Django  │
              └────┬────┘
                   │
             CSV Processing
                   │
                   ▼
              ┌─────────┐
              │ Pandas  │
              └────┬────┘
                   │
                   ▼
             ┌────────────┐
             │ PostgreSQL │
             └─────┬──────┘
                   │
              SQL Queries
                   │
                   ▼
              ┌─────────┐
              │ Grafana │
              └─────────┘
```

The central responsibility split is:

> **Django manages the application.
> Pandas processes the data.
> PostgreSQL stores the data.
> Grafana presents the analytics.**

This separation is intended to keep Vendilume understandable and maintainable as development progresses.
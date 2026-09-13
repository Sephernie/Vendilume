# Vendilume — Project Plan

## 1. Purpose

This document defines the planned development process for Vendilume.

Development will be divided into sequential phases. Each phase should produce a clear result before work begins on the next major stage.

The guiding principle is:

> **Build the core workflow first, verify that it works, and introduce additional complexity afterward.**

---

## 2. Development Roadmap

### Roadmap Revision — September 2026

Vendilume was originally planned as a twelve-phase project. That roadmap
scheduled **Testing & Polish** as Phase 11 and **Final Documentation &
Presentation** as Phase 12.

After the original MVP was completed through Phase 10, its stable repository
state was preserved with the Git tag `v0.1-mvp`. The roadmap was then expanded
from twelve to fifteen phases to reflect additional time and a broader product
direction.

Three new phases were introduced:

* Phase 11 — AI-Enhanced Business Insights
* Phase 12 — User Accounts & Role-Based Access Control
* Phase 13 — Vendilume UI/UX Redesign

The two remaining phases from the original roadmap were retained and
renumbered:

* Original Phase 11 — Testing & Polish became Phase 14 — Testing, Security & Final Polish.
* Original Phase 12 — Final Documentation & Presentation became Phase 15 — Final Documentation & Presentation.

This revision preserves the completed original MVP as a clear milestone while
allowing Vendilume's AI, internal-access, and interface goals to be developed as
separate, testable stages.

### Revised Roadmap

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
Phase 11  AI-Enhanced Business Insights [New]
              ↓
Phase 12  User Accounts & Role-Based Access Control [New]
              ↓
Phase 13  Vendilume UI/UX Redesign [New]
              ↓
Phase 14  Testing, Security & Final Polish [Originally Phase 11]
              ↓
Phase 15  Final Documentation & Presentation [Originally Phase 12]
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

### Deliverables

```text
docs/
├── DATA_SPECIFICATION.md
├── SYSTEM_DESIGN.md
└── DATABASE_DESIGN.md
```

### Completion

The major system components, data structures, relationships, and user interactions are understood before implementation begins.

---

## Phase 3 — Django Foundation

### Goal

Create the first functioning Vendilume web application.

### Tasks

* Create an isolated Python environment.
* Install Django and record project dependencies.
* Create the Django project.
* Create the initial `core` application.
* Configure environment-based project settings.
* Protect the Django secret key using an ignored `.env` file.
* Provide a safe `.env.example`.
* Create the first URL and view.
* Create the home-page template.
* Establish a reusable base template and basic navigation.
* Add an initial automated test.
* Run the development server.
* Verify the application in the browser.

### Deliverables

```text
config/
core/
templates/
.env.example
manage.py
requirements.txt
```

### Completion

Phase 3 is complete. Vendilume successfully runs as a Django application, displays its first page, loads configuration from environment variables, and passes its initial automated test.

---

## Phase 4 — PostgreSQL & Data Models

### Goal

Establish PostgreSQL as Vendilume's persistent database and implement the data model designed during Phase 2.

### Tasks

* Set up PostgreSQL for local development.
* Create the Vendilume database and dedicated application role.
* Install and record Django's supported PostgreSQL driver.
* Add protected database environment variables.
* Replace the temporary SQLite configuration with PostgreSQL.
* Verify Django's connection to PostgreSQL.
* Create the dedicated `datasets` application.
* Implement the `Dataset`, `DatasetWarning`, `SalesOrder`, and `SalesLine` models.
* Add the designed fields, relationships, indexes, check constraints, and unique constraints.
* Create, review, and apply the initial version-controlled migration.
* Inspect the resulting physical PostgreSQL schema.
* Test record creation, retrieval, and relationships.
* Test database constraints and valid edge cases.
* Test cascade deletion and atomic transaction rollback.

### Deliverables

```text
datasets/
├── migrations/
│   └── 0001_initial.py
├── models.py
└── tests.py

Updated:
├── .env.example
├── config/settings.py
└── requirements.txt
```

### Completion

Phase 4 is complete. Django uses PostgreSQL as its persistent database, all four Vendilume tables exist through a version-controlled migration, the physical schema matches the approved database design, and automated tests verify creation, retrieval, relationships, constraints, cascade deletion, valid edge cases, and transaction rollback.

---

## Phase 5 — Django User Interface

### Goal

Create the main application pages and navigation.

### Tasks

* Expand the shared template structure and base layout.
* Add Bootstrap.
* Refine the home page.
* Build the dataset upload page.
* Build the dataset history page.
* Build the dataset details page.
* Add confirmed dataset deletion.
* Expand application navigation for the main application areas.
* Add basic success and error messages.

### Deliverables

```text
datasets/
├── templates/
│   └── datasets/
│       ├── delete_confirm.html
│       ├── detail.html
│       ├── history.html
│       └── upload.html
├── tests.py
├── urls.py
└── views.py

Updated:
├── core/templates/core/home.html
├── config/urls.py
└── templates/base.html
```

### Completion

Phase 5 is complete. Vendilume now has a responsive Bootstrap interface with shared navigation, a refined home page, dataset upload, history and detail pages, confirmed deletion, application messages, and automated view tests. The complete interface workflow has also been verified manually in the browser.

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

Phase 6 is complete. Vendilume now provides a functioning, all-or-nothing data-ingestion pipeline:

```text
CSV Upload
    ↓
Complete Validation
    ↓
Cleaning and Financial Calculations
    ↓
Atomic PostgreSQL Persistence
    ↓
Dataset Details
```

---

## Phase 7 — Grafana Foundation

### Goal

Introduce the analytics platform.

### Tasks

* Install or configure Grafana.
* Verify that the `analytics_sales` view returns ready Vendilume data.
* Create a dedicated read-only PostgreSQL role for Grafana.
* Connect Grafana to the `analytics_sales` view using the read-only role.
* Verify that Grafana can read analytics data but cannot modify application data.
* Create an initial dashboard.
* Test SQL queries against imported Vendilume data.
* Create the first working dashboard panel.

### Completion

Phase 7 is complete. The `analytics_sales` PostgreSQL view is created through a reversible Django migration and exposes only ready Vendilume sales data. Automated tests verify both inclusion and exclusion behavior. Grafana connects through a dedicated read-only database role that can query the analytics view but cannot modify data, create schema objects, or read the underlying application tables. The initial `Vendilume Sales Overview` dashboard successfully displays total net revenue from imported sales data.

---

## Phase 8 — Sales Analytics Dashboard

### Goal

Build the main business intelligence dashboard.

### Tasks

* Create a single-selection dataset variable.
* Restrict every dashboard query to the selected dataset.
* Derive and display the selected dataset's currency.
* Create KPI panels for total net revenue, total orders, total items sold, and average order value.
* Create a revenue-over-time time-series visualization.
* Create bar charts for top products by net revenue and revenue by category.
* Arrange the panels into a clear and balanced dashboard layout.
* Validate the KPI calculations independently against a known sample dataset.
* Export the dashboard as portable, version-controlled Grafana JSON.

### Deliverables

```text
grafana/
└── dashboards/
    └── vendilume-sales-overview.json
```

### Completion

Phase 8 is complete. The `Vendilume Sales Overview` dashboard allows one ready dataset to be selected at a time and presents total net revenue, total orders, total items sold, average order value, revenue over time, top products by net revenue, and revenue by category. Monetary panels identify the selected dataset's currency, all queries remain dataset-scoped, the known Phase 7 sample results were independently validated, and the portable dashboard definition is stored in version control.

---

## Phase 9 — Django ↔ Grafana Integration

### Goal

Connect the web application and analytics experience.

### Tasks

* Add dataset-specific dashboard access to the Vendilume interface.
* Add environment-controlled Grafana base URL and dashboard UID settings.
* Configure Grafana for local-only iframe embedding and anonymous Viewer access.
* Create the dataset analytics URL, Django view, and embedded-dashboard template.
* Verify that the requested dataset exists and is ready before exposing analytics.
* Pass the validated dataset ID to Grafana through the `var-dataset_id` URL variable.
* Set Grafana's time range from the selected dataset's stored start and end dates.
* Use Grafana kiosk mode and a full-height iframe for a cleaner embedded experience.
* Check Grafana's health endpoint with a short timeout before displaying the iframe.
* Display clear messages for non-ready datasets and unavailable Grafana service.
* Connect dataset details to analytics through understandable navigation.
* Add automated tests for successful embedding and all important unavailable states.

### Deliverables

```text
datasets/
├── templates/
│   └── datasets/
│       └── analytics.html
├── tests.py
├── urls.py
└── views.py

Updated:
├── .env.example
├── config/settings.py
└── datasets/templates/datasets/detail.html
```

### Completion

Phase 9 is complete. A user can move from a ready dataset's detail page to its corresponding Grafana sales dashboard inside Vendilume. Django validates the dataset, supplies its ID and complete date range to Grafana, and presents the dashboard in a cleaner kiosk-mode iframe. Grafana is restricted to the local computer, embedded anonymous access receives only the Viewer role, and the existing datasource remains read-only. If the dataset is not ready, does not exist, or Grafana cannot be reached, Vendilume provides the appropriate unavailable state. Automated tests cover the integration and navigation behavior.

---

## Phase 10 — Filters & Smart Insights

### Goal

Improve the user's ability to explore and understand sales performance.

### Tasks

Add Django-controlled analytics filters such as:

* Date range
* Product
* Category

When supported by the selected dataset, add optional filters such as:

* Region
* Sales channel
* Customer

Ensure that every analytics query remains restricted to the dataset selected through the Django application.

Develop rule-based observations such as:

```text
Electronics generated the highest revenue.

July recorded the strongest sales performance.

Product A sold the most units.
```

Pass the same validated filter state to Grafana and the Django smart-insight service.

Verify that filters update the relevant KPIs, visualizations, and smart insights consistently.

### Completion

Phase 10 is complete. Users can filter a ready dataset by date range, product, and category, with region, sales channel, and customer filters appearing when supported by the uploaded data. Django validates the selected values and sends the same filter state to all seven Grafana panels and the rule-based Smart Insights service. The generated observations identify leading products, categories, unit sales, and monthly revenue while remaining available if Grafana is offline. Automated tests cover dataset-scoped choices, invalid values, conditional filters, insight calculations, empty results, and Django-to-Grafana parameter integration.

---

## Phase 11 — AI-Enhanced Business Insights

> **Roadmap status:** New phase introduced after completion of the original Phase 10 MVP.

### Goal

Transform Vendilume's trusted KPI calculations and deterministic observations
into clearer executive explanations, identified risks, and practical business
recommendations through an external AI API.

### Tasks

* Define a structured AI-input schema based on the selected dataset and validated filter state.
* Include trusted calculated KPIs, comparison periods, trends, leading and underperforming products or categories, discount behavior, and existing rule-based findings.
* Keep authoritative calculations inside Vendilume rather than asking the AI model to calculate KPIs.
* Create a dedicated AI-insight service that is independent from Django views and any future user account.
* Store API credentials and configurable model settings in environment variables.
* Request a structured response containing an executive summary, key findings, risks, recommended actions, and areas for further investigation.
* Validate returned content and prevent unsupported numeric claims from being presented as trusted calculations.
* Add timeouts, controlled error handling, and clear unavailable states.
* Preserve the existing rule-based Smart Insights as the default fallback when the AI API is unavailable, disabled, or not configured.
* Avoid sending the original CSV file when a smaller calculated business summary provides the required context.
* Add automated tests using mocked API responses so the test suite does not depend on network access or paid API calls.
* Document configuration, privacy considerations, limitations, and fallback behavior.

### Completion

Phase 11 is complete. Vendilume builds a versioned summary of trusted, filtered analytics and sends a sanitized form of that summary—not the original CSV—to Google Gemini only when AI insights are explicitly requested. Gemini returns a structured executive summary, important findings, risks, recommended actions, and areas for investigation, which Vendilume validates before display.

Authoritative KPI calculations remain inside Vendilume. Dataset names, internal dataset IDs, and customer identifiers are removed from the external prompt. Configurable environment-based credentials and model selection, a controlled timeout, invalid-response handling, no-data handling, and provider-failure handling are implemented. Existing deterministic Smart Insights remain available as the fallback without an API key or network connection.

Automated tests use mocked provider responses and cover trusted-summary calculations, filtering, rankings, trends, period comparisons, prompt construction, privacy sanitization, response validation, successful generation, invalid output, provider failure, timeout behavior, no matching data, fallback behavior, and analytics-page integration. The complete suite contains 118 passing tests.

---

## Phase 12 — User Accounts & Role-Based Access Control

> **Roadmap status:** New phase introduced after completion of the original Phase 10 MVP — **Complete**.

### Goal

Add authenticated company accounts with role-based access to one shared
Vendilume installation and its shared collection of sales datasets.

### Access Model

Vendilume is intended to run locally within a company's network. Datasets
belong to the company installation rather than to individual users, so this
phase does not introduce per-user dataset ownership or multi-tenant data
separation.

Planned roles include:

| Capability | Administrator | Sales Analyst | Manager |
| --- | --- | --- | --- |
| View available datasets | Yes | Yes | Yes |
| View dashboards and insights | Yes | Yes | Yes |
| Apply analytics filters | Yes | Yes | Yes |
| Upload CSV datasets | Yes | Yes | No |
| Delete or manage datasets | Yes | Yes | No |
| Manage users and roles | Yes | No | No |

### Tasks

* Add login, logout, password-management, and authenticated-session behavior.
* Use Django groups and permissions for administrator, sales-analyst, and manager roles.
* Let administrators create employee accounts and assign roles instead of offering unrestricted public signup.
* Require authentication for company datasets, dashboards, and insights.
* Enforce upload, deletion, user-management, and analytics permissions in Django views.
* Hide navigation links and actions that the current role cannot use.
* Return an appropriate permission-denied response when a user directly requests a forbidden URL.
* Keep all authorized users on the same shared dataset history.
* Review direct Grafana access so it cannot unintentionally bypass Vendilume's intended access controls.
* Add automated tests for anonymous users, every role, permitted actions, forbidden actions, and direct URL access.

### Completion

Phase 12 is complete. Vendilume now provides authenticated company accounts using Django's authentication system, including login, logout, password changes, protected dataset pages, session-expiration behavior, and a clear permission-denied response.

Three shared-installation roles are configured through an idempotent management command:

- **Administrators** can view, upload, change, and delete datasets and can manage employee accounts and roles through Django Admin.
- **Sales Analysts** can upload, review, and delete shared datasets and access dashboards, filters, and insights, but cannot manage users or roles.
- **Managers** can review shared datasets, dashboards, filters, and insights without access to upload, deletion, or user management.

Administrators create employee accounts and assign their roles through the protected Django Admin interface. Vendilume does not expose public account registration. Navigation links and dataset actions reflect the current user's permissions, while server-side permission checks prevent unauthorized access through manually entered URLs.

Authenticated sessions expire when the browser session ends and after 15 minutes of inactivity. Grafana was verified to listen only on `127.0.0.1`, embedded anonymous access is limited to the Viewer role, and its PostgreSQL datasource continues to use a read-only database account.

Automated tests cover authentication, logout, password changes, role creation, role permissions, shared dataset access, upload and deletion restrictions, administrator account management, unavailable public signup, role-aware interface behavior, direct-URL enforcement, and the custom permission-denied page. The complete suite contains **136 passing tests**.

---

## Phase 13 — Vendilume UI/UX Redesign

> **Roadmap status:** New phase introduced after completion of the original Phase 10 MVP.

> **Implementation status:** Completed on September 13, 2026.

### Goal

Create a distinctive, consistent, and professional Vendilume interface across
the complete authenticated workflow.

### Tasks

* Define a reusable visual system for color, typography, spacing, buttons, forms, cards, tables, alerts, and navigation.
* Redesign the home, login, dataset history, upload, detail, deletion, analytics, and AI-insight experiences.
* Adapt navigation and visible actions to the current user's role.
* Improve information hierarchy and make primary actions immediately understandable.
* Create consistent loading, success, warning, empty, unavailable, and permission-denied states.
* Improve the visual relationship between Django controls, AI insights, and the embedded Grafana dashboard.
* Review responsive behavior across desktop and smaller displays.
* Improve keyboard navigation, focus visibility, contrast, labels, and other accessibility fundamentals.
* Preserve existing application behavior while templates and styles are changed.

### Implementation Summary

Phase 13 introduced a shared Vendilume application shell built around the
brand's dark-purple and cyan palette. A persistent desktop sidebar now carries
the Vendilume logo, icon-based navigation, active-page styling, and
permission-aware links. On smaller screens, the sidebar becomes an accessible
menu that can be closed from its control, backdrop, or the Escape key. The
signed-in user's name, avatar, password action, and sign-out action are grouped
in the top-right account menu. Anonymous pages no longer claim that analytics
are ready, and the login page does not repeat its sign-in action in the top bar.

The home page now combines product information with a softly blurred,
animated three-dimensional chart illustration and respects reduced-motion
preferences. The sign-in page uses the same visual language and presents
company access in a clearer split layout. Shared styling covers typography,
spacing, cards, tables, forms, buttons, alerts, empty states, focus treatment,
and responsive layouts across the existing dataset and account workflows. An
icon-only Vendilume SVG is also used as the browser favicon.

Dataset upload now presents a controlled currency dropdown containing
supported three-letter currency codes and readable currency names. A
downloadable, ready-to-fill CSV template demonstrates every supported column
and includes a valid example sales row. The
analytics workspace places a narrow Smart Insights and AI-insights column to
the left of the wider embedded Grafana dashboard on desktop, then stacks the
sections on smaller displays. The version-controlled Grafana dashboard was
updated from its previous green presentation to fixed Vendilume cyan and
purple series and value colors.

### Verification

The final dashboard export was parsed successfully as JSON. Django's system
check reported no issues, the complete suite of **138 automated tests** passed,
and `makemigrations --check --dry-run` reported no model changes. Tests added
for this phase cover the redesigned home and sign-in content, anonymous
top-bar behavior, favicon integration, the controlled currency selector, and
the downloadable CSV template link.
`git diff --check` reported no whitespace errors; its remaining messages were
Windows CRLF-to-LF normalization warnings only.

### Completion

Phase 13 is complete when all user-facing pages share a consistent Vendilume
design, role-specific workflows are clear, analytics and AI insights feel like
one application experience, and the interface remains responsive and
accessible without breaking existing functionality.

---

## Phase 14 — Testing, Security & Final Polish

> **Roadmap history:** This phase continues and expands the original Phase 11 — Testing & Polish.

### Goal

Verify that the expanded Vendilume application behaves reliably and securely,
then complete the final usability and quality improvements.

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
* AI response validation and fallback behavior
* Authentication and session behavior
* Role permissions and forbidden direct URLs
* Shared company dataset access
* Responsive and accessible interface behavior

Additional work includes:

* Improve error messages.
* Improve navigation and layout.
* Fix identified bugs.
* Add automated tests where appropriate.
* Review environment-variable and secret handling.
* Review direct Grafana access within the intended local-network deployment.
* Document testing results.

### Completion

Core requirements and post-MVP additions have been tested, access restrictions
are enforced, and common failures are handled appropriately.

---

## Phase 15 — Final Documentation & Presentation

> **Roadmap history:** This is the original Phase 12, renumbered after three new phases were introduced.

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
View Rule-Based and AI-Enhanced Insights
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

The original workflow was completed through Phase 10 and preserved as
`v0.1-mvp`. Phases 11 through 13 are deliberate post-MVP additions rather than
unfinished parts of that original checkpoint.

If development time becomes limited, the priority remains a reliable,
demonstrable application. The `v0.1-mvp` tag provides a stable reference to the
completed original scope while expanded features are developed and verified.

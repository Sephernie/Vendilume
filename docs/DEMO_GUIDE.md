# Vendilume User and Demo Guide

## Ordinary use

An administrator creates an employee account and assigns a role. Administrators and Sales Analysts can upload a CSV; Managers can review ready datasets and analytics. The download link on the upload page supplies a CSV template with the supported columns. Choose the dataset name and currency when uploading. Vendilume reports validation errors before import and stores a successful dataset for later access through **Datasets**.

Open a ready dataset to review its metadata and available optional data. Select **View Analytics**. The date, product, and category controls appear for a ready dataset; region, channel, and customer filters appear when supported by the imported data. **Apply filters** updates the trusted calculations and embedded Grafana dashboard from the same validated state. Rule-based Smart Insights work without Grafana or Gemini. **Generate AI Insights** requests optional Gemini interpretation when configured; if unavailable, Smart Insights remain visible.

## Live demonstration route

Use a non-sensitive dataset with more than one product, category, and date. If possible, include optional region and discount data so their behavior is visible. Keep a known-good file and a deliberately invalid CSV in separate locations.

| Stage | Action | Point to explain |
| --- | --- | --- |
| Sign in | Use a Sales Analyst or Administrator account | Employee access is controlled by role. |
| Upload | Upload the known-good CSV and select its actual currency | Vendilume validates and transforms the entire file before atomic storage. |
| Inspect | Open the ready dataset | Metadata and available optional fields reflect stored usable values. |
| Dashboard | Choose **View Analytics** | Seven Grafana panels read the selected dataset through a read-only view. |
| Filters | Select a product or category and apply | Django sends one filter state to Grafana and trusted analytics calculations. |
| Insights | Explain Smart Insights, then request AI Insights if configured | Vendilume computes the numbers. Gemini interprets a sanitized summary and may fail safely. |

Allocate roughly two minutes to the problem and architecture, five minutes to this live route, and two minutes to verification and questions. Rehearse with the exact dataset before presenting. Do not use private customer data or show `.env` on screen.

## Recovery during the presentation

| If this happens | Continue with |
| --- | --- |
| The CSV is rejected | Show the useful validation feedback, then upload the known-good copy. |
| Grafana is unavailable | Show dataset details and Smart Insights; explain that stored data and Django calculations remain available. |
| Gemini is unavailable or unconfigured | Show the deterministic Smart Insights fallback. |
| The network fails | Continue without the optional external AI request. |

Before the demo, start PostgreSQL and Grafana, run Django, sign in, confirm the dashboard UID and datasource, test the known-good upload, and prepare the browser at a sensible zoom level. Keep the current analytics screenshots in `docs/images/analytics-insights.png` and `docs/images/analytics-dashboard.png` as backup for the live demonstration. They show the filters and insights above the full-width dashboard.

## Suggested presentation outline

1. Problem and intended users.
2. CSV to database to dashboard architecture.
3. Validation, atomic import, and trusted calculations.
4. Dataset-scoped Grafana filters.
5. Smart Insights and optional Gemini interpretation.
6. Employee roles and local security boundaries.
7. Test evidence and remaining deployment limits.
8. Live workflow and questions.

For the report, explain design decisions using the current architecture and historical plan rather than claiming unimplemented Docker deployment or public hosting.

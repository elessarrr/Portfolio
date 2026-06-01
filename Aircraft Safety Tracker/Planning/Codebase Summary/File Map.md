# File Map

| File Path | Responsibility |
|---|---|
| **Core Application (`app/`)** | |
| `app/__init__.py` | Initializes the Flask application, configures extensions, and registers blueprints. |
| `app/models.py` | Defines the SQLAlchemy ORM models for all database entities like Aircraft, Incident, and Users. |
| `app/routes.py` | Handles all web routes, processes HTTP requests, and renders HTML templates or returns JSON responses. |
| `app/forms.py` | Defines web forms used for user input and validation within the application. |
| `app/context_processors.py` | Provides global variables and utility functions accessible to all Jinja2 templates. |
| **Services (`app/services/`)** | |
| `app/services/deepseek.py` | Integrates with the DeepSeek LLM API for generating AI summaries and analysis. |
| `app/services/gemini.py` | Integrates with the Google Gemini LLM API for generating AI summaries and analysis. |
| `app/services/report_analyzer.py` | Orchestrates the process of analyzing incident reports and generating structured findings using various LLM services. |
| **Data Ingestion (`app/ingestion/`)** | |
| `app/ingestion/cli.py` | Provides command-line interface commands for managing data ingestion processes. |
| `app/ingestion/canonical.py` | Defines and applies rules for standardizing incident data across different sources. |
| `app/ingestion/dedupe.py` | Implements logic to identify and handle duplicate incident records during ingestion. |
| `app/ingestion/system_tagging.py` | Manages the automatic application of system-generated tags to incidents based on their content. |
| **Importers (`app/ingestion/importers/`)** | |
| `app/ingestion/importers/base.py` | Provides an abstract base class and common utilities for all data source importers. |
| `app/ingestion/importers/faa_aids_importer.py` | Implements the specific logic for importing aviation incident data from FAA AIDS. |
| `app/ingestion/importers/faa_sdr_importer.py` | Implements the specific logic for importing aviation incident data from FAA SDR. |
| `app/ingestion/importers/ntsb_importer.py` | Implements the specific logic for importing aviation incident data from NTSB. |
| **Bulk Processing (`app/ingestion/bulk/`)** | |
| `app/ingestion/bulk/faa_aids_bulk.py` | Contains utilities and logic for bulk processing of FAA AIDS data. |
| `app/ingestion/bulk/faa_sdr_bulk.py` | Contains utilities and logic for bulk processing of FAA SDR data. |
| `app/ingestion/bulk/ntsb_bulk.py` | Contains utilities and logic for bulk processing of NTSB data. |
| **Clients (`app/ingestion/clients/`)** | |
| `app/ingestion/clients/ntsb.py` | Provides a client for interacting with the NTSB API to fetch raw incident data. |
| **Normalization (`app/ingestion/normalization/`)** | |
| `app/ingestion/normalization/jasc.py` | Defines normalization rules and mappings specific to JASC codes for incident classification. |
| **Seed Data (`app/ingestion/seed/`)** | |
| `app/ingestion/seed/jasc_seed.py` | Generates initial seed data for JASC code mappings in the database. |
| **Static Assets (`app/static/`)** | |
| `app/static/css/styles.css` | Contains the main CSS stylesheets for the application's visual presentation. |
| `app/static/js/main.js` | Contains global JavaScript code for client-side interactivity and dynamic UI elements. |
| **Templates (`app/templates/`)** | |
| `app/templates/base.html` | The base Jinja2 template that defines the overall structure and common elements of all web pages. |
| `app/templates/index.html` | The template for the application's homepage, providing an overview or entry point. |
| `app/templates/aircraft.html` | The template for displaying detailed information about a specific aircraft model. |
| `app/templates/incidents_database.html` | The template for browsing and searching the database of aviation incidents. |
| `app/templates/request_data.html` | The template for a page where users can request specific data or reports. |
| `app/templates/404.html` | The custom error page template displayed when a requested resource is not found. |
| **Template Components (`app/templates/components/`)** | |
| `app/templates/components/global_charts.html` | A reusable component for rendering global charts related to incident data. |
| `app/templates/components/global_incident_list.html` | A reusable component for displaying a global list of aviation incidents. |
| `app/templates/components/incident_list.html` | A reusable component for rendering a list of incidents, often filtered or specific to an aircraft. |
| `app/templates/components/stats_grid.html` | A reusable component for displaying a grid of key statistics or metrics. |
| `app/templates/components/summary_card.html` | A reusable component for displaying an AI-generated summary of an incident or report. |
| `app/templates/components/summary_card_polling.html` | A reusable component for displaying an AI summary card that polls for updates from background jobs. |
| **Configuration & Project Management** | |
| `config.py` | Manages application-wide configuration settings for different deployment environments. |
| `pyproject.toml` | Defines project metadata, dependencies, and configuration for tools like Ruff and Mypy. |
| `requirements.txt` | Lists all Python package dependencies required for the project. |
| `.pre-commit-config.yaml` | Configures pre-commit hooks to automatically run code quality checks before commits. |
| **Database Migrations (`migrations/`)** | |
| `migrations/env.py` | Configures the Alembic environment for database migrations. |
| `migrations/versions/*.py` | Individual Alembic scripts that define database schema changes and migrations. |
| **Scripts (`scripts/`)** | |
| `scripts/import_data.py` | Main script for orchestrating the import of various aviation safety data sources into the database. |
| `scripts/asn_sync.py` | Synchronizes data from the Aviation Safety Network (ASN). |
| `scripts/batch_import_ntsb.py` | Handles batch imports of NTSB data, potentially from local files or archives. |
| `scripts/debug_scraper.py` | A utility script used for debugging data scraping processes. |
| `scripts/deduplicate.py` | A standalone script to run the deduplication process on existing incident data. |
| `scripts/generate_summaries.py` | A script to trigger the generation of AI summaries for incidents. |
| `scripts/scrape_airbus.py` | Script specifically designed to scrape incident data related to Airbus aircraft. |
| `scripts/scrape_boeing.py` | Script specifically designed to scrape incident data related to Boeing aircraft. |
| `scripts/scrape_faa.py` | Script specifically designed to scrape data from FAA sources. |
| `scripts/scrape_ntsb.py` | Script specifically designed to scrape data from NTSB sources. |
| `scripts/scraper_utils.py` | Provides common utility functions and helpers for various scraping scripts. |
| `scripts/update_data.sh` | A shell script to automate the process of updating data within the application. |
| `scripts/validate_import.py` | A script to validate the integrity and correctness of imported data. |
| **Tests (`tests/`)** | |
| `tests/conftest.py` | Contains Pytest fixtures and hooks for setting up test environments and data. |
| `tests/test_models.py` | Contains unit and integration tests for the SQLAlchemy ORM models. |
| `tests/test_routes.py` | Contains tests for the application's web routes and their expected behavior. |
| `tests/test_security.py` | Contains tests to verify security-related features and protections. |
| `tests/test_summary.py` | Contains tests for the AI summary generation functionality. |
| `tests/test_deepseek.py` | Contains tests specifically for the DeepSeek LLM integration. |
| `tests/test_gemini.py` | Contains tests specifically for the Google Gemini LLM integration. |
| `tests/test_report_analyzer_service.py` | Contains tests for the report analysis service. |
| `tests/test_importer_base.py` | Contains tests for the base data importer class and its common functionalities. |
| `tests/test_ntsb_importer.py` | Contains tests for the NTSB data importer. |
| `tests/test_faa_sdr_importer.py` | Contains tests for the FAA SDR data importer. |
| `tests/test_faa_aids_importer.py` | Contains tests for the FAA AIDS data importer. |
| `tests/test_ntsb_bulk.py` | Contains tests for the NTSB bulk data processing utilities. |
| `tests/test_faa_sdr_bulk.py` | Contains tests for the FAA SDR bulk data processing utilities. |
| `tests/test_faa_aids_bulk.py` | Contains tests for the FAA AIDS bulk data processing utilities. |
| `tests/test_dedupe.py` | Contains tests for the deduplication logic. |
| `tests/test_system_tagging.py` | Contains tests for the system tagging logic. |
| `tests/test_import_cli.py` | Contains tests for the data ingestion command-line interface. |
| `tests/test_import_data_variants.py` | Contains tests for different data import scenarios and variants. |
| `tests/test_importer_validation.py` | Contains tests for the data validation mechanisms within importers. |
| `tests/test_jasc_normalization.py` | Contains tests for the JASC code normalization logic. |
| `tests/test_asn_sync.py` | Contains tests for the ASN data synchronization process. |
| `tests/test_ntsb_client.py` | Contains tests for the NTSB API client. |
| `tests/test_source_filtering.py` | Contains tests for filtering incidents by source. |
| `tests/test_source_linking.py` | Contains tests for linking incidents to their original sources. |
| `tests/test_source_links.py` | Contains tests for the integrity and functionality of source links. |
| **Documentation & Planning (`Planning/`)** | |
| `Planning/Codebase Summary/Architecture_Overview.md` | Provides a high-level overview of the application's architecture. |
| `Planning/Codebase Summary/Data_Flow_Diagram.md` | Visualizes the data flow within the application using Mermaid.js. |
| `Planning/Reviews/Prioritised_remediation_plan_5Apr2026.md` | Outlines the prioritized plan for addressing code remediation items. |
| `Planning/Prompts/19_Apr_Codebase_review_missing_data_source` | A prompt for codebase review regarding missing data sources. |
| `Planning/tasks/tasks-0007-prd-faa-sdr-importer.md` | Task documentation for the FAA SDR importer. |
| `learnings_from_errors.md` | Documents lessons learned from encountered errors and their resolutions. |

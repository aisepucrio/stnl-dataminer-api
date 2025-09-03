# Stack Overflow Django App

## Overview
This Django app is responsible for mining, storing, and managing Stack Overflow data as part of the larger RAISE data mining platform. It provides a robust, asynchronous API to collect questions, answers, users, and related metadata from the Stack Exchange API and allows for powerful querying of the collected data.

## Features
- **Asynchronous Data Mining**: Uses Celery to run long data collection jobs in the background, providing an immediate API response.
- **Real-Time Progress Tracking**: Integrates with the `jobs` app to provide real-time status updates of ongoing tasks, which can be displayed by a frontend.
- **Comprehensive Data Collection**: Fetches questions, answers, comments, users, tags, and badges.
- **Flexible & Unified API**:
    - A single `POST` endpoint to initiate complex mining jobs with multiple operations (e.g., collect questions and then enrich user data).
    - Automatic dependency resolution between tasks.
- **Advanced Querying**:
    - `GET` endpoints to read and explore the collected data.
    - Supports powerful filtering by tags, full-text search, and ordering of results.
- **Safe and Efficient**: Includes rate-limit handling, pagination to fetch all results, and clean, user-friendly progress logs in the Celery worker terminal.

---

## Code Structure
The app follows a standardized, modular structure that separates concerns for better maintainability.

| File/Folder                  | Description                                                                  |
|------------------------------|------------------------------------------------------------------------------|
| `models.py`                  | Django models for all Stack Overflow entities.                               |
| `serializers.py`             | DRF serializers for API query (`GET`) responses.                             |
| `tasks.py`                   | Celery task definitions for asynchronous data mining.                        |
| `urls.py`                    | URL routing for the app's API endpoints.                                     |
| `operations.py`              | Defines the available mining operations and their dependencies.              |
| `views/`                     | Contains the API ViewSets, separated by concern:                             |
| &nbsp;&nbsp;`collect.py`     | `ViewSet` for initiating data collection jobs (`POST` requests).               |
| &nbsp;&nbsp;`lookup.py`      | `ViewSet`s for querying stored data (`GET` requests).                        |
| `miners/`                    | Core logic for data fetching and population.                                 |
| &nbsp;&nbsp;`question_fetcher.py`    | Handles fetching of questions and their related data.                      |
| &nbsp;&nbsp;`get_additional_data.py` | Handles enrichment of user data (profiles, badges, etc.).                  |
| `admin.py`                   | Django admin customizations for the data models.                             |
| `guide/`                     | Guides for generating API tokens.                                            |

---

## API Usage

All interaction with the miner is done via API endpoints.

### 1. Environment Setup

1.  Follow the main project `README.md` to set up Docker and your `.env` file.
2.  Follow the guide in `stackoverflow/guide/` to generate your Stack Exchange API credentials.
3.  Add your credentials to the `.env` file:
    ```
    STACK_API_KEY="your_api_key"
    STACK_ACCESS_TOKEN="your_token"
    ```
4.  Start the application:
    ```sh
    docker compose up --build
    ```

---

### 2. API Endpoints

#### To Start a Mining Job (`POST`)

This is the main endpoint to initiate all data collection and enrichment tasks.

- **URL:** `POST http://localhost:8000/api/stackoverflow/collect/`
- **Body (JSON):**
  ```json
  {
    "options": ["collect_questions", "repopulate_users"],
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "tags": "input filter tags here(these tags can be found at: https://stackoverflow.com/tags)"
  }
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
  - Supports filtering by tags, full-text search, and ordering of results.
- **Safe and Efficient**: Includes rate-limit handling, pagination to fetch all results, and clean, user-friendly progress logs in the Celery worker terminal.

---

## Code Structure

| File/Folder | Description |
|------------|-------------|
| `models.py` | Django models for all Stack Overflow entities |
| `serializers.py` | DRF serializers for API query (`GET`) responses |
| `tasks.py` | Celery task definitions for asynchronous data mining |
| `urls.py` | URL routing for the app's API endpoints |
| `views/collect.py` | ViewSet for initiating data collection jobs (`POST`) |
| `views/lookup.py` | ViewSets for querying stored data (`GET`) |
| `miners/question_fetcher.py` | Core logic for fetching questions |
| `miners/get_additional_data.py` | User enrichment logic |
| `admin.py` | Django admin customizations |
| `guide/` | Guides for generating API tokens |

---

## API Usage

### 1. Environment Setup

1. Follow the main project README to set up Docker and environment variables.
2. Generate Stack Exchange API credentials using the guide in `stackoverflow/guide/`.
3. Add credentials to `.env`:
```
STACK_API_KEY="your_api_key"
STACK_ACCESS_TOKEN="your_token"
```
4. Start the application:
```
docker compose up --build
```

---

### 2. API Endpoints

#### Basic Mining Job (POST)

- **URL**
```
POST http://localhost:8000/api/stackoverflow/collect/
```

- **Body**
```json
{
  "options": ["collect_questions", "repopulate_users"],
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "tags": ["python", "django"]
}
```

This endpoint performs basic mining using the Stack Exchange `/questions` API.

---

#### Advanced Mining Job with Filters (POST)

This endpoint uses the Stack Exchange `/search/advanced` API and must be used when advanced filters are required.

- **URL**
```
POST http://localhost:8000/api/stackoverflow/collect/advanced/
```

- **Body**
```json
{
  "options": ["collect_questions"],
  "start_date": "2024-01-01",
  "end_date": "2024-01-10",
  "tags": ["python", "django"],
  "filters": {
    "intitle": "celery",
    "accepted": true,
    "answers": 1,
    "views": 100,
    "nottagged": ["flask"]
  }
}
```

This endpoint shares the same payload structure as `/collect/`, but enables advanced filtering.

---

### 3. Supported Filters

Filters are optional and provided inside the `filters` object.

**Important**
Most filters below are only supported by the advanced endpoint (`/collect/advanced/`).
If sent to `/collect/`, unsupported filters are ignored with a warning.

| Filter | Type | Description |
|------|------|-------------|
| `min` | number | Minimum value for the current sort |
| `max` | number | Maximum value for the current sort |
| `accepted` | boolean | Only questions with accepted answers |
| `answers` | number | Minimum number of answers |
| `views` | number | Minimum view count |
| `intitle` | string | Search term in question title |
| `closed` | boolean | Only closed questions |
| `migrated` | boolean | Only migrated questions |
| `user` | number | Filter by author user ID |
| `nottagged` | string or array | Exclude questions with these tags |

Examples:
```json
"nottagged": ["flask", "fastapi"]
```
```json
"nottagged": "flask;fastapi"
```

---

### 4. Endpoint Selection Summary

| Use Case | Endpoint |
|--------|----------|
| Basic tag + date mining | `/api/stackoverflow/collect/` |
| Title search | `/api/stackoverflow/collect/advanced/` |
| Accepted / views / answers filters | `/api/stackoverflow/collect/advanced/` |
| Excluding tags | `/api/stackoverflow/collect/advanced/` |

---

### 5. Notes

- All mining jobs are asynchronous via Celery
- The API responds immediately with a `task_id`
- Progress is stored and tracked via the `jobs` app
- Tag values are normalized automatically (`["python","django"] → "python;django"`)
- Prefer short date ranges during development to avoid long-running jobs

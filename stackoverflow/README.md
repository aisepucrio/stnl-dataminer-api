  # Stack Overflow Django App

## Overview
This Django app is responsible for mining, storing, and managing Stack Overflow data as part of the larger RAISE data mining platform. It provides a robust, asynchronous API to collect questions, answers, users, and related metadata from the Stack Exchange API and allows for querying of the collected data.

## Features
- **Asynchronous Data Mining**: Uses Celery to run long data collection tasks in the background, providing an immediate API response.
- **Real-Time Progress Tracking**: Integrates with the `jobs` app to provide real-time status updates of ongoing tasks, visible to a frontend.
- **Comprehensive Data Collection**: Fetches questions, answers, comments, users, tags, and badges.
- **Advanced API Functionality**:
    - **Collection Endpoints (`POST`)**: To initiate data mining tasks.
    - **Query Endpoints (`GET`)**: To read and filter the collected data.
    - **Filtering & Searching**: Supports powerful filtering by tags, full-text search, and ordering of results.
- **Clean User Feedback**: Provides clear, formatted progress logs in the Celery worker terminal.
- **Safe API Calls**: Includes rate-limit handling and exponential backoff.
- **Pagination**: Automatically fetches all pages of results from the API, not just the first 100 items.

---

## Code Structure
The app follows a standardized structure, separating concerns into logical modules.

| File/Folder          | Description                                                                  |
|----------------------|------------------------------------------------------------------------------|
| `models.py`          | Django models for all Stack Overflow entities.                               |
| `serializers.py`     | DRF serializers for API query (`GET`) responses.                             |
| `tasks.py`           | Celery task definitions for asynchronous data mining.                        |
| `urls.py`            | URL routing for the Stack Overflow app's API endpoints.                        |
| `views/`             | Contains the API ViewSets, separated by concern:                             |
| &nbsp;&nbsp;`collect.py` | `ViewSet` for initiating data collection tasks (`POST` requests).            |
| &nbsp;&nbsp;`lookup.py`  | `ViewSet`s for querying stored data (`GET` requests).                        |
| `miners/`            | Core logic for data fetching, population, and safe API calls.                |
| &nbsp;&nbsp;`question_fetcher.py`    | Handles fetching of questions and their related data.              |
| &nbsp;&nbsp;`get_additional_data.py` | Handles enrichment of user data (badges, collectives, etc.).     |
| &nbsp;&nbsp;`safe_api_call.py`       | A robust, reusable function for making safe API requests.            |
| `admin.py`           | Django admin customizations for managing the data.                           |
| `guide/`             | Guides for generating API tokens.                                            |

---

## API Usage

All interaction with the miner is now done via API endpoints, which can be called with clients like **Bruno** or Postman.

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

#### To Collect Data (`POST` requests)

- **Collect Questions by Date and Tags:**
  - **URL:** `POST http://localhost:8000/api/stackoverflow/collect/collect-questions/`
  - **Body (JSON):**
    ```json
    {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "tags": "java;python"
    }
    ```
    *(The `tags` field is optional.)*

- **Enrich User Data (Repopulate):**
  - **URL:** `POST http://localhost:8000/api/stackoverflow/collect/re-populate-data/`
  - **Body:** No body required.

#### To Query Data (`GET` requests)

- **List, Filter, and Search Questions:**
  - **URL:** `GET http://localhost:8000/api/stackoverflow/questions/`
  - **Example Filters (as URL parameters):**
    - `?search=celery`: Search for "celery" in the title and body.
    - `?tags__name=python`: Get questions with the "python" tag.
    - `?is_answered=true`: Get only answered questions.
    - `?ordering=-score`: Order by score, highest first.

---

### 3. Troubleshooting
- **Errors during startup:** Ensure all required variables are in your `.env` file and that you've run `docker compose up --build` after any changes to `docker-compose.yml` or `requirements.txt`.
- **Task Failures:** Check the logs of the **`worker-1`** container for detailed error messages from the mining process. The `web-1` container will only show errors related to receiving the API request.

---

## Future Work
- Implement filtering for the data enrichment process (`re-populate-data`).
- Integrate the `token_manager.py` to support multiple API tokens and avoid rate limiting more effectively.
- Add more query endpoints (e.g., for users, tags, answers).
- Create automated tests for the app.
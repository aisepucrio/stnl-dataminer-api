# StackOverflow Django App

## Overview
This Django app is responsible for mining, storing, and managing Stack Overflow user data, badges, collectives, and related metadata as part of the larger RAISE data mining platform. It integrates with the Stack Exchange API and keeps Stack Overflow-related data up to date in the local database.

## Features
- Fetches and updates Stack Overflow user profiles
- Fetches questions, comments and answers
- Safe API calls with rate limit handling and logging
- **Some intended but not implemented:**
    - **Parallel Data Mining:** Uses Celery to process data mining tasks in parallel, improving efficiency and scalability
    - **Saving data to the database:** Currently saving data locally.

## Code Structure
Below is an overview of the main files and folders in this app:

| File/Folder         | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `models.py`         | Django models for Stack Overflow users, badges, collectives, etc.           |
| `admin.py`          | Django admin customizations for managing Stack Overflow data                 |
| `serializers.py`    | DRF serializers for API responses (if any)                                  |
| `views.py`          | API endpoints and admin actions for Stack Overflow data                     |
| `urls.py`           | URL routing for the StackOverflow app                                       |
| `functions/`        | Core logic for data fetching, population, and safe API calls:               |
| &nbsp;&nbsp;`data_populator.py` | Main script for updating/fetching data from Stack Exchange API         |
| &nbsp;&nbsp;`safe_api_call.py`  | Handles API requests with error handling and backoff                  |
| &nbsp;&nbsp;`question_fetcher.py`, `token_manager.py` | Additional helpers for API interaction and token management |
| `management/commands/` | Custom Django management commands for data population                  |
| `migrations/`       | Database migrations for this app                                            |
| `guide/`            | Contains guides for generating API tokens and setup (see referenced docs)   |

## Usage

### 1. Environment Setup

1. **Follow the main [README](../README.md)** to set up Docker, and your `.env` file.
2. **Follow the guide [here](/guide/generateAccessToken.md)** to generate a Stack Exchange API token.
3. **Add Stack Overflow credentials** to your `.env`:
    ```
    STACK_API_KEY="your_api_key"
    STACK_ACCESS_TOKEN="your_token"
    ```
4. **Start the application:**
    ```sh
    docker compose up --build
    ```

> **Tip:** Use TablePlus (see main README) to inspect the database. This is a great tool for inspecting your database.

---

### 2. Accessing the Admin Interface

- Go to [http://localhost:8000/](http://localhost:8000/) in your browser.
- Log in with your Django superuser credentials.
- Scroll to the **StackOverflow** section to find:
  - **Collect-questions**
  - **Re-populate-data**

---

### 3. Explanation of Functions

- **Collect-questions**
  - Fetches 100 questions at a time (pagination required for more).
  - You can set the date range using the **start** and **end** fields in the admin interface.
  - Click **Execute** to start. The function fetches questions, comments, answers, and users, and stores them in the database.

- **Re-populate-data**
  - Fills in missing user and relational data not provided in the initial API call.
  - Triggered by clicking **Execute** in the admin interface.

---

### 4. Notes

- All data interaction is currently via the Django admin interface.
- For troubleshooting, see the section below.

## Having issues / Troubleshooting
- **Missing API Key/Token:** Ensure `STACK_API_KEY` and `STACK_ACCESS_TOKEN` are set in your environment (`.env`) or Django settings.
- **API Rate Limits:** The app handles rate limits, but if you see repeated warnings, consider increasing your quota or spacing out requests.
- **Database Issues:** Run migrations and check your database connection settings. If you have to make the migrations, make sure to run them in the web container:
  ```
  docker compose exec web python manage.py makemigrations
  ```
  If you needed to make migrations in the web container, run them in the web container:
  ```
  docker compose exec web python manage.py migrate
  ```
- **Logging:** Check the console output for detailed logs and errors.

## Known Limitations
- Paginazation is required, can not collect more than 100 objects each api call.
- Data is currently saved locally, not directly to the main database like the GitHub and Jira apps.
- Celery-based parallel data mining is not yet implemented (intended for future work).
- The api will call backoff if the miner is requesting too much too fast. (Not known what waiting time should be used.)

## Future Work
- Currently this part of RAISE saves locally. Should save the data to the database, like Github and Jira.
- Add a more comprehensive mining script that fetches more data and updates more frequently. Currently, it only fetches 100 questions and the corresponding data. The other function is populating missing columns from the first call.
- Parrallelize data mining tasks. Using cellery like the other two (Github and Jira).
- Make tests for this part of the app.
- Improve error handling and retry logic for unstable API responses
- Expand coverage to additional Stack Exchange sites beyond Stack Overflow.  

---

For general setup, installation, and environment configuration, please refer to the main project README at the root of the repository. 
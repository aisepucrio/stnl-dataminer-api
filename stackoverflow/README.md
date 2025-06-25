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
1. **Environment Setup**
   - Ensure you have followed the main [README](../README.md#example-connecting-with-tableplus) and get your setup running.
   - **Important notes from the main README:** 
     1. Ensure you have Docker and Docker Compose installed, as the [Docker Desktop section](../README.md#1-docker-desktop) explains how to do this.
     2. Recommended using TablePlus to easily manage and see what's happening in the database. This is also explained in the [tabelplus section](../README.md#example-connecting-with-tableplus).
     3. Ensure you have a `.env` file updated as explained in the [.env section](../README.md#2-configure-a-file-named-env)
   - Follow the guide for creating **Stack Api Key** and **Stack Access Token**. This is explained [here](guide/generateAccessToken.md)
   - Put your `STACK_API_KEY` and your `STACK_ACCESS_TOKEN` in the `.env` file, and make sure it contains the following:
     ```
     GITHUB_TOKENS="your_github_token"
     ...
     other fields
     ...
     POSTGRES_PORT=5432
     STACK_API_KEY="you_api_key"
     STACK_ACCESS_TOKEN="your_token"
     ```
   - If you have followed the instructions in the main readme file, and these steps above. Run this command
     ```
     docker compose up --build
     ``` 

3. **Admin Interface:**
   - After setting up the enviroment variables you can access the Django admin interface at `http://localhost:8000/`.
   - You can go down to the StackOverflow section and look at the two current funcitons. Collect-questions and Re-populate-data. 

3. **Explination of the functions:**
   - **Collect-questions:** This function fetches 100 questions at a time. You can yourself change the date of which period you want to fetch questions. This is by edting the **start** and **end** date on the infterface.  The functions starts when a user clicks on the **Execute**-button. It then fetches the questions, comments, answers and corresponding users and stores them in the database. 
  - **Re-populate-data:** The `collect-questions` function retrieves a large amount of data, but some fields, such as user information, may be incomplete because they aren't provided in that specific API call. Therefore, we perform an additional request to fill in the missing fields and create more complete and consistent connections between the data. This function is triggered when you click on the **Execute**-button.

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
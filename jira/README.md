# Jira Django App

## Overview
This Django app is responsible for mining, storing, and managing project data from Jira as part of the larger **RAISE data mining platform**.  
It provides a robust, asynchronous API to collect issues and related metadata from Jira projects and allows for powerful, detailed querying of the collected data.

## Features
- **Asynchronous Data Mining**: Uses Celery to run long data collection jobs in the background, providing an immediate API response.  
- **Real-Time Progress Tracking**: Integrates with the `jobs` app to provide real-time status updates of ongoing tasks, visible to a frontend.  
- **Flexible Collection**: Allows mining of multiple projects at once and filtering by issue types and date ranges.  
- **Advanced Querying**: Provides a rich set of `GET` endpoints to read and explore all collected Jira entities, with support for pagination, exact-match filtering, full-text search, and ordering.  
- **Safe API Calls**: The underlying miner class handles rate limiting and rotation of multiple API tokens.  

---

## API Usage

### 1. Environment Setup
1. Follow the main project `README.md` for general Docker and `.env` setup.  
2. Generate a Jira API Token by following the guide in the main `README.md`.  
3. Add your Jira credentials to the `.env` file. To avoid API rate limits, you can add multiple tokens separated by commas:  

   ```env
   JIRA_API_TOKEN="your_token_1,your_token_2"
   JIRA_EMAIL="your_jira_email"
   ```

---

### 2. API Endpoints

#### To Collect Data (`POST`)

##### **Collect Issues**
Starts an asynchronous mining job to collect issues from one or more specified Jira projects.

- **URL:** `POST /api/jira/issues/collect/`  
- **Body (JSON):**
  ```json
  {
    "projects": [
      {
        "jira_domain": "ecosystem.atlassian.net",
        "project_key": "AO"
      }
    ],
    "issuetypes": ["Bug", "Documentation"],
    "start_date": "2011-11-15",
    "end_date": "2013-12-27"
  }
  ```

**Parameters:**
- `projects` (**required**): A list of project objects to mine. Each must contain:  
  - `jira_domain` *(string)*: Your Jira instance domain.  
  - `project_key` *(string)*: The project key in Jira (e.g., `PROJ`).  
- `issuetypes` *(optional)*: A list of issue types to filter by (e.g., `["Bug", "Task"]`). If omitted, all types are collected.  
- `start_date` / `end_date` *(optional)*: The date range for the issue search (format `YYYY-MM-DD` or `YYYY-MM-DD HH:mm`). If omitted, all issues are collected.  

---

#### To Query Data (`GET`)
The API provides a rich set of endpoints to query all mined Jira data.  
All list endpoints support **pagination, filtering, searching, and ordering**.

##### **List Jira Issues**
- **URL:** `GET /api/jira/issues/`  
- **Example:**  
  ```
  GET /api/jira/issues/?project__key=PROJ&status=Done&ordering=-created
  ```

**Available Filters:**
- **Date:** `created_after`, `created_before`, `updated_after`, `updated_before`  
- **Text Search:** `summary`, `description`, `creator__displayName`, `assignee__displayName`  
- **Exact Match:** `status`, `project__key`, `priority`, `issuetype__issuetype`  
- **Ordering:** `created`, `updated`, `priority`, `status`  

---

##### **List Jira Projects**
- **URL:** `GET /api/jira/projects/`  
- **Example:**  
  ```
  GET /api/jira/projects/?key=PROJ
  ```

---

##### **List Jira Users**
- **URL:** `GET /api/jira/users/`  
- **Example:**  
  ```
  GET /api/jira/users/?search=John
  ```

---

Additional query endpoints are available for **sprints, comments, commits, activity-logs, etc.**  
For a complete list of available views and their specific filters, please refer to the `jira/views/lookup.py` file and the **auto-generated API documentation**.

---

### 3. Job Monitoring
All collection tasks are **asynchronous**.  
You can monitor their progress using the `/api/jobs/` endpoints as described in the main project `README.md`.

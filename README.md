# STNL DataMiner API

STNL DataMiner API is a modular backend platform designed to collect and
analyze data from multiple development ecosystems:

- GitHub
- Jira
- StackOverflow

The system follows a modular architecture where each mining source is
implemented as an isolated Django app, allowing independent evolution
and scalability.

---

## Architecture Overview

The platform follows a two-phase mining pattern:

### 1. Collection Phase (POST)

Triggers background data mining tasks. Data is fetched from external
APIs and stored in the database asynchronously.

### 2. Query Phase (GET)

Retrieves previously collected and processed data from the local
database.

This separation ensures scalability, reliability, and safe long-running
operations.

---

## Project Structure

```text
backend/
├── github/         # GitHub mining module
├── jira/           # Jira mining module
├── stackoverflow/  # StackOverflow mining module
├── jobs/           # Background task tracking
├── config/         # Django project configuration
└── manage.py
```

Each mining source contains its own models, services, serializers, and
endpoints.

---

## Technologies

- Python 3.11+
- Django
- Django REST Framework
- PostgreSQL
- Docker
- Docker Compose

---

## Running the Project

### 1. Clone the repository

```bash
git clone <repository-url>
cd <project-folder>
```

### 2. Configure environment variables

Create a `.env` file in the root directory:

```env
POSTGRES_DB=dataminer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

GITHUB_TOKEN=your_github_token

JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your_email
JIRA_API_TOKEN=your_jira_token
```

### 3. Start with Docker

```bash
docker-compose up --build
```

The API will be available at:

http://localhost:8000/

---

## Jobs System

All mining operations run asynchronously and are tracked through the
Jobs module.

### Task States

- PENDING
- STARTED
- PROGRESS
- SUCCESS
- FAILURE

### Jobs Endpoints

```http
GET /jobs/
GET /jobs/{task_id}/
```

These endpoints allow monitoring the status of background mining tasks.

---

## Module Documentation

Detailed documentation for each mining source is available in their
respective READMEs:

- GitHub Mining → [GitHub Module README](./github/README.md)
- Jira Mining → [Jira Module README](./jira/README.md)
- StackOverflow Mining → [StackOverflow Module README](./stackoverflow/README.md)

All module-specific endpoints, filters, parameters, and response
examples are documented there.

---

## Best Practices for Mining

- Use date filters to limit data volume.
- Avoid mining multi-year periods in a single request.
- Provide valid API tokens for higher rate limits.
- Monitor task execution using the Jobs endpoints.
- Query stored data instead of repeatedly triggering new mining operations.

---

## Database

PostgreSQL is used as the primary relational database.

The data model connects repositories, issues, pull requests,
contributors, and other mined entities depending on the source module.

---

## Summary

This README provides an architectural and operational overview of the
backend.

For detailed endpoint documentation and usage examples, refer to the
module-specific READMEs listed above.
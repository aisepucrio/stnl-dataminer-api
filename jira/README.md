# Jira Mining Module

This module is responsible for mining, storing, and querying Jira
project data as part of the RAISE Data Mining Platform.

It supports:

-   Issue collection (asynchronous)
-   Multi-project mining
-   Date-range filtering
-   Issue type filtering
-   Advanced querying with pagination, filtering, search, and ordering
-   Real-time job tracking
-   Token rotation and rate-limit protection

## Architecture Overview

The Jira module follows a two-phase architecture:

1.  Collection Phase (POST endpoints)
    -   Fetches data from Jira REST API
    -   Stores normalized data in PostgreSQL
    -   Executes asynchronously via Celery
    -   Returns a task object for monitoring
2.  Query Phase (GET endpoints)
    -   Reads previously mined data from the database
    -   Supports filtering, searching, ordering, and pagination

All collection endpoints return:

{ “task_id”: “uuid”, “message”: “Task successfully initiated”,
“status_endpoint”: “/api/jobs/tasks/{task_id}/” }

## Environment Configuration 

1.  Follow the main project README.md for:

    -   Docker setup
    -   PostgreSQL configuration
    -   Base environment configuration

2.  Generate a Jira API Token via Atlassian account settings.

3.  Add credentials to your .env file:

JIRA_API_TOKEN=“your_token_1,your_token_2” JIRA_EMAIL=“your_jira_email”

Multiple tokens can be provided (comma-separated). The system
automatically rotates tokens to prevent rate limiting.

 ## Collection Endpoints (POST) 

1) Collect Issues

POST /api/jira/issues/collect/

Starts an asynchronous mining job to collect issues from one or more
Jira projects.

Body (JSON):

{ “projects”: [ { “jira_domain”: “ecosystem.atlassian.net”,
“project_key”: “AO” } ], “issuetypes”: [“Bug”, “Documentation”],
“start_date”: “2011-11-15”, “end_date”: “2013-12-27” }

Parameters:

-   projects (required) List of project objects:

    -   jira_domain (string)
    -   project_key (string)

-   issuetypes (optional) List of issue types (e.g., [“Bug”, “Task”]) If
    omitted, all issue types are collected.

-   start_date / end_date (optional) Date range in format:

    -   YYYY-MM-DD
    -   YYYY-MM-DD HH:mm

If omitted, all issues are collected.

## Query Endpoints (GET)

All list endpoints support:

-   Pagination
-   Exact-match filtering
-   Full-text search
-   Ordering

  ---------------------
  1) List Jira Issues
  ---------------------

GET /api/jira/issues/

Example:

GET /api/jira/issues/?project__key=PROJ&status=Done&ordering=-created

Available Filters:

Date Filters: - created_after - created_before - updated_after -
updated_before

Text Search: - summary - description - creator__displayName -
assignee__displayName

Exact Match: - status - project__key - priority - issuetype__issuetype

Ordering: - created - updated - priority - status

  -----------------------
  2) List Jira Projects
  -----------------------

GET /api/jira/projects/

Example:

GET /api/jira/projects/?key=PROJ

  --------------------
  3) List Jira Users
  --------------------

GET /api/jira/users/

Example:

GET /api/jira/users/?search=John

  ---------------------
  Additional Entities
  ---------------------

Additional endpoints are available for:

-   Sprints
-   Comments
-   Commits (linked development data)
-   Activity Logs
-   Issue Types
-   Priorities
-   Statuses

For a complete list of endpoints and filters, refer to:

-   jira/views/lookup.py
-   Auto-generated API documentation

## Job Monitoring


All collection operations are asynchronous.

Use the Jobs module endpoints to track task progress:

GET /api/jobs/ GET /api/jobs/tasks/{task_id}/

Task states typically include:

-   PENDING
-   STARTED
-   PROGRESS
-   SUCCESS
-   FAILURE

Refer to the main README.md for detailed job tracking documentation.

## Rate Limiting & TokenRotation 

The Jira miner includes:

-   Automatic rate-limit handling
-   Retry logic
-   Multiple token rotation

To maximize throughput:

-   Provide multiple API tokens
-   Use date filters for large projects
-   Avoid collecting entire multi-year histories in a single job

## Best Practices


-   Prefer date-range filtering for large instances
-   Limit issue types when possible
-   Monitor jobs instead of waiting synchronously
-   Avoid mining multiple very large projects simultaneously
-   Use filtering in GET endpoints instead of post-processing externally

## Related Documentation


-   Main Project → ../README.md
-   GitHub Module → ../github/README.md
-   Jobs Module → ../jobs/README.md

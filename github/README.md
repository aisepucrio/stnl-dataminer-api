# GitHub Mining Module

This module is responsible for mining, storing, and querying data from
GitHub repositories.

It supports: - Commits - Issues - Pull Requests - Branches - Repository
Metadata - Statistical Dashboards

## Architecture Overview


The GitHub module follows a two-phase flow:

1.  Collection (POST endpoints)
    -   Fetches data from the GitHub API
    -   Stores it in PostgreSQL
    -   Runs asynchronously (Celery tasks)
2.  Query (GET endpoints)
    -   Retrieves mined data from the local database
    -   Supports filtering, searching, ordering, and pagination

All collection endpoints return:

{ “task_id”: “uuid”, “message”: “Task successfully initiated”,
“status_endpoint”: “/api/jobs/tasks/{task_id}/” }

 ## Collection Endpoints(POST) 

### 1)  Commit Collection POST /api/github/commits/collect/

Body Parameters: - repo_name (required) → Format: owner/repo -
start_date (optional) → ISO 8601 - end_date (optional) → ISO 8601 -
commit_sha (optional)

Example (date range): { “repo_name”: “facebook/react”, “start_date”:
“2023-01-01T00:00:00Z”, “end_date”: “2023-12-31T23:59:59Z” }

Example (specific commit): { “repo_name”: “facebook/react”,
“commit_sha”: “a1b2c3d4e5” }

------------------------------------------------------------------------

### 2)  Issue Collection POST /api/github/issues/collect/

Body Parameters: - repo_name (required) - start_date (optional) -
end_date (optional) - depth → “basic” (default) or “complex”

Example: { “repo_name”: “pandas-dev/pandas”, “depth”: “complex” }

------------------------------------------------------------------------

### 3)  Pull Request Collection POST /api/github/pull-requests/collect/

Same structure as Issues.

------------------------------------------------------------------------

### 4)  Branch Collection POST /api/github/branches/collect/

{ “repo_name”: “django/django” }

------------------------------------------------------------------------

### 5)  Metadata Collection POST /api/github/metadata/collect/

## Query Endpoints (GET)


Commits GET /api/github/commits/

Filters: - repository - created_after - created_before - author_name -
message - sha - ordering

Example: GET
/api/github/commits/?repository=facebook/react&created_after=2023-01-01

------------------------------------------------------------------------

Issues GET /api/github/issues/

Filters: - repository - state - creator - has_label - created_after -
updated_after - ordering

------------------------------------------------------------------------

Pull Requests GET /api/github/pull-requests/

Filters: - All issue filters - state = open, closed, merged

------------------------------------------------------------------------

Branches GET /api/github/branches/

Filters: - repository - name

------------------------------------------------------------------------

Metadata GET /api/github/metadata/

## Dashboard

GET /api/github/dashboard/

Parameters: - repository_id (optional) - start_date - end_date

Global Example: GET /api/github/dashboard/

Repository Example: GET /api/github/dashboard/?repository_id=1

## Rate Limits & TokenRotation 

The system supports multiple GitHub tokens.

In your .env:

GITHUB_TOKENS=‘token1,token2,token3’

The system automatically rotates tokens when rate limits are reached.

## Best Practices

-   Use date ranges for large repositories.
-   Prefer “basic” depth unless detailed data is required.
-   Monitor tasks via /api/jobs/.
-   Avoid mining entire large repositories without filters.

## Related Documentation

-   Main Project → ../README.md
-   Jira Module → ../jira/README.md
-   Jobs Module → ../jobs/README.md

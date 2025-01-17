# Diggit

## Description

This is a Django-based API designed for mining and analyzing software development data, enabling the extraction of valuable insights from GitHub repositories and Jira projects. The tool provides detailed tracking of the project lifecycle, including commit analysis, pull requests, issues, and branches, offering critical insights into the development process.

## Features

1. **GitHub Mining**: Extract data from commits, pull requests, issues, and branches.
2. **Jira Mining**: Extract data from Jira issues.
3. **Temporal Analysis**: Monitor project evolution over time.
4. **Documented API**: Endpoints documented using DRF Spectacular.

## Requirements

Before getting started, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/downloads)

## Installation and Configuration

1. **Clone the Repository**
   ```bash
   git clone https://github.com/aisepucrio/stnl-dataminer-api.git
   cd stnl-dataminer-api
   ```

2. **Configure a file named .env**
   
   Create a file named `.env` (this is the complete filename, not a file extension) at the root of the project with the following information:
   ```
   GITHUB_TOKENS="your_github_token"
   DJANGO_SUPERUSER_PASSWORD="your_superuser_password"
   POSTGRES_DB=database_name
   POSTGRES_USER=postgres_user
   POSTGRES_PASSWORD=postgres_password
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   ```
   
   Note: For instructions on how to generate your GitHub token, see the "GitHub Token Configuration" section below (lines 107-115).

3. **Verify the Line Format of `start.sh`**
   
   Open the `start.sh` file in your IDE and confirm that the line format is set to LF (this is usually visible at the bottom-right corner of the IDE). If it shows CRLF, change it to LF.

4. **Check for Existing Database or Server Conflicts**
   
   Ensure that no other PostgreSQL instances are running on port 5432. To check and terminate existing instances:
   
   1. Open Task Manager (Ctrl + Shift + Esc)
   2. Go to the "Processes" or "Details" tab
   3. Look for processes named "postgres" or "postgresql"
   4. Select each PostgreSQL-related process
   5. Click "End Task" or "End Process"

5. **Start the Containers**
   
   1. Open Docker Desktop and wait until it's fully initialized
   2. Run the command:
   ```bash
   docker compose up --build
   ```
## GitHub Token Configuration

### How to Generate a GitHub Token:

1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens > Tokens (classic)](https://github.com/settings/tokens).
2. Click on "Generate new token (classic)".
3. Select the following scopes:
   - `repo` (full access to repositories)
   - `read:org` (read organization data)
   - `read:user` (read user data)
4. Generate the token and copy it immediately.

### Configuring Multiple Tokens:

To avoid GitHub API rate limits, you can configure multiple tokens. In the `.env` file, add them separated by commas:

```
GITHUB_TOKENS='token1,token2,token3'
```

The API will automatically switch between tokens when one reaches its request limit.

## Using the API

The API provides various endpoints for data mining. To test the endpoints, we recommend using one of the following tools:

- [Postman](https://www.postman.com/downloads/) - Popular GUI for API testing
- [Bruno](https://www.usebruno.com/) - Open source alternative to Postman

### **GitHub Mining**

#### Basic Request Structure

All requests follow the base format:
```
http://localhost:8000/api/github/{endpoint}/?repo_name={owner}/{repository}&start_date={start_date}&end_date={end_date}
```

Where:
- `{endpoint}`: can be commits, issues, pull-requests, or branches
- `{owner}`: repository owner/organization
- `{repository}`: repository name
- `{start_date}` and `{end_date}`: dates in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ)

#### Request Examples

1. **Commit Mining**
```
GET http://localhost:8000/api/github/commits/?repo_name=facebook/react&start_date=2023-01-01T00:00:00Z&end_date=2023-12-31T00:00:00Z
```

2. **Issue Mining**
```
GET http://localhost:8000/api/github/issues/?repo_name=tensorflow/tensorflow&start_date=2023-01-01T00:00:00Z&end_date=2023-12-31T00:00:00Z
```

3. **Pull Request Mining**
```
GET http://localhost:8000/api/github/pull-requests/?repo_name=kubernetes/kubernetes&start_date=2023-01-01T00:00:00Z&end_date=2023-12-31T00:00:00Z
```

4. **Branch Mining**
```
GET http://localhost:8000/api/github/branches/?repo_name=django/django
```

#### Query Parameters

- `repo_name` (required): In the format `owner/repository` (e.g., `microsoft/vscode`)
- `start_date` (optional): Initial date to filter data
- `end_date` (optional): Final date to filter data
- `per_page` (optional): Number of items per page (default: 100)
- `page` (optional): Page number for pagination (default: 1)

#### Important Notes

1. Dates must be in ISO 8601 format: `YYYY-MM-DDTHH:mm:ssZ`
2. The repository must be public or your token must have access to it
3. For large repositories, consider using smaller date ranges to avoid timeout
4. Branch mining doesn't require date parameters

### **Jira Mining**

#### **1. Collect Issues (`POST`)**

**Request**

```http
POST http://localhost:8000/api/jira/issues/collect/
```
- **Description:** Fetches all Jira issues saved in the database.

**Request Body Parameters**

The request body must be in JSON format, containing the following fields:

- `jira_domain` (required): Your Jira domain, e.g., `yourcompany.atlassian.net`
- `project_key` (required): The project key in Jira (e.g., `PROJ`)
- `jira_email` (required): The email associated with your Jira account
- `jira_api_token` (required): Your Jira API token
- `issuetypes` (optional): A list of issue types to filter (e.g., `["Bug", "Task"]`)
- `start_date` (optional): Start date in "yyyy-MM-dd" or "yyyy-MM-dd HH:mm" format.
- `end_date` (optional): End date in "yyyy-MM-dd" or "yyyy-MM-dd HH:mm" format.

**Request Example**

```json
Content-Type: application/json

{
    "jira_domain": "yourcompany.atlassian.net",
    "project_key": "PROJ",
    "jira_email": "user@example.com",
    "jira_api_token": "your_api_token",
    "issuetypes": ["Bug", "Task"],
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
}
```

**Additional Testing Examples**

Here are two real project examples from the domain `ecosystem.atlassian.net` that you can use for testing:

1. **Project AO**:
   - [Explore Issues](https://ecosystem.atlassian.net/jira/software/c/projects/AO/issues/?jql=project%20%3D%20%22AO%22%20ORDER%20BY%20created%20DESC)
   - Example Request Body:
     ```json
     {
         "jira_domain": "ecosystem.atlassian.net",
         "project_key": "AO",
         "jira_email": "user@example.com",
         "jira_api_token": "your_api_token",
         "issuetypes": ["Bug", "Documentation"],
         "start_date": "2011-11-15",
         "end_date": "2013-12-27"
     }
     ```

2. **Project ACCESS**:
   - [Explore Issues](https://ecosystem.atlassian.net/jira/software/c/projects/ACCESS/issues/?jql=project%20%3D%20%22ACCESS%22%20ORDER%20BY%20created%20DESC)
   - Example Request Body:
     ```json
     {
         "jira_domain": "ecosystem.atlassian.net",
         "project_key": "ACCESS",
         "jira_email": "user@example.com",
         "jira_api_token": "your_api_token",
         "issuetypes": ["Story", "Bug"],
         "start_date": "2013-09-25",
         "end_date": "2014-12-23"
     }
     ```

Additionally, there are many other projects within the `ecosystem.atlassian.net` domain that can be mined. Explore them [here](https://ecosystem.atlassian.net).

---

#### **2. List Issues (`GET`)**

**Request**

```http
GET http://localhost:8000/api/jira/issues/
```

- **Description:** Fetches all Jira issues saved in the database. The endpoint supports multiple filters to narrow down the results based on various criteria.

**Available Filters**
You can apply the following query parameters to filter the issues:

1. **Date Filters**:
   - `created_after`: Fetch issues created on or after a specific date (e.g., `2023-01-01T00:00:00Z`).
   - `created_before`: Fetch issues created on or before a specific date (e.g., `2023-12-31T23:59:59Z`).
   - `updated_after`: Fetch issues updated on or after a specific date.
   - `updated_before`: Fetch issues updated on or before a specific date.

2. **Text Search**:
   - `summary`: Search for issues whose summaries contain a specific term (case-insensitive).
   - `description`: Search for issues whose descriptions contain a specific term (case-insensitive).
   - `creator`: Search for issues created by a specific user (case-insensitive).
   - `assignee`: Search for issues assigned to a specific user (case-insensitive).

3. **Exact Match Filters**:
   - `status`: Filter issues by their status (e.g., `Open`, `Closed`).
   - `project`: Filter issues by the project key (e.g., `PROJ`).
   - `priority`: Filter issues by their priority (e.g., `High`, `Low`).
   - `issuetype`: Filter issues by their type (e.g., `Bug`, `Task`).

4. **Ordering**:
   - Use the `ordering` parameter to sort the results by specific fields. Available fields:
     - `created`
     - `updated`
     - `priority`
     - `status`

   Example: `?ordering=created` or `?ordering=-updated` (descending order).

**Request Examples**

1. **Fetch all issues in the database**:

```http
GET http://localhost:8000/api/jira/issues/
```

2. **Fetch issues created after a specific date**:
```http
GET http://localhost:8000/api/jira/issues/?created_after=2023-01-01
```

3. **Search for issues containing "login" in the summary**:
```http
GET http://localhost:8000/api/jira/issues/?summary=login
```

4. **Filter issues assigned to a specific user**:
```http
GET http://localhost:8000/api/jira/issues/?assignee=johndoe
```

5. **Combine filters**:
Fetch issues from the project `PROJ` with status `Open`, created after `2023-01-01`:
```http
GET http://localhost:8000/api/jira/issues/?project=PROJ&status=Open&created_after=2023-01-01
```

6. **Order issues by priority**:
```http
GET http://localhost:8000/api/jira/issues/?ordering=priority
```
---

#### **3. Issue Details (`GET`)**

**Request**

```http
GET http://localhost:8000/api/jira/issues/{issue_key}/
```
- **Description:** Fetches details for a specific Jira issue by its key.
- **Path Parameter:**
  - `issue_key` (required): The unique key of the issue (e.g., `PROJ-123`).

**Request Example**

```http
GET http://localhost:8000/api/jira/issues/PROJ-123/
```

---

#### **Important Notes**

1. To generate a Jira API token, follow these steps:
   - Go to [Jira API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
   - Click **Create API token**.
   - Enter a label for your token (e.g., `My Jira Token`) and click **Create**.
   - Copy the token displayed on the screen (it will not be shown again).
   - Use this token in your API requests.
2. Ensure that the Jira API token has the necessary permissions to access the specified project.
3. The `project_key` must correspond to an existing project in the provided Jira domain.
4. If `start_date` and `end_date` aren't specified, all available issues will be mined.
5. If no `issuetypes` are specified, all issue types will be mined.
6. Dates must be in "yyyy-MM-dd" or "yyyy-MM-dd HH:mm" format.
7. The start and end dates provided by the user during the request are interpreted in the timezone of the Jira project being mined.

## Data Storage

After mining is complete, the data is:

1. **Stored in PostgreSQL**: You can access the data locally in two ways:
   
   a. Using the terminal with the same credentials configured in the `.env` file:
   ```bash
   psql -h localhost -U your_user -d database_name
   ```
   
   b. Using pgAdmin:
   - Open pgAdmin
   - Right-click on "Servers" > "Register" > "Server"
   - In the "General" tab, give your connection a name
   - In the "Connection" tab, fill in:
     - Host: localhost
     - Port: 5432
     - Database: your POSTGRES_DB value from .env
     - Username: your POSTGRES_USER value from .env
     - Password: your POSTGRES_PASSWORD value from .env

2. **Returned as JSON**: A JSON response is immediately provided for viewing the collected data.

## Testing the API

To quickly test the API, you can use the `example/user_test.py` script provided in the repository:

```bash
python example/user_test.py
```

This script will make a series of test requests to verify the data mining functionality.

## Important Note

- PostgreSQL must be running on the default port 5432.

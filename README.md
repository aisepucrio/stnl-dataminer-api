# Diggit

## Description

This is a Django-based API designed for mining and analyzing software development data, enabling the extraction of valuable insights from GitHub repositories and Jira projects. The tool provides detailed tracking of the project lifecycle, including commit analysis, pull requests, issues, and branches, offering critical insights into the development process.

## Features

1. **GitHub Mining**: Extract data from commits, pull requests, issues, and branches.
2. **Jira Mining**: Extract data from Jira issues.
3. **Temporal Analysis**: Monitor project evolution over time.
4. **Documented API**: Endpoints documented using DRF Spectacular.

## Requirements

Before starting, make sure you have the following programs installed:

### 1. Docker
- **Windows**:
  1. Download [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
  2. Run the installer
  3. If prompted, enable WSL 2 (Windows Subsystem for Linux)
  4. Restart your computer after installation
  5. Verify the installation by opening terminal and typing: `docker --version`

- **macOS**:
  1. Download [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
  2. Drag Docker to Applications folder
  3. Open Docker and allow installation of additional components
  4. Verify the installation by opening terminal and typing: `docker --version`

- **Linux (Ubuntu)**:
  ```bash
  sudo apt update
  sudo apt install docker.io
  sudo systemctl start docker
  sudo systemctl enable docker
  sudo usermod -aG docker $USER
  # Logout and login again
  docker --version
  ```

### 2. Docker Compose
- **Windows/macOS**: 
  - Already included in Docker Desktop

- **Linux**:
  ```bash
  sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  docker-compose --version
  ```

### 3. PostgreSQL
- **Windows**:
  1. Download the [PostgreSQL installer](https://www.postgresql.org/download/windows/)
  2. Run the installer
  3. Select components (at least "Server" and "pgAdmin")
  4. Set a password for postgres user
  5. Keep the default port (5432)
  6. Verify installation by opening pgAdmin

- **macOS**:
  ```bash
  brew install postgresql
  brew services start postgresql
  psql --version
  ```

- **Linux (Ubuntu)**:
  ```bash
  sudo apt update
  sudo apt install postgresql postgresql-contrib
  sudo systemctl start postgresql
  sudo systemctl enable postgresql
  psql --version
  ```

### 4. Git
- **Windows**:
  1. Download [Git for Windows](https://git-scm.com/download/win)
  2. Run the installer
  3. Keep default options during installation
  4. Verify installation: `git --version`

- **macOS**:
  ```bash
  brew install git
  git --version
  ```

- **Linux (Ubuntu)**:
  ```bash
  sudo apt update
  sudo apt install git
  git --version
  ```

### Installation Verification

After installing all requirements, you can verify everything is working correctly by running:

```bash
# Verify Docker
docker --version

# Verify Docker Compose
docker-compose --version

# Verify PostgreSQL
psql --version

# Verify Git
git --version
```

If all commands return the program versions, you're ready to proceed with the project installation.

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
   
   Note: For instructions on how to generate your GitHub token, see the [GitHub Token Configuration](#github-token-configuration) section below.

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

All collection requests follow the base format:
```
POST http://localhost:8000/api/github/{endpoint}/collect/
```

All query requests follow the base format:
```
GET http://localhost:8000/api/github/{endpoint}/?{parameters}
```

Where:
- `{endpoint}`: can be commits, issues, pull-requests, branches, or metadata
- `{parameters}`: query parameters for filtering data

#### Collection Endpoints (POST)

1. **Commit Collection**
```http
POST http://localhost:8000/api/github/commits/collect/
Content-Type: application/json

{
    "repo_name": "facebook/react",
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2023-12-31T00:00:00Z"
}
```

2. **Issue Collection**
```http
POST http://localhost:8000/api/github/issues/collect/
Content-Type: application/json

{
    "repo_name": "tensorflow/tensorflow",
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2023-12-31T00:00:00Z",
    "depth": "basic"
}
```

3. **Pull Request Collection**
```http
POST http://localhost:8000/api/github/pull-requests/collect/
Content-Type: application/json

{
    "repo_name": "kubernetes/kubernetes",
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2023-12-31T00:00:00Z",
    "depth": "basic"
}
```

4. **Branch Collection**
```http
POST http://localhost:8000/api/github/branches/collect/
Content-Type: application/json

{
    "repo_name": "django/django"
}
```

5. **Metadata Collection**
```http
POST http://localhost:8000/api/github/metadata/collect/
Content-Type: application/json

{
    "repo_name": "microsoft/vscode"
}
```

#### Query Endpoints (GET)

1. **Query Commits**
```http
GET http://localhost:8000/api/github/commits/?repository=facebook/react&created_after=2023-01-01&created_before=2023-12-31
```

2. **Query Issues**
```http
GET http://localhost:8000/api/github/issues/?repository=tensorflow/tensorflow&state=open&created_after=2023-01-01
```

3. **Query Pull Requests**
```http
GET http://localhost:8000/api/github/pull-requests/?repository=kubernetes/kubernetes&state=merged&created_after=2023-01-01
```

4. **Query Branches**
```http
GET http://localhost:8000/api/github/branches/?repository=django/django
```

5. **Query Metadata**
```http
GET http://localhost:8000/api/github/metadata/?repository=microsoft/vscode
```

#### Request Parameters

Collection Parameters (POST body):
- `repo_name` (required): Repository in format `owner/repository`
- `start_date` (optional): Initial date to filter data (ISO 8601 format)
- `end_date` (optional): Final date to filter data (ISO 8601 format)
- `depth` (optional): Data collection depth ("basic" or "full", default: "basic")

Query Parameters (GET):
- `repository`: Filter by repository name
- `created_after`: Filter items created after date
- `created_before`: Filter items created before date
- `state`: Filter by state (e.g., "open", "closed", "merged")
- `per_page`: Number of items per page (default: 100)
- `page`: Page number for pagination (default: 1)

#### Response Format

Collection endpoints return:
```json
{
    "task_id": "task-uuid",
    "message": "Task successfully initiated",
    "status_endpoint": "http://localhost:8000/api/jobs/task/task-uuid/"
}
```

Query endpoints return paginated lists of items in JSON format.

#### Important Notes

1. All dates must be in ISO 8601 format: `YYYY-MM-DDTHH:mm:ssZ`
2. Collection endpoints return 202 Accepted status code
3. Query endpoints return 200 OK status code
4. The repository must be public or your token must have access to it
5. For large repositories, consider using smaller date ranges
6. Branch and metadata endpoints don't require date parameters

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

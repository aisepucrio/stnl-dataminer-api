# Diggit

## Description

This is a Django-based API designed for mining and analyzing software development data, enabling the extraction of valuable insights from GitHub and Jira repositories. The tool provides detailed tracking of the project lifecycle, including commit analysis, pull requests, issues, and branches, offering critical insights into the development process.

## Features

1. **GitHub Mining**: Extract data from commits, pull requests, issues, and branches.
2. **Jira Integration**: Collect ticket and sprint data.
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

## Using the API

The API provides various endpoints for data mining. To test the endpoints, we recommend using one of the following tools:

- [Postman](https://www.postman.com/downloads/) - Popular GUI for API testing
- [Bruno](https://www.usebruno.com/) - Open source alternative to Postman

### Basic Request Structure

All requests follow the base format:
```
http://localhost:8000/api/github/{endpoint}/?repo_name={owner}/{repository}&start_date={start_date}&end_date={end_date}
```

Where:
- `{endpoint}`: can be commits, issues, pull-requests, or branches
- `{owner}`: repository owner/organization
- `{repository}`: repository name
- `{start_date}` and `{end_date}`: dates in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ)

### Request Examples

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

### Query Parameters

- `repo_name` (required): In the format `owner/repository` (e.g., `microsoft/vscode`)
- `start_date` (optional): Initial date to filter data
- `end_date` (optional): Final date to filter data
- `per_page` (optional): Number of items per page (default: 100)
- `page` (optional): Page number for pagination (default: 1)

### Important Notes

1. Dates must be in ISO 8601 format: `YYYY-MM-DDTHH:mm:ssZ`
2. The repository must be public or your token must have access to it
3. For large repositories, consider using smaller date ranges to avoid timeout
4. Branch mining doesn't require date parameters

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

## Testing the API

To quickly test the API, you can use the `example/user_test.py` script provided in the repository:

```bash
python example/user_test.py
```

This script will make a series of test requests to verify the data mining functionality.

## Important Notes

- Ensure your GitHub token has the necessary permissions to access the desired repositories.
- PostgreSQL must be running on the default port 5432.
- All timestamps must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ).

## Using the API

The API provides various endpoints for data mining. To test the endpoints, we recommend using one of the following tools:

- [Postman](https://www.postman.com/downloads/) - Popular GUI for API testing
- [Bruno](https://www.usebruno.com/) - Open source alternative to Postman

The examples below use the `esp8266/Arduino` repository as a demonstration...
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
   git clone https://github.com/your_user/dataminer-api.git
   cd dataminer-api
   ```

2. **Configure the .env File**

   Create a `.env` file at the root of the project with the following information:
   ```
   GITHUB_TOKENS=your_github_token
   POSTGRES_DB=database_name
   POSTGRES_USER=postgres_user
   POSTGRES_PASSWORD=postgres_password
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   ```

3. **Verify the Line Format of `start.sh`**

   Open the `start.sh` file in your IDE and confirm that the line format is set to LF (this is usually visible at the bottom-right corner of the IDE). If it shows CRLF, change it to LF.

4. **Check for Existing Database or Server Conflicts**

   Ensure that no other database or server is already running on port 5432, as this will prevent the new database from being created and saving data correctly. Stop any conflicting processes before proceeding.

5. **Start the Containers**
   ```bash
   docker-compose up --build
   ```

## Using the API

The API provides various endpoints for data mining. The examples below use the `esp8266/Arduino` repository as a demonstration, but you can replace it with any public GitHub repository by adjusting the `repo_name` parameter. Similarly, the date range (`start_date` and `end_date`) can be adjusted as needed.

### 1. Commit Mining
```
GET http://localhost:8000/api/github/commits/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 2. Issue Mining
```
GET http://localhost:8000/api/github/issues/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 3. Pull Request Mining
```
GET http://localhost:8000/api/github/pull-requests/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 4. Branch Mining
```
GET http://localhost:8000/api/github/branches/?repo_name=esp8266/Arduino
```

## Data Storage

After mining is complete, the data is:

1. **Stored in PostgreSQL**: You can access the data locally using the same credentials configured in the `.env` file. For example:
   ```bash
   psql -h localhost -U your_user -d database_name
   ```

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

To quickly test the API, you can use the `user_test.py` script provided in the repository:

```bash
python user_test.py
```

This script will make a series of test requests to verify the data mining functionality.

## Important Notes

- Ensure your GitHub token has the necessary permissions to access the desired repositories.
- PostgreSQL must be running on the default port 5432.
- All timestamps must be in ISO 8601 format (YYYY-MM-DDTHH:mm:ssZ).

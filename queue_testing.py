import time
import requests

class SequentialAPITest:
    def __init__(self, base_url, interval_seconds):
        """
        Initializes the test requester with the base URL of the API and the interval between requests.
        """
        self.base_url = base_url
        self.interval_seconds = interval_seconds

    def fetch_commits(self, repo_name, start_date=None, end_date=None):
        """
        Sends a request to fetch commits from the specified repository within the date range.
        """
        url = f"{self.base_url}/api/github/commits/"
        params = {
            "repo_name": repo_name,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code in [200, 202]:
                print(f"Commits for {repo_name}:", response.json())
            else:
                print(f"Request for {repo_name} failed with status {response.status_code}: {response.text}")
        except requests.RequestException as e:
            print(f"An error occurred for {repo_name}:", e)

    def start_sequential_requests(self, repositories, start_date=None, end_date=None):
        """
        Starts sending requests for each repository in the list with a delay between requests.
        """
        for repo_name in repositories:
            print(f"Fetching commits for repository: {repo_name}")
            self.fetch_commits(repo_name, start_date, end_date)
            print(f"Waiting {self.interval_seconds} seconds before the next request...")
            time.sleep(self.interval_seconds)


if __name__ == "__main__":
    base_url = "http://localhost:8000"  
    interval_seconds = 2 

    repositories = [
        "grafana/github-datasource",
        "esp8266/Arduino",
    ]
    
    start_date = "2022-11-01T00:00:00Z"  
    end_date = "2023-12-29T00:00:00Z"    

    api_tester = SequentialAPITest(base_url, interval_seconds)
    api_tester.start_sequential_requests(repositories, start_date, end_date)

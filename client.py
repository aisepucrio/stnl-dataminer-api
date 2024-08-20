import requests
import json

class GitHubMinerClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_commits(self, repo_name, start_date=None, end_date=None):
        url = f"{self.base_url}/commits/"
        params = {
            "repo_name": repo_name,
            "start_date": start_date,
            "end_date": end_date
        }
        response = requests.get(url, params=params)
        return self.process_response(response)

    def get_issues(self, repo_name, start_date=None, end_date=None):
        url = f"{self.base_url}/issues/"
        params = {
            "repo_name": repo_name,
            "start_date": start_date,
            "end_date": end_date
        }
        response = requests.get(url, params=params)
        return self.process_response(response)

    def get_pull_requests(self, repo_name, start_date=None, end_date=None):
        url = f"{self.base_url}/pull-requests/"
        params = {
            "repo_name": repo_name,
            "start_date": start_date,
            "end_date": end_date
        }
        response = requests.get(url, params=params)
        return self.process_response(response)

    def get_branches(self, repo_name):
        url = f"{self.base_url}/branches/"
        params = {"repo_name": repo_name}
        response = requests.get(url, params=params)
        return self.process_response(response)

    def process_response(self, response):
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            return None

    def save_to_json(self, data, filename):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to {filename}")

if __name__ == "__main__":
    base_url = "http://127.0.0.1:8000/api/github"
    repo_name = "aisepucrio/stnl-dataminer"
    start_date = "2024-01-01"
    end_date = "2024-01-31"

    client = GitHubMinerClient(base_url)

    print("Mining commits...")
    commits = client.get_commits(repo_name, start_date, end_date)
    if commits:
        client.save_to_json(commits, "commits.json")

    '''
    
        print("Mining issues...")
    issues = client.get_issues(repo_name, start_date, end_date)
    if issues:
        client.save_to_json(issues, "issues.json")

    print("Mining pull requests...")
    pull_requests = client.get_pull_requests(repo_name, start_date, end_date)
    if pull_requests:
        client.save_to_json(pull_requests, "pull_requests.json")

    print("Mining branches...")
    branches = client.get_branches(repo_name)
    if branches:
        client.save_to_json(branches, "branches.json")

    print("Mining completed.")
    
    '''
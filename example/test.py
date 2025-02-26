import requests

def get_repo_readme(owner: str, repo: str, headers: dict = None):
    
    if headers is None:
        headers = {}
    
    url = f'https://api.github.com/repos/{owner}/{repo}/readme'
    headers = {**headers, 'Accept': 'application/vnd.github.v3.raw'}
    response = requests.get(url, headers=headers)
    return response.text if response.status_code == 200 else None

print(get_repo_readme('grafana', 'grafana'))

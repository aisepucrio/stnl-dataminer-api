import requests
import json
from datetime import datetime
import time
import os
from dotenv import load_dotenv

class APIMetrics:
    def __init__(self):
        self.execution_start = time.time()
        self.total_requests = 0
        self.total_prs_collected = 0
        self.pages_processed = 0
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.rate_limit_limit = None
        self.requests_used = None
        self.average_time_per_request = 0
    
    def update_rate_limit(self, headers):
        """Updates rate limit information based on response headers"""
        # Para a Search API
        self.rate_limit_remaining = headers.get('X-RateLimit-Remaining')
        self.rate_limit_reset = headers.get('X-RateLimit-Reset')
        self.rate_limit_limit = headers.get('X-RateLimit-Limit', 30)  # Search API tem limite de 30/minuto
        
        if self.rate_limit_limit and self.rate_limit_remaining:
            self.requests_used = int(self.rate_limit_limit) - int(self.rate_limit_remaining)
        
        # Calcular tempo médio por requisição
        if self.total_requests > 0:
            total_time = time.time() - self.execution_start
            self.average_time_per_request = total_time / self.total_requests

    def format_reset_time(self):
        """Converte o timestamp Unix para formato legível"""
        if self.rate_limit_reset:
            try:
                reset_time = datetime.fromtimestamp(int(self.rate_limit_reset))
                return reset_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return "Unknown"
        return "Unknown"

    def get_execution_time(self):
        """Calculate execution time metrics"""
        total_time = time.time() - self.execution_start
        return {
            "seconds": round(total_time, 2),
            "formatted": f"{int(total_time // 60)}min {int(total_time % 60)}s"
        }
    
    def generate_report(self):
        execution_time = self.get_execution_time()
        return {
            "total_prs_collected": self.total_prs_collected,
            "pages_processed": self.pages_processed,
            "total_requests": self.total_requests,
            "execution_time_formatted": execution_time["formatted"],
            "average_time_per_request": round(self.average_time_per_request, 2),
            "api_rate_limit": {
                "total_limit": self.rate_limit_limit,
                "remaining": self.rate_limit_remaining,
                "used_in_session": self.requests_used,
                "reset_time": self.format_reset_time()
            }
        }

def fetch_prs_with_pagination(repo, start_date, end_date, token):
    """
    Fetches PRs from repository with pagination
    """
    metrics = APIMetrics()
    base_url = "https://api.github.com/search/issues"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    
    all_prs = []
    page = 1
    has_more_pages = True
    
    while has_more_pages:
        request_start = time.time()
        query = f"repo:{repo} is:pr created:{start_date}..{end_date}"
        
        params = {
            'q': query,
            'per_page': 100,
            'page': page
        }
        
        try:
            print(f"\n[Page {page}] Starting search...")
            print(f'URL: {base_url}\nParams: {params}\nHeaders: {headers}\n')
            print(f'Full URL: {base_url}?q={query}&per_page=100&page={page}')
            response = requests.get(base_url, params=params, headers=headers)
            metrics.total_requests += 1
            metrics.pages_processed += 1
            
            # Update rate limit metrics and show current usage
            metrics.update_rate_limit(response.headers)
            print(f"[API Usage] Requests remaining: {metrics.rate_limit_remaining}/{metrics.rate_limit_limit}")
            print(f"[API Usage] Requests used in this session: {metrics.requests_used}")
            
            request_time = time.time() - request_start
            print(f"[Page {page}] Response time: {request_time:.2f}s")
            
            if response.status_code != 200:
                print(f"Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                break
                
            data = response.json()
            
            if data['items']:
                all_prs.extend(data['items'])
                metrics.total_prs_collected += len(data['items'])
                print(f"[Page {page}] Found {len(data['items'])} PRs")
                print(f"Rate limit remaining: {metrics.rate_limit_remaining}")
                
                if len(data['items']) < 100:
                    has_more_pages = False
                else:
                    page += 1
            else:
                has_more_pages = False
            
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            break
            
    return all_prs, metrics

def save_json(data, metrics, filename, repo, start_date, end_date):
    """
    Saves data and metrics to a JSON file
    
    Parameters:
        data: List of PRs
        metrics: APIMetrics object
        filename: Output file name
        repo: Repository name
        start_date: Start date of extraction
        end_date: End date of extraction
    """
    try:
        # Process PR data to ensure English fields
        processed_prs = []
        for pr in data:
            processed_pr = {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "closed_at": pr.get("closed_at"),
                "merged_at": pr.get("merged_at"),
                "author": pr["user"]["login"],
                "labels": [label["name"] for label in pr["labels"]],
                "comments_count": pr["comments"],
                "review_comments_count": pr.get("review_comments", 0),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "changed_files": pr.get("changed_files", 0),
                "url": pr["html_url"],
                "api_url": pr["url"]
            }
            processed_prs.append(processed_pr)

        execution_time = metrics.get_execution_time()
        
        output = {
            "metadata": {
                "repository": repo,
                "start_date": start_date,
                "end_date": end_date,
                "extraction_timestamp": datetime.now().isoformat(),
                "metrics": {
                    "execution_time": execution_time,
                    "api_usage": {
                        "total_requests": metrics.total_requests,
                        "total_prs_collected": metrics.total_prs_collected,
                        "pages_processed": metrics.pages_processed,
                        "average_request_time": f"{round(metrics.average_time_per_request, 2)}s",
                        "rate_limit": {
                            "total": metrics.rate_limit_limit,
                            "remaining": metrics.rate_limit_remaining,
                            "used_in_session": metrics.requests_used,
                            "reset_time": metrics.format_reset_time()
                        }
                    }
                }
            },
            "pull_requests": processed_prs
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nData successfully saved to {filename}")
        
    except Exception as e:
        print(f"Error saving file: {e}")

def validate_token(token):
    """Validates GitHub token and shows rate limit info"""
    url = "https://api.github.com/rate_limit"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 401:
            print("Erro de autenticação: Token inválido ou mal formatado")
            return False
            
        if response.status_code != 200:
            print(f"Erro na API: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
        data = response.json()
        
        # Acessando os dados corretos da estrutura
        rate = data['resources']['core']  # Mudança aqui
        search = data['resources']['search']  # Mudança aqui
        
        print("\n=== GitHub API Token Status ===")
        print("Core API:")
        print(f"  Limite total: {rate['limit']}")
        print(f"  Restantes: {rate['remaining']}")
        print(f"  Reset em: {datetime.fromtimestamp(rate['reset']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\nSearch API:")
        print(f"  Limite total: {search['limit']}")
        print(f"  Restantes: {search['remaining']}")
        print(f"  Reset em: {datetime.fromtimestamp(search['reset']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if rate['limit'] < 1000:
            print("\nAVISO: Token parece não estar autenticado ou é inválido!")
            print("Tokens autenticados devem ter limite de 5000 requisições/hora")
            return False
                
        return True
        
    except Exception as e:
        print(f"Erro ao validar token: {e}")
        return False

def main():
    # Load environment variables
    load_dotenv()
    
    # Configuration
    repo = "elastic/elasticsearch"
    start_date = "2024-01-01"
    end_date = "2025-01-15"
    output_file = f"{repo.split('/')[1]}_prs.json"
    token = os.getenv("GITHUB_TOKENS").strip('"')
    
    if not token:
        print("ERROR: GitHub token not found in environment variables!")
        return
    
    # Para debug - mostra o token sem as aspas
    print(f"Token lido (início/fim): {token[:5]}...{token[-5:]}")
    
    # Validate token before starting
    print("Validating GitHub token...")
    if not validate_token(token):
        print("ERROR: Invalid or unauthorized token!")
        print("Please check your token and make sure it has the necessary permissions")
        return
    
    print(f"\nStarting PR extraction for {repo}")
    print(f"Period: {start_date} to {end_date}")
    
    # Fetch PRs with metrics
    prs, metrics = fetch_prs_with_pagination(repo, start_date, end_date, token)
    
    # Save results with all necessary parameters
    save_json(prs, metrics, output_file, repo, start_date, end_date)
    
    # Print final report
    report = metrics.generate_report()
    print("\nExtraction Complete!")
    print("=== Final Report ===")
    print(f"Total PRs collected: {report['total_prs_collected']}")
    print(f"Pages processed: {report['pages_processed']}")
    print(f"Total requests made: {report['total_requests']}")
    print(f"Total execution time: {report['execution_time_formatted']}")
    print(f"Average time per request: {report['average_time_per_request']}s")
    print("\n=== API Usage ===")
    print(f"Total API limit: {report['api_rate_limit']['total_limit']}")
    print(f"Remaining requests: {report['api_rate_limit']['remaining']}")
    print(f"Used in this session: {report['api_rate_limit']['used_in_session']}")
    print(f"Rate limit resets at: {report['api_rate_limit']['reset_time']}")

if __name__ == "__main__":
    main()

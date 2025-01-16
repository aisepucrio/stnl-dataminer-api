import requests
import json
from datetime import datetime, timedelta
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
            response = requests.get(base_url, params=params, headers=headers)
            metrics.total_requests += 1
            metrics.pages_processed += 1
            
            metrics.update_rate_limit(response.headers)
            print(f"[API Usage] Requests remaining: {metrics.rate_limit_remaining}/{metrics.rate_limit_limit}")
            
            if response.status_code != 200:
                print(f"Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                break
                
            data = response.json()
            
            if data['items']:
                for pr in data['items']:
                    pr_number = pr['number']
                    
                    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
                    pr_response = requests.get(pr_url, headers=headers)
                    metrics.total_requests += 1
                    
                    if pr_response.status_code == 200:
                        pr_details = pr_response.json()
                        
                        commits_url = f"{pr_url}/commits"
                        commits_response = requests.get(commits_url, headers=headers)
                        metrics.total_requests += 1
                        commits = []
                        if commits_response.status_code == 200:
                            commits = [{'sha': c['sha'], 'message': c['commit']['message']} 
                                     for c in commits_response.json()]
                        
                        comments_url = f"{pr_url}/comments"
                        comments_response = requests.get(comments_url, headers=headers)
                        metrics.total_requests += 1
                        comments = []
                        if comments_response.status_code == 200:
                            comments = [{'user': c['user']['login'], 'body': c['body']} 
                                      for c in comments_response.json()]
                        
                        pr_details['commits_data'] = commits
                        pr_details['comments_data'] = comments
                        all_prs.append(pr_details)
                        
                        print(f"Collected detailed information for PR #{pr_number}")
                    
                    time.sleep(1) 
                
                metrics.total_prs_collected += len(data['items'])
                print(f"[Page {page}] Found {len(data['items'])} PRs")
                
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
                "api_url": pr["url"],
                "commits": pr.get("commits_data", []),
                "comments": pr.get("comments_data", []),
                "body": pr.get("body", ""),
                "base_ref": pr.get("base", {}).get("ref", ""),
                "head_ref": pr.get("head", {}).get("ref", ""),
                "mergeable": pr.get("mergeable", None),
                "mergeable_state": pr.get("mergeable_state", None),
                "review_comments_url": pr.get("review_comments_url", "")
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

def split_date_range(start_date, end_date, interval_days=1):
    """
    Divide o intervalo de datas em períodos menores
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    current = start
    while current < end:
        interval_end = min(current + timedelta(days=interval_days), end)
        yield (
            current.strftime("%Y-%m-%d"),
            interval_end.strftime("%Y-%m-%d")
        )
        current = interval_end + timedelta(days=1)

def main():
    # Load environment variables
    load_dotenv()
    
    # Configuração centralizada
    config = {
        "repo": "elastic/elasticsearch",
        "start_date": "2024-01-09",
        "end_date": "2024-01-16",
        "interval_days": 1, 
        "query_template": "repo:{repo} is:pr created:{start_date}..{end_date} label:>test",
        "output_file": None  
    }
    
    # Gerar nome do arquivo de saída baseado no repositório
    config["output_file"] = f"{config['repo'].split('/')[1]}_prs.json"
    
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
    
    print(f"\nStarting PR extraction for {config['repo']}")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    
    all_prs = []
    total_metrics = APIMetrics()
    
    print(f"\nIniciando extração de PRs para {config['repo']}")
    print(f"Período total: {config['start_date']} até {config['end_date']}")
    
    # Dividir em períodos menores usando o interval_days da config
    for period_start, period_end in split_date_range(
        config['start_date'], 
        config['end_date'], 
        config['interval_days']
    ):
        print(f"\nProcessando período: {period_start} até {period_end}")
        
        period_prs, period_metrics = fetch_prs_with_pagination(
            config['repo'], period_start, period_end, token
        )
        
        all_prs.extend(period_prs)
        total_metrics.total_prs_collected += period_metrics.total_prs_collected
        total_metrics.total_requests += period_metrics.total_requests
        total_metrics.pages_processed += period_metrics.pages_processed
        
        # Atualizar métricas da API
        total_metrics.rate_limit_remaining = period_metrics.rate_limit_remaining
        total_metrics.rate_limit_limit = period_metrics.rate_limit_limit
        total_metrics.requests_used = period_metrics.requests_used
        
        print(f"PRs encontrados neste período: {len(period_prs)}")
        
        # Verificar limite de API e aguardar se necessário
        if period_metrics.rate_limit_remaining and int(period_metrics.rate_limit_remaining) < 5:
            reset_time = datetime.fromtimestamp(int(period_metrics.rate_limit_reset))
            wait_time = (reset_time - datetime.now()).total_seconds() + 10
            print(f"\nAguardando reset do limite de API: {wait_time:.0f} segundos")
            time.sleep(max(0, wait_time))
    
    # Salvar todos os resultados
    save_json(all_prs, total_metrics, config['output_file'], config['repo'], 
             config['start_date'], config['end_date'])
    
    # Print final report
    report = total_metrics.generate_report()
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

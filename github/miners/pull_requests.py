import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.utils import timezone

from .base import BaseMiner
from .utils import APIMetrics, split_date_range
from ..models import GitHubIssuePullRequest, GitHubMetadata


class PullRequestsMiner(BaseMiner):
    """Specialized miner for GitHub pull requests extraction"""

    def get_pull_requests(self, repo_name: str, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None, depth: str = 'basic', task_obj=None) -> List[Dict[str, Any]]:
        """
        Extract pull requests from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            depth: Extraction depth ('basic' or 'complex')
            task_obj: Task object for progress updates (optional)
            
        Returns:
            List of extracted pull request data
        """
        all_prs = []
        metrics = APIMetrics()
        total_prs_count = 0
        processed_count = 0
        debug_buffer = []  
        
        def log_progress(message: str) -> None:
            """Log progress message and update task if available"""
            print(message, flush=True)
            if task_obj:
                task_obj.operation = message
                task_obj.save(update_fields=["operation"])
        
        def log_debug(pr_number: int, message: str) -> None:
            """Adds a debug message to the buffer"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            debug_buffer.append(f"[{timestamp}][PRs][DEBUG][PR #{pr_number}] {message}")

        def log_error(pr_number: int, message: str, error: Optional[Exception] = None) -> None:
            """Logs error and prints immediately"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_message = f"[{timestamp}][PRs][ERROR][PR #{pr_number}] {message}"
            if error:
                error_message += f"\nDetails: {str(error)}"
            log_progress(error_message)

        def flush_debug_logs() -> None:
            """Prints and clears the debug log buffer"""
            if debug_buffer:
                log_progress("\n=== Debug Logs ===")
                log_progress('\n'.join(debug_buffer))
                log_progress("=================\n")
                debug_buffer.clear()

        log_progress(f"🔍 STARTING PULL REQUEST EXTRACTION: {repo_name}")
        log_progress(f"📅 Period: {start_date or 'start'} to {end_date or 'current'}")
        log_progress(f"🔎 Depth: {depth.upper()}")

        try:
            log_progress("Verificando o total de pull requests a serem minerados...")
            
            for period_start, period_end in split_date_range(start_date, end_date):
                query = f"repo:{repo_name} is:pr"
                if period_start:
                    query += f" created:{period_start}"
                if period_end:
                    query += f"..{period_end}"

                params = {
                    'q': query,
                    'per_page': 1,  
                    'page': 1
                }

                response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)
                metrics.total_requests += 1
                
                if response.status_code == 403 and 'rate limit' in response.text.lower():
                    if not self.handle_rate_limit(response):
                        log_progress("Failed to recover after rate limit during preflight check")
                        continue
                    response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    period_total = data.get('total_count', 0)
                    total_prs_count += period_total
                    log_progress(f"Período {period_start} a {period_end}: {period_total} pull requests encontrados")
                else:
                    log_progress(f"Erro na pré-verificação do período {period_start} a {period_end}: {response.status_code}")

            log_progress(f"Total de {total_prs_count} pull requests encontrados. Iniciando a coleta.")

            for period_start, period_end in split_date_range(start_date, end_date):
                log_progress(f"📊 Processing period: {period_start} to {period_end}")
                
                base_url = "https://api.github.com/search/issues"
                page = 1
                has_more_pages = True

                while has_more_pages:
                    query = f"repo:{repo_name} is:pr"
                    if period_start:
                        query += f" created:{period_start}"
                    if period_end:
                        query += f"..{period_end}"

                    params = {
                        'q': query,
                        'per_page': 100,
                        'page': page
                    }

                    log_progress(f"📝 Page {page}: Starting search...")

                    response = requests.get(base_url, params=params, headers=self.headers)
                    metrics.total_requests += 1
                    
                    if response.status_code == 403 and 'rate limit' in response.text.lower():
                        if not self.handle_rate_limit(response):
                            log_progress("Failed to recover after rate limit")
                            break
                        response = requests.get(base_url, params=params, headers=self.headers)

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        log_progress("No PRs found on this page.")
                        break

                    prs_in_page = len(data['items'])
                    log_progress(f"📝 Page {page}: Processing {prs_in_page} pull requests...")

                    for index, pr in enumerate(data['items']):
                        current_timestamp = timezone.now()
                        processed_count += 1
                        
                        pr_number = pr['number']
                        
                        if total_prs_count > 0:
                            log_progress(f"Mining pull request {processed_count} of {total_prs_count}. Key: #{pr_number} - {pr['title']}")
                        else:
                            log_progress(f"Mining pull request #{pr_number} - {pr['title']}")
                        
                        pr_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
                        pr_response = requests.get(pr_url, headers=self.headers)
                        metrics.total_requests += 1
                        
                        if pr_response.status_code == 403 and 'rate limit' in pr_response.text.lower():
                            if not self.handle_rate_limit(pr_response):
                                log_error(pr_number, "Failed to recover after rate limit")
                                continue
                            pr_response = requests.get(pr_url, headers=self.headers)
                        
                        if pr_response.status_code != 200:
                            log_error(pr_number, f"Failed to get PR details: {pr_response.status_code}")
                            continue
                        
                        pr_details = pr_response.json()
                        
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{pr_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        metrics.total_requests += 1
                        
                        timeline_events = []
                        if timeline_response.status_code == 403 and 'rate limit' in timeline_response.text.lower():
                            if not self.handle_rate_limit(timeline_response, 'core'):
                                log_error(pr_number, "Failed to recover timeline after rate limit")
                                continue
                            timeline_response = requests.get(timeline_url, headers=headers)
                        
                        if timeline_response.status_code == 200:
                            timeline_events = [{
                                'event': event.get('event'),
                                'actor': event.get('actor', {}).get('login') if event.get('actor') else None,
                                'created_at': event.get('created_at'),
                                'assignee': event.get('assignee', {}).get('login') if event.get('assignee') else None,
                                'label': event.get('label', {}).get('name') if event.get('label') else None
                            } for event in timeline_response.json()]

                        comments = []
                        if depth == 'complex':
                            comments_url = pr['comments_url']
                            comments_response = requests.get(comments_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                if not self.handle_rate_limit(comments_response, 'core'):
                                    log_error(pr_number, "Failed to retrieve comments after rate limit")
                                    continue
                                comments_response = requests.get(comments_url, headers=self.headers)
                            
                            if comments_response.status_code == 200:
                                comments = [{
                                    'id': c['id'],
                                    'user': c['user']['login'],
                                    'body': c['body'],
                                    'created_at': c['created_at'],
                                    'updated_at': c['updated_at'],
                                    'author_association': c['author_association'],
                                    'reactions': c.get('reactions', {})
                                } for c in comments_response.json()]

                        processed_pr = {
                            'id': pr['id'],
                            'number': pr['number'],
                            'title': pr['title'],
                            'state': pr['state'],
                            'locked': pr['locked'],
                            'assignees': [assignee['login'] for assignee in pr['assignees']],
                            'labels': [label['name'] for label in pr['labels']],
                            'milestone': pr['milestone']['title'] if pr['milestone'] else None,
                            'created_at': pr['created_at'],
                            'updated_at': pr['updated_at'],
                            'closed_at': pr['closed_at'],
                            'author_association': pr['author_association'],
                            'body': pr['body'],
                            'reactions': pr.get('reactions', {}),
                            'is_pull_request': True,
                            'timeline_events': timeline_events,
                            'comments_data': comments if depth == 'complex' else [],
                            'time_mined': current_timestamp,
                            'data_type': 'pull_request',
                            'merged_at': pr_details.get('merged_at'),
                            'commits_data': []  
                        }

                        metadata_obj = GitHubMetadata.objects.filter(repository=repo_name).first()
                        if metadata_obj is None:
                            log_error(pr_number, f"GitHubMetadata not found for {repo_name}. Skipping PR.")
                            continue

                        GitHubIssuePullRequest.objects.update_or_create(
                            record_id=processed_pr['id'],
                            defaults={
                                'repository': metadata_obj,
                                'repository_name': repo_name,
                                'number': processed_pr['number'],
                                'title': processed_pr['title'],
                                'state': processed_pr['state'],
                                'creator': pr['user']['login'],
                                'assignees': processed_pr['assignees'],
                                'labels': processed_pr['labels'],
                                'milestone': processed_pr['milestone'],
                                'locked': processed_pr['locked'],
                                'created_at': processed_pr['created_at'],
                                'updated_at': processed_pr['updated_at'],
                                'closed_at': processed_pr['closed_at'],
                                'body': processed_pr['body'],
                                'comments': processed_pr.get('comments_data', []),
                                'timeline_events': processed_pr.get('timeline_events', []),
                                'is_pull_request': True,
                                'author_association': processed_pr['author_association'],
                                'reactions': processed_pr['reactions'],
                                'time_mined': current_timestamp,
                                'data_type': 'pull_request',
                                'merged_at': processed_pr['merged_at'],
                                'commits': processed_pr.get('commits_data', [])
                            }
                        )

                        all_prs.append(processed_pr)

                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

                log_progress(f"✅ Period completed: {len(data['items'])} pull requests collected in {page} pages")

            log_progress(f"✅ Extraction completed! Total pull requests collected: {len(all_prs)}")
            return all_prs

        except Exception as e:
            log_progress(f"❌ Error during extraction: {str(e)}")
            raise RuntimeError(f"Pull request extraction failed: {str(e)}") from e
        finally:
            flush_debug_logs()
            self.verify_token() 
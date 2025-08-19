import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.utils import timezone

from .base import BaseMiner
from .utils import APIMetrics, split_date_range
from ..models import GitHubIssuePullRequest, GitHubIssue, GitHubMetadata


class IssuesMiner(BaseMiner):
    """Specialized miner for GitHub issues extraction"""

    def get_issues(self, repo_name: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, depth: str = 'basic', task_obj=None) -> List[Dict[str, Any]]:
        """
        Extract issues from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            depth: Extraction depth ('basic' or 'complex')
            task_obj: Task object for progress updates (optional)
            
        Returns:
            List of extracted issue data
        """
        all_issues = []
        metrics = APIMetrics()
        total_issues_count = 0
        processed_count = 0
        
        def log_progress(message: str) -> None:
            """Log progress message and update task if available"""
            print(message, flush=True)
            if task_obj:
                task_obj.operation = message
                task_obj.save(update_fields=["operation"])
        
        log_progress(f"🔍 STARTING ISSUE EXTRACTION: {repo_name}")
        log_progress(f"📅 Period: {start_date or 'start'} to {end_date or 'current'}")
        log_progress(f"🔎 Depth: {depth.upper()}")

        try:
            log_progress("Verificando o total de issues a serem mineradas...")
            
            for period_start, period_end in split_date_range(start_date, end_date):
                query = f"repo:{repo_name} is:issue"
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
                    if not self.handle_rate_limit(response, 'search'):
                        log_progress("Failed to recover after rate limit during preflight check")
                        continue
                    response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    period_total = data.get('total_count', 0)
                    total_issues_count += period_total
                    log_progress(f"Período {period_start} a {period_end}: {period_total} issues encontradas")
                else:
                    log_progress(f"Erro na pré-verificação do período {period_start} a {period_end}: {response.status_code}")

            log_progress(f"Total de {total_issues_count} issues encontradas. Iniciando a coleta.")

            for period_start, period_end in split_date_range(start_date, end_date):
                log_progress(f"📊 Processing period: {period_start} to {period_end}")
                
                page = 1
                has_more_pages = True
                period_issues_count = 0

                while has_more_pages:
                    query = f"repo:{repo_name} is:issue"
                    if period_start:
                        query += f" created:{period_start}"
                    if period_end:
                        query += f"..{period_end}"

                    params = {
                        'q': query,
                        'per_page': 100,
                        'page': page
                    }

                    response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)
                    metrics.total_requests += 1

                    if response.status_code == 403 and 'rate limit' in response.text.lower():
                        if not self.handle_rate_limit(response, 'search'):
                            log_progress("Failed to recover after rate limit")
                            break
                        response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                    data = response.json()
                    if not data.get('items'):
                        break

                    issues_in_page = len(data['items'])
                    period_issues_count += issues_in_page
                    log_progress(f"📝 Page {page}: Processing {issues_in_page} issues...")

                    for index, issue in enumerate(data['items']):
                        current_timestamp = timezone.now()
                        processed_count += 1
                        
                        if 'pull_request' in issue:
                            continue

                        issue_number = issue['number']
                        
                        if total_issues_count > 0:
                            log_progress(f"Mining issue {processed_count} of {total_issues_count}. Key: #{issue_number} - {issue['title']}")
                        else:
                            log_progress(f"Mining issue #{issue_number} - {issue['title']}")
                        
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        metrics.total_requests += 1
                        
                        timeline_events = []
                        if timeline_response.status_code == 403 and 'rate limit' in timeline_response.text.lower():
                            if not self.handle_rate_limit(timeline_response, 'core'):
                                log_progress(f"[Issues] Failed to recover timeline #{issue_number} after rate limit")
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
                            comments_url = issue['comments_url']
                            comments_response = requests.get(comments_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                if not self.handle_rate_limit(comments_response, 'core'):
                                    log_progress(f"[Issues] Failed to retrieve comments #{issue_number} after rate limit")
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
                        processed_issue = {
                            'id': issue['id'],
                            'number': issue['number'],
                            'title': issue['title'],
                            'state': issue['state'],
                            'locked': issue['locked'],
                            'assignees': [assignee['login'] for assignee in issue['assignees']],
                            'labels': [label['name'] for label in issue['labels']],
                            'milestone': issue['milestone']['title'] if issue['milestone'] else None,
                            'created_at': issue['created_at'],
                            'updated_at': issue['updated_at'],
                            'closed_at': issue['closed_at'],
                            'author_association': issue['author_association'],
                            'body': issue['body'],
                            'reactions': issue.get('reactions', {}),
                            'is_pull_request': False,
                            'timeline_events': timeline_events,
                            'comments_data': comments if depth == 'complex' else [],
                            'time_mined': current_timestamp,
                            'data_type': 'issue'
                        }

                        existing_issue = None
                        if depth == 'basic':
                            existing_issue = GitHubIssue.objects.filter(issue_id=processed_issue['id']).first()
                            if existing_issue:
                                processed_issue['comments_data'] = existing_issue.comments
                                processed_issue['timeline_events'] = existing_issue.timeline_events

                        metadata_obj = GitHubMetadata.objects.filter(repository=repo_name).first()
                        if metadata_obj is None:
                            log_progress(f"[ISSUES] GitHubMetadata not found for {repo_name}. Skipping.")
                            continue

                        GitHubIssuePullRequest.objects.update_or_create(
                            record_id=processed_issue['id'],
                            defaults={
                                'repository': metadata_obj,
                                'repository_name': repo_name,
                                'number': processed_issue['number'],
                                'title': processed_issue['title'],
                                'state': processed_issue['state'],
                                'creator': issue['user']['login'],
                                'assignees': processed_issue['assignees'],
                                'labels': processed_issue['labels'],
                                'milestone': processed_issue['milestone'],
                                'locked': processed_issue['locked'],
                                'created_at': processed_issue['created_at'],
                                'updated_at': processed_issue['updated_at'],
                                'closed_at': processed_issue['closed_at'],
                                'body': processed_issue['body'],
                                'comments': processed_issue.get('comments_data', existing_issue.comments if existing_issue else []),
                                'timeline_events': processed_issue.get('timeline_events', existing_issue.timeline_events if existing_issue else []),
                                'is_pull_request': False,
                                'author_association': processed_issue['author_association'],
                                'reactions': processed_issue['reactions'],
                                'time_mined': current_timestamp,
                                'data_type': 'issue'  
                            }
                        )

                        all_issues.append(processed_issue)

                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

                log_progress(f"✅ Period completed: {period_issues_count} issues collected in {page} pages")

            log_progress(f"✅ Extraction completed! Total issues collected: {len(all_issues)}")
            return all_issues

        except Exception as e:
            log_progress(f"❌ Error during extraction: {str(e)}")
            raise RuntimeError(f"Issue extraction failed: {str(e)}") from e
        finally:
            self.verify_token() 
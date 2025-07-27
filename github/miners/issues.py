import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.utils import timezone

from .base import BaseMiner
from .utils import APIMetrics, split_date_range
from ..models import GitHubIssuePullRequest, GitHubIssue


class IssuesMiner(BaseMiner):
    """Specialized miner for GitHub issues extraction"""

    def get_issues(self, repo_name: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, depth: str = 'basic') -> List[Dict[str, Any]]:
        """
        Extract issues from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            depth: Extraction depth ('basic' or 'complex')
            
        Returns:
            List of extracted issue data
        """
        all_issues = []
        metrics = APIMetrics()
        
        print("\n" + "="*50)
        print(f"🔍 STARTING ISSUE EXTRACTION: {repo_name}")
        print(f"📅 Period: {start_date or 'start'} to {end_date or 'current'}")
        print(f"🔎 Depth: {depth.upper()}")
        print("="*50 + "\n")

        try:
            for period_start, period_end in split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"📊 Processing period: {period_start} to {period_end}")
                print("-"*40)
                
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
                            print("Failed to recover after rate limit", flush=True)
                            break
                        response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                    data = response.json()
                    if not data.get('items'):
                        break

                    issues_in_page = len(data['items'])
                    period_issues_count += issues_in_page
                    print(f"\n📝 Page {page}: Processing {issues_in_page} issues...")

                    for issue in data['items']:
                        current_timestamp = timezone.now()
                        
                        # Skip pull requests (they appear in issues search)
                        if 'pull_request' in issue:
                            continue

                        issue_number = issue['number']
                        
                        # Get timeline events
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        metrics.total_requests += 1
                        
                        timeline_events = []
                        if timeline_response.status_code == 403 and 'rate limit' in timeline_response.text.lower():
                            if not self.handle_rate_limit(timeline_response, 'core'):
                                print(f"[Issues] Failed to recover timeline #{issue_number} after rate limit", flush=True)
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

                        # Get comments only if complex mining
                        comments = []
                        if depth == 'complex':
                            comments_url = issue['comments_url']
                            comments_response = requests.get(comments_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                if not self.handle_rate_limit(comments_response, 'core'):
                                    print(f"[Issues] Failed to retrieve comments #{issue_number} after rate limit", flush=True)
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

                        # Create object to save in the database
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

                        # Preserve existing data if doing basic mining
                        existing_issue = None
                        if depth == 'basic':
                            existing_issue = GitHubIssue.objects.filter(issue_id=processed_issue['id']).first()
                            if existing_issue:
                                processed_issue['comments_data'] = existing_issue.comments
                                processed_issue['timeline_events'] = existing_issue.timeline_events

                        # Save to database using the unified model
                        GitHubIssuePullRequest.objects.update_or_create(
                            record_id=processed_issue['id'],
                            defaults={
                                'repository': repo_name,
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
                        print(f"✓ Issue #{issue_number} processed", end='\r')

                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

                print(f"\n✅ Period completed: {period_issues_count} issues collected in {page} pages")

            print("\n" + "="*50)
            print(f"Extraction completed! Total issues collected: {len(all_issues)}")
            print("="*50 + "\n")
            return all_issues

        except Exception as e:
            print(f"\n❌ Error during extraction: {str(e)}", flush=True)
            raise RuntimeError(f"Issue extraction failed: {str(e)}") from e
        finally:
            self.verify_token() 
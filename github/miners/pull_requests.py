import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.utils import timezone

from .base import BaseMiner
from .utils import APIMetrics, split_date_range
from ..models import GitHubIssuePullRequest


class PullRequestsMiner(BaseMiner):
    """Specialized miner for GitHub pull requests extraction"""

    def get_pull_requests(self, repo_name: str, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None, depth: str = 'basic') -> List[Dict[str, Any]]:
        """
        Extract pull requests from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            depth: Extraction depth ('basic' or 'complex')
            
        Returns:
            List of extracted pull request data
        """
        all_prs = []
        metrics = APIMetrics()
        debug_buffer = []  # Buffer to accumulate debug messages
        
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
            print(f"\n{error_message}", flush=True)

        def flush_debug_logs() -> None:
            """Prints and clears the debug log buffer"""
            if debug_buffer:
                print("\n=== Debug Logs ===", flush=True)
                print('\n'.join(debug_buffer), flush=True)
                print("=================\n", flush=True)
                debug_buffer.clear()

        print("\n" + "="*50)
        print(f"[PRs] 🔍 STARTING PULL REQUEST EXTRACTION: {repo_name}")
        print(f"[PRs] 📅 Period: {start_date or 'start'} to {end_date or 'current'}")
        print(f"[PRs] 🔎 Depth: {depth.upper()}")
        print("="*50 + "\n")

        try:
            for period_start, period_end in split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"[PRs] 📊 Processing period: {period_start} to {period_end}")
                print("-"*40)
                
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

                    print(f"[PRs] [Page {page}] Starting search...", flush=True)
                    print(f"[PRs] Query: {query}", flush=True)

                    response = requests.get(base_url, params=params, headers=self.headers)
                    metrics.total_requests += 1
                    
                    if response.status_code == 403 and 'rate limit' in response.text.lower():
                        if not self.handle_rate_limit(response):
                            print("[PRs] Failed to recover after rate limit", flush=True)
                            break
                        response = requests.get(base_url, params=params, headers=self.headers)

                    response.raise_for_status()
                    data = response.json()

                    if not data['items']:
                        print("[PRs] No PRs found on this page.", flush=True)
                        break

                    print(f"[PRs] [Page {page}] Found {len(data['items'])} PRs", flush=True)

                    for pr in data.get('items', []):
                        current_timestamp = timezone.now()
                        try:
                            pr_number = pr.get('number')
                            if not pr_number:
                                continue

                            log_debug(pr_number, "Starting processing")
                            
                            # Get PR details
                            pr_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_number}'
                            pr_response = requests.get(pr_url, headers=self.headers)
                            metrics.total_requests += 1
                            
                            if pr_response.status_code == 403 and 'rate limit' in pr_response.text.lower():
                                if self.handle_rate_limit(pr_response, 'core'):
                                    # If a new token is found, try the request again
                                    pr_response = requests.get(pr_url, headers=self.headers)
                                    if pr_response.status_code != 200:
                                        print(f"[PRs] Failed to recover PR #{pr_number} even after token swap", flush=True)
                                        continue
                                else:
                                    print(f"[PRs] Failed to recover PR #{pr_number} after rate limit", flush=True)
                                    continue

                            pr_details = pr_response.json()
                            
                            if not pr_details:
                                log_error(pr_number, "[PRs] Empty PR details")
                                continue
                            log_debug(pr_number, "[PRs] Details successfully obtained")

                            # Basic data that will always be collected
                            processed_pr = {
                                'id': pr_details.get('id'),
                                'number': pr_details.get('number'),
                                'title': pr_details.get('title'),
                                'state': pr_details.get('state'),
                                'created_at': pr_details.get('created_at'),
                                'updated_at': pr_details.get('updated_at'),
                                'closed_at': pr_details.get('closed_at'),
                                'merged_at': pr_details.get('merged_at'),
                                'user': pr_details.get('user', {}).get('login'),
                                'labels': [label.get('name') for label in pr_details.get('labels', []) if label],
                                'body': pr_details.get('body'),
                                'time_mined': current_timestamp,
                                'data_type': 'pull_request'  # Adds the type as 'pull_request'
                            }

                            # Additional data collected only in complex mode
                            if depth == 'complex':
                                # Get commits
                                commits_url = f'{pr_url}/commits'
                                commits_response = requests.get(commits_url, headers=self.headers)
                                metrics.total_requests += 1
                                
                                commits = []
                                if commits_response.status_code == 200:
                                    commits = commits_response.json() or []
                                    log_debug(pr_number, f"[PRs] Commits found: {len(commits)}")

                                # Get comments
                                comments_url = f'{pr_url}/comments'
                                comments_response = requests.get(comments_url, headers=self.headers)
                                metrics.total_requests += 1
                                
                                comments = []
                                if comments_response.status_code == 403 and 'rate limit' in comments_response.text.lower():
                                    if self.handle_rate_limit(comments_response, 'core'):
                                        comments_response = requests.get(comments_url, headers=self.headers)
                                    else:
                                        print(f"[PRs] Failed to recover comments for PR #{pr_number} after rate limit", flush=True)
                                        continue
                                
                                if comments_response.status_code == 200:
                                    comments = comments_response.json() or []
                                    log_debug(pr_number, f"[PRs] Comments found: {len(comments)}")

                                processed_pr.update({
                                    'commits_data': [
                                        {
                                            'sha': c.get('sha'),
                                            'message': c.get('commit', {}).get('message')
                                        } for c in commits
                                    ],
                                    'comments_data': [
                                        {
                                            'user': c.get('user', {}).get('login'),
                                            'body': c.get('body')
                                        } for c in comments
                                    ]
                                })

                            # Preserve existing complex data if doing basic mining
                            if depth == 'basic':
                                existing_pr = GitHubIssuePullRequest.objects.filter(record_id=processed_pr['id']).first()
                                if existing_pr:
                                    # Preserve complex data if it exists
                                    processed_pr['commits'] = existing_pr.commits
                                    processed_pr['comments'] = existing_pr.comments
                                    processed_pr['timeline_events'] = existing_pr.timeline_events

                            # Update or create PR
                            pr_obj, created = GitHubIssuePullRequest.objects.update_or_create(
                                record_id=processed_pr['id'],
                                defaults={
                                    'repository': repo_name,
                                    'number': processed_pr['number'],
                                    'title': processed_pr['title'],
                                    'state': processed_pr['state'],
                                    'creator': processed_pr['user'],
                                    'created_at': processed_pr['created_at'],
                                    'updated_at': processed_pr['updated_at'],
                                    'closed_at': processed_pr['closed_at'],
                                    'merged_at': processed_pr['merged_at'],
                                    'labels': processed_pr['labels'],
                                    'commits': processed_pr.get('commits_data', processed_pr.get('commits', [])),
                                    'comments': processed_pr.get('comments_data', processed_pr.get('comments', [])),
                                    'body': processed_pr.get('body'),
                                    'is_pull_request': True,
                                    'time_mined': current_timestamp,
                                    'data_type': 'pull_request'  # Adds the type as 'pull_request'
                                }
                            )
                            
                            action = 'created' if created else 'updated'
                            log_debug(pr_number, f"PR {action} successfully")

                            all_prs.append(processed_pr)
                            flush_debug_logs()

                        except Exception as e:
                            log_error(pr_number, f"Error processing PR", error=e)
                            continue

                    print(f"[PRs] Progress of current period: {len(all_prs)} PRs collected in {page} pages", flush=True)
                    
                    if len(data['items']) < 100:
                        has_more_pages = False
                    else:
                        page += 1

                    time.sleep(1)

            print("\n" + "="*50)
            print(f"[PRs] Extraction completed! Total PRs collected: {len(all_prs)}")
            print("="*50 + "\n")
            return all_prs

        except Exception as e:
            print(f"[PRs] ❌ Error during extraction: {str(e)}", flush=True)
            raise RuntimeError(f"Failed to extract PRs: {str(e)}") from e
        finally:
            self.verify_token() 
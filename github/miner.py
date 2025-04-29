import os
import requests
import json
from dotenv import load_dotenv
from git import Repo, GitCommandError
from pydriller import Repository
from datetime import datetime, timezone, timedelta
from .models import GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubBranch, GitHubAuthor, GitHubModifiedFile, GitHubMethod, GitHubMetadata, GitHubIssuePullRequest
import time
from bs4 import BeautifulSoup
import base64
from django.utils import timezone

class APIMetrics:
    def __init__(self):
        self.execution_start = time.time()
        self.total_requests = 0
        self.total_prs_collected = 0
        self.pages_processed = 0
        # Core metrics
        self.core_limit_remaining = None
        self.core_limit_reset = None
        self.core_limit_limit = None
        # Search metrics
        self.search_limit_remaining = None
        self.search_limit_reset = None
        self.search_limit_limit = None
        self.requests_used = None
        self.average_time_per_request = 0
    
    def update_rate_limit(self, headers, endpoint_type='core'):
        """
        Updates rate limit information based on response headers
        
        Args:
            headers: Response headers from GitHub API
            endpoint_type: Type of endpoint being accessed ('core' or 'search')
        """
        if endpoint_type == 'search':
            self.search_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.search_limit_reset = headers.get('X-RateLimit-Reset')
            self.search_limit_limit = headers.get('X-RateLimit-Limit', 30)  # Search has a limit of 30/min
            
            if self.search_limit_limit and self.search_limit_remaining:
                self.requests_used = int(self.search_limit_limit) - int(self.search_limit_remaining)
        else:  # core
            self.core_limit_remaining = headers.get('X-RateLimit-Remaining')
            self.core_limit_reset = headers.get('X-RateLimit-Reset')
            self.core_limit_limit = headers.get('X-RateLimit-Limit', 5000)  # Core has a limit of 5000/hour
            
            if self.core_limit_limit and self.core_limit_remaining:
                self.requests_used = int(self.core_limit_limit) - int(self.core_limit_remaining)
        
        if self.total_requests > 0:
            total_time = time.time() - self.execution_start
            self.average_time_per_request = total_time / self.total_requests

    def format_reset_time(self, endpoint_type='core'):
        """Converts the Unix timestamp to a readable format considering the local timezone"""
        reset_time = self.core_limit_reset if endpoint_type == 'core' else self.search_limit_reset
        if reset_time:
            try:
                
                reset_time_utc = datetime.fromtimestamp(int(reset_time), tz=timezone.utc)
                reset_time_local = reset_time_utc.astimezone(timezone(timedelta(hours=-3)))  # Brasília timezone
                
                time_until_reset = reset_time_local - datetime.now().astimezone(timezone(timedelta(hours=-3))) # Same timezone
                seconds_until_reset = int(time_until_reset.total_seconds())
                
                return f"{reset_time_local.strftime('%Y-%m-%d %H:%M:%S')} (in {seconds_until_reset} seconds)"
            except Exception as e:
                print(f"Error formatting reset time: {e}")
                return "Unknown"
        return "Unknown"

    def get_remaining_requests(self, endpoint_type='core'):
        """Returns the number of remaining requests for the specified endpoint type"""
        return (self.core_limit_remaining if endpoint_type == 'core' 
                else self.search_limit_remaining)

    def get_execution_time(self):
        """Calculates execution time metrics"""
        total_time = time.time() - self.execution_start
        return {
            "seconds": round(total_time, 2),
            "formatted": f"{int(total_time // 60)}min {int(total_time % 60)}s"
        }

class GitHubMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.tokens = []
        self.current_token_index = 0
        
        if not self.load_tokens():
            raise Exception("Failed to initialize GitHub tokens. Check your credentials.")
        
        self.update_auth_header()

    def verify_token(self):
        """Verifies if the current token is valid and has proper permissions"""
        try:
            url = "https://api.github.com/rate_limit"
            response = requests.get(url, headers=self.headers)
            metrics = APIMetrics()
            
            if response.status_code != 200:
                print(f"Error verifying token: {response.status_code}", flush=True)
                return False

            # Use the unified function to show status
            self.check_and_log_rate_limit(response, metrics, 'core', "Token Verification")
            return True

        except Exception as e:
            print(f"Error verifying token: {e}", flush=True)
            return False

    def load_tokens(self):
        """Loads GitHub tokens from .env file or environment variables"""
        load_dotenv()
        tokens_str = os.getenv("GITHUB_TOKENS")
        if not tokens_str:
            print("No token found. Make sure GITHUB_TOKENS is set in your .env file.", flush=True)
            return False
        
        self.tokens = [token.strip() for token in tokens_str.split(",") if token.strip()]
        if not self.tokens:
            print("No valid tokens found after processing.", flush=True)
            return False
        
        print(f"{len(self.tokens)} tokens loaded.", flush=True)
        return self.verify_token()

    def update_auth_header(self):
        """Updates the Authorization header with the current token"""
        if self.tokens:
            self.headers['Authorization'] = f'token {self.tokens[self.current_token_index]}'

    def switch_token(self):
        """Switches to the next available token"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth_header()
        print(f"Switching to the next token. Current token: {self.current_token_index + 1}/{len(self.tokens)}", flush=True)

    def wait_for_rate_limit_reset(self, endpoint_type='core'):
        """Waits for the rate limit to reset with a safety margin"""
        try:
            response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
            metrics = APIMetrics()
            
            # Use the unified function to show status
            self.check_and_log_rate_limit(response, metrics, endpoint_type, "Waiting for Reset")
            
            rate_limits = response.json()['resources'][endpoint_type]
            reset_time = int(rate_limits['reset'])
            current_time = int(time.time())
            
            # Adding 5 seconds safety margin
            wait_time = reset_time - current_time + 5
            
            if wait_time > 0:
                print(f"\n⏳ [RATE LIMIT] Waiting {wait_time} seconds for reset (including safety margin)...", flush=True)
                time.sleep(wait_time)
                print("✅ [RATE LIMIT] Reset complete! Resuming operations...\n", flush=True)
                
                response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
                if response.status_code == 200:
                    new_limits = response.json()['resources'][endpoint_type]
                    if int(new_limits['remaining']) > 0:
                        return True
                    else:
                        print("⚠️ [RATE LIMIT] Token not reset yet, waiting another 5 seconds...", flush=True)
                        time.sleep(5)
                        return True
        except Exception as e:
            print(f"❌ [RATE LIMIT] Error while waiting for reset: {str(e)}", flush=True)
            raise RuntimeError(f"Failed to wait for rate limit reset: {str(e)}")
        return False

    def handle_rate_limit(self, response, endpoint_type='core'):
        """Handles the rate limit based on the endpoint type"""
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
                
                print("\n" + "="*50)
                print("🚫 RATE LIMIT REACHED!")
                print(f"Endpoint type: {endpoint_type.upper()}")
                print(f"Reset scheduled for: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Waiting time required: {int(wait_time)} seconds")
                print("="*50 + "\n")
                
            if endpoint_type == 'search':
                print("[RATE LIMIT] Search limit reached. Waiting for reset...", flush=True)
                return self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Searching for an available alternative token...", flush=True)
                    best_token = self.find_best_available_token()
                    
                    if best_token is not None:
                        self.current_token_index = best_token
                        self.update_auth_header()
                        print(f"[RATE LIMIT] Alternative token found! Using token {best_token + 1}/{len(self.tokens)}", flush=True)
                        return True
                    else:
                        print("[RATE LIMIT] No alternative tokens available. Waiting for reset...", flush=True)
                        return self.wait_for_rate_limit_reset()
                else:
                    print("[RATE LIMIT] ⚠️ WARNING: Limit reached and no alternative tokens available!", flush=True)
                    return self.wait_for_rate_limit_reset()
        return False

    def find_best_available_token(self):
        """
        Checks all tokens and returns the index of the best available token,
        or None if all tokens are unavailable.
        """
        best_token = None
        max_remaining = 0
        original_token_index = self.current_token_index

        for i in range(len(self.tokens)):
            # Skip the current token
            if i == original_token_index:
                continue

            self.current_token_index = i
            self.update_auth_header()

            try:
                response = requests.get("https://api.github.com/rate_limit", headers=self.headers)
                if response.status_code == 200:
                    rate_data = response.json()['resources']
                    core_remaining = int(rate_data['core']['remaining'])

                    # If a token with more requests available is found
                    if core_remaining > max_remaining:
                        max_remaining = core_remaining
                        best_token = i

                        # If a token with enough requests is found, use it immediately
                        if core_remaining > 100:
                            print(f"[TOKEN] Found token {i + 1} with {core_remaining} requests available", flush=True)
                            return i

            except Exception as e:
                print(f"Error checking token {i + 1}: {str(e)}", flush=True)

        # If no token with more than 100 requests was found but some are available
        if best_token is not None and max_remaining > 0:
            print(f"[TOKEN] Using token {best_token + 1} with {max_remaining} requests remaining", flush=True)
            return best_token

        # If no available token was found, revert to the original token
        self.current_token_index = original_token_index
        self.update_auth_header()
        return None

    def project_root_directory(self):
        return os.getcwd()

    def user_home_directory(self):
        return os.path.expanduser("~")

    def clone_repo(self, repo_url, clone_path):
        if not os.path.exists(clone_path):
            print(f"Cloning repo: {repo_url}", flush=True)
            # Use token for authentication
            token = self.tokens[self.current_token_index]
            auth_url = f'https://{token}@github.com/{repo_url.split("github.com/")[1]}'
            Repo.clone_from(auth_url, clone_path)
        else:
            print(f"Repo already exists: {clone_path}", flush=True)
            self.update_repo(clone_path)

    def update_repo(self, repo_path):
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repo updated: {repo_path}", flush=True)
        except GitCommandError as e:
            print(f"Error updating repo: {e}", flush=True)
            raise Exception(f"Error updating repo: {e}")

    def save_to_json(self, data, filename):
        output_path = os.path.join(self.project_root_directory(), filename)
        try:
            with open(output_path, 'w') as outfile:
                json.dump(data, outfile, indent=4)
            print(f"Data successfully saved to {output_path}", flush=True)
        except Exception as e:
            print(f"Failed to save data to {output_path}: {e}", flush=True)
    
    def convert_to_iso8601(self, date):
        return date.isoformat()

    def get_commits(self, repo_name: str, start_date: str = None, end_date: str = None, clone_path: str = None, commit_sha: str = None):
        try:
            print(f"\n[COMMITS] Starting commits extraction for {repo_name}", flush=True)

            if commit_sha:
                print(f"[COMMITS] Extraction mode: Specific commit (SHA: {commit_sha})", flush=True)
            else:
                print(f"[COMMITS] Extraction mode: Period from {start_date or 'beginning'} to {end_date or 'now'}", flush=True)

            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%SZ')
            else:
                start_date = datetime.min

            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%SZ')
            else:
                end_date = datetime.now()

            clone_path = clone_path if clone_path is not None else os.path.join(self.user_home_directory(), 'GitHubClones')
            repo_path = os.path.join(clone_path, repo_name.split('/')[1])

            if not os.path.exists(repo_path):
                repo_url = f'https://github.com/{repo_name}'
                print(f"[COMMITS] Cloning repository: {repo_url}", flush=True)
                self.clone_repo(repo_url, repo_path)
            else:
                print(f"[COMMITS] Repository already exists: {repo_path}", flush=True)
                self.update_repo(repo_path)

            print("[COMMITS] Starting commits analysis...", flush=True)

            if commit_sha:
                repo = Repository(repo_path, single=commit_sha).traverse_commits()
            else:
                repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()

            essential_commits = []

            for commit in repo:
                current_timestamp = timezone.now()
                print(f"[COMMITS] Processing commit: {commit.hash[:7]}", flush=True)
                # Create or get author and committer
                author, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.author.name, email=commit.author.email if commit.author else None)
                committer, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.committer.name, email=commit.committer.email if commit.committer else None)

                # Create or update commit in the database with timestamp
                db_commit, created = GitHubCommit.objects.update_or_create(
                    sha=commit.hash,
                    defaults={
                        'repository': repo_name,
                        'message': commit.msg,
                        'date': commit.author_date,
                        'author': author,
                        'committer': committer,
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files_changed': len(commit.modified_files),
                        'in_main_branch': commit.in_main_branch,
                        'merge': commit.merge,
                        'dmm_unit_size': commit.dmm_unit_size,
                        'dmm_unit_complexity': commit.dmm_unit_complexity,
                        'dmm_unit_interfacing': commit.dmm_unit_interfacing,
                        'time_mined': current_timestamp
                    }
                )

                # Prepare data for JSON
                commit_data = {
                    'sha': commit.hash,
                    'message': commit.msg,
                    'date': self.convert_to_iso8601(commit.author_date),
                    'author': {
                        'name': author.name,
                        'email': author.email
                    },
                    'committer': {
                        'name': committer.name,
                        'email': committer.email
                    },
                    'lines': {
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files': len(commit.modified_files)
                    },
                    'in_main_branch': commit.in_main_branch,
                    'merge': commit.merge,
                    'dmm_unit_size': commit.dmm_unit_size,
                    'dmm_unit_complexity': commit.dmm_unit_complexity,
                    'dmm_unit_interfacing': commit.dmm_unit_interfacing,
                    'modified_files': []
                }

                # Process modified files, avoid duplicates
                for mod in commit.modified_files:
                    db_mod_file, _ = GitHubModifiedFile.objects.update_or_create(
                        commit=db_commit,
                        filename=mod.filename,
                        defaults={
                            'old_path': mod.old_path,
                            'new_path': mod.new_path,
                            'change_type': mod.change_type.name,
                            'diff': mod.diff,
                            'added_lines': mod.added_lines,
                            'deleted_lines': mod.deleted_lines,
                            'complexity': mod.complexity,
                            'time_mined': current_timestamp
                        }
                    )

                    # Add modified file data to JSON
                    mod_data = {
                        'old_path': mod.old_path,
                        'new_path': mod.new_path,
                        'filename': mod.filename,
                        'change_type': mod.change_type.name,
                        'diff': mod.diff,
                        'added_lines': mod.added_lines,
                        'deleted_lines': mod.deleted_lines,
                        'complexity': mod.complexity,
                        'methods': []
                    }

                    # Process methods, avoid duplicates
                    for method in mod.methods:
                        GitHubMethod.objects.update_or_create(
                            modified_file=db_mod_file,
                            name=method.name,
                            defaults={
                                'complexity': method.complexity,
                                'max_nesting': getattr(method, 'max_nesting', None),
                                'time_mined': current_timestamp
                            }
                        )

                        method_data = {
                            'name': method.name,
                            'complexity': method.complexity,
                            'max_nesting': getattr(method, 'max_nesting', None)
                        }
                        mod_data['methods'].append(method_data)

                commit_data['modified_files'].append(mod_data)

            essential_commits.append(commit_data)

            print("\n[COMMITS] Saving data to JSON...", flush=True)
            filename = f"{repo_name.replace('/', '_')}_commit_{commit_sha}.json" if commit_sha else f"{repo_name.replace('/', '_')}_commits.json"
            self.save_to_json(essential_commits, filename)
            print("[COMMITS] Detailed commits saved to database and JSON successfully.", flush=True)
            print(f"[COMMITS] Total commits processed: {len(essential_commits)}", flush=True)
            return essential_commits

        except Exception as e:
            print(f"[COMMITS] Error accessing repository: {e}", flush=True)
            return []
        finally:
            self.verify_token()

    def sanitize_text(self, text):
        """Remove or replace invalid characters from text"""
        if text is None:
            return None
        # Replace null characters with space
        return text.replace('\u0000', ' ')

    def split_date_range(self, start_date, end_date, interval_days=1):
        """
        Split the date range into smaller periods
        
        Args:
            start_date (str): Start date in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)
            end_date (str): End date in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)
            interval_days (int): Number of days per interval
            
        Returns:
            generator: Yields tuples of (start_date, end_date) for each interval
        """
        if not start_date or not end_date:
            yield (start_date, end_date)
            return

        start = datetime.strptime(start_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end_date.rstrip('Z'), "%Y-%m-%dT%H:%M:%S")
        
        current = start
        while current < end:
            interval_end = min(current + timedelta(days=interval_days), end)
            yield (
                current.strftime("%Y-%m-%d"),
                interval_end.strftime("%Y-%m-%d")
            )
            current = interval_end + timedelta(days=1)

    def check_and_log_rate_limit(self, response, metrics, endpoint_type='core', context=""):
        """Unified function to check and log rate limit status"""
        metrics.update_rate_limit(response.headers, endpoint_type)
        
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            print("\n" + "="*50)
            print(f"🚫 RATE LIMIT REACHED! {context}")
            print(f"Endpoint type: {endpoint_type.upper()}")
            
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
                print(f"Reset scheduled for: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Wait time required: {int(wait_time)} seconds")
            print("="*50 + "\n")
            
            if endpoint_type == 'search':
                print("[RATE LIMIT] Search limit reached. Waiting for reset...", flush=True)
                self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Core limit reached. Switching to next token...", flush=True)
                    self.switch_token()
                    self.verify_token()
                else:
                    print("[RATE LIMIT] ⚠️ WARNING: Limit reached and no alternative tokens available!", flush=True)
                    self.wait_for_rate_limit_reset()
            return True

        remaining = (metrics.search_limit_remaining if endpoint_type == 'search' 
                    else metrics.core_limit_remaining)
        if remaining and int(remaining) < 50:
            print(f"\n⚠️ WARNING: Only {remaining} requests remaining for the current token ({endpoint_type})", flush=True)
        
        return False

    def get_branches(self, repo_name: str):
        url = f'https://api.github.com/repos/{repo_name}/branches'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                if not self.handle_rate_limit(response, 'core'):
                    print("[Branches] Failed to recover after rate limit", flush=True)
                    return []
                response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            branches = response.json()
            self.save_to_json(branches, f"{repo_name.replace('/', '_')}_branches.json")

            for branch in branches:
                current_timestamp = timezone.now()
                GitHubBranch.objects.update_or_create(
                    name=branch['name'],
                    defaults={
                        'repository': repo_name,
                        'sha': branch['commit']['sha'],
                        'time_mined': current_timestamp
                    }
                )
            print("Branches successfully saved to database and JSON.", flush=True)
            return branches
        except requests.exceptions.RequestException as e:
            print(f"Error accessing branches: {e}", flush=True)
            return []
        finally:
            self.verify_token()

    def calculate_period_days(self, start_date, end_date):
        """
        Calculates the number of days between two dates
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            int: Number of days between the dates
        """
        if not start_date or not end_date:
            return "full period"
            
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return (end - start).days + 1

    def get_watchers_from_html(self, owner: str, repo: str):
        """Fetches the number of watchers from the repository's HTML page"""
        url = f'https://github.com/{owner}/{repo}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                watchers_link = soup.find('a', {'href': f'/{owner}/{repo}/watchers', 'class': 'Link--muted'})
                if watchers_link:
                    strong_element = watchers_link.find('strong')
                    if strong_element and strong_element.text.strip():
                        text = strong_element.text.strip()
                        if 'k' in text.lower():
                            return int(float(text.lower().replace('k', '')) * 1000)
                        return int(text.replace(',', ''))
            return 0
        except Exception as e:
            print(f"[METADATA] Error fetching watchers: {e}", flush=True)
            return 0

    def get_used_by_from_html(self, owner: str, repo: str):
        """Fetches the 'Used by' count from the repository API"""
        url = f'https://api.github.com/repos/{owner}/{repo}/network/dependents'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                if 'Link' in response.headers:
                    link_header = response.headers['Link']
                    if 'page=' in link_header:
                        last_page = int(link_header.split('page=')[-1].split('>')[0])
                        return last_page * 30
                soup = BeautifulSoup(response.content, 'lxml')
                dependents = soup.find_all('div', class_='Box-row')

                return len(dependents)
            return 0
        except Exception as e:
            print(f"[METADATA] Error fetching Used by: {e}", flush=True)
            return 0

    def get_releases_count(self, owner: str, repo: str):
        """Fetches the number of releases from the repository's HTML page"""
        url = f'https://github.com/{owner}/{repo}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                releases_link = soup.find('a', {'href': f'/{owner}/{repo}/releases', 'class': 'Link--primary'})
                if releases_link:
                    span_element = releases_link.find('span', class_='Counter')
                    if span_element and span_element.text.strip():
                        return int(span_element.text.strip().replace(',', ''))
            return 0
        except Exception as e:
            print(f"[METADATA] Error fetching releases: {e}", flush=True)
            return 0

    def get_repository_metadata(self, repo_name: str):
        """
        Fetches repository metadata from GitHub
        """
        print(f"\n[METADATA] Starting metadata extraction for {repo_name}", flush=True)
        
        try:
            owner, repo = repo_name.split('/')
            url = f'https://api.github.com/repos/{repo_name}'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                if not self.handle_rate_limit(response, 'core'):
                    print("[METADATA] Failed to recover after rate limit", flush=True)
                    return None
                response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"[METADATA] Error fetching metadata: {response.status_code}", flush=True)
                return None

            data = response.json()
            
            languages = self.get_repo_languages(owner, repo)
            readme = self.get_repo_readme(owner, repo)
            contributors_count = self.get_contributors_from_html(owner, repo)
            labels_count = self.get_repo_labels_count(owner, repo)
            
            watchers_count = self.get_watchers_from_html(owner, repo)
            used_by_count = self.get_used_by_from_html(owner, repo)
            releases_count = self.get_releases_count(owner, repo)
            
            current_timestamp = timezone.now()
            metadata, created = GitHubMetadata.objects.update_or_create(
                repository=repo_name,
                defaults={
                    'owner': data.get('owner', {}).get('login'),
                    'organization': data.get('organization', {}).get('login') if data.get('organization') else None,
                    'stars_count': data.get('stargazers_count', 0),
                    'watchers_count': watchers_count,
                    'used_by_count': used_by_count,
                    'releases_count': releases_count,
                    'forks_count': data.get('forks_count', 0),
                    'open_issues_count': data.get('open_issues_count', 0),
                    'default_branch': data.get('default_branch'),
                    'description': data.get('description'),
                    'html_url': data.get('html_url'),
                    'contributors_count': contributors_count,
                    'topics': data.get('topics'),
                    'languages': languages,
                    'readme': readme,
                    'labels_count': labels_count,
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'is_archived': data.get('archived', False),
                    'is_template': data.get('is_template', False),
                    'time_mined': current_timestamp
                }
            )
            
            print(f"[METADATA] Metadata {'created' if created else 'updated'} successfully", flush=True)
            return metadata

        except Exception as e:
            print(f"[METADATA] Error during extraction: {str(e)}", flush=True)

    def get_repo_languages(self, owner: str, repo: str):
        url = f'https://api.github.com/repos/{owner}/{repo}/languages'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            total_bytes = sum(data.values())
            
            return {
                'languages': [
                    {
                        'language': lang,
                        'percentage': round((bytes_used / total_bytes) * 100, 2)
                    }
                    for lang, bytes_used in data.items()
                ]
            }
            
    def get_repo_readme(self, owner: str, repo: str):
        """
        Gets the content of the repository's README using the GitHub API
        and decodes the returned Base64 content.
        """
        url = f'https://api.github.com/repos/{owner}/{repo}/readme'
        headers = {**self.headers, 'Accept': 'application/vnd.github.v3+json'}
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                if not self.handle_rate_limit(response, 'core'):
                    return None
                response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                content = response.json()
                if 'content' in content:
                    # Decodes the Base64 content and converts it to a string
                    readme_content = base64.b64decode(content['content']).decode('utf-8')
                    return readme_content
            
            return None
        
        except Exception as e:
            print(f"[README] Error getting README: {str(e)}", flush=True)
            return None

    def get_contributors_from_html(self, owner: str, repo: str):
        url = f'https://github.com/{owner}/{repo}'
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            contributors_element = soup.find('a', {'href': f'/{owner}/{repo}/graphs/contributors'})
            if contributors_element:
                span_element = contributors_element.find('span', class_='Counter ml-1')
                if span_element and 'title' in span_element.attrs:
                    try:
                        return int(span_element['title'].replace(',', ''))
                    except ValueError:
                        return None
        return None

    def get_repo_labels_count(self, owner: str, repo: str):
        """
        Gets the total count of labels for a repository, considering all pages.
        """
        url = f'https://api.github.com/repos/{owner}/{repo}/labels'
        total_labels = []
        
        while url:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                if not self.handle_rate_limit(response, 'core'):
                    return None
                response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return None
                
            total_labels.extend(response.json())
            url = response.links.get('next', {}).get('url')
        
        return len(total_labels)

    def get_pull_requests(self, repo_name: str, start_date: str = None, end_date: str = None, depth: str = 'basic'):
        all_prs = []
        metrics = APIMetrics()
        debug_buffer = []  # Buffer to accumulate debug messages
        
        def log_debug(pr_number, message):
            """Adds a debug message to the buffer"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            debug_buffer.append(f"[{timestamp}][PRs][DEBUG][PR #{pr_number}] {message}")

        def log_error(pr_number, message, error=None):
            """Logs error and prints immediately"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_message = f"[{timestamp}][PRs][ERROR][PR #{pr_number}] {message}"
            if error:
                error_message += f"\nDetails: {str(error)}"
            print(f"\n{error_message}", flush=True)

        def flush_debug_logs():
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
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"[PRs] 📊 Processing period: {period_start} to {period_end}")
                print("-"*40)
                
                base_url = "https://api.github.com/search/issues"
                page = 1
                has_more_pages = True
                period_prs_count = 0

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
                        current_timestamp = timezone.now()  # Changed to use timezone.now()
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

                            # Inside the get_pull_requests method
                            if depth == 'basic':
                                # If it's basic mining, check for existing PR
                                existing_pr = GitHubPullRequest.objects.filter(pr_id=processed_pr['id']).first()
                                if existing_pr:
                                    # Preserve complex data if it exists
                                    processed_pr['commits'] = existing_pr.commits
                                    processed_pr['comments'] = existing_pr.comments

                            # Update or create PR
                            GitHubIssuePullRequest.objects.update_or_create(
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

                            all_prs.append(processed_pr)
                            log_debug(pr_number, "Processing and saving completed successfully")
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
            print("[PRs] 💾 Saving data to JSON...")
            self.save_to_json(all_prs, f"{repo_name.replace('/', '_')}_pull_requests.json")
            print(f"[PRs] ✨ Extraction completed! Total PRs collected: {len(all_prs)}")
            print("="*50 + "\n")
            return all_prs

        except Exception as e:
            print(f"[PRs] ❌ Error during extraction: {str(e)}", flush=True)
            raise RuntimeError(f"Failed to extract PRs: {str(e)}") from e
        finally:
            self.verify_token()


    def get_issues(self, repo_name: str, start_date: str = None, end_date: str = None, depth: str = 'basic'):
        all_issues = []
        metrics = APIMetrics()
        
        print("\n" + "="*50)
        print(f"🔍 INICIANDO EXTRAÇÃO DE ISSUES: {repo_name}")
        print(f"📅 Período: {start_date or 'início'} até {end_date or 'atual'}")
        print(f"🔎 Profundidade: {depth.upper()}")
        print("="*50 + "\n")

        try:
            for period_start, period_end in self.split_date_range(start_date, end_date):
                print("\n" + "-"*40)
                print(f"📊 Processando período: {period_start} até {period_end}")
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
                            print("Falha ao recuperar após rate limit", flush=True)
                            break
                        response = requests.get("https://api.github.com/search/issues", params=params, headers=self.headers)

                    data = response.json()
                    if not data.get('items'):
                        break

                    issues_in_page = len(data['items'])
                    period_issues_count += issues_in_page
                    print(f"\n📝 Página {page}: Processando {issues_in_page} issues...")

                    for issue in data['items']:
                        current_timestamp = timezone.now()
                        if 'pull_request' in issue:
                            continue

                        issue_number = issue['number']
                        
                        # Search Events
                        timeline_url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/timeline'
                        headers = {**self.headers, 'Accept': 'application/vnd.github.mockingbird-preview'}
                        timeline_response = requests.get(timeline_url, headers=headers)
                        metrics.total_requests += 1
                        
                        timeline_events = []
                        if timeline_response.status_code == 403 and 'rate limit' in timeline_response.text.lower():
                            if not self.handle_rate_limit(timeline_response, 'core'):
                                print(f"[Issues] Falha ao recuperar timeline #{issue_number} após rate limit", flush=True)
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

                        # Search comments only if complex mining
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

                        if depth == 'basic':
                            existing_issue = GitHubIssue.objects.filter(issue_id=processed_issue['id']).first()
                            if existing_issue:
                                processed_issue['comments_data'] = existing_issue.comments
                                processed_issue['timeline_events'] = existing_issue.timeline_events

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
            print("💾 Saving data in JSON...")
            self.save_to_json(all_issues, f"{repo_name.replace('/', '_')}_issues.json")
            print(f"✨ Extraction completed! Total issues collected: {len(all_issues)}")
            print("="*50 + "\n")
            return all_issues

        except Exception as e:
            print(f"\n❌ Error during extraction: {str(e)}", flush=True)
            raise RuntimeError(f"Issue extraction failed: {str(e)}") from e
        finally:
            self.verify_token()
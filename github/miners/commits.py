import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from git import Repo, GitCommandError
from pydriller import Repository
from django.utils import timezone as django_timezone

from .base import BaseMiner
from .utils import convert_to_iso8601
from ..models import (
    GitHubCommit, GitHubAuthor, GitHubModifiedFile, GitHubMethod, GitHubMetadata
)


class CommitsMiner(BaseMiner):
    """Specialized miner for GitHub commits extraction"""

    def project_root_directory(self) -> str:
        """Returns the current working directory"""
        return os.getcwd()

    def user_home_directory(self) -> str:
        """Returns the user's home directory"""
        return os.path.expanduser("~")

    def clone_repo(self, repo_url: str, clone_path: str) -> bool:
        """Clone repository with retry logic"""
        max_retries = 3
        retry_delay = 5  
        
        for attempt in range(max_retries):
            try:
                if not os.path.exists(clone_path):
                    print(f"Cloning repo: {repo_url} (attempt {attempt + 1}/{max_retries})", flush=True)
                    token = self.tokens[self.current_token_index]
                    auth_url = f'https://{token}@github.com/{repo_url.split("github.com/")[1]}'
                    
                    git_config = [
                        'http.postBuffer=524288000',  
                        'http.lowSpeedLimit=1000',
                        'http.lowSpeedTime=300',
                        'http.sslVerify=false'  
                    ]
                    
                    for config in git_config:
                        os.system(f'git config --global {config}')
                    
                    Repo.clone_from(auth_url, clone_path)
                    print(f"Repository cloned successfully: {clone_path}", flush=True)
                    return True
                else:
                    print(f"Repo already exists: {clone_path}", flush=True)
                    self.update_repo(clone_path)
                    return True
                
            except GitCommandError as e:
                print(f"Error cloning repository (attempt {attempt + 1}/{max_retries}): {str(e)}", flush=True)
                if attempt < max_retries - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...", flush=True)
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2 
                else:
                    print("Max retries reached. Giving up.", flush=True)
                    raise Exception(f"Failed to clone repository after {max_retries} attempts: {str(e)}")
                
            except Exception as e:
                print(f"Unexpected error during clone (attempt {attempt + 1}/{max_retries}): {str(e)}", flush=True)
                if attempt < max_retries - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...", flush=True)
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print("Max retries reached. Giving up.", flush=True)
                    raise Exception(f"Failed to clone repository after {max_retries} attempts: {str(e)}")

    def update_repo(self, repo_path: str) -> None:
        """Update existing repository"""
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repo updated: {repo_path}", flush=True)
        except GitCommandError as e:
            print(f"Error updating repo: {e}", flush=True)
            raise Exception(f"Error updating repo: {e}")

    def get_commits(self, repo_name: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, clone_path: Optional[str] = None, 
                   commit_sha: Optional[str] = None, task_obj=None) -> List[Dict[str, Any]]:
        """
        Extract commits from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            clone_path: Path to clone repository (optional)
            commit_sha: Specific commit SHA to extract (optional)
            task_obj: Task object for progress updates (optional)
            
        Returns:
            List of extracted commit data
        """
        
        def log_progress(message: str) -> None:
            """Log progress message and update task if available"""
            print(message, flush=True)
            if task_obj:
                task_obj.operation = message
                task_obj.save(update_fields=["operation"])
        
        try:
            log_progress(f"🔍 STARTING COMMITS EXTRACTION: {repo_name}")

            if commit_sha:
                log_progress(f"📋 Extraction mode: Specific commit (SHA: {commit_sha})")
            else:
                log_progress(f"📅 Period: {start_date or 'beginning'} to {end_date or 'now'}")

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
                log_progress(f"📥 Cloning repository: {repo_url}")
                self.clone_repo(repo_url, repo_path)
            else:
                log_progress(f"📂 Repository already exists: {repo_path}")
                self.update_repo(repo_path)

            log_progress("🔍 Starting commits analysis...")

            if commit_sha:
                repo = Repository(repo_path, single=commit_sha).traverse_commits()
                log_progress(f"🎯 Processing specific commit: {commit_sha}")
            else:
                repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()
                log_progress("📊 Processing commits in date range...")

            essential_commits = []
            current_timestamp = django_timezone.now()
            processed_count = 0

            if not commit_sha:
                log_progress("🔢 Counting total commits to process...")
                total_commits = 0
                for _ in repo:
                    total_commits += 1
                
                log_progress(f"📈 Total commits to process: {total_commits}")
                
                if commit_sha:
                    repo = Repository(repo_path, single=commit_sha).traverse_commits()
                else:
                    repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()
            else:
                total_commits = 1

            metadata_obj = GitHubMetadata.objects.filter(repository=repo_name).first()
            if metadata_obj is None:
                log_progress(f"[COMMITS] GitHubMetadata not found for {repo_name}. Ensure metadata task runs before commits.")
                return []

            for commit in repo:
                processed_count += 1
                
                if total_commits > 0:
                    log_progress(f"Mining commit {processed_count} of {total_commits}. SHA: {commit.hash[:7]} - {commit.msg[:50]}...")
                else:
                    log_progress(f"Mining commit SHA: {commit.hash[:7]} - {commit.msg[:50]}...")
                
                author, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.author.name, 
                    email=commit.author.email if commit.author else None
                )
                committer, _ = GitHubAuthor.objects.get_or_create(
                    name=commit.committer.name, 
                    email=commit.committer.email if commit.committer else None
                )

                db_commit, created = GitHubCommit.objects.update_or_create(
                    sha=commit.hash,
                    defaults={
                        'repository': metadata_obj,
                        'repository_name': repo_name,
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

                commit_data = {
                    'sha': commit.hash,
                    'message': commit.msg,
                    'date': convert_to_iso8601(commit.author_date),
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

            log_progress(f"✅ Extraction completed! Total commits processed: {len(essential_commits)}")
            return essential_commits

        except Exception as e:
            log_progress(f"❌ Error during commits extraction: {str(e)}")
            return []
        finally:
            self.verify_token() 
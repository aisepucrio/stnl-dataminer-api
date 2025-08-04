"""
GitHub Miners Module

This module provides a modular approach to GitHub data mining while maintaining
backward compatibility with existing code.

The GitHubMiner class combines all specialized miners into a single interface
that matches the original implementation.
"""

from typing import List, Dict, Any, Optional

from .base import BaseMiner
from .utils import APIMetrics, sanitize_text, split_date_range, calculate_period_days, convert_to_iso8601
from .commits import CommitsMiner
from .pull_requests import PullRequestsMiner
from .issues import IssuesMiner
from .metadata import MetadataMiner


class GitHubMiner(BaseMiner):
    """
    Unified GitHub miner that combines all specialized miners.
    
    This class maintains backward compatibility with the original GitHubMiner
    implementation while leveraging the new modular architecture.
    """
    
    def __init__(self):
        """Initialize the unified GitHub miner"""
        # Initialize miners first (without auth)
        self._commits_miner = None
        self._pull_requests_miner = None
        self._issues_miner = None
        self._metadata_miner = None
        
        # Initialize base class (this will load tokens and setup auth)
        super().__init__()
        
        # Now create specialized miners
        self._commits_miner = CommitsMiner()
        self._pull_requests_miner = PullRequestsMiner()
        self._issues_miner = IssuesMiner()
        self._metadata_miner = MetadataMiner()
        
        # Share authentication state across all miners
        self._sync_auth_state()
    
    def _sync_auth_state(self) -> None:
        """Synchronize authentication state across all miners"""
        miners = [
            self._commits_miner,
            self._pull_requests_miner, 
            self._issues_miner,
            self._metadata_miner
        ]
        
        for miner in miners:
            # Only sync if miner is initialized
            if miner is not None:
                miner.headers = self.headers.copy()
                miner.tokens = self.tokens.copy()
                miner.current_token_index = self.current_token_index
    
    def switch_token(self) -> None:
        """Override to sync token changes across all miners"""
        super().switch_token()
        self._sync_auth_state()
    
    def update_auth_header(self) -> None:
        """Override to sync header updates across all miners"""
        super().update_auth_header()
        self._sync_auth_state()
    
    # Commits mining methods
    def project_root_directory(self) -> str:
        """Returns the current working directory"""
        return self._commits_miner.project_root_directory()
    
    def user_home_directory(self) -> str:
        """Returns the user's home directory"""
        return self._commits_miner.user_home_directory()
    
    def clone_repo(self, repo_url: str, clone_path: str) -> bool:
        """Clone repository with retry logic"""
        return self._commits_miner.clone_repo(repo_url, clone_path)
    
    def update_repo(self, repo_path: str) -> None:
        """Update existing repository"""
        return self._commits_miner.update_repo(repo_path)
    
    def convert_to_iso8601(self, date) -> str:
        """Convert datetime to ISO8601 format"""
        return convert_to_iso8601(date)
    
    def get_commits(self, repo_name: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, clone_path: Optional[str] = None, 
                   commit_sha: Optional[str] = None, task_obj=None) -> List[Dict[str, Any]]:
        """Extract commits from a GitHub repository"""
        self._sync_auth_state()
        return self._commits_miner.get_commits(repo_name, start_date, end_date, clone_path, commit_sha, task_obj)
    
    # Pull requests mining methods
    def get_pull_requests(self, repo_name: str, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None, depth: str = 'basic', task_obj=None) -> List[Dict[str, Any]]:
        """Extract pull requests from a GitHub repository"""
        self._sync_auth_state()
        return self._pull_requests_miner.get_pull_requests(repo_name, start_date, end_date, depth, task_obj)
    
    # Issues mining methods
    def get_issues(self, repo_name: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, depth: str = 'basic', task_obj=None) -> List[Dict[str, Any]]:
        """Extract issues from a GitHub repository"""
        self._sync_auth_state()
        return self._issues_miner.get_issues(repo_name, start_date, end_date, depth, task_obj)
    
    # Metadata and branches mining methods
    def get_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """Extract branches from a GitHub repository"""
        self._sync_auth_state()
        return self._metadata_miner.get_branches(repo_name)
    
    def get_repository_metadata(self, repo_name: str):
        """Fetches repository metadata from GitHub"""
        self._sync_auth_state()
        return self._metadata_miner.get_repository_metadata(repo_name)
    
    def get_watchers_from_html(self, owner: str, repo: str) -> int:
        """Fetches the number of watchers from the repository's HTML page"""
        return self._metadata_miner.get_watchers_from_html(owner, repo)
    
    def get_used_by_from_html(self, owner: str, repo: str) -> int:
        """Fetches the 'Used by' count from the repository API"""
        return self._metadata_miner.get_used_by_from_html(owner, repo)
    
    def get_releases_count(self, owner: str, repo: str) -> int:
        """Fetches the number of releases from the repository's HTML page"""
        return self._metadata_miner.get_releases_count(owner, repo)
    
    def get_repo_languages(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get programming languages used in the repository"""
        return self._metadata_miner.get_repo_languages(owner, repo)
    
    def get_repo_readme(self, owner: str, repo: str) -> Optional[str]:
        """Gets the content of the repository's README"""
        return self._metadata_miner.get_repo_readme(owner, repo)
    
    def get_contributors_from_html(self, owner: str, repo: str) -> Optional[int]:
        """Get contributors count from repository HTML page"""
        return self._metadata_miner.get_contributors_from_html(owner, repo)
    
    def get_repo_labels_count(self, owner: str, repo: str) -> Optional[int]:
        """Gets the total count of labels for a repository"""
        return self._metadata_miner.get_repo_labels_count(owner, repo)
    
    # Utility methods
    def sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """Remove or replace invalid characters from text"""
        return sanitize_text(text)
    
    def split_date_range(self, start_date: Optional[str], end_date: Optional[str], 
                        interval_days: int = 1):
        """Split the date range into smaller periods"""
        return split_date_range(start_date, end_date, interval_days)
    
    def calculate_period_days(self, start_date: Optional[str], end_date: Optional[str]) -> int:
        """Calculates the number of days between two dates"""
        return calculate_period_days(start_date, end_date)
    
    def check_and_log_rate_limit(self, response, metrics, endpoint_type='core', context="") -> bool:
        """Unified function to check and log rate limit status"""
        result = super().check_and_log_rate_limit(response, metrics, endpoint_type, context)
        if result:  # If rate limit was hit and handled, sync auth state
            self._sync_auth_state()
        return result


# Export the main class and utilities for backward compatibility
__all__ = [
    'GitHubMiner',
    'APIMetrics',
    'BaseMiner',
    'CommitsMiner',
    'PullRequestsMiner', 
    'IssuesMiner',
    'MetadataMiner',
    'sanitize_text',
    'split_date_range',
    'calculate_period_days',
    'convert_to_iso8601'
] 
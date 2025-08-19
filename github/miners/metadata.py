import base64
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from django.utils import timezone

from .base import BaseMiner
from ..models import GitHubBranch, GitHubMetadata


class MetadataMiner(BaseMiner):
    """Specialized miner for GitHub repository metadata and branches"""

    def get_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        Extract branches from a GitHub repository
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            
        Returns:
            List of extracted branch data
        """
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

            for branch in branches:
                current_timestamp = timezone.now()
                GitHubBranch.objects.update_or_create(
                    name=branch['name'],
                    defaults={
                        'repository': repo_name,
                        'repository_name': repo_name,
                        'sha': branch['commit']['sha'],
                        'time_mined': current_timestamp
                    }
                )
            print("Branches successfully saved to database.", flush=True)
            return branches
        except requests.exceptions.RequestException as e:
            print(f"Error accessing branches: {e}", flush=True)
            return []
        finally:
            self.verify_token()

    def get_watchers_from_html(self, owner: str, repo: str) -> int:
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

    def get_used_by_from_html(self, owner: str, repo: str) -> int:
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

    def get_releases_count(self, owner: str, repo: str) -> int:
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

    def get_repo_languages(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get programming languages used in the repository"""
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

    def get_repo_readme(self, owner: str, repo: str) -> Optional[str]:
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

    def get_contributors_from_html(self, owner: str, repo: str) -> Optional[int]:
        """Get contributors count from repository HTML page"""
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

    def get_repo_labels_count(self, owner: str, repo: str) -> Optional[int]:
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

    def get_repository_metadata(self, repo_name: str) -> Optional[GitHubMetadata]:
        """
        Fetches repository metadata from GitHub
        
        Args:
            repo_name: Repository name in format 'owner/repo'
            
        Returns:
            GitHubMetadata object or None if extraction fails
        """
        print(f"[METADATA] Starting metadata extraction for {repo_name}", flush=True)
        
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

            if response.status_code == 401:
                print("[METADATA] Unauthorized access. Check your GitHub tokens.", flush=True)
                return None

            data = response.json()
            
            # Get additional data
            languages = self.get_repo_languages(owner, repo)
            readme = self.get_repo_readme(owner, repo)
            contributors_count = self.get_contributors_from_html(owner, repo)
            labels_count = self.get_repo_labels_count(owner, repo)
            watchers_count = self.get_watchers_from_html(owner, repo)
            used_by_count = self.get_used_by_from_html(owner, repo)
            releases_count = self.get_releases_count(owner, repo)
            
            current_timestamp = timezone.now()

            # Use update_or_create instead of create
            metadata, created = GitHubMetadata.objects.update_or_create(
                repository=repo_name,
                owner=data.get('owner', {}).get('login'),
                defaults={
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
            
            action = 'created' if created else 'updated'
            print(f"[METADATA] Metadata {action} successfully", flush=True)
            return metadata

        except Exception as e:
            print(f"[METADATA] Error during extraction: {str(e)}", flush=True)
            return None 
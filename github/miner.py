# github/miner.py

import os
import requests
from git import Repo, GitCommandError
from pydriller import Repository
from datetime import datetime
import json

class GitHubMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.auth = None
        self.tokens = None
        self.usernames = None
        self.current_token_index = 0
        self.load_tokens()

    def project_root_directory(self):
        return os.getcwd()

    def load_tokens(self):
        # Carrega tokens do arquivo .env
        pass

    def user_home_directory(self):
        return os.path.expanduser("~")

    def clone_repo(self, repo_url, clone_path):
        if not os.path.exists(clone_path):
            print(f"Cloning repo: {repo_url}")
            Repo.clone_from(repo_url, clone_path)
        else:
            print(f"Repo already exists: {clone_path}")
            self.update_repo(clone_path)

    def update_repo(self, repo_path):
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repo updated: {repo_path}")
        except GitCommandError as e:
            print(f"Error updating repo: {e}")
            raise Exception(f"Error updating repo: {e}")

    def save_to_json(self, data, filename):
        output_path = os.path.join(self.project_root_directory(), filename)
        try:
            with open(output_path, 'w') as outfile:
                json.dump(data, outfile, indent=4)
            print(f"Data successfully saved to {output_path}")
        except Exception as e:
            print(f"Failed to save data to {output_path}: {e}")
    
    def convert_to_iso8601(self, date):
        return date.isoformat()

    def get_commits(self, repo_name: str, start_date: str = None, end_date: str = None, clone_path: str = None):
        try:
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
                self.clone_repo(repo_url, repo_path)

            # Usando Pydriller para minerar os commits do repositório local
            repo = Repository(repo_path, since=start_date, to=end_date).traverse_commits()

            essential_commits = []
            for commit in repo:
                commit_data = {
                    'sha': commit.hash,
                    'message': commit.msg,
                    'date': self.convert_to_iso8601(commit.author_date),
                    'author': {
                        'name': None,
                        'email': None
                    },
                    'committer': {
                        'name': None,
                        'email': None
                    },
                    'lines': {
                        'insertions': commit.insertions,
                        'deletions': commit.deletions,
                        'files': commit.files
                    },
                    'in_main_branch': commit.in_main_branch,
                    'merge': commit.merge,
                    'dmm_unit_size': None,
                    'dmm_unit_complexity': None,
                    'dmm_unit_interfacing': None,
                    'modified_files': []
                }
                
                # Process author
                try:
                    commit_data['author']['name'] = commit.author.name
                    commit_data['author']['email'] = commit.author.email
                except Exception as e:
                    print(f"Erro ao processar autor do commit {commit.hash}: {e}")
                
                # Process committer
                try:
                    commit_data['committer']['name'] = commit.committer.name
                    commit_data['committer']['email'] = commit.committer.email
                except Exception as e:
                    print(f"Erro ao processar committer do commit {commit.hash}: {e}")
                
                # Process DMM metrics
                try:
                    commit_data['dmm_unit_size'] = commit.dmm_unit_size
                    commit_data['dmm_unit_complexity'] = commit.dmm_unit_complexity
                    commit_data['dmm_unit_interfacing'] = commit.dmm_unit_interfacing
                except Exception as e:
                    print(f"Erro ao processar DMM metrics do commit {commit.hash}: {e}")
                
                # Process modified files
                for mod in commit.modified_files:
                    try:
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
                        
                        # Process methods
                        for method in mod.methods:
                            try:
                                method_data = {
                                    'name': method.name,
                                    'complexity': method.complexity,
                                    'max_nesting': None
                                }
                                try:
                                    method_data['max_nesting'] = method.max_nesting
                                except AttributeError:
                                    print(f"Commit {commit.hash}: 'Method' object has no attribute 'max_nesting'")
                                
                                mod_data['methods'].append(method_data)
                            except Exception as e:
                                print(f"Erro ao processar método {method.name} do arquivo {mod.filename} no commit {commit.hash}: {e}")

                        commit_data['modified_files'].append(mod_data)
                    except Exception as e:
                        print(f"Erro ao processar arquivo modificado {mod.filename} no commit {commit.hash}: {e}")

                essential_commits.append(commit_data)

            # Salva os commits no arquivo JSON no diretório raiz do projeto
            self.save_to_json(essential_commits, f"{repo_name.replace('/', '_')}_commits.json")

            return essential_commits

        except Exception as e:
            print(f"Erro ao acessar o repositório: {e}")
            return []

    def get_issues(self, repo_name: str, start_date: str = None, end_date: str = None):
        url = f'https://api.github.com/repos/{repo_name}/issues'
        params = {
            'since': start_date,
            'until': end_date
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            issues = response.json()

            # Salva as issues no arquivo JSON no diretório raiz do projeto
            self.save_to_json(issues, f"{repo_name.replace('/', '_')}_issues.json")

            return issues
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar issues: {e}")
            return []

    def get_pull_requests(self, repo_name: str, start_date: str = None, end_date: str = None):
        url = f'https://api.github.com/repos/{repo_name}/pulls'
        params = {
            'state': 'all',
            'since': start_date,
            'until': end_date
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            pull_requests = response.json()

            # Salva os pull requests no arquivo JSON no diretório raiz do projeto
            self.save_to_json(pull_requests, f"{repo_name.replace('/', '_')}_pull_requests.json")

            return pull_requests
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar pull requests: {e}")
            return []

    def get_branches(self, repo_name: str):
        url = f'https://api.github.com/repos/{repo_name}/branches'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            branches = response.json()

            # Salva as branches no arquivo JSON no diretório raiz do projeto
            self.save_to_json(branches, f"{repo_name.replace('/', '_')}_branches.json")

            return branches
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar branches: {e}")
            return []
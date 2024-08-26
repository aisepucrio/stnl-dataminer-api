# jobs/tasks.py

from celery import shared_task
from github.miner import GitHubMiner

@shared_task
def fetch_commits(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_commits(repo_name, start_date, end_date)

@shared_task
def fetch_issues(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_issues(repo_name, start_date, end_date)

@shared_task
def fetch_pull_requests(repo_name, start_date=None, end_date=None):
    miner = GitHubMiner()
    return miner.get_pull_requests(repo_name, start_date, end_date)

@shared_task
def fetch_branches(repo_name):
    miner = GitHubMiner()
    return miner.get_branches(repo_name)

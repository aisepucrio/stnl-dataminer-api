import os
import json
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from github.models import (
    GitHubMetadata,
    GitHubAuthor,
    GitHubCommit,
    GitHubIssue,
)

REPO_OWNER = "psf"
REPO_NAME = "requests"
BASE_URL = "https://api.github.com"


def dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def write_done_file():
    """
    Cria o arquivo '.github_seed_done' dentro de:
    github/management/commands/
    """
    base_path = os.path.dirname(__file__)
    filepath = os.path.join(base_path, ".github_seed_done")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("done")
    return filepath


class Command(BaseCommand):
    help = "Populate database with real GitHub sample data (minimal, stable, safe)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            help="Save fetched GitHub API data into github_seed.json",
            action="store_true",
        )
        parser.add_argument(
            "--load",
            help="Load seed data from a local JSON file",
            type=str,
        )

    def handle(self, *args, **options):
        if options.get("load"):
            result = self._load_from_snapshot(options["load"])
            done_file = write_done_file()
            self.stdout.write(f"Seed done file created: {done_file}")
            return result

        result = self._fetch_and_seed(options.get("dump"))
        done_file = write_done_file()
        self.stdout.write(f"Seed done file created: {done_file}")
        return result

    # ---------------------------------------------------------
    # FETCH + SEED
    # ---------------------------------------------------------
    def _fetch_and_seed(self, dump):

        token = os.environ.get("GITHUB_TOKENS")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        self.stdout.write(f"Fetching GitHub data for {REPO_OWNER}/{REPO_NAME}...")

        # -------------------- METADATA --------------------
        meta_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}"
        repo_data = requests.get(meta_url, headers=headers).json()

        metadata, _ = GitHubMetadata.objects.update_or_create(
            repository=REPO_NAME,
            owner=REPO_OWNER,
            defaults={
                "organization": repo_data.get("organization", {}).get("login"),
                "stars_count": repo_data.get("stargazers_count", 0),
                "watchers_count": repo_data.get("subscribers_count", 0),
                "forks_count": repo_data.get("forks_count", 0),
                "open_issues_count": repo_data.get("open_issues_count", 0),
                "default_branch": repo_data.get("default_branch", "main"),
                "description": repo_data.get("description"),
                "html_url": repo_data.get("html_url"),
                "contributors_count": None,
                "topics": repo_data.get("topics", []),
                "languages": None,
                "labels_count": None,
                "github_created_at": dt(repo_data.get("created_at")),
                "github_updated_at": dt(repo_data.get("updated_at")),
            }
        )

        # -------------------- COMMITS --------------------
        commits_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/commits?per_page=50"
        commits_data = requests.get(commits_url, headers=headers).json()

        for c in commits_data:
            commit_info = c.get("commit", {})
            author_info = commit_info.get("author", {})
            committer_info = commit_info.get("committer", {})

            # Author
            author = None
            if author_info.get("email"):
                author, _ = GitHubAuthor.objects.get_or_create(
                    name=author_info.get("name", "Unknown"),
                    email=author_info.get("email"),
                )

            # Committer
            committer = None
            if committer_info.get("email"):
                committer, _ = GitHubAuthor.objects.get_or_create(
                    name=committer_info.get("name", "Unknown"),
                    email=committer_info.get("email"),
                )

            GitHubCommit.objects.update_or_create(
                sha=c["sha"],
                defaults={
                    "repository": metadata,
                    "repository_name": REPO_NAME,
                    "message": commit_info.get("message"),
                    "date": dt(author_info.get("date")),
                    "author": author,
                    "committer": committer,
                    "insertions": 0,
                    "deletions": 0,
                    "files_changed": 0,
                    "in_main_branch": True,
                    "merge": c.get("parents") and len(c["parents"]) > 1,
                    "time_mined": None,
                },
            )

        # -------------------- ISSUES --------------------
        issues_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues?state=all&per_page=20"
        issues_data = requests.get(issues_url, headers=headers).json()

        for issue in issues_data:
            if "pull_request" in issue:
                continue

            GitHubIssue.objects.update_or_create(
                issue_id=issue["id"],
                defaults={
                    "repository": metadata,
                    "repository_name": REPO_NAME,
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "creator": issue.get("user", {}).get("login"),
                    "assignees": [a["login"] for a in issue.get("assignees", [])],
                    "labels": [l["name"] for l in issue.get("labels", [])],
                    "milestone": None,
                    "locked": issue.get("locked", False),
                    "github_created_at": dt(issue.get("created_at")),
                    "github_updated_at": dt(issue.get("updated_at")),
                    "closed_at": dt(issue.get("closed_at")),
                    "body": issue.get("body"),
                    "comments": [],
                    "timeline_events": [],
                    "is_pull_request": False,
                    "author_association": issue.get("author_association"),
                    "reactions": issue.get("reactions", {}),
                    "time_mined": None,
                },
            )

        # -------------------- SNAPSHOT --------------------
        if dump:
            snapshot = {
                "metadata": repo_data,
                "commits": commits_data,
                "issues": issues_data,
            }
            dirpath = os.path.dirname(__file__)
            filepath = os.path.join(dirpath, "github_seed.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)

            self.stdout.write("Snapshot saved to github_seed.json")

        self.stdout.write(self.style.SUCCESS("GitHub seed data successfully populated."))
        return "done"

    # ---------------------------------------------------------
    # LOAD SNAPSHOT
    # ---------------------------------------------------------
    def _load_from_snapshot(self, filename):
        self.stdout.write(f"Loading GitHub seed from {filename}...")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"Snapshot not found: {filename}")
            return

        repo_data = data.get("metadata", {})
        issues = data.get("issues", [])

        metadata, _ = GitHubMetadata.objects.update_or_create(
            repository=repo_data.get("name", REPO_NAME),
            owner=repo_data.get("owner", {}).get("login", REPO_OWNER),
            defaults={
                "stars_count": repo_data.get("stargazers_count", 0),
                "description": repo_data.get("description"),
                "html_url": repo_data.get("html_url"),
                "github_created_at": dt(repo_data.get("created_at")),
                "github_updated_at": dt(repo_data.get("updated_at")),
            }
        )

        for issue in issues:
            if "pull_request" in issue:
                continue

            GitHubIssue.objects.update_or_create(
                issue_id=issue["id"],
                defaults={
                    "repository": metadata,
                    "repository_name": repo_data.get("name", REPO_NAME),
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "creator": issue.get("user", {}).get("login"),
                    "assignees": [a["login"] for a in issue.get("assignees", [])],
                    "labels": [l["name"] for l in issue.get("labels", [])],
                    "milestone": None,
                    "locked": issue.get("locked", False),
                    "github_created_at": dt(issue.get("created_at")),
                    "github_updated_at": dt(issue.get("updated_at")),
                    "closed_at": dt(issue.get("closed_at")),
                    "body": issue.get("body"),
                    "comments": [],
                    "timeline_events": [],
                    "is_pull_request": False,
                    "author_association": issue.get("author_association"),
                    "reactions": issue.get("reactions", {}),
                    "time_mined": None,
                }
            )

        self.stdout.write(self.style.SUCCESS("GitHub snapshot loaded."))
        return "done"

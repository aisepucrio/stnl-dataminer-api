import json
import os
import requests
from django.core.management.base import BaseCommand
from jira.models import (
    JiraIssue,
    JiraUser,
    JiraStatus,
    JiraProject
)


JIRA_API_URL = (
    "https://jira.atlassian.com/rest/api/2/search"
    "?jql=project=JRASERVER ORDER BY created DESC&maxResults=50"
)


class Command(BaseCommand):
    """
    Management command to populate the database with real Jira issues
    """

    help = "Populate the database with real sample Jira issues from Atlassian."

    def add_arguments(self, parser):
        parser.add_argument("--dump", action="store_true", help="Save snapshot JSON")
        parser.add_argument("--load", type=str, help="Load snapshot JSON")

    def handle(self, *args, **options):
        if options.get("load"):
            return self._load_from_snapshot(options["load"])
        return self._fetch_and_seed(options.get("dump"))

    # FETCH FROM API
    def _fetch_and_seed(self, dump=False):
        self.stdout.write("Fetching Jira data...")

        try:
            response = requests.get(JIRA_API_URL, timeout=20)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f"Failed to fetch Jira data: {e}")
            return

        data = response.json()
        issues = data.get("issues", [])
        self.stdout.write(f"Retrieved {len(issues)} issues")

        for issue in issues:
            fields = issue.get("fields", {})

    
            # USER: assignee, creator, reporter
            def get_user(user_data):
                if not user_data:
                    return None

                return JiraUser.objects.get_or_create(
                    accountId=user_data.get("accountId", "unknown"),
                    defaults={
                        "displayName": user_data.get("displayName", "Unknown User"),
                        "emailAddress": user_data.get("emailAddress", "") or "",
                        "active": user_data.get("active", False),
                        "timeZone": user_data.get("timeZone", "UTC"),
                        "accountType": user_data.get("accountType", "unknown"),
                    },
                )[0]

            assignee = get_user(fields.get("assignee"))
            creator = get_user(fields.get("creator"))
            reporter = get_user(fields.get("reporter"))

    
            # PROJECT 
            project_data = fields.get("project") or {}

            project, _ = JiraProject.objects.get_or_create(
                id=project_data.get("id", "unknown"),
                defaults={
                    "key": project_data.get("key", "UNKNOWN"),
                    "name": project_data.get("name", "Unknown Project"),
                    "simplified": project_data.get("simplified", False),
                    "projectTypeKey": project_data.get("projectTypeKey", "unknown"),
                }
            )

    
            # STATUS (string)
            status_data = fields.get("status") or {}
            status_name = status_data.get("name", "Unknown")
    
            # ISSUE  
            JiraIssue.objects.update_or_create(
                issue_key=issue["key"],
                defaults={
                    "issue_id": issue.get("id"),
                    "project": project,
                    "summary": fields.get("summary"),
                    "description": fields.get("description"),
                    "status": status_name,
                    "priority": fields.get("priority", {}).get("name"),
                    "assignee": assignee,
                    "creator": creator,
                    "reporter": reporter,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                }
            )


        # SAVE SNAPSHOT
        if dump:
            base_path = os.path.dirname(__file__)  
            filename = os.path.join(base_path, "jira_seed.json")

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.stdout.write(f"Snapshot saved to {filename}")
    # LOAD FROM SNAPSHOT
    def _load_from_snapshot(self, filename):
        self.stdout.write(f"Loading Jira seed data from {filename}")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(f"Snapshot file not found: {filename}")
            return

        issues = data.get("issues", [])

        for issue in issues:
            fields = issue.get("fields", {})

            def get_user(user_data):
                if not user_data:
                    return None

                return JiraUser.objects.get_or_create(
                    accountId=user_data.get("accountId", "unknown"),
                    defaults={
                        "displayName": user_data.get("displayName", "Unknown User"),
                        "emailAddress": user_data.get("emailAddress", "") or "",
                        "active": user_data.get("active", False),
                        "timeZone": user_data.get("timeZone", "UTC"),
                        "accountType": user_data.get("accountType", "unknown"),
                    },
                )[0]

            assignee = get_user(fields.get("assignee"))
            creator = get_user(fields.get("creator"))
            reporter = get_user(fields.get("reporter"))

            # PROJECT
            project_data = fields.get("project") or {}

            project, _ = JiraProject.objects.get_or_create(
                id=project_data.get("id", "unknown"),
                defaults={
                    "key": project_data.get("key", "UNKNOWN"),
                    "name": project_data.get("name", "Unknown Project"),
                    "simplified": project_data.get("simplified", False),
                    "projectTypeKey": project_data.get("projectTypeKey", "unknown"),
                }
            )

            status_name = (fields.get("status") or {}).get("name", "Unknown")

            JiraIssue.objects.update_or_create(
                issue_key=issue["key"],
                defaults={
                    "issue_id": issue.get("id"),
                    "project": project,
                    "summary": fields.get("summary"),
                    "description": fields.get("description"),
                    "status": status_name,
                    "priority": fields.get("priority", {}).get("name"),
                    "assignee": assignee,
                    "creator": creator,
                    "reporter": reporter,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                }
            )

        self.stdout.write(self.style.SUCCESS("Loaded Jira data from snapshot."))
        return "done"

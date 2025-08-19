import os
import time
from datetime import datetime
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    JiraIssue,
    JiraProject,
    JiraUser,
    JiraComment,
    JiraHistory,
    JiraHistoryItem,
    JiraActivityLog,
    JiraChecklist,
    JiraSprint,
    JiraCommit,
    JiraIssueType
)


class JiraMiner:
    class NoValidJiraTokenError(Exception):
        """Invalid token or all tokens have expired."""
        pass

    def __init__(self, jira_domain, task_obj=None):
        load_dotenv()
        self.jira_domain = jira_domain.strip()
        self.task_obj = task_obj 
        self.log_progress(f"[DEBUG] received domain in JiraMiner: '{self.jira_domain}'")


        # Loading tokens
        self.tokens = [token.strip() for token in os.getenv("JIRA_API_TOKEN", "").split(",") if token.strip()]
        self.jira_email = os.getenv("JIRA_EMAIL")
        self.current_token_index = 0

        if not self.tokens or not self.jira_email:
            raise Exception("JIRA_API_TOKEN and JIRA_EMAIL must be correctly configured in .env")

        self.headers = {"Accept": "application/json"}
        self.update_auth()
        self.verify_token()


    def log_progress(self, message):
        print(message, flush=True)
        if self.task_obj:
            self.task_obj.operation = message
            self.task_obj.save(update_fields=["operation"])
            from jobs.models import Task
            refreshed = Task.objects.get(pk=self.task_obj.pk)
        

    def update_auth(self):
        self.auth = HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])


    def _get_auth(self):
        return HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])


    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth()
        self.log_progress(f"Switching to token {self.current_token_index + 1}/{len(self.tokens)}")


    def verify_token(self):
        for _ in range(len(self.tokens)):
            try:
                url = f"https://{self.jira_domain}/rest/api/3/myself"
                response = requests.get(url, headers=self.headers, auth=self.auth)
                if response.status_code == 200:
                    print(f"Token {self.current_token_index + 1} is valid")
                    return
                else:
                    self.log_progress(f"Token {self.current_token_index + 1} is invalid: {response.status_code}")

                    
                    
            except Exception as e:
                self.log_progress(f"Problem verifying {self.current_token_index + 1}: {e}")


            self.switch_token()

        raise self.NoValidJiraTokenError("❌ No valid Jira token found.")


    def handle_rate_limit(self, response):
        if response.status_code == 429 or "rate limit" in response.text.lower():
            self.log_progress("Rate limit reached. Trying next token...")

            original_index = self.current_token_index

            for _ in range(len(self.tokens)):
                self.switch_token()
                retry = requests.get(response.request.url, headers=self.headers, auth=self.auth)
                if retry.status_code != 429:
                    self.log_progress("New Token worked after rate limit.")

                    return True

            # If no token worked, wait for 60 seconds
            self.log_progress("All tokens failed after rate limit. Waiting for 60 seconds before retrying...")

            time.sleep(60)
            return True

        return False


    def collect_jira_issues(self, project_key, issuetypes, start_date=None, end_date=None):
        max_results, start_at, total_collected = 100, 0, 0
        custom_fields_mapping = self.get_custom_fields_mapping()
        self.log_progress(f"Colecting project issues {project_key}...")

        # Find the Sprint field (e.g., customfield_10020)
        sprint_field_key = None
        for field_id, field_name in custom_fields_mapping.items():
            if field_name.lower() == "sprint":
                sprint_field_key = field_id
                break


        self.log_progress(f"Token {self.current_token_index + 1} is valid")


        jql_query = f'project="{project_key}"'

        if issuetypes:
            issuetypes_jql = " OR ".join([f'issuetype="{issuetype}"' for issuetype in issuetypes])
            jql_query += f' AND ({issuetypes_jql})'

        if start_date:
            start_date_parsed = self.validate_and_parse_date(start_date)
            jql_query += f' AND created >= "{start_date_parsed.strftime("%Y-%m-%d %H:%M")}"'

        if end_date:
            end_date_parsed = self.validate_and_parse_date(end_date)
            jql_query += f' AND created <= "{end_date_parsed.strftime("%Y-%m-%d %H:%M")}"'

        encoded_jql = quote(jql_query)


        self.log_progress("Verificando o total de issues a serem mineradas...")
        preflight_url = f"https://{self.jira_domain}/rest/api/3/search?jql={encoded_jql}&maxResults=0"
        try:
            preflight_response = requests.get(preflight_url, headers=self.headers, auth=self.auth)
            if preflight_response.status_code != 200:

                raise Exception(f"A pré-verificação falhou com status {preflight_response.status_code}: {preflight_response.text}")

 
            total_issues_count = preflight_response.json().get('total', 0)
            self.log_progress(f"Total de {total_issues_count} issues encontradas. Iniciando a coleta.")

        except Exception as e:

            return {"error": f"Não foi possível obter a contagem total de issues: {e}"}


        while True:
            jira_url = f"https://{self.jira_domain}/rest/api/3/search?jql={encoded_jql}&startAt={start_at}&maxResults={max_results}&expand=changelog"
            response = requests.get(jira_url, headers=self.headers, auth=self.auth)

            if self.handle_rate_limit(response):
                continue

            if response.status_code != 200:
                return {"error": f"Failed to collect issues: {response.status_code} - {response.text}"}

            issues = response.json().get('issues', [])
            if not issues:
                break

            for index, issue_data in enumerate(issues):
                issue_count = total_collected + index + 1
                fields = issue_data["fields"]
                issue_id = issue_data["id"]
                issue_key = issue_data["key"]
                current_timestamp = timezone.now()
                description = self.extract_words_from_description(fields.get("description"))

                # Injects the sprint field readable
                if sprint_field_key:
                    fields["sprint"] = fields.get(sprint_field_key)


                # Ensure related objects
                project_obj, _ = JiraProject.objects.get_or_create(
                    id=fields['project']['id'],
                    defaults={
                        'key': fields['project']['key'],
                        'name': fields['project']['name'],
                        'simplified': fields['project'].get('simplified', False),
                        'projectTypeKey': fields['project']['projectTypeKey']
                    }
                )

                creator_obj = self.ensure_user(fields["creator"])
                assignee_obj = self.ensure_user(fields.get("assignee"))
                reporter_obj = self.ensure_user(fields.get("reporter"))

                parent_issue_id = fields.get('parent', {}).get('id')
                parent_issue_obj = None
                if parent_issue_id:
                    parent_issue_obj = JiraIssue.objects.filter(issue_id=parent_issue_id).first()

                issue_obj, _ = JiraIssue.objects.update_or_create(
                    issue_id=issue_id,
                    defaults={
                        "issue_key": issue_key,
                        "project": project_obj,
                        "created": parse_datetime(fields["created"]),
                        "updated": parse_datetime(fields["updated"]),
                        "status": fields["status"]["name"],
                        "priority": fields["priority"]["name"] if fields.get("priority") else None,
                        "assignee": assignee_obj,
                        "creator": creator_obj,
                        "reporter": reporter_obj,
                        "summary": fields["summary"],
                        "description": description,
                        "duedate": parse_datetime(fields["duedate"]) if fields.get("duedate") else None,
                        "timeoriginalestimate": fields.get("timeoriginalestimate"),
                        "timeestimate": fields.get("timeestimate"),
                        "timespent": fields.get("timespent"),
                        "time_mined": current_timestamp,
                        "parent_issue": parent_issue_obj
                    }
                )

                JiraIssueType.objects.update_or_create(
                    issue=issue_obj,
                    defaults={
                        'issuetype': fields['issuetype']['name'],
                        'issuetype_description': fields['issuetype'].get('description', ''),
                        'hierarchyLevel': fields['issuetype'].get('hierarchyLevel', 0),
                        'subtask': fields['issuetype'].get('subtask', False)
                    }
                )

                self.log_progress(f"Mining issue {issue_count} of {total_issues_count}. Key: {issue_key} - {fields['summary']}")



                # Sub-tables
                self.save_comments(issue_key, issue_obj)
                self.save_history(issue_key, issue_obj)
                self.save_activity(issue_key, issue_obj)
                self.save_checklist(issue_key, issue_obj)
                self.save_commits(issue_key, issue_obj)
                self.save_sprints(fields, issue_obj)

            total_collected += len(issues)
            start_at += max_results
            if len(issues) < max_results:
                break

        return {"status": f"Collected {total_collected} issues successfully.", "total_issues": total_collected}


    def get_commits_for_issue(self, issue_key):
        # Buscar o id numérico da issue
        issue_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}?fields=id"
        response = requests.get(issue_url, headers=self.headers, auth=self.auth)
        if response.status_code != 200:
            return []
        issue_id = response.json().get('id')
        if not issue_id:
            return []

        # Buscar os commits usando o id
        jira_commits_url = f"https://{self.jira_domain}/rest/dev-status/latest/issue/detail?issueId={issue_id}&applicationType=GitHub&dataType=repository"
        response = requests.get(jira_commits_url, headers=self.headers, auth=self.auth)
        if response.status_code != 200:
            return []

        details = response.json().get('detail', [])
        commits = []

        for detail in details:
            repositories = detail.get('repositories', [])
            for repo in repositories:
                for commit in repo.get('commits', []):
                    commits.append({
                        'id': commit.get('id'),
                        'message': commit.get('message'),
                        'author': commit.get('author', {}).get('name'),
                        'author_email': commit.get('author', {}).get('emailAddress'),
                        'url': commit.get('url')
                    })
        return commits


    def get_comments_for_issue(self, issue_key):
        """
        Collects comments for a Jira issue.
        
        Args:
            issue_key (str): The issue key (e.g., PROJ-123)
            
        Returns:
            list: List of comments with their information
        """
        comments_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}/comment"
        
        response = requests.get(comments_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_comments_for_issue(issue_key)
            
        if response.status_code != 200:
            self.log_progress(f" Problem collecting comments for {issue_key}: {response.status_code}")

            return []
            
        comments_data = response.json()
        comments = []
        
        for comment in comments_data.get('comments', []):
            comments.append({
                'id': comment.get('id'),
                'body': self.extract_words_from_description(comment.get('body', '')),
                'author': comment.get('author', {}).get('displayName'),
                'created': comment.get('created'),
                'updated': comment.get('updated'),
                'reactions': comment.get('reactions', {})
            })
            
        return comments


    def get_issue_history(self, issue_key):
        """
        Collects the change history of a Jira issue.
        
        Args:
            issue_key (str): The issue key (e.g., PROJ-123)
            
        Returns:
            list: List of changes with their information
        """
        history_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}?expand=changelog"
        
        response = requests.get(history_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_issue_history(issue_key)
            
        if response.status_code != 200:
            self.log_progress(f"Problem collecting history for {issue_key}: {response.status_code}")

            return []
            
        history_data = response.json()
        history = []
        
        for change in history_data.get('changelog', {}).get('histories', []):
            history.append({
                'id': change.get('id'),
                'author': change.get('author', {}).get('displayName'),
                'created': change.get('created'),
                'items': [
                    {
                        'field': item.get('field'),
                        'fieldtype': item.get('fieldtype'),
                        'from': item.get('from'),
                        'fromString': item.get('fromString'),
                        'to': item.get('to'),
                        'toString': item.get('toString')
                    } for item in change.get('items', [])
                ]
            })
            
        return history
    

    def get_activity_log(self, issue_key):
        """
        Collects the activity log of a Jira issue, focusing on:
        - Status changes
        - Resolution updates
        - Estimate updates
        - Time logs
        
        Args:
            issue_key (str): The issue key (e.g., PROJ-123)
            
        Returns:
            list: List of activities with their information
        """
        # First, get the complete history of the issue
        history_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}?expand=changelog"
        
        response = requests.get(history_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_activity_log(issue_key)
            
        if response.status_code != 200:
            self.log_progress(f"Problem collecting activity log for {issue_key}: {response.status_code}")

            return []
            
        history_data = response.json()
        activities = []
        
        # Process the history of changes
        for change in history_data.get('changelog', {}).get('histories', []):
            author = change.get('author', {}).get('displayName')
            created = change.get('created')
            
            for item in change.get('items', []):
                field = item.get('field')
                from_value = item.get('fromString')
                to_value = item.get('toString')
                
                # Status changes
                if field == 'status':
                    activities.append({
                        'type': 'status_change',
                        'author': author,
                        'created': created,
                        'from': from_value,
                        'to': to_value,
                        'description': f"{author} changed Status {from_value} → {to_value}"
                    })
                
                # Resolution updates
                elif field == 'resolution':
                    from_text = from_value if from_value else "None"
                    to_text = to_value if to_value else "Done"
                    activities.append({
                        'type': 'resolution_change',
                        'author': author,
                        'created': created,
                        'from': from_text,
                        'to': to_text,
                        'description': f"{author} updated Resolution {from_text} → {to_text}"
                    })
                
                # Estimate updates
                elif field == 'timeestimate' or field == 'remainingEstimate':
                    from_hours = str(int(float(from_value or '0') / 3600)) + 'H' if from_value else '0H'
                    to_hours = str(int(float(to_value or '0') / 3600)) + 'H' if to_value else '0H'
                    activities.append({
                        'type': 'estimate_change',
                        'author': author,
                        'created': created,
                        'from': from_hours,
                        'to': to_hours,
                        'description': f"{author} updated Remaining Work Estimate {from_hours} → {to_hours}"
                    })
                
                # Time log
                elif field == 'timespent':
                    time_spent = str(int(float(to_value or '0') / 3600)) + 'h'
                    activities.append({
                        'type': 'time_logged',
                        'author': author,
                        'created': created,
                        'time': time_spent,
                        'description': f"{author} logged {time_spent}"
                    })
        
        # Sort activities by creation date (newest first)
        activities.sort(key=lambda x: x['created'], reverse=True)
        return activities
        

    def get_checklist(self, issue_key):
        """
        Collects the checklist of a Jira issue.
        
        Args:
            issue_key (str): The issue key (e.g., PROJ-123)
            
        Returns:
            list: List of checklist items with their information
        """
        # Note: The Jira API does not have a specific endpoint for checklists
        # We will try to get this from custom fields or the description
        issue_url = f"https://{self.jira_domain}/rest/api/3/issue/{issue_key}"
        
        response = requests.get(issue_url, headers=self.headers, auth=self.auth)
        
        if self.handle_rate_limit(response):
            return self.get_checklist(issue_key)
            
        if response.status_code != 200:
            self.log_progress(f"Problem collecting checklist for {issue_key}: {response.status_code}")

            return []
            
        issue_data = response.json()
        checklist = []
        
        # Check for a custom field for the checklist
        fields = issue_data.get('fields', {})
        
        # Look for fields that may contain the checklist
        for field_id, field_value in fields.items():
            if isinstance(field_value, dict) and field_value.get('type') == 'checklist':
                for item in field_value.get('items', []):
                    checklist.append({
                        'id': item.get('id'),
                        'text': item.get('text'),
                        'status': item.get('status'),
                        'created': item.get('created'),
                        'updated': item.get('updated'),
                        'completed': item.get('completed'),
                        'completed_by': item.get('completedBy', {}).get('displayName') if item.get('completedBy') else None
                    })
        
        # If no checklist field was found, try to extract from the description
        if not checklist and 'description' in fields:
            description = fields.get('description', {})
            if description and 'content' in description:
                # Look for checklist items in the description
                checklist_items = self.extract_checklist_from_description(description)
                if checklist_items:
                    checklist = checklist_items
        
        return checklist
    

    def extract_checklist_from_description(self, description):
        """
        Tries to extract checklist items from the description of an issue.
        
        Args:
            description (dict): The issue description in JSON format
            
        Returns:
            list: List of checklist items extracted from the description
        """
        checklist_items = []
        
        def traverse_content(content):
            if isinstance(content, list):
                for item in content:
                    traverse_content(item)
            elif isinstance(content, dict):
                # Check if it is a checklist item
                if content.get('type') == 'checkbox':
                    checklist_items.append({
                        'text': content.get('text', ''),
                        'status': 'completed' if content.get('checked', False) else 'pending',
                        'created': None,  # We don't have this information in the description
                        'updated': None,
                        'completed': content.get('checked', False),
                        'completed_by': None
                    })
                # Continue traversing other keys
                if 'content' in content:
                    traverse_content(content['content'])
        
        traverse_content(description.get('content', []))
        return checklist_items
    

    def get_custom_fields_mapping(self):
        url = f"https://{self.jira_domain}/rest/api/3/field"
        response = requests.get(url, headers=self.headers, auth=self.auth)

        if self.handle_rate_limit(response):
            return self.get_custom_fields_mapping()

        if response.status_code != 200:
            raise Exception(f"Failed to get custom fields: {response.status_code} - {response.text}")

        fields = response.json()
        return {field['id']: field['name'] for field in fields if field['id'].startswith('customfield_')}
        

    def extract_words_from_description(self, description):
        """
        Extracts all words from the description of a Jira issue, handling cases where the field is empty or nonexistent.
        
        Args:
            description (dict): The JSON representing the issue description.
            
        Returns:
            str: A string containing all the extracted words, separated by space. Returns an empty string if the field doesn't exist or is empty.
        """
        if not description or "content" not in description:
            # Returns empty if the description is None, empty, or does not contain the "content" field
            return ""

        words = []

        def traverse_content(content):
            if isinstance(content, list):
                for item in content:
                    traverse_content(item)
            elif isinstance(content, dict):
                # If the content is a dictionary, check if it contains the "text" key
                if "text" in content and isinstance(content["text"], str):
                    words.append(content["text"])
                # Continue traversing other keys
                if "content" in content:
                    traverse_content(content["content"])

        # Start traversing the "content" structure in the description
        traverse_content(description.get("content", []))

        # Return the words concatenated into a single string
        return " ".join(words)


    def replace_custom_fields_with_names(self, issue_json, custom_fields_mapping):
        if 'fields' not in issue_json:
            return issue_json
        
        fields = issue_json['fields']
        updated_fields = {}
        
        for key, value in fields.items():
            # If the field is a customfield, replace it with the name
            if key in custom_fields_mapping:
                new_key = custom_fields_mapping[key]
            else:
                new_key = key
            updated_fields[new_key] = value
        
        issue_json['fields'] = updated_fields
        return issue_json


    def validate_and_parse_date(self, date_string):
        formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M"]
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {date_string}. Expected formats are: 'yyyy-MM-dd' or 'yyyy-MM-dd HH:mm'.")
    

    def ensure_user(self, user_data):
        if not user_data:
            return None

        user_obj, _ = JiraUser.objects.get_or_create(
            accountId=user_data['accountId'],
            defaults={
                'displayName': user_data.get('displayName', ''),
                'emailAddress': user_data.get('emailAddress', ''),
                'active': user_data.get('active', True),
                'timeZone': user_data.get('timeZone', 'UTC'),
                'accountType': user_data.get('accountType', 'atlassian')
            }
        )
        return user_obj


    def save_comments(self, issue_key, issue_obj):
        comments = self.get_comments_for_issue(issue_key)
        for c in comments:
            author_obj = self.ensure_user({
                'accountId': f"temp_{(c.get('author') or 'unknown').replace(' ', '_')}",
                'displayName': c.get('author') or 'Unknown',
                'emailAddress': '',
                'active': True,
                'timeZone': 'UTC',
                'accountType': 'atlassian'
            })

            JiraComment.objects.update_or_create(
                id=c['id'],
                defaults={
                    'issue': issue_obj,
                    'author': author_obj,
                    'body': c['body'],
                    'created': parse_datetime(c['created']),
                    'updated': parse_datetime(c['updated'])
                }
            )


    def save_history(self, issue_key, issue_obj):
        history_list = self.get_issue_history(issue_key)
        for h in history_list:
            author_obj = self.ensure_user({
                'accountId': f"temp_{(h.get('author') or 'unknown').replace(' ', '_')}",
                'displayName': h.get('author') or 'Unknown',
                'emailAddress': '',
                'active': True,
                'timeZone': 'UTC',
                'accountType': 'atlassian'
            })
            history_obj, _ = JiraHistory.objects.update_or_create(
                id=h['id'],
                defaults={
                    'issue': issue_obj,
                    'author': author_obj,
                    'created': parse_datetime(h['created'])
                }
            )
            for item in h['items']:
                JiraHistoryItem.objects.update_or_create(
                    history=history_obj,
                    field=item['field'],
                    defaults={
                        'fieldtype': item['fieldtype'],
                        'from_value': item['from'],
                        'to_value': item['to'],
                        'fromString': item['fromString'],
                        'toString': item['toString']
                    }
                )


    def save_activity(self, issue_key, issue_obj):
        activities = self.get_activity_log(issue_key)
        for a in activities:
            author_obj = self.ensure_user({
                'accountId': f"temp_{(a.get('author') or 'unknown').replace(' ', '_')}",
                'displayName': a.get('author') or 'Unknown',
                'emailAddress': '',
                'active': True,
                'timeZone': 'UTC',
                'accountType': 'atlassian'
            })
            JiraActivityLog.objects.create(
                issue=issue_obj,
                to_value=a.get('to'),
                from_value=a.get('from'),
                author=author_obj,
                created=parse_datetime(a['created']),
                description=a['description'][:300]
            )


    def save_checklist(self, issue_key, issue_obj):
        checklist = self.get_checklist(issue_key)
        if checklist:
            JiraChecklist.objects.update_or_create(
                issue=issue_obj,
                defaults={
                    'checklist': checklist,
                    'progress': f"Checklist: {sum(1 for i in checklist if i['completed'])}/{len(checklist)}",
                    'completed': all(i['completed'] for i in checklist)
                }
            )


    def save_commits(self, issue_key, issue_obj):
        commits = self.get_commits_for_issue(issue_key)
        for c in commits:
            JiraCommit.objects.update_or_create(
                sha=c['id'],
                defaults={
                    'issue': issue_obj,
                    'author': c.get('author', ''),
                    'author_email': c.get('authorEmail', ''),
                    'message': c.get('message'),
                    # repository: tentamos mapear para um GitHubMetadata existente pelo html_url
                    # Caso não exista, deixamos como None
                    'repository': None,
                    'timestamp': timezone.now()  # Ideally parse from data if available
                }
            )
                
                
    def save_sprints(self, fields, issue_obj):      
        sprints_data = fields.get("sprint")
        if not sprints_data:
            return

        if isinstance(sprints_data, dict):  # If it comes as a single dict
            sprints_data = [sprints_data]

        for sprint in sprints_data:
            try:
                sprint_obj, _ = JiraSprint.objects.update_or_create(
                    id=sprint["id"],
                    defaults={
                        "name": sprint["name"],
                        "goal": sprint.get("goal", ""),
                        "state": sprint.get("state"),
                        "boardId": sprint.get("originBoardId", 0),
                        "startDate": parse_datetime(sprint.get("startDate")) if sprint.get("startDate") else None,
                        "endDate": parse_datetime(sprint.get("endDate")) if sprint.get("endDate") else None,
                        "completeDate": parse_datetime(sprint.get("completeDate")) if sprint.get("completeDate") else None,
                    }
                )
                issue_obj.sprints.add(sprint_obj)


            except Exception as e:
                self.log_progress(f"Problem on saving sprint for {issue_obj.issue_key}: {e}")




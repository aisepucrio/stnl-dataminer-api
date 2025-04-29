import os
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from .models import JiraIssue
from django.utils.dateparse import parse_datetime
from urllib.parse import quote
import time
import traceback
from dotenv import load_dotenv
from django.utils import timezone

class JiraMiner:
    def __init__(self, jira_domain):
        load_dotenv()
        self.jira_domain = jira_domain.strip()
        print(f"DEBUG received domain in JiraMiner: '{self.jira_domain}'", flush=True)

        # Loading tokens
        self.tokens = [token.strip() for token in os.getenv("JIRA_API_TOKEN", "").split(",") if token.strip()]
        self.jira_email = os.getenv("JIRA_EMAIL")
        self.current_token_index = 0

        if not self.tokens or not self.jira_email:
            raise Exception("JIRA_API_TOKEN and JIRA_EMAIL must be correctly configured in .env")

        self.headers = {"Accept": "application/json"}
        self.update_auth()
        self.verify_token()
        
    def update_auth(self):
        self.auth = HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])

    def _get_auth(self):
        return HTTPBasicAuth(self.jira_email, self.tokens[self.current_token_index])

    def switch_token(self):
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth()
        print(f"[JiraMiner] 🔁 Switching to token {self.current_token_index + 1}/{len(self.tokens)}", flush=True)

    def verify_token(self):
        for _ in range(len(self.tokens)):
            try:
                url = f"https://{self.jira_domain}/rest/api/3/myself"
                response = requests.get(url, headers=self.headers, auth=self.auth)
                if response.status_code == 200:
                    print(f"[JiraMiner] ✅ Token {self.current_token_index + 1} is valid", flush=True)
                    return
                else:
                    print(f"[JiraMiner] ⚠️ Token {self.current_token_index + 1} is invalid: {response.status_code}", flush=True)
            except Exception as e:
                print(f"[JiraMiner] ❌ Error verifying token {self.current_token_index + 1}: {e}", flush=True)

            self.switch_token()

        raise Exception("❌ No valid Jira token found.")

    def handle_rate_limit(self, response):
        if response.status_code == 429 or "rate limit" in response.text.lower():
            print("[JiraMiner] 🚫 Rate limit reached. Trying next token...", flush=True)
            original_index = self.current_token_index

            for _ in range(len(self.tokens)):
                self.switch_token()
                retry = requests.get(response.request.url, headers=self.headers, auth=self.auth)
                if retry.status_code != 429:
                    print("[JiraMiner] ✅ New token worked!", flush=True)
                    return True

            # If no token worked, wait for 60 seconds
            print("[JiraMiner] 🕒 All tokens hit the limit. Waiting for 60 seconds...", flush=True)
            time.sleep(60)
            return True

        return False

    def collect_jira_issues(self, project_key, issuetypes, start_date=None, end_date=None):
        max_results, start_at, total_collected = 100, 0, 0
        custom_fields_mapping = self.get_custom_fields_mapping()

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

        while True:
            jira_url = f"https://{self.jira_domain}/rest/api/3/search?jql={encoded_jql}&startAt={start_at}&maxResults={max_results}"
            response = requests.get(jira_url, headers=self.headers, auth=self.auth)

            if self.handle_rate_limit(response):
                continue

            if response.status_code != 200:
                return {"error": f"Failed to collect issues: {response.status_code} - {response.text}"}

            issues = response.json().get('issues', [])
            if not issues:
                break

            for issue_data in issues:
                current_timestamp = timezone.make_aware(datetime.fromtimestamp(time.time()))
                description = self.extract_words_from_description(issue_data['fields'].get('description', ''))
                issue_data = self.replace_custom_fields_with_names(issue_data, custom_fields_mapping)
                commits = self.get_commits_for_issue(issue_data['key'])
                comments = self.get_comments_for_issue(issue_data['key'])
                
                # Collecting new data
                history = self.get_issue_history(issue_data['key'])
                activity_log = self.get_activity_log(issue_data['key'])
                checklist = self.get_checklist(issue_data['key'])

                JiraIssue.objects.update_or_create(
                    issue_id=issue_data['id'],
                    defaults={
                        'issue_key': issue_data['key'],
                        'issuetype': issue_data['fields']['issuetype']['name'],
                        'issuetype_description': issue_data['fields']['issuetype']['description'],
                        'summary': issue_data['fields']['summary'],
                        'description': description,
                        'created': issue_data['fields']['created'],
                        'updated': issue_data['fields']['updated'],
                        'status': issue_data['fields']['status']['name'],
                        'priority': issue_data['fields']['priority']['name'] if issue_data['fields'].get('priority') else None,
                        'project': project_key,
                        'creator': issue_data['fields']['creator']['displayName'],
                        'assignee': issue_data['fields']['assignee']['displayName'] if issue_data['fields'].get('assignee') else None,
                        'all_fields': issue_data['fields'],
                        'time_mined': current_timestamp,
                        'commits': commits,
                        'comments': comments,
                        'history': history,
                        'activity_log': activity_log,
                        'checklist': checklist
                    }
                )

            total_collected += len(issues)
            start_at += max_results
            if len(issues) < max_results:
                break

        return {"status": f"Collected {total_collected} issues successfully.", "total_issues": total_collected}

    def get_commits_for_issue(self, issue_key):
        jira_commits_url = f"https://{self.jira_domain}/rest/dev-status/1.0/issue/detail?issueId={issue_key}&applicationType=git&dataType=repository"

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
            print(f"[JiraMiner] ⚠️ Error collecting comments for issue {issue_key}: {response.status_code}", flush=True)
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
            print(f"[JiraMiner] ⚠️ Error collecting history for issue {issue_key}: {response.status_code}", flush=True)
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
            print(f"[JiraMiner] ⚠️ Error collecting activity log for issue {issue_key}: {response.status_code}", flush=True)
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
            print(f"[JiraMiner] ⚠️ Error collecting checklist for issue {issue_key}: {response.status_code}", flush=True)
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

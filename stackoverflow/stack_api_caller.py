import requests
from dotenv import load_dotenv
import os
import json

# Load the API key from .env file
load_dotenv()
API_KEY = os.getenv("STACK_API_KEY")
ACCESS_TOKEN = os.getenv("STACK_ACCESS_TOKEN")
SITE = "stackoverflow"
BASE_URL = "https://api.stackexchange.com/2.3"

# Use a rich filter to get extended info (title, body, score, comments, etc.)
# FILTER = "!)Rm-Ag_ZixQvpDE.3s.paOrN"
PAGE_SIZE = 1


def fetch_questions():
    FILTER = "!2xWEp6FHz8hT56C1LBQjFx25D4Dzmr*3(8D4ngdB5g"
    url = f"{BASE_URL}/questions"
    params = {
        "site": SITE,
        "key": API_KEY,
        "pagesize": PAGE_SIZE,
        "access_token": ACCESS_TOKEN,
        "order": "desc",
        "sort": "creation",
        "filter": FILTER
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_answers():
    FILTER = "!)Rm-Ag_ZixQvpDE.3s.paOrN"
    url = f"{BASE_URL}/answers"
    params = {
        "site": SITE,
        "key": API_KEY,
        "pagesize": PAGE_SIZE,
        "access_token": ACCESS_TOKEN,
        "order": "desc",
        "sort": "creation",
        "filter": FILTER
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_tags():
    FILTER = "!6WPIommryG6wE"
    url = f"{BASE_URL}/tags"
    params = {
        "site": SITE,
        "key": API_KEY,
        "pagesize": PAGE_SIZE,
        "access_token": ACCESS_TOKEN,
        "order": "desc",
        "sort": "popular",
        "filter": FILTER
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_users():
    FILTER = "!T3Audpe81eZTLAf2z2"  # Filter for user profile data
    url = f"{BASE_URL}/users"
    params = {
        "site": SITE,
        "key": API_KEY,
        "pagesize": PAGE_SIZE,
        "access_token": ACCESS_TOKEN,
        "order": "desc",
        "sort": "reputation",
        "filter": FILTER
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print("Hey")
    # print("🔍 Fetching recent questions...")
    # questions = fetch_questions()
    
    # # Pretty print the first question's fields
    # if questions.get("items"):
    #     first_question = questions["items"][0]
    #     print("\nFirst Question Details:")
    #     print(json.dumps(first_question, indent=2))
    
    # print("\n🧠 Fetching recent answers...")
    # answers = fetch_answers()
    
    # # Pretty print the first answer's fields
    # if answers.get("items"):
    #     first_answer = answers["items"][0]
    #     print("\nFirst Answer Details:")
    #     print(json.dumps(first_answer, indent=2))

    # tags = fetch_tags()
    # if tags.get("items"):
    #     print(json.dumps(tags["items"][0], indent=2))

    # users = fetch_users()
    # if users.get("items"):
    #     print(json.dumps(users["items"][0], indent=2))


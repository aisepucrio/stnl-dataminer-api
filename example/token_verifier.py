import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import argparse

load_dotenv()

def check_github_token(token):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get('https://api.github.com/rate_limit', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        rate = data['rate']
        
        total_limit = rate['limit']
        remaining = rate['remaining']
        reset_time = datetime.fromtimestamp(rate['reset'])
        
        print(f"GitHub Token Status:")
        print(f"Total request limit: {total_limit}")
        print(f"Remaining requests: {remaining}")
        print(f"Limit will reset at: {reset_time}")
        
        return remaining
    else:
        print(f"Error checking token. Status code: {response.status_code}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check the status of a GitHub token')
    parser.add_argument('-i', '--index', type=int, default=0,
                        help='Index of the token to check (starting at 0)')
    
    args = parser.parse_args()
    
    token = os.getenv('GITHUB_TOKENS')
    token = token.split(',')
    
    if args.index >= len(token):
        print(f"Error: index {args.index} is greater than the number of available tokens ({len(token)})")
        exit(1)
        
    token = token[args.index]
    check_github_token(token)
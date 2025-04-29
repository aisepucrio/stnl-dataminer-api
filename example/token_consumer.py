import os
import requests
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import multiprocessing

load_dotenv()

def make_github_request(headers, request_number, print_lock):
    url = "https://api.github.com/user"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        with print_lock:
            print(f"Request #{request_number}")
            print(f"Status: {response.status_code}")
            print(f"Remaining: {response.headers.get('X-RateLimit-Remaining', 0)}")
            print("-" * 40)
            
        return int(response.headers.get("X-RateLimit-Remaining", 0))
    
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(f"Error in request {request_number}: {str(e)}")
        return 0

def frenetic_github_requests():
    token = os.getenv("GITHUB_TOKENS")

    tokens = token.split(",")

    token = tokens[1]
    
    if not token:
        raise ValueError("Token not found in .env file")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print_lock = Lock()
    
    # Calculate the maximum number of threads
    max_workers = min(32, (multiprocessing.cpu_count() * 4))  # Limiting to 32 for safety
    print(f"Starting with {max_workers} concurrent threads")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        request_number = 0
        futures = []
        
        while True:
            # Create several requests at once
            for _ in range(max_workers):
                request_number += 1
                future = executor.submit(make_github_request, headers, request_number, print_lock)
                futures.append(future)
            
            # Check completed futures
            for completed_future in [f for f in futures if f.done()]:
                remaining = completed_future.result()
                if remaining <= 0:
                    print("⚠️ Rate limit reached! Stopping all threads...")
                    executor._threads.clear()
                    return
            
            # Remove completed futures from the list
            futures = [f for f in futures if not f.done()]
            
            # Reduce the interval between batches of requests
            time.sleep(0.5)

# Execute the function
if __name__ == "__main__":
    frenetic_github_requests()
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
from .utils import APIMetrics


class BaseMiner:
    """Base class for GitHub miners with authentication and rate limiting capabilities"""
    
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        self.tokens: List[str] = []
        self.current_token_index = 0
        
        result = self.load_tokens()
        if not result['success']:
            raise Exception(f"Failed to initialize GitHub tokens: {result['error']}")
        
        print(f"✅ GitHub tokens initialized successfully:")
        print(f"   - Total tokens loaded: {result['tokens_loaded']}")
        print(f"   - Valid tokens: {result['valid_tokens']}")
        print(f"   - Selected token: {result['selected_token']['index'] + 1} (with {result['selected_token']['remaining']} requests available)")
        
        self.update_auth_header()

    def verify_token(self) -> Dict[str, Any]:
        """Verifies if the current token is valid and has proper permissions"""
        try:
            url = "https://api.github.com/rate_limit"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 401:
                return {
                    'valid': False,
                    'error': 'Token invalid or expired',
                    'status_code': response.status_code
                }
            
            if response.status_code == 403:
                return {
                    'valid': False,
                    'error': 'Token does not have sufficient permissions',
                    'status_code': response.status_code
                }
            
            if response.status_code != 200:
                return {
                    'valid': False,
                    'error': f'Error verifying token: {response.status_code}',
                    'status_code': response.status_code
                }

            data = response.json()
            rate = data['rate']
            
            return {
                'valid': True,
                'limit': rate['limit'],
                'remaining': rate['remaining'],
                'reset': rate['reset']
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f'Error verifying token: {str(e)}',
                'status_code': None
            }

    def load_tokens(self) -> Dict[str, Any]:
        """Loads GitHub tokens from .env file or environment variables"""
        load_dotenv()
        tokens_str = os.getenv("GITHUB_TOKENS")
        if not tokens_str:
            return {
                'success': False,
                'error': 'No tokens found. Make sure GITHUB_TOKENS is configured in the .env file'
            }
        
        self.tokens = [token.strip() for token in tokens_str.split(",") if token.strip()]
        if not self.tokens:
            return {
                'success': False,
                'error': 'No valid tokens found after processing'
            }
        
        print(f"{len(self.tokens)} tokens loaded.", flush=True)
        
        valid_tokens = []
        for i, token in enumerate(self.tokens):
            self.current_token_index = i
            self.update_auth_header()
            result = self.verify_token()
            
            if result['valid']:
                valid_tokens.append({
                    'index': i,
                    'limit': result['limit'],
                    'remaining': result['remaining']
                })
        
        if not valid_tokens:
            return {
                'success': False,
                'error': 'No valid tokens found after verification'
            }
        
        best_token = max(valid_tokens, key=lambda x: x['remaining'])
        self.current_token_index = best_token['index']
        self.update_auth_header()
        
        return {
            'success': True,
            'tokens_loaded': len(self.tokens),
            'valid_tokens': len(valid_tokens),
            'selected_token': best_token
        }

    def update_auth_header(self) -> None:
        """Updates the Authorization header with the current token"""
        if self.tokens:
            self.headers['Authorization'] = f'token {self.tokens[self.current_token_index]}'

    def switch_token(self) -> None:
        """Switches to the next available token"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.update_auth_header()
        print(f"Switching to the next token. Current token: {self.current_token_index + 1}/{len(self.tokens)}", flush=True)

    def wait_for_rate_limit_reset(self, endpoint_type: str = 'core') -> bool:
        """Waits for the rate limit to reset with a safety margin"""
        try:
            response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
            metrics = APIMetrics()
            
            # Use the unified function to show status
            self.check_and_log_rate_limit(response, metrics, endpoint_type, "Waiting for Reset")
            
            rate_limits = response.json()['resources'][endpoint_type]
            reset_time = int(rate_limits['reset'])
            current_time = int(time.time())
            
            # Adding 5 seconds safety margin
            wait_time = reset_time - current_time + 5
            
            if wait_time > 0:
                print(f"\n⏳ [RATE LIMIT] Waiting {wait_time} seconds for reset (including safety margin)...", flush=True)
                time.sleep(wait_time)
                print("✅ [RATE LIMIT] Reset complete! Resuming operations...\n", flush=True)
                
                response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
                if response.status_code == 200:
                    new_limits = response.json()['resources'][endpoint_type]
                    if int(new_limits['remaining']) > 0:
                        return True
                    else:
                        print("⚠️ [RATE LIMIT] Token not reset yet, waiting another 5 seconds...", flush=True)
                        time.sleep(5)
                        return True
        except Exception as e:
            print(f"❌ [RATE LIMIT] Error while waiting for reset: {str(e)}", flush=True)
            raise RuntimeError(f"Failed to wait for rate limit reset: {str(e)}")
        return False

    def handle_rate_limit(self, response: requests.Response, endpoint_type: str = 'core') -> bool:
        """Handles the rate limit based on the endpoint type"""
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
                
                print("\n" + "="*50)
                print("🚫 RATE LIMIT REACHED!")
                print(f"Endpoint type: {endpoint_type.upper()}")
                print(f"Reset scheduled for: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Waiting time required: {int(wait_time)} seconds")
                print("="*50 + "\n")
                
            if endpoint_type == 'search':
                print("[RATE LIMIT] Search limit reached. Waiting for reset...", flush=True)
                return self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Searching for an available alternative token...", flush=True)
                    best_token = self.find_best_available_token()
                    
                    if best_token is not None:
                        self.current_token_index = best_token
                        self.update_auth_header()
                        print(f"[RATE LIMIT] Alternative token found! Using token {best_token + 1}/{len(self.tokens)}", flush=True)
                        return True
                    else:
                        print("[RATE LIMIT] No alternative tokens available. Waiting for reset...", flush=True)
                        return self.wait_for_rate_limit_reset()
                else:
                    print("[RATE LIMIT] ⚠️ WARNING: Limit reached and no alternative tokens available!", flush=True)
                    return self.wait_for_rate_limit_reset()
        return False

    def find_best_available_token(self) -> Optional[int]:
        """
        Checks all tokens and returns the index of the best available token,
        or None if all tokens are unavailable.
        """
        best_token = None
        max_remaining = 0
        original_token_index = self.current_token_index

        for i in range(len(self.tokens)):
            # Skip the current token
            if i == original_token_index:
                continue

            self.current_token_index = i
            self.update_auth_header()

            try:
                response = requests.get("https://api.github.com/rate_limit", headers=self.headers)
                if response.status_code == 200:
                    rate_data = response.json()['resources']
                    core_remaining = int(rate_data['core']['remaining'])

                    # If a token with more requests available is found
                    if core_remaining > max_remaining:
                        max_remaining = core_remaining
                        best_token = i

                        # If a token with enough requests is found, use it immediately
                        if core_remaining > 100:
                            print(f"[TOKEN] Found token {i + 1} with {core_remaining} requests available", flush=True)
                            return i

            except Exception as e:
                print(f"Error checking token {i + 1}: {str(e)}", flush=True)

        # If no token with more than 100 requests was found but some are available
        if best_token is not None and max_remaining > 0:
            print(f"[TOKEN] Using token {best_token + 1} with {max_remaining} requests remaining", flush=True)
            return best_token

        # If no available token was found, revert to the original token
        self.current_token_index = original_token_index
        self.update_auth_header()
        return None

    def check_and_log_rate_limit(self, response: requests.Response, metrics: APIMetrics, 
                                endpoint_type: str = 'core', context: str = "") -> bool:
        """Unified function to check and log rate limit status"""
        metrics.update_rate_limit(response.headers, endpoint_type)
        
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            print("\n" + "="*50)
            print(f"🚫 RATE LIMIT REACHED! {context}")
            print(f"Endpoint type: {endpoint_type.upper()}")
            
            reset_time = response.headers.get('X-RateLimit-Reset')
            if reset_time:
                reset_datetime = datetime.fromtimestamp(int(reset_time))
                wait_time = (reset_datetime - datetime.now()).total_seconds()
                print(f"Reset scheduled for: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Wait time required: {int(wait_time)} seconds")
            print("="*50 + "\n")
            
            if endpoint_type == 'search':
                print("[RATE LIMIT] Search limit reached. Waiting for reset...", flush=True)
                self.wait_for_rate_limit_reset('search')
            else:
                if len(self.tokens) > 1:
                    print("[RATE LIMIT] Core limit reached. Switching to next token...", flush=True)
                    self.switch_token()
                    self.verify_token()
                else:
                    print("[RATE LIMIT] ⚠️ WARNING: Limit reached and no alternative tokens available!", flush=True)
                    self.wait_for_rate_limit_reset()
            return True

        remaining = (metrics.search_limit_remaining if endpoint_type == 'search' 
                    else metrics.core_limit_remaining)
        if remaining and int(remaining) < 50:
            print(f"\n⚠️ WARNING: Only {remaining} requests remaining for the current token ({endpoint_type})", flush=True)
        
        return False 
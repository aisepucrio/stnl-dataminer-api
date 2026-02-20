import os
import requests
from typing import Dict

class TokenManager:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        self.current_token = self.tokens[0] if self.tokens else None
        
    def _load_tokens(self) -> list:
        """Load tokens from environment variables"""
        tokens_str = os.getenv("STACK_TOKENS", "")
        if not tokens_str:
            raise Exception("No STACK_TOKENS found in environment variables")
        
        tokens = [token.strip() for token in tokens_str.split(",") if token.strip()]
        if not tokens:
            raise Exception("No valid tokens found after processing")
            
        print(f"{len(tokens)} tokens loaded")
        return tokens
    
    def get_current_token(self) -> Dict[str, str]:
        """Get the current token configuration"""
        return {
            'key': self.current_token,
            'access_token': os.getenv("STACK_ACCESS_TOKEN")
        }
    
    def rotate_token(self) -> None:
        """Rotate to the next available token"""
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        self.current_token = self.tokens[self.current_token_index]
        print(f"Rotated to token {self.current_token_index + 1}/{len(self.tokens)}")
    
    def check_quota(self, response: requests.Response) -> bool:
        """Check if we need to rotate token based on remaining quota"""
        remaining = response.headers.get('quota-remaining')
        if remaining and int(remaining) < 100:
            print(f"Low quota remaining ({remaining}). Rotating token...")
            self.rotate_token()
            return True
        return False
    
    def verify_token(self) -> bool:
        """Verify if the current token is valid"""
        try:
            url = f"{self.base_url}/info"
            params = self.get_current_token()
            response = requests.get(url, params=params)
            return response.status_code == 200
        except Exception as e:
            print(f"Error verifying token: {str(e)}")
            return False 
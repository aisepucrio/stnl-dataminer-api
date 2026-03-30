import os
from typing import Any, Optional

from dotenv import load_dotenv
import praw


class BaseMiner:
    """Base class for Reddit miners with shared client and progress helpers."""

    def __init__(self, reddit_client: Optional[praw.Reddit] = None):
        self.reddit = reddit_client or self.create_reddit_client()

    def create_reddit_client(self) -> praw.Reddit:
        """Create a configured read-only Reddit client from environment variables."""
        load_dotenv()

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")

        if not all([client_id, client_secret, user_agent]):
            raise RuntimeError(
                "Missing Reddit credentials. Configure REDDIT_CLIENT_ID, "
                "REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT in the environment."
            )

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        reddit.read_only = True
        return reddit

    def sync_client(self, reddit_client: praw.Reddit) -> None:
        """Share the same Reddit client with specialized miners."""
        self.reddit = reddit_client

    def log_progress(self, message: str, task_obj: Optional[Any] = None) -> None:
        """Print progress and optionally persist it in the task row."""
        print(message, flush=True)
        if task_obj is not None:
            task_obj.operation = message
            task_obj.save(update_fields=["operation"])

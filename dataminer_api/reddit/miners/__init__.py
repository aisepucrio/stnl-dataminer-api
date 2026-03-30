from typing import Any, Dict, List, Optional

from .base import BaseMiner
from .comments import CommentsMiner
from .posts import PostsMiner


class RedditMiner(BaseMiner):
    """Facade that exposes the specialized Reddit miners through one entrypoint."""

    def __init__(self):
        super().__init__()
        self._posts_miner = PostsMiner(self.reddit)
        self._comments_miner = CommentsMiner(self.reddit)
        self._sync_client()

    def _sync_client(self) -> None:
        """Share the same configured PRAW client across specialized miners."""
        self._posts_miner.sync_client(self.reddit)
        self._comments_miner.sync_client(self.reddit)

    def get_posts(
        self,
        subreddits: Optional[List[str]] = None,
        search_queries: Optional[List[str]] = None,
        match_keywords: Optional[List[str]] = None,
        time_filter: str = "all",
        sort: str = "new",
        limit_per_query: int = 300,
        task_obj: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        self._sync_client()
        return self._posts_miner.get_posts(
            subreddits=subreddits,
            search_queries=search_queries,
            match_keywords=match_keywords,
            time_filter=time_filter,
            sort=sort,
            limit_per_query=limit_per_query,
            task_obj=task_obj,
        )

    def get_comments(
        self,
        posts: List[Dict[str, Any]],
        max_comments_per_post: int = 400,
        match_keywords: Optional[List[str]] = None,
        task_obj: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        self._sync_client()
        return self._comments_miner.get_comments(
            posts=posts,
            max_comments_per_post=max_comments_per_post,
            match_keywords=match_keywords,
            task_obj=task_obj,
        )


__all__ = ["RedditMiner", "BaseMiner", "PostsMiner", "CommentsMiner"]

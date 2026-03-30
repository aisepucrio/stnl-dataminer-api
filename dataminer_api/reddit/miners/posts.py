from typing import Any, Dict, List, Optional

from .base import BaseMiner
from .utils import (
    build_patterns,
    created_utc_to_iso,
    find_keywords,
    normalize_keywords,
)


class PostsMiner(BaseMiner):
    """Miner responsible for generic Reddit submission discovery and filtering."""

    def collect_posts_for_subreddit(
        self,
        subreddit_name: str,
        search_queries: Optional[List[str]] = None,
        match_keywords: Optional[List[str]] = None,
        time_filter: str = "all",
        sort: str = "new",
        limit_per_query: int = 300,
        task_obj: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Collect unique posts from a subreddit using generic search and filtering."""
        subreddit = self.reddit.subreddit(subreddit_name)
        collected: Dict[str, Dict[str, Any]] = {}
        normalized_keywords = normalize_keywords(match_keywords)
        keyword_patterns = build_patterns(normalized_keywords) if normalized_keywords else {}
        normalized_queries = normalize_keywords(search_queries)
        query_list: List[Optional[str]] = normalized_queries or [None]

        for query in query_list:
            if query is None:
                self.log_progress(
                    f"[reddit][posts] Fetching recent posts from r/{subreddit_name}",
                    task_obj,
                )
                submissions = subreddit.new(limit=limit_per_query)
            else:
                self.log_progress(
                    f"[reddit][posts] Searching r/{subreddit_name} with query '{query}'",
                    task_obj,
                )
                submissions = subreddit.search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit_per_query,
                )

            for submission in submissions:
                if submission.id in collected:
                    continue

                full_text = f"{submission.title}\n{submission.selftext}"
                matched_keywords = find_keywords(full_text, keyword_patterns)
                if normalized_keywords and not matched_keywords:
                    continue

                collected[submission.id] = {
                    "subreddit": subreddit_name,
                    "id": submission.id,
                    "title": submission.title,
                    "search_query": query,
                    "matched_keywords": ",".join(sorted(set(matched_keywords))),
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "created_iso": created_utc_to_iso(submission.created_utc),
                    "author": str(submission.author) if submission.author else None,
                    "url": submission.url,
                    "permalink": f"https://www.reddit.com{submission.permalink}",
                    "selftext": submission.selftext,
                }

        self.log_progress(
            f"[reddit][posts] r/{subreddit_name}: {len(collected)} unique posts collected",
            task_obj,
        )
        return collected

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
        """Collect posts across the configured subreddit list."""
        target_subreddits = normalize_keywords(subreddits)
        if not target_subreddits:
            raise ValueError("At least one subreddit must be provided.")

        posts_by_id: Dict[str, Dict[str, Any]] = {}

        for subreddit_name in target_subreddits:
            posts = self.collect_posts_for_subreddit(
                subreddit_name=subreddit_name,
                search_queries=search_queries,
                match_keywords=match_keywords,
                time_filter=time_filter,
                sort=sort,
                limit_per_query=limit_per_query,
                task_obj=task_obj,
            )
            posts_by_id.update(posts)

        all_posts = list(posts_by_id.values())
        self.log_progress(
            f"[reddit][posts] Total unique posts collected: {len(all_posts)}",
            task_obj,
        )
        return all_posts

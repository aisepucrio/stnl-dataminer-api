from typing import Any, Dict, List, Optional

from .base import BaseMiner
from .utils import build_patterns, created_utc_to_iso, find_keywords, normalize_keywords


class CommentsMiner(BaseMiner):
    """Miner responsible for generic Reddit comment extraction and filtering."""

    def get_comments(
        self,
        posts: List[Dict[str, Any]],
        max_comments_per_post: int = 400,
        match_keywords: Optional[List[str]] = None,
        task_obj: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        all_comments: List[Dict[str, Any]] = []
        normalized_keywords = normalize_keywords(match_keywords)
        keyword_patterns = build_patterns(normalized_keywords) if normalized_keywords else {}

        for post in posts:
            submission_id = post["id"]
            subreddit_name = post["subreddit"]
            self.log_progress(
                f"[reddit][comments] Collecting comments for r/{subreddit_name} / {submission_id}",
                task_obj,
            )

            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=None)

            count = 0
            for comment in submission.comments.list():
                if count >= max_comments_per_post:
                    break

                matched_keywords = find_keywords(comment.body, keyword_patterns)
                if normalized_keywords and not matched_keywords:
                    continue

                all_comments.append(
                    {
                        "subreddit": subreddit_name,
                        "submission_id": submission_id,
                        "comment_id": comment.id,
                        "parent_id": comment.parent_id,
                        "matched_keywords": ",".join(sorted(set(matched_keywords))),
                        "author": str(comment.author) if comment.author else None,
                        "body": comment.body,
                        "score": comment.score,
                        "created_utc": comment.created_utc,
                        "created_iso": created_utc_to_iso(comment.created_utc),
                        "comment_permalink": (
                            f"https://www.reddit.com{submission.permalink}{comment.id}"
                        ),
                    }
                )
                count += 1

            self.log_progress(
                f"[reddit][comments] r/{subreddit_name} / {submission_id}: {count} comments collected",
                task_obj,
            )

        self.log_progress(
            f"[reddit][comments] Total comments collected: {len(all_comments)}",
            task_obj,
        )
        return all_comments

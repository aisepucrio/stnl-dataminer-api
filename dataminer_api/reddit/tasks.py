from typing import Any, Dict, List, Optional

from celery import shared_task
from django.utils import timezone as dj_tz

from jobs.models import Task

from .miners import RedditMiner


def _reuse_or_create_task(self, *, defaults, task_pk=None):
    if task_pk:
        update_data = {**defaults, "task_id": self.request.id}
        update_data.pop("date_init", None)
        updated = Task.objects.filter(pk=task_pk).update(**update_data)
        if updated:
            return Task.objects.get(pk=task_pk), False
    return Task.objects.get_or_create(task_id=self.request.id, defaults=defaults)


def _base_task_defaults(operation: str) -> Dict[str, Any]:
    now = dj_tz.now()
    return {
        "operation": operation,
        "repository": "reddit",
        "type": "reddit_lookup",
        "status": "STARTED",
        "error": None,
        "date_init": now,
    }


@shared_task(bind=True)
def fetch_posts(
    self,
    subreddits: Optional[List[str]] = None,
    search_queries: Optional[List[str]] = None,
    match_keywords: Optional[List[str]] = None,
    time_filter: str = "all",
    sort: str = "new",
    limit_per_query: int = 300,
) -> List[Dict[str, Any]]:
    operation = "[reddit] Starting post collection"
    task_obj, _ = _reuse_or_create_task(
        self,
        defaults=_base_task_defaults(operation),
        task_pk=None,
    )
    self.update_state(
        state="STARTED",
        meta={"operation": operation, "status": "STARTED"},
    )

    miner = RedditMiner()
    try:
        posts = miner.get_posts(
            subreddits=subreddits,
            search_queries=search_queries,
            match_keywords=match_keywords,
            time_filter=time_filter,
            sort=sort,
            limit_per_query=limit_per_query,
            task_obj=task_obj,
        )
        task_obj.status = "SUCCESS"
        task_obj.date_end = dj_tz.now()
        task_obj.result = {"posts_count": len(posts)}
        task_obj.save(update_fields=["status", "date_end", "result"])
        return posts
    except Exception as exc:
        task_obj.status = "FAILURE"
        task_obj.date_end = dj_tz.now()
        task_obj.error = str(exc)
        task_obj.save(update_fields=["status", "date_end", "error"])
        raise


@shared_task(bind=True)
def fetch_comments(
    self,
    posts: List[Dict[str, Any]],
    max_comments_per_post: int = 400,
    match_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    operation = "[reddit] Starting comment collection"
    task_obj, _ = _reuse_or_create_task(
        self,
        defaults=_base_task_defaults(operation),
        task_pk=None,
    )
    self.update_state(
        state="STARTED",
        meta={"operation": operation, "status": "STARTED"},
    )

    miner = RedditMiner()
    try:
        comments = miner.get_comments(
            posts=posts,
            max_comments_per_post=max_comments_per_post,
            match_keywords=match_keywords,
            task_obj=task_obj,
        )
        task_obj.status = "SUCCESS"
        task_obj.date_end = dj_tz.now()
        task_obj.result = {"comments_count": len(comments)}
        task_obj.save(update_fields=["status", "date_end", "result"])
        return comments
    except Exception as exc:
        task_obj.status = "FAILURE"
        task_obj.date_end = dj_tz.now()
        task_obj.error = str(exc)
        task_obj.save(update_fields=["status", "date_end", "error"])
        raise


@shared_task(bind=True)
def fetch_posts_and_comments(
    self,
    subreddits: Optional[List[str]] = None,
    search_queries: Optional[List[str]] = None,
    match_keywords: Optional[List[str]] = None,
    time_filter: str = "all",
    sort: str = "new",
    limit_per_query: int = 300,
    max_comments_per_post: int = 400,
) -> Dict[str, List[Dict[str, Any]]]:
    operation = "[reddit] Starting post and comment collection"
    task_obj, _ = _reuse_or_create_task(
        self,
        defaults=_base_task_defaults(operation),
        task_pk=None,
    )
    self.update_state(
        state="STARTED",
        meta={"operation": operation, "status": "STARTED"},
    )

    miner = RedditMiner()
    try:
        posts = miner.get_posts(
            subreddits=subreddits,
            search_queries=search_queries,
            match_keywords=match_keywords,
            time_filter=time_filter,
            sort=sort,
            limit_per_query=limit_per_query,
            task_obj=task_obj,
        )
        comments = miner.get_comments(
            posts=posts,
            max_comments_per_post=max_comments_per_post,
            match_keywords=match_keywords,
            task_obj=task_obj,
        )
        task_obj.status = "SUCCESS"
        task_obj.date_end = dj_tz.now()
        task_obj.result = {
            "posts_count": len(posts),
            "comments_count": len(comments),
        }
        task_obj.save(update_fields=["status", "date_end", "result"])
        return {"posts": posts, "comments": comments}
    except Exception as exc:
        task_obj.status = "FAILURE"
        task_obj.date_end = dj_tz.now()
        task_obj.error = str(exc)
        task_obj.save(update_fields=["status", "date_end", "error"])
        raise

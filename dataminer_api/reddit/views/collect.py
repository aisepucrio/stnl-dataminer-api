import logging

from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.test import APIClient

from jobs.models import Task
from ..tasks import (
    fetch_comments,
    fetch_posts,
    fetch_posts_and_comments
)

logger = logging.getLogger(__name__)

class RedditViewSet(viewsets.ViewSet):
    """
    ViewSet responsible for starting and managing Reddit data collection jobs.
    """
"""
    @extend_schema(
        summary="Mine reddit posts",
        tags=["Reddit"],
        description="Endpoint to mine posts from a subreddit"
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "subreddits": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of subreddit names to mine (e.g., ['python', 'datascience']).",
                    },
                    "search_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of search queries to filter posts (e.g., ['machine learning', 'web scraping']).",
                    },
                    "match_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords that must be present in the post (e.g., ['praw', 'api']).",
                    },
                    "time_filter": {
                        "type": "string",
                        "enum": ["all", "day", "hour", "month", "week", "year"],
                        "default": "all",
                        "description": (
                            "Time filter for posts. Options: 'all' (default), 'day', 'hour', 'month', 'week', 'year'."
                            "\n\nExample: To mine posts from the last week, set this to 'week'."
                        ),
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["new", "hot", "top", "relevance"],
                        "default": "new",
                        "description": (
                            "Sorting method for posts. Options: 'new' (default), 'hot', 'top', 'relevance'."
                            "\n\nExample: To get the most relevant posts for a search query, set this to 'relevance'."
                        ),
                    },
                    "limit_per_query": {
                        "type": "integer",
                        "default": 300,
                        "description": (
                            "Maximum number of posts to retrieve per query. Default is 300."
                            "\n\nExample: To limit the results to 100 posts per query, set this to 100."
                        ),
                    },
                },
                # Make all fields optional since they have defaults or can be empty
                # and add validation in the view if needed
            }
        },
        responses={200: OpenApiResponse(description="Job started successfully")},
    )
        """
from rest_framework import serializers

from .models import RedditComment, RedditPost


class RedditCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedditComment
        fields = "__all__"


class RedditPostSerializer(serializers.ModelSerializer):
    comments = RedditCommentSerializer(many=True, read_only=True)

    class Meta:
        model = RedditPost
        fields = "__all__"


class RedditPostsCollectSerializer(serializers.Serializer):
    subreddits = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of subreddit names to mine.",
    )
    search_queries = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="Optional list of search queries used inside each subreddit.",
    )
    match_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="Optional list of keywords that must match the post content.",
    )
    time_filter = serializers.ChoiceField(
        choices=["all", "day", "hour", "month", "week", "year"],
        default="all",
        required=False,
    )
    sort = serializers.ChoiceField(
        choices=["new", "hot", "top", "relevance"],
        default="new",
        required=False,
    )
    limit_per_query = serializers.IntegerField(min_value=1, default=300, required=False)

    def validate_subreddits(self, value):
        if not value:
            raise serializers.ValidationError("At least one subreddit must be provided.")

        normalized = []
        seen = set()
        for subreddit in value:
            cleaned = subreddit.strip().lower()
            if cleaned and cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        if not normalized:
            raise serializers.ValidationError("At least one valid subreddit must be provided.")
        return normalized


class RedditCommentsCollectSerializer(serializers.Serializer):
    posts = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of previously collected Reddit posts.",
    )
    max_comments_per_post = serializers.IntegerField(min_value=1, default=400, required=False)
    match_keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="Optional list of keywords used to filter comments.",
    )


class RedditPostsAndCommentsCollectSerializer(RedditPostsCollectSerializer):
    max_comments_per_post = serializers.IntegerField(min_value=1, default=400, required=False)


class ExportDataSerializer(serializers.Serializer):
    table = serializers.ChoiceField(
        choices=["redditpost", "redditcomment"],
        help_text="Table name to export.",
    )
    format = serializers.ChoiceField(
        choices=["json", "csv"],
        default="json",
        help_text="Output format.",
    )
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Optional list of row ids to export.",
    )
    subreddit = serializers.CharField(required=False, allow_blank=True)
    author = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be earlier than end_date.")
        return data

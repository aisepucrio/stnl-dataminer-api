from django.db import models


class RedditPost(models.Model):
    subreddit = models.CharField(max_length=255, db_index=True)
    post_id = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.TextField()
    search_query = models.CharField(max_length=255, null=True, blank=True)
    matched_keywords = models.TextField(null=True, blank=True)
    score = models.IntegerField(default=0)
    num_comments = models.IntegerField(default=0)
    created_utc = models.FloatField()
    reddit_created_at = models.DateTimeField()
    author = models.CharField(max_length=255, null=True, blank=True)
    url = models.TextField()
    permalink = models.TextField()
    selftext = models.TextField(null=True, blank=True)
    time_mined = models.DateTimeField(null=True, blank=True, help_text="Date and time of mining")

    class Meta:
        indexes = [
            models.Index(fields=["subreddit"]),
            models.Index(fields=["post_id"]),
            models.Index(fields=["reddit_created_at"]),
        ]

    def __str__(self):
        return f"r/{self.subreddit} - {self.post_id}"


class RedditComment(models.Model):
    post = models.ForeignKey(RedditPost, related_name="comments", on_delete=models.CASCADE)
    subreddit = models.CharField(max_length=255, db_index=True)
    submission_id = models.CharField(max_length=32, db_index=True)
    comment_id = models.CharField(max_length=32, unique=True, db_index=True)
    parent_id = models.CharField(max_length=32, null=True, blank=True)
    matched_keywords = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    score = models.IntegerField(default=0)
    created_utc = models.FloatField()
    reddit_created_at = models.DateTimeField()
    comment_permalink = models.TextField()
    time_mined = models.DateTimeField(null=True, blank=True, help_text="Date and time of mining")

    class Meta:
        indexes = [
            models.Index(fields=["subreddit"]),
            models.Index(fields=["submission_id"]),
            models.Index(fields=["comment_id"]),
            models.Index(fields=["reddit_created_at"]),
        ]

    def __str__(self):
        return f"Comment {self.comment_id} on {self.submission_id}"

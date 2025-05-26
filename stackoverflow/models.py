from django.db import models
from django.utils import timezone

class StackUser(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    display_name = models.CharField(max_length=255)
    reputation = models.IntegerField(default=0)
    profile_image = models.URLField()
    user_type = models.CharField(max_length=50)
    is_employee = models.BooleanField(default=False)
    creation_date = models.DateTimeField()
    last_access_date = models.DateTimeField()
    last_modified_date = models.DateTimeField()
    link = models.URLField()
    accept_rate = models.IntegerField(null=True)
    about_me = models.TextField(null=True)
    location = models.CharField(max_length=255, null=True)
    website_url = models.URLField(null=True)
    account_id = models.BigIntegerField()
    badge_counts = models.JSONField()
    collectives = models.JSONField()
    view_count = models.IntegerField(default=0)
    down_vote_count = models.IntegerField(default=0)
    up_vote_count = models.IntegerField(default=0)
    answer_count = models.IntegerField(default=0)
    question_count = models.IntegerField(default=0)
    reputation_change_year = models.IntegerField(default=0)
    reputation_change_quarter = models.IntegerField(default=0)
    reputation_change_month = models.IntegerField(default=0)
    reputation_change_week = models.IntegerField(default=0)
    reputation_change_day = models.IntegerField(default=0)

    class Meta:
        db_table = 'stack_user'

class StackQuestion(models.Model):
    question_id = models.BigIntegerField(primary_key=True)
    title = models.TextField()
    body = models.TextField()
    score = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    answer_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    up_vote_count = models.IntegerField(default=0)
    down_vote_count = models.IntegerField(default=0)
    is_answered = models.BooleanField(default=False)
    creation_date = models.DateTimeField()
    content_license = models.CharField(max_length=50, null=True)
    last_activity_date = models.DateTimeField()
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='questions')
    share_link = models.URLField()
    body_markdown = models.TextField()
    link = models.URLField()
    favorite_count = models.IntegerField(default=0)
    time_mined = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField('StackTag', through='StackQuestionTag')

    class Meta:
        db_table = 'stack_question'

class StackAnswer(models.Model):
    answer_id = models.BigIntegerField(primary_key=True)
    question = models.ForeignKey(StackQuestion, on_delete=models.CASCADE, related_name='answers')
    body = models.TextField()
    score = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    up_vote_count = models.IntegerField(default=0)
    down_vote_count = models.IntegerField(default=0)
    is_accepted = models.BooleanField(default=False)
    creation_date = models.DateTimeField()
    content_license = models.CharField(max_length=50, null=True)
    last_activity_date = models.DateTimeField()
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='answers')
    share_link = models.URLField()
    body_markdown = models.TextField()
    link = models.URLField()
    title = models.TextField()
    time_mined = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'stack_answer'

class StackComment(models.Model):
    comment_id = models.BigIntegerField(primary_key=True)
    post_type = models.CharField(max_length=10)
    post_id = models.BigIntegerField()
    body = models.TextField()
    score = models.IntegerField(default=0)
    creation_date = models.DateTimeField()
    content_license = models.CharField(max_length=50)
    edited = models.BooleanField(default=False)
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='comments')
    body_markdown = models.TextField()
    link = models.URLField()
    time_mined = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'stack_comment'

class StackTag(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    has_synonyms = models.BooleanField(default=False)
    is_moderator_only = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    count = models.IntegerField(default=0)
    last_activity_date = models.DateTimeField()
    last_sync = models.DateTimeField(default=timezone.now)
    questions = models.ManyToManyField(StackQuestion, through='StackQuestionTag')

    class Meta:
        db_table = 'stack_tag'

class StackQuestionTag(models.Model):
    question = models.ForeignKey(StackQuestion, on_delete=models.CASCADE)
    tag = models.ForeignKey(StackTag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'stack_question_tag'
        unique_together = ('question', 'tag')

class StackBadge(models.Model):
    badge_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    badge_type = models.CharField(max_length=50)
    rank = models.CharField(max_length=50)
    link = models.URLField()
    description = models.TextField()
    users = models.ManyToManyField(StackUser, through='StackUserBadge')

    class Meta:
        db_table = 'stack_badge'

class StackUserBadge(models.Model):
    user = models.ForeignKey(StackUser, on_delete=models.CASCADE)
    badge = models.ForeignKey(StackBadge, on_delete=models.CASCADE)
    award_count = models.IntegerField(default=1)

    class Meta:
        db_table = 'stack_user_badge'
        unique_together = ('user', 'badge')

class StackCollective(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    link = models.URLField()
    slug = models.CharField(max_length=255)
    last_sync = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField(StackTag, through='StackCollectiveTag')
    users = models.ManyToManyField(StackUser, through='StackCollectiveUser')

    class Meta:
        db_table = 'stack_collective'

class StackCollectiveTag(models.Model):
    collective = models.ForeignKey(StackCollective, on_delete=models.CASCADE)
    tag = models.ForeignKey(StackTag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'stack_collective_tag'
        unique_together = ('collective', 'tag')

class StackCollectiveUser(models.Model):
    collective = models.ForeignKey(StackCollective, on_delete=models.CASCADE)
    user = models.ForeignKey(StackUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)

    class Meta:
        db_table = 'stack_collective_user'
        unique_together = ('collective', 'user')

class StackTagSynonym(models.Model):
    tag = models.ForeignKey(StackTag, on_delete=models.CASCADE)
    synonym = models.CharField(max_length=255)

    class Meta:
        db_table = 'stack_tag_synonym'
        unique_together = ('tag', 'synonym') 
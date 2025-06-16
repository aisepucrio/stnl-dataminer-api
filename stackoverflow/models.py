from django.db import models
from django.utils import timezone

class StackUser(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    display_name = models.CharField(max_length=255, null=True)
    reputation = models.IntegerField(default=0)
    profile_image = models.URLField(null=True)
    user_type = models.CharField(max_length=50, null=True)
    is_employee = models.BooleanField(default=False)
    creation_date = models.BigIntegerField(null=True)
    last_access_date = models.BigIntegerField(null=True)
    last_modified_date = models.BigIntegerField(null=True)
    link = models.URLField(null=True)
    accept_rate = models.IntegerField(null=True)
    about_me = models.TextField(null=True)
    location = models.CharField(max_length=255, null=True)
    website_url = models.URLField(null=True)
    account_id = models.BigIntegerField(null=True)
    badge_counts = models.JSONField(null=True)
    collectives = models.JSONField(null=True)
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
    time_mined = models.BigIntegerField(null=True)

    class Meta:
        db_table = 'stack_user'

class StackQuestion(models.Model):
    question_id = models.BigIntegerField(primary_key=True)
    title = models.TextField(null=True)
    body = models.TextField(null=True)
    score = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    answer_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    up_vote_count = models.IntegerField(default=0)
    down_vote_count = models.IntegerField(default=0)
    is_answered = models.BooleanField(default=False)
    creation_date = models.BigIntegerField(null=True)
    content_license = models.CharField(max_length=50, null=True)
    last_activity_date = models.BigIntegerField(null=True)
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='questions')
    share_link = models.URLField(null=True)
    body_markdown = models.TextField(null=True)
    link = models.URLField(null=True)
    favorite_count = models.IntegerField(default=0)
    accepted_answer_id = models.BigIntegerField(null=True)
    time_mined = models.BigIntegerField(default=int(timezone.now().timestamp()), null=True)
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
    creation_date = models.BigIntegerField()
    content_license = models.CharField(max_length=50, null=True)
    last_activity_date = models.BigIntegerField()
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='answers')
    share_link = models.URLField()
    body_markdown = models.TextField()
    link = models.URLField()
    title = models.TextField()
    time_mined = models.BigIntegerField(default=int(timezone.now().timestamp()))

    class Meta:
        db_table = 'stack_answer'

class StackComment(models.Model):
    comment_id = models.BigIntegerField(primary_key=True)
    post_type = models.CharField(max_length=10)
    post_id = models.BigIntegerField()
    body = models.TextField()
    score = models.IntegerField(default=0)
    creation_date = models.BigIntegerField()
    content_license = models.CharField(max_length=50)
    edited = models.BooleanField(default=False)
    owner = models.ForeignKey(StackUser, on_delete=models.SET_NULL, null=True, related_name='comments')
    body_markdown = models.TextField()
    link = models.URLField()
    time_mined = models.BigIntegerField(default=int(timezone.now().timestamp()))
    question = models.ForeignKey(StackQuestion, on_delete=models.CASCADE, null=True, related_name='comments')
    answer = models.ForeignKey(StackAnswer, on_delete=models.CASCADE, null=True, related_name='comments')

    class Meta:
        db_table = 'stack_comment'

class StackTag(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    has_synonyms = models.BooleanField(default=False)
    is_moderator_only = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    count = models.IntegerField(default=0)
    last_activity_date = models.BigIntegerField(null=True)
    last_sync = models.BigIntegerField(default=int(timezone.now().timestamp()))
    questions = models.ManyToManyField('StackQuestion', through='StackQuestionTag')

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
    slug = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    link = models.URLField()
    last_sync = models.BigIntegerField(default=int(timezone.now().timestamp()))
    tags = models.ManyToManyField(StackTag, through='StackCollectiveTag')
    users = models.ManyToManyField(StackUser, through='StackCollectiveUser')

    class Meta:
        db_table = 'stack_collective'

class StackCollectiveTag(models.Model):
    collective = models.ForeignKey(StackCollective, on_delete=models.CASCADE, to_field='slug', db_column='collective_slug')
    tag = models.ForeignKey(StackTag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'stack_collective_tag'
        unique_together = ('collective', 'tag')

class StackCollectiveUser(models.Model):
    collective = models.ForeignKey(StackCollective, on_delete=models.CASCADE, to_field='slug', db_column='collective_slug')
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
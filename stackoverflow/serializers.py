from rest_framework import serializers
from .models import (
    StackUser, StackQuestion, StackAnswer, StackComment,
    StackTag, StackBadge, StackCollective, StackTagSynonym
)

class StackUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackUser
        fields = '__all__'

class StackTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackTag
        fields = '__all__'

class StackQuestionSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)
    tags = StackTagSerializer(many=True, read_only=True)

    class Meta:
        model = StackQuestion
        fields = '__all__'

class StackAnswerSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)
    question = StackQuestionSerializer(read_only=True)

    class Meta:
        model = StackAnswer
        fields = '__all__'

class StackCommentSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)

    class Meta:
        model = StackComment
        fields = '__all__'

class StackBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackBadge
        fields = '__all__'

class StackCollectiveSerializer(serializers.ModelSerializer):
    tags = StackTagSerializer(many=True, read_only=True)

    class Meta:
        model = StackCollective
        fields = '__all__'

class StackTagSynonymSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackTagSynonym
        fields = '__all__' 
from rest_framework import serializers
from .models import (
    StackUser, StackQuestion, StackAnswer, StackComment,
    StackTag,
    # StackBadge, StackCollective, StackTagSynonym
)
from .utils import StackDateTimeHandler


class StackUserSerializer(serializers.ModelSerializer):
    creation_date_formatted = serializers.SerializerMethodField()
    last_access_date_formatted = serializers.SerializerMethodField()
    last_modified_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = StackUser
        fields = '__all__'

    def get_creation_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.creation_date)

    def get_last_access_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.last_access_date)

    def get_last_modified_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.last_modified_date)


class StackTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackTag
        fields = '__all__'


class StackQuestionSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)
    tags = StackTagSerializer(many=True, read_only=True)

    creation_date_formatted = serializers.SerializerMethodField()
    last_activity_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = StackQuestion
        fields = '__all__'

    def get_creation_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.creation_date)

    def get_last_activity_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.last_activity_date)


class StackAnswerSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)
    question = StackQuestionSerializer(read_only=True)

    creation_date_formatted = serializers.SerializerMethodField()
    last_activity_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = StackAnswer
        fields = '__all__'

    def get_creation_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.creation_date)

    def get_last_activity_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.last_activity_date)


class StackCommentSerializer(serializers.ModelSerializer):
    owner = StackUserSerializer(read_only=True)

    creation_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = StackComment
        fields = '__all__'

    def get_creation_date_formatted(self, obj):
        return StackDateTimeHandler.format_date(obj.creation_date)


# class StackBadgeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = StackBadge
#         fields = '__all__'


# class StackCollectiveSerializer(serializers.ModelSerializer):
#     tags = StackTagSerializer(many=True, read_only=True)

#     last_sync_formatted = serializers.SerializerMethodField()

#     class Meta:
#         model = StackCollective
#         fields = '__all__'

#     def get_last_sync_formatted(self, obj):
#         return StackDateTimeHandler.format_date(obj.last_sync)


# class StackTagSynonymSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = StackTagSynonym
#         fields = '__all__'

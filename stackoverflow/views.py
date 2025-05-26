from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    StackUser, StackQuestion, StackAnswer, StackComment,
    StackTag, StackBadge, StackCollective, StackTagSynonym
)
from .serializers import (
    StackUserSerializer, StackQuestionSerializer, StackAnswerSerializer,
    StackCommentSerializer, StackTagSerializer, StackBadgeSerializer,
    StackCollectiveSerializer, StackTagSynonymSerializer
)

class StackUserViewSet(viewsets.ModelViewSet):
    queryset = StackUser.objects.all()
    serializer_class = StackUserSerializer

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        user = self.get_object()
        questions = user.questions.all()
        serializer = StackQuestionSerializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def answers(self, request, pk=None):
        user = self.get_object()
        answers = user.answers.all()
        serializer = StackAnswerSerializer(answers, many=True)
        return Response(serializer.data)

class StackQuestionViewSet(viewsets.ModelViewSet):
    queryset = StackQuestion.objects.all()
    serializer_class = StackQuestionSerializer

    @action(detail=True, methods=['get'])
    def answers(self, request, pk=None):
        question = self.get_object()
        answers = question.answers.all()
        serializer = StackAnswerSerializer(answers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        question = self.get_object()
        comments = StackComment.objects.filter(post_type='question', post_id=question.question_id)
        serializer = StackCommentSerializer(comments, many=True)
        return Response(serializer.data)

class StackAnswerViewSet(viewsets.ModelViewSet):
    queryset = StackAnswer.objects.all()
    serializer_class = StackAnswerSerializer

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        answer = self.get_object()
        comments = StackComment.objects.filter(post_type='answer', post_id=answer.answer_id)
        serializer = StackCommentSerializer(comments, many=True)
        return Response(serializer.data)

class StackCommentViewSet(viewsets.ModelViewSet):
    queryset = StackComment.objects.all()
    serializer_class = StackCommentSerializer

class StackTagViewSet(viewsets.ModelViewSet):
    queryset = StackTag.objects.all()
    serializer_class = StackTagSerializer

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        tag = self.get_object()
        questions = tag.questions.all()
        serializer = StackQuestionSerializer(questions, many=True)
        return Response(serializer.data)

class StackBadgeViewSet(viewsets.ModelViewSet):
    queryset = StackBadge.objects.all()
    serializer_class = StackBadgeSerializer

class StackCollectiveViewSet(viewsets.ModelViewSet):
    queryset = StackCollective.objects.all()
    serializer_class = StackCollectiveSerializer

    @action(detail=True, methods=['get'])
    def tags(self, request, pk=None):
        collective = self.get_object()
        tags = collective.tags.all()
        serializer = StackTagSerializer(tags, many=True)
        return Response(serializer.data)

class StackTagSynonymViewSet(viewsets.ModelViewSet):
    queryset = StackTagSynonym.objects.all()
    serializer_class = StackTagSynonymSerializer 
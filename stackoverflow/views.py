from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import (
    StackUser, StackQuestion, StackAnswer, StackComment,
    StackTag, StackBadge, StackCollective, StackTagSynonym
)
from .serializers import (
    StackUserSerializer, StackQuestionSerializer, StackAnswerSerializer,
    StackCommentSerializer, StackTagSerializer, StackBadgeSerializer,
    StackCollectiveSerializer, StackTagSynonymSerializer
)
from .miner import StackOverflowMiner

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

class StackOverflowViewSet(viewsets.ModelViewSet):
    queryset = StackAnswer.objects.all()
    serializer_class = StackAnswerSerializer

    @action(detail=False, methods=['post'])
    def collect_answers(self, request):
        """
        Collect answers from Stack Overflow within a date range
        
        Parameters:
        - site: The site to fetch from (default: stackoverflow)
        - start_date: Start date in ISO format (YYYY-MM-DD)
        - end_date: End date in ISO format (YYYY-MM-DD)
        """
        try:
            site = request.data.get('site', 'stackoverflow')
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')

            miner = StackOverflowMiner()
            answers = miner.get_answers(
                site=site,
                start_date=start_date,
                end_date=end_date
            )

            # Save answers to database
            for answer_data in answers:
                StackAnswer.objects.update_or_create(
                    answer_id=answer_data['answer_id'],
                    defaults=answer_data
                )

            return Response({
                'message': f'Successfully collected {len(answers)} answers',
                'answers': answers
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class StackTagSynonymViewSet(viewsets.ModelViewSet):
#     queryset = StackTagSynonym.objects.all()
#     serializer_class = StackTagSynonymSerializer 
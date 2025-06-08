from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import datetime
from .models import StackAnswer, StackQuestion, StackTag
from .serializers import StackAnswerSerializer
from .miner import StackOverflowMiner
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter

@extend_schema_view(
    collect_answers=extend_schema(
        summary="Collect Stack Overflow Answers",
        description="""
        Collect all answers from Stack Overflow within a date range and save them to the database.
        
        Notes:
        - Answers are saved to database in batches
        - Duplicate answers are updated if they exist
        - The API will automatically handle rate limiting
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "site": {"type": "string", "default": "stackoverflow"},
                    "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD"},
                    "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "total_answers": {"type": "integer"},
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "answer_id": {"type": "integer"},
                                "question_id": {"type": "integer"},
                                "body": {"type": "string"},
                                "creation_date": {"type": "string", "format": "date-time"},
                                "score": {"type": "integer"},
                                "is_accepted": {"type": "boolean"}
                            }
                        }
                    }
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            429: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        tags=["StackOverflow"]
    ),
    collect_questions=extend_schema(
        summary="Collect Stack Overflow Questions",
        description="""
        Collect all questions from Stack Overflow within a date range and save them to the database.
        
        Notes:
        - Questions are saved to database in batches
        - Duplicate questions are updated if they exist
        - The API will automatically handle rate limiting
        """,
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "site": {"type": "string", "default": "stackoverflow"},
                    "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD"},
                    "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "total_questions": {"type": "integer"},
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {"type": "integer"},
                                "title": {"type": "string"},
                                "body": {"type": "string"},
                                "creation_date": {"type": "string", "format": "date-time"},
                                "score": {"type": "integer"},
                                "view_count": {"type": "integer"},
                                "answer_count": {"type": "integer"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "is_answered": {"type": "boolean"},
                                "accepted_answer_id": {"type": "integer", "nullable": True},
                                "owner": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "integer"},
                                        "display_name": {"type": "string"},
                                        "reputation": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            429: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        },
        tags=["StackOverflow"]
    )
)
class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet for collecting Stack Overflow data.
    Provides endpoints for collecting answers and questions.
    """
    
    @action(detail=False, methods=['post'])
    def collect_answers(self, request):
        """
        Collect all answers from Stack Overflow within a date range
        
        Parameters:
        - site: The site to fetch from (default: stackoverflow)
        - start_date: Start date in ISO format (YYYY-MM-DD)
        - end_date: End date in ISO format (YYYY-MM-DD)
        """
        try:
            # Get and validate parameters
            site = request.data.get('site', 'stackoverflow')
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')

            # Validate dates
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate date range
            if end < start:
                return Response({
                    'error': 'End date must be after start date'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Initialize miner and get answers
            miner = StackOverflowMiner()
            try:
                answers = miner.get_answers(
                    site=site,
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                if 'rate limit' in str(e).lower():
                    return Response({
                        'error': 'Stack Overflow API rate limit exceeded. Please try again later.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                raise

            # Save answers to database in a transaction
            try:
                with transaction.atomic():
                    for answer_data in answers:
                        StackAnswer.objects.update_or_create(
                            answer_id=answer_data['answer_id'],
                            defaults=answer_data
                        )
            except Exception as e:
                return Response({
                    'error': f'Database error: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Prepare response
            return Response({
                'message': 'Successfully collected answers',
                'total_answers': len(answers),
                'answers': answers
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'An unexpected error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def collect_questions(self, request):
        """
        Collect all questions from Stack Overflow within a date range
        
        Parameters:
        - site: The site to fetch from (default: stackoverflow)
        - start_date: Start date in ISO format (YYYY-MM-DD)
        - end_date: End date in ISO format (YYYY-MM-DD)
        """
        try:
            # Get and validate parameters
            site = request.data.get('site', 'stackoverflow')
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')

            # Validate dates
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate date range
            if end < start:
                return Response({
                    'error': 'End date must be after start date'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Initialize miner and get questions
            miner = StackOverflowMiner()
            try:
                questions = miner.get_questions(
                    site=site,
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                if 'rate limit' in str(e).lower():
                    return Response({
                        'error': 'Stack Overflow API rate limit exceeded. Please try again later.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                raise

            # Save questions to database in a transaction
            try:
                with transaction.atomic():
                    for question_data in questions:
                        # Remove tags from question_data to avoid direct assignment
                        tags = question_data.pop('tags', [])
                        # Create or update the question
                        question, created = StackQuestion.objects.update_or_create(
                            question_id=question_data['question_id'],
                            defaults=question_data
                        )
                        # Set tags using the set() method
                        # tag_instances = [StackTag.objects.get_or_create(name=tag)[0] for tag in tags]
                        # question.tags.set(tag_instances)
            except Exception as e:
                return Response({
                    'error': f'Database error: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Prepare response
            return Response({
                'message': 'Successfully collected questions',
                'total_questions': len(questions),
                'questions': questions
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'An unexpected error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
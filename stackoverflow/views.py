from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import datetime
from .models import StackAnswer
from .serializers import StackAnswerSerializer
from .miner import StackOverflowMiner
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter

@extend_schema_view(
    collect_answers=extend_schema(
        summary="Collect Stack Overflow Answers",
        description="""
        Collect answers from Stack Overflow within a date range and save them to the database.
        
        Notes:
        - Maximum 100 items per page
        - Answers are saved to database in batches
        - Duplicate answers are updated if they exist
        """,
        parameters=[
            OpenApiParameter(
                name='page',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination (default: 1)',
                default=1
            ),
            OpenApiParameter(
                name='page_size',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Number of items per page (default: 100, max: 100)',
                default=100
            ),
        ],
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
            200: OpenApiExample(
                "Success",
                value={
                    "message": "Successfully collected answers",
                    "total_answers": 50,
                    "page": 1,
                    "page_size": 100,
                    "has_next": False,
                    "answers": [
                        {"answer_id": 123, "question_id": 456, "body": "...", "creation_date": "2024-01-01"}
                    ]
                },
                response_only=True
            ),
            400: OpenApiExample(
                "Bad Request",
                value={
                    "error": "Invalid date range. End date must be after start date."
                },
                response_only=True
            ),
            429: OpenApiExample(
                "Rate Limit",
                value={
                    "error": "Stack Overflow API rate limit exceeded. Please try again later."
                },
                response_only=True
            ),
            500: OpenApiExample(
                "Server Error",
                value={
                    "error": "An unexpected error occurred while collecting answers."
                },
                response_only=True
            )
        },
        tags=["StackOverflow"]
    )
)
class StackOverflowViewSet(viewsets.ViewSet):
    """
    ViewSet for collecting Stack Overflow data.
    Only provides a POST endpoint for collecting answers.
    """
    
    @action(detail=False, methods=['post'])
    def collect_answers(self, request):
        """
        Collect answers from Stack Overflow within a date range
        
        Parameters:
        - site: The site to fetch from (default: stackoverflow)
        - start_date: Start date in ISO format (YYYY-MM-DD)
        - end_date: End date in ISO format (YYYY-MM-DD)
        - page: Page number for pagination (default: 1)
        - page_size: Number of items per page (default: 100, max: 100)
        """
        try:
            # Get and validate parameters
            site = request.data.get('site', 'stackoverflow')
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 100)), 100)

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
                    end_date=end_date,
                    page=page,
                    page_size=page_size
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
                'page': page,
                'page_size': page_size,
                'has_next': len(answers) == page_size,  # If we got a full page, there might be more
                'answers': answers
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'An unexpected error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
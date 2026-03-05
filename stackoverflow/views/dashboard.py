import logging

from django.db.models import Count, Min, Max, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import StackQuestion, StackAnswer, StackComment, StackUser, StackTag
from ..utils import StackDateTimeHandler

logger = logging.getLogger(__name__)


class GraphDashboardSerializer(serializers.Serializer):
    tag = serializers.CharField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    interval = serializers.ChoiceField(choices=["day", "month", "year"], default="day", required=False)

    def validate(self, data):
        if data.get("start_date") and data.get("end_date"):
            StackDateTimeHandler.validate_date_range(data["start_date"], data["end_date"])
        return data


@extend_schema(
    tags=["StackOverflow"],
    summary="Dashboard statistics",
    description="Provides statistics about Stack Overflow questions, answers, comments and users. "
                "If a tag is provided, returns detailed stats for that tag.",
    parameters=[
        OpenApiParameter(
            name="tag",
            description="Tag name to filter questions (e.g. 'python'). If not provided, returns aggregated stats.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="start_date",
            description="Filter data from this date onwards (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
        OpenApiParameter(
            name="end_date",
            description="Filter data up to this date (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "nullable": True},
                "questions_count": {"type": "integer"},
                "answers_count": {"type": "integer"},
                "comments_count": {"type": "integer"},
                "users_count": {"type": "integer"},
                "tags_count": {"type": "integer", "nullable": True},
                "top_tags": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}, "count": {"type": "integer"}}},
                    "nullable": True,
                },
                "time_mined": {"type": "string", "format": "date-time", "nullable": True},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}}},
    },
    examples=[
        OpenApiExample(
            "Tag Example",
            value={
                "tag": "python",
                "questions_count": 120,
                "answers_count": 260,
                "comments_count": 480,
                "users_count": 180,
                "time_mined": "2025-12-31T23:59:59Z",
            },
            summary="Example with tag filter",
        ),
        OpenApiExample(
            "All Tags Example",
            value={
                "questions_count": 500,
                "answers_count": 1100,
                "comments_count": 2400,
                "users_count": 850,
                "tags_count": 50,
                "top_tags": [
                    {"name": "python", "count": 200},
                    {"name": "javascript", "count": 150},
                ],
            },
            summary="Example without tag filter",
        ),
    ],
)
class DashboardView(APIView):
    def get(self, request):
        tag = request.query_params.get("tag")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            if start_date:
                start_date = StackDateTimeHandler.parse_date(start_date)
            if end_date:
                end_date = StackDateTimeHandler.parse_date(end_date)
            if start_date and end_date:
                StackDateTimeHandler.validate_date_range(start_date, end_date)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        question_filters = {}
        if start_date:
            question_filters["creation_date__gte"] = start_date
        if end_date:
            question_filters["creation_date__lte"] = end_date
        if tag:
            question_filters["tags__name"] = tag

        questions_qs = StackQuestion.objects.filter(**question_filters).distinct()

        answers_qs = StackAnswer.objects.filter(question__in=questions_qs).distinct()
        comments_qs = StackComment.objects.filter(
            Q(question__in=questions_qs) | Q(answer__question__in=questions_qs)
        ).distinct()

        users_qs = StackUser.objects.filter(
            Q(questions__in=questions_qs) | Q(answers__in=answers_qs) | Q(comments__in=comments_qs)
        ).distinct()

        latest_time_mined = questions_qs.order_by("-time_mined").first()
        time_mined = StackDateTimeHandler.format_date(latest_time_mined.time_mined) if latest_time_mined else None

        response_data = {
            "tag": tag,
            "questions_count": questions_qs.count(),
            "answers_count": answers_qs.count(),
            "comments_count": comments_qs.count(),
            "users_count": users_qs.count(),
            "time_mined": time_mined,
        }

        if not tag:
            tag_counts = (
                questions_qs.values("tags__name")
                .annotate(count=Count("tags__name"))
                .exclude(tags__name__isnull=True)
                .order_by("-count")
            )
            response_data["tags_count"] = tag_counts.count()
            response_data["top_tags"] = [
                {"name": entry["tags__name"], "count": entry["count"]} for entry in tag_counts[:10]
            ]
        else:
            response_data["tags_count"] = None
            response_data["top_tags"] = None

        return Response(response_data)


@extend_schema(
    tags=["StackOverflow"],
    summary="Graph Dashboard",
    description="Provides cumulative time-series data for questions, answers and comments. "
                "Can be filtered by tag, start_date and end_date.",
    parameters=[
        OpenApiParameter(
            name="tag",
            description="Tag name to filter questions (e.g. 'python').",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="start_date",
            description="Filter display window from this date onwards (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
        OpenApiParameter(
            name="end_date",
            description="Filter display window up to this date (ISO format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
        OpenApiParameter(
            name="interval",
            description="Time interval for grouping data (day, month, year). Default is 'day'.",
            required=False,
            type=str,
            default="day",
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "nullable": True},
                "time_series": {
                    "type": "object",
                    "properties": {
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "questions": {"type": "array", "items": {"type": "integer"}},
                        "answers": {"type": "array", "items": {"type": "integer"}},
                        "comments": {"type": "array", "items": {"type": "integer"}},
                    },
                },
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}}},
    },
    examples=[
        OpenApiExample(
            "Single Tag Example",
            value={
                "tag": "python",
                "time_series": {
                    "labels": ["2025-01-01", "2025-01-02"],
                    "questions": [5, 9],
                    "answers": [2, 6],
                    "comments": [3, 8],
                },
            },
            description="Example response for a specific tag showing cumulative counts",
        ),
        OpenApiExample(
            "All Tags Example",
            value={
                "time_series": {
                    "labels": ["2025-01-01", "2025-01-02"],
                    "questions": [10, 18],
                    "answers": [4, 10],
                    "comments": [6, 15],
                },
            },
            description="Example response for all questions showing cumulative counts",
        ),
    ],
)
class GraphDashboardView(APIView):
    def get(self, request):
        serializer = GraphDashboardSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        tag = serializer.validated_data.get("tag")
        start_date = serializer.validated_data.get("start_date")
        end_date = serializer.validated_data.get("end_date")
        interval = serializer.validated_data.get("interval", "day")

        if interval == "day":
            trunc_func = TruncDay
            date_format = "%Y-%m-%d"
        elif interval == "month":
            trunc_func = TruncMonth
            date_format = "%Y-%m"
        else:
            trunc_func = TruncYear
            date_format = "%Y"

        question_filters = {}
        if start_date:
            question_filters["creation_date__gte"] = start_date
        if end_date:
            question_filters["creation_date__lte"] = end_date
        if tag:
            question_filters["tags__name"] = tag

        questions_qs = StackQuestion.objects.filter(**question_filters).distinct()
        answers_qs = StackAnswer.objects.filter(question__in=questions_qs).distinct()
        comments_qs = StackComment.objects.filter(
            Q(question__in=questions_qs) | Q(answer__question__in=questions_qs)
        ).distinct()

        questions_by_date = (
            questions_qs.annotate(interval=trunc_func("creation_date"))
            .values("interval")
            .annotate(count=Count("question_id"))
            .order_by("interval")
        )
        answers_by_date = (
            answers_qs.annotate(interval=trunc_func("creation_date"))
            .values("interval")
            .annotate(count=Count("answer_id"))
            .order_by("interval")
        )
        comments_by_date = (
            comments_qs.annotate(interval=trunc_func("creation_date"))
            .values("interval")
            .annotate(count=Count("comment_id"))
            .order_by("interval")
        )

        cumulative_questions = 0
        cumulative_answers = 0
        cumulative_comments = 0

        questions_dict = {}
        answers_dict = {}
        comments_dict = {}

        for item in questions_by_date:
            cumulative_questions += item["count"]
            questions_dict[item["interval"].strftime(date_format)] = cumulative_questions

        for item in answers_by_date:
            cumulative_answers += item["count"]
            answers_dict[item["interval"].strftime(date_format)] = cumulative_answers

        for item in comments_by_date:
            cumulative_comments += item["count"]
            comments_dict[item["interval"].strftime(date_format)] = cumulative_comments

        all_dates = set()
        for date_dict in [questions_dict, answers_dict, comments_dict]:
            all_dates.update(date_dict.keys())

        date_range = sorted(list(all_dates))
        if start_date:
            start_str = start_date.strftime(date_format)
            date_range = [d for d in date_range if d >= start_str]

        questions_data = []
        answers_data = []
        comments_data = []

        last_q = 0
        last_a = 0
        last_c = 0

        for date_str in date_range:
            last_q = questions_dict.get(date_str, last_q)
            last_a = answers_dict.get(date_str, last_a)
            last_c = comments_dict.get(date_str, last_c)

            questions_data.append(last_q)
            answers_data.append(last_a)
            comments_data.append(last_c)

        response_data = {
            "time_series": {
                "labels": date_range,
                "questions": questions_data,
                "answers": answers_data,
                "comments": comments_data,
            }
        }

        if tag:
            response_data["tag"] = tag

        return Response(response_data)


@extend_schema(
    tags=["StackOverflow"],
    summary="Tag date range",
    description="Returns the earliest (min_date) and latest (max_date) question creation dates. "
                "Can be filtered by tag.",
    parameters=[
        OpenApiParameter(
            name="tag",
            description="Tag to filter questions (optional).",
            required=False,
            type=str,
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "nullable": True},
                "min_date": {"type": "string", "format": "date-time", "nullable": True},
                "max_date": {"type": "string", "format": "date-time", "nullable": True},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}}},
    },
)
class TagDateRangeView(APIView):
    def get(self, request):
        tag = request.query_params.get("tag")

        question_filters = {}
        if tag:
            question_filters["tags__name"] = tag

        date_agg = StackQuestion.objects.filter(**question_filters).aggregate(
            min_date=Min("creation_date"),
            max_date=Max("creation_date"),
        )

        min_date = date_agg.get("min_date")
        max_date = date_agg.get("max_date")

        response = {
            "tag": tag,
            "min_date": StackDateTimeHandler.format_date(min_date) if min_date else None,
            "max_date": StackDateTimeHandler.format_date(max_date) if max_date else None,
        }

        return Response(response)

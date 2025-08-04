import json
import logging

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import GitHubCommit, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest
from ..serializers import ExportDataSerializer

logger = logging.getLogger(__name__)


class ExportDataView(APIView):
    @extend_schema(
        summary="Export GitHub data",
        tags=["GitHub"],
        description="Export data from GitHub tables. For githubissuepullrequest table, you can filter by data_type (issue/pull_request).",
        request=ExportDataSerializer,
        responses={
            200: OpenApiResponse(description="Exported data file"),
            400: OpenApiResponse(description="Invalid parameters"),
            404: OpenApiResponse(description="Table not found or no data found"),
            500: OpenApiResponse(description="Server error")
        },
        examples=[
            OpenApiExample(
                "Export all issues and pull requests",
                value={
                    "table": "githubissuepullrequest",
                    "format": "json"
                },
                summary="Export all data from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export only issues",
                value={
                    "table": "githubissuepullrequest",
                    "data_type": "issue",
                    "format": "json"
                },
                summary="Export only issues from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export only pull requests",
                value={
                    "table": "githubissuepullrequest",
                    "data_type": "pull_request",
                    "format": "json"
                },
                summary="Export only pull requests from githubissuepullrequest table"
            ),
            OpenApiExample(
                "Export specific commits by IDs",
                value={
                    "table": "githubcommit",
                    "ids": [1, 2, 3],
                    "format": "json"
                },
                summary="Export specific commits by their IDs"
            )
        ]
    )
    def post(self, request):
        serializer = ExportDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        table = serializer.validated_data['table']
        ids = serializer.validated_data.get('ids', [])
        format_type = serializer.validated_data['format']
        data_type = serializer.validated_data.get('data_type')

        model_mapping = {
            'githubcommit': GitHubCommit,
            'githubbranch': GitHubBranch,
            'githubmetadata': GitHubMetadata,
            'githubissuepullrequest': GitHubIssuePullRequest
        }

        if table not in model_mapping:
            return Response(
                {"error": f"Table '{table}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        model = model_mapping[table]
        queryset = model.objects.all()

        if table == 'githubissuepullrequest':
            if data_type:
                queryset = queryset.filter(data_type=data_type)

        if ids:
            queryset = queryset.filter(id__in=ids)

        data = []
        for obj in queryset:
            obj_dict = {}
            for field in obj._meta.fields:
                value = getattr(obj, field.name)
                if hasattr(value, 'id'):
                    obj_dict[field.name] = value.id
                else:
                    obj_dict[field.name] = value
            data.append(obj_dict)

        if not data:
            return Response(
                {"error": "No data found to export"},
                status=status.HTTP_404_NOT_FOUND
            )

        filename_parts = [table]
        if table == 'githubissuepullrequest':
            if data_type:
                filename_parts.append(data_type)
        filename = f"{'_'.join(filename_parts)}_export.json"

        try:
            response = HttpResponse(
                json.dumps(data, default=str, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'

            return response

        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return Response(
                {"error": f"Error exporting data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 
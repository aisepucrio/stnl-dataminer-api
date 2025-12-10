import json
import csv
import logging
from io import StringIO

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from jira.models import JiraIssue
from .serializers import ExportDataSerializer

logger = logging.getLogger(__name__)


class ExportDataView(APIView):
    @extend_schema(
        summary="Export Jira data",
        tags=["Jira"],
        description="Export data from Jira tables. You can filter by issue_type.",
        request=ExportDataSerializer,
        responses={
            200: OpenApiResponse(description="Exported data file"),
            400: OpenApiResponse(description="Invalid parameters"),
            404: OpenApiResponse(description="Table not found or no data found"),
            500: OpenApiResponse(description="Server error")
        },
        examples=[
            OpenApiExample(
                "Export all Jira issues",
                value={"table": "jiraissue", "format": "json"},
                summary="Export all data from jiraissue table"
            ),
            OpenApiExample(
                "Export only bugs",
                value={"table": "jiraissue", "issue_type": "Bug", "format": "csv"},
                summary="Export only bugs from jiraissue table"
            )
        ]
    )
    def post(self, request):
        serializer = ExportDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        table = validated['table']
        ids = validated.get('ids', [])
        format_type = validated['format']
        issue_type = validated.get('issue_type')

        model_mapping = {
            'jiraissue': JiraIssue,
        }

        if table not in model_mapping:
            return Response({"error": f"Table '{table}' not found"}, status=status.HTTP_404_NOT_FOUND)

        model = model_mapping[table]
        queryset = model.objects.all()

        if issue_type:
            queryset = queryset.filter(issue_type=issue_type)
        if ids:
            queryset = queryset.filter(id__in=ids)

        data = []
        for obj in queryset:
            obj_dict = {
                field.name: getattr(obj, field.name).id if hasattr(getattr(obj, field.name), 'id') else getattr(obj, field.name)
                for field in obj._meta.fields
            }
            data.append(obj_dict)

        if not data:
            return Response({"error": "No data found to export"}, status=status.HTTP_404_NOT_FOUND)

        filename_parts = [table]
        if issue_type:
            filename_parts.append(issue_type.lower())
        extension = 'csv' if format_type == 'csv' else 'json'
        filename = f"{'_'.join(filename_parts)}_export.{extension}"

        try:
            if format_type == 'csv':
                buffer = StringIO()
                writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                buffer.seek(0)

                response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8-sig')
            else:
                response = HttpResponse(
                    json.dumps(data, default=str, indent=2),
                    content_type='application/json'
                )

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response

        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Error exporting data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

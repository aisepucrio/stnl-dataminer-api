import csv
import json
from io import StringIO

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from stackoverflow.models import StackQuestion
from .serializers import ExportStackoverflowDataSerializer


class ExportStackoverflowCSVView(APIView):
    def post(self, request):
        serializer = ExportStackoverflowDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ids = serializer.validated_data.get("ids", [])
        min_score = serializer.validated_data.get("min_score")
        format_type = serializer.validated_data.get("format", "csv")

        queryset = StackQuestion.objects.all()
        if ids:
            queryset = queryset.filter(question_id__in=ids)
        if min_score is not None:
            queryset = queryset.filter(score__gte=min_score)

        if not queryset.exists():
            return Response({"error": "No data found to export"}, status=status.HTTP_404_NOT_FOUND)

        data = []
        for q in queryset:
            data.append({
                "question_id": q.question_id,
                "title": q.title,
                "score": q.score,
                "creation_date": q.creation_date,
                "link": q.link
            })

        filename = "stackoverflow_export.csv" if format_type == "csv" else "stackoverflow_export.json"

        try:
            if format_type == "csv":
                buffer = StringIO()
                writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

                response = HttpResponse(buffer.getvalue(), content_type='text/csv')
            else:
                response = HttpResponse(
                    json.dumps(data, indent=2, default=str),
                    content_type='application/json'
                )

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response

        except Exception as e:
            return Response({"error": f"Export failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

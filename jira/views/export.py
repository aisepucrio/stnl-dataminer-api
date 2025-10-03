# jira/views/export.py
import json
import logging
import csv
from datetime import datetime, time, timezone

from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from ..models import (
    JiraIssue, JiraProject, JiraUser, JiraSprint, JiraComment, JiraChecklist,
    JiraIssueType, JiraIssueLink, JiraCommit, JiraActivityLog, JiraHistory, JiraHistoryItem
)

from ..serializers import JiraExportDataSerializer
from utils.lookup import (
    get_filterset_fields as _get_filterset_fields,
    get_search_fields as _get_search_fields,
)

logger = logging.getLogger(__name__)

def _day_bounds_utc(d):
    start = datetime.combine(d, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(d, time.max).replace(tzinfo=timezone.utc)
    return start, end

def _date_field_for_model(model):
    """
    Escolha o campo de data padrão para filtros por dia/intervalo.
    Ajuste conforme seus models.
    """
    if model is JiraIssue:
        # típico: created/updated/resolved. Ajuste se os seus nomes forem outros
        return "created"  # ex.: JiraIssue.created (DateTimeField)
    if model is JiraComment:
        return "created"
    if model is JiraHistory:
        return "created"
    if model is JiraHistoryItem:
        return "created"
    if model is JiraCommit:
        return "author_date"
    if model is JiraActivityLog:
        return "created"
    if model is JiraSprint:
        return "start_date"
    # para entidades mais estáticas (project/user/issuetype/issuelink/checklist) geralmente não filtra por data
    return None

class JiraExportDataView(APIView):
    """
    Exporta dados das tabelas JIRA em CSV/JSON.
    - Reaproveita filtros via querystring (django-filters, search, ordering).
    - Aceita filtros no BODY: date OU start_date/end_date.
    - Campos simples de filtro no body: project, status, reporter, assignee, issue_type, sprint, priority (se existirem).
    - 'fields' limita as colunas do CSV.
    """

    def post(self, request):
        serializer = JiraExportDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        table = serializer.validated_data["table"]
        ids = serializer.validated_data.get("ids", [])
        fmt = serializer.validated_data["format"]
        selected_fields = serializer.validated_data.get("fields")

        # filtros simples no body
        project  = serializer.validated_data.get("project")
        status_s = serializer.validated_data.get("status")
        reporter = serializer.validated_data.get("reporter")
        assignee = serializer.validated_data.get("assignee")
        issue_type = serializer.validated_data.get("issue_type")
        sprint   = serializer.validated_data.get("sprint")
        priority = serializer.validated_data.get("priority")

        # filtros de data no body
        body_date  = serializer.validated_data.get("date")
        body_start = serializer.validated_data.get("start_date")
        body_end   = serializer.validated_data.get("end_date")

        model_mapping = {
            "jiraissue": JiraIssue,
            "jiracomment": JiraComment,
            "jirahistory": JiraHistory,
            "jirahistoryitem": JiraHistoryItem,
            "jiraactivitylog": JiraActivityLog,
            "jiracommit": JiraCommit,
            "jirasprint": JiraSprint,
            "jiraproject": JiraProject,
            "jirauser": JiraUser,
            "jiraissuetype": JiraIssueType,
            "jiraissuelink": JiraIssueLink,
            "jirachecklist": JiraChecklist,
        }
        if table not in model_mapping:
            return Response({"error": f"Table '{table}' not found"}, status=status.HTTP_404_NOT_FOUND)

        model = model_mapping[table]
        queryset = model.objects.all()

        # by IDs
        if ids:
            queryset = queryset.filter(id__in=ids)

        # filtros simples (só aplicamos se o campo existir no model)
        # Ajuste os nomes dos campos conforme seus models JIRA:
        def _safe_filter(qs, **kw):
            valid = {}
            for k, v in kw.items():
                if v is None:
                    continue
                # só filtra se o campo base existir no model
                base_field = k.split("__", 1)[0]
                if hasattr(model, base_field) or base_field in [f.name for f in model._meta.fields]:
                    valid[k] = v
            return qs.filter(**valid) if valid else qs

        # Exemplos comuns (ajuste os nomes dos campos do seu model):
        # project: pode ser FK -> JiraProject (use project__key ou project__name)
        if project:
            # primeiro tentamos por key; se der erro, mude para name
            try:
                queryset = queryset.filter(project__key__icontains=project)
            except Exception:
                queryset = _safe_filter(queryset, **{"project__name__icontains": project})

        if status_s:
            queryset = _safe_filter(queryset, **{"status__icontains": status_s})

        if reporter:
            # pode ser texto (reporter_name) ou FK (reporter__display_name)
            try:
                queryset = queryset.filter(reporter__icontains=reporter)
            except Exception:
                queryset = _safe_filter(queryset, **{"reporter__display_name__icontains": reporter})

        if assignee:
            try:
                queryset = queryset.filter(assignee__icontains=assignee)
            except Exception:
                queryset = _safe_filter(queryset, **{"assignee__display_name__icontains": assignee})

        if issue_type:
            try:
                queryset = queryset.filter(issue_type__icontains=issue_type)
            except Exception:
                queryset = _safe_filter(queryset, **{"issue_type__name__icontains": issue_type})

        if sprint:
            try:
                queryset = queryset.filter(sprint__name__icontains=sprint)
            except Exception:
                queryset = _safe_filter(queryset, **{"sprint__icontains": sprint})

        if priority:
            queryset = _safe_filter(queryset, **{"priority__icontains": priority})

        # ===== Filtros da UI via querystring (django-filters) =====
        filterset_fields = _get_filterset_fields(model)
        if filterset_fields:
            DummyView = type(
                "DummyView",
                (),
                {"filterset_fields": filterset_fields, "get_queryset": lambda self: model.objects.all()},
            )
            backend = DjangoFilterBackend()
            queryset = backend.filter_queryset(request, queryset, DummyView())

        # ===== Busca ('search=') =====
        search_query = request.query_params.get("search")
        if search_query:
            search_fields = _get_search_fields(model) or []
            if search_fields:
                q = Q()
                for fld in search_fields:
                    if "__" in fld:
                        q |= Q(**{fld: search_query})
                    else:
                        q |= Q(**{f"{fld}__icontains": search_query})
                queryset = queryset.filter(q)

        # ===== Ordenação ('ordering=') =====
        ordering = request.query_params.get("ordering")
        if ordering:
            try:
                queryset = queryset.order_by(*[seg.strip() for seg in ordering.split(",") if seg.strip()])
            except Exception as e:
                logger.warning(f"Ignoring invalid ordering '{ordering}': {e}")

        # ===== Filtro de data do BODY =====
        date_field = _date_field_for_model(model)
        if date_field:
            if body_date:
                start_dt, end_dt = _day_bounds_utc(body_date)
                queryset = queryset.filter(**{f"{date_field}__gte": start_dt, f"{date_field}__lte": end_dt})
            else:
                if body_start:
                    queryset = queryset.filter(**{f"{date_field}__gte": body_start})
                if body_end:
                    queryset = queryset.filter(**{f"{date_field}__lte": body_end})

        if not queryset.exists():
            return Response({"error": "No data found to export"}, status=status.HTTP_404_NOT_FOUND)

        filename_base = f"{table}_export"

        # ===== JSON =====
        if fmt == "json":
            data = []
            for obj in queryset:
                obj_dict = {}
                for field in obj._meta.fields:
                    value = getattr(obj, field.name)
                    if hasattr(value, "id"):
                        obj_dict[field.name] = value.id
                    else:
                        obj_dict[field.name] = value
                data.append(obj_dict)

            response = HttpResponse(json.dumps(data, default=str, indent=2), content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{filename_base}.json"'
            response["Access-Control-Expose-Headers"] = "Content-Disposition"
            return response

        # ===== CSV =====
        if not selected_fields:
            selected_fields = [f.name for f in model._meta.fields]

        def row_iter():
            yield [smart_str(col) for col in selected_fields]
            for obj in queryset.iterator(chunk_size=5000):
                row = []
                for col in selected_fields:
                    val = getattr(obj, col, "")
                    if hasattr(val, "id"):
                        val = val.id
                    if val is None:
                        val = ""
                    elif hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif isinstance(val, bool):
                        val = "true" if val else "false"
                    elif isinstance(val, (list, tuple, set)):
                        val = ", ".join(map(str, val))
                    row.append(smart_str(val))
                yield row

        class Echo:
            def write(self, v): return v

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        def stream():
            for r in row_iter():
                yield writer.writerow(r)

        response = HttpResponse(stream(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename_base}.csv"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response

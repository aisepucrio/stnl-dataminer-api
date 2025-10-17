import json
import logging
import csv
from datetime import datetime, time, timezone

from django.http import HttpResponse
from django.utils.encoding import smart_str

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend  # usar backend diretamente
from django.db.models import Q

from ..models import GitHubCommit, GitHubBranch, GitHubMetadata, GitHubIssuePullRequest
from ..serializers import ExportDataSerializer
from utils.lookup import get_filterset_fields as _get_filterset_fields, get_search_fields as _get_search_fields

logger = logging.getLogger(__name__)


def _day_bounds_utc(d):
    """Recebe date e devolve (start_dt_utc, end_dt_utc) no mesmo dia."""
    start = datetime.combine(d, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(d, time.max).replace(tzinfo=timezone.utc)
    return start, end


def _date_field_for_model(model):
    """
    Define qual campo de data usar para filtro por intervalo.
    Ajuste aqui se necessário para outras tabelas.
    """
    if model is GitHubCommit:
        return "date"
    if model is GitHubIssuePullRequest:
        return "github_created_at"
    if model is GitHubMetadata:
        return "github_created_at"  # ajuste se preferir outro
    if model is GitHubBranch:
        # se houver um campo de criação/atualização no model:
        return "github_created_at"
    # fallback (sem filtro específico)
    return None


class ExportDataView(APIView):
    @extend_schema(
        summary="Export GitHub data",
        tags=["GitHub"],
        description=(
            "Export data from GitHub tables.\n"
            "- `format=json|csv`\n"
            "- Reaproveita filtros da UI via querystring (django-filters, search, ordering).\n"
            "- Também aceita filtros no BODY: `date` (um dia), ou `start_date`/`end_date` (intervalo).\n"
            "- Para `githubissuepullrequest`, permite `data_type=issue|pull_request`.\n"
            "- Campo opcional `fields` para limitar colunas do CSV."
        ),
        request=ExportDataSerializer,
        responses={
            200: OpenApiResponse(description="Exported data file"),
            400: OpenApiResponse(description="Invalid parameters"),
            404: OpenApiResponse(description="Table not found or no data found"),
            500: OpenApiResponse(description="Server error")
        },
        examples=[
            OpenApiExample(
                "Export issues of a single day (CSV)",
                value={"table": "githubissuepullrequest", "data_type": "issue", "format": "csv", "date": "2025-09-29"},
                summary="Export issues for a single day via body"
            ),
            OpenApiExample(
                "Export commits in a range (CSV)",
                value={"table": "githubcommit", "format": "csv", "start_date": "2025-03-15T00:00:00Z", "end_date": "2025-03-15T23:59:59Z"},
                summary="Export commits in a date range via body"
            ),
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
        selected_fields = serializer.validated_data.get('fields')

        # filtros de data vindos do body
        body_date = serializer.validated_data.get('date')
        body_start = serializer.validated_data.get('start_date')
        body_end = serializer.validated_data.get('end_date')

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
        repo = serializer.validated_data.get("repository")
        state = serializer.validated_data.get("state")
        creator = serializer.validated_data.get("creator")

        # Filtro específico de data_type para issues/PRs
        if model is GitHubIssuePullRequest and data_type:
            queryset = queryset.filter(data_type=data_type)

        # Filtro por IDs explícitos (se fornecidos)
        if ids:
            queryset = queryset.filter(id__in=ids)

        if repo:
            queryset = queryset.filter(repository_name__icontains=repo)

        if state:
            queryset = queryset.filter(state__iexact=state)
        if creator:
            queryset = queryset.filter(creator__icontains=creator)

        # ===== Filtros da UI via querystring (DjangoFilterBackend) =====
        filterset_fields = _get_filterset_fields(model)
        if filterset_fields:
            # Criamos uma "view fake" só com os atributos que o backend usa
            DummyView = type(
                "DummyView",
                (),
                {
                    "filterset_fields": filterset_fields,
                    "get_queryset": lambda self: model.objects.all(),
                },
            )
            backend = DjangoFilterBackend()
            queryset = backend.filter_queryset(request, queryset, DummyView())

        # ===== Busca ('search=') compatível com SearchFilter =====
        search_query = request.query_params.get('search')
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

        # ===== Ordenação ('ordering=') compatível com OrderingFilter =====
        ordering = request.query_params.get('ordering')
        if ordering:
            try:
                queryset = queryset.order_by(*[seg.strip() for seg in ordering.split(",") if seg.strip()])
            except Exception as e:
                logger.warning(f"Ignorando ordering inválido '{ordering}': {e}")

        # ===== Filtro de data vindo do BODY (um dia ou intervalo) =====
        date_field = _date_field_for_model(model)
        if date_field:
            if body_date:
                start_dt, end_dt = _day_bounds_utc(body_date)
                queryset = queryset.filter(**{f"{date_field}__gte": start_dt, f"{date_field}__lte": end_dt})
            elif body_start or body_end:
                if body_start:
                    queryset = queryset.filter(**{f"{date_field}__gte": body_start})
                if body_end:
                    queryset = queryset.filter(**{f"{date_field}__lte": body_end})

        if not queryset.exists():
            return Response(
                {"error": "No data found to export"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Base do nome do arquivo
        filename_parts = [table]
        if model is GitHubIssuePullRequest and data_type:
            filename_parts.append(data_type)
        filename_base = f"{'_'.join(filename_parts)}_export"

        # ===== Export JSON =====
        if format_type == 'json':
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

            try:
                response = HttpResponse(
                    json.dumps(data, default=str, indent=2),
                    content_type='application/json'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename_base}.json"'
                response['Access-Control-Expose-Headers'] = 'Content-Disposition'
                return response
            except Exception as e:
                logger.error(f"Error exporting data (json): {str(e)}")
                return Response(
                    {"error": f"Error exporting data: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # ===== Export CSV =====
        if not selected_fields:
            selected_fields = [f.name for f in model._meta.fields]

        def row_iter():
            # Cabeçalho
            yield [smart_str(col) for col in selected_fields]
            # Linhas
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
            def write(self, v):
                return v

        try:
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            def stream():
                for r in row_iter():
                    yield writer.writerow(r)

            response = HttpResponse(stream(), content_type="text/csv; charset=utf-8")
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response
        except Exception as e:
            logger.error(f"Error exporting data (csv): {str(e)}")
            return Response(
                {"error": f"Error exporting data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

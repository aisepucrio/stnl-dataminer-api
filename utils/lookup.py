
from django.db import models

def get_filterset_fields(model):
    """Generate filterset_fields dictionary for django-filters"""
    filterset_fields = {}
    for field in model._meta.fields:
        if isinstance(field, models.JSONField):
            continue
        elif isinstance(field, (models.DateField, models.TimeField, models.DateTimeField)):
            filterset_fields[field.name] = ['exact', 'gte', 'lte', 'year', 'month', 'day']
        elif isinstance(field, (models.CharField, models.TextField)):
            filterset_fields[field.name] = ['exact', 'icontains', 'iexact']
        elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
            filterset_fields[field.name] = ['exact', 'gte', 'lte']
        else:
            filterset_fields[field.name] = ['exact']
    
    return filterset_fields


def get_search_fields(model):
    """Generate a list of fields that are searchable (CharField, TextField) for DRF search_fields."""
    search_fields = []
    for field in model._meta.fields:
        if not isinstance(field, (models.JSONField, models.ForeignKey, models.ManyToManyField, models.OneToOneField, models.DateField, models.TimeField, models.DateTimeField)):
            search_fields.append(field.name)
    return search_fields
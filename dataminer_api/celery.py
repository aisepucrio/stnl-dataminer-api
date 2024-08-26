from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Define o módulo padrão de configurações do Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dataminer_api.settings')

app = Celery('dataminer_api')

# Carrega as configurações a partir do settings.py usando a configuração do Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre e carrega automaticamente tasks dos apps Django
app.autodiscover_tasks()

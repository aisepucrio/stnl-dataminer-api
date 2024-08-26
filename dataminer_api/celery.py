# dataminer_api/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# define o módulo de configuração do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dataminer_api.settings')

app = Celery('dataminer_api')

# Carrega as configurações do Celery a partir do arquivo settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobre tarefas dos apps registrados (procura por um arquivo tasks.py em cada app)
app.autodiscover_tasks(['jobs'])


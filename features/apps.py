from django.apps import AppConfig
from django.db import connection

class MiningConfig(AppConfig):
    name = 'mining'
    
    def ready(self):
        self.create_partitions()

    def create_partitions(self):
        sql_path = 'sql/create_partitions.sql'
        with open(sql_path, 'r') as f:
            sql = f.read()
        with connection.cursor() as cursor:
            cursor.execute(sql)

class FeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'features'

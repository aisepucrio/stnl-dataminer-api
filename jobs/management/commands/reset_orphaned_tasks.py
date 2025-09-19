from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Task


class Command(BaseCommand):
    help = 'Reset orphaned tasks after container restart'

    def handle(self, *args, **options):
        orphaned_tasks = Task.objects.filter(status__in=['STARTED', 'PENDING'])
        count = orphaned_tasks.count()
        
        if count == 0:
            self.stdout.write("Nenhuma tarefa órfã encontrada")
            return
        
        orphaned_tasks.update(
            status='FAILURE',
            error='Tarefa cancelada por reinício do container',
        )
        
        self.stdout.write(f"Resetadas {count} tarefa(s) órfã(s)")
        print(f"[INFO] Reset de {count} tarefas órfãs concluído")

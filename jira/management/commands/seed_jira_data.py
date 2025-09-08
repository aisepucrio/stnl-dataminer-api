# Em jira/management/commands/seed_jira_data.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

# Importa os modelos necessários do Jira
from jira.models import JiraProject, JiraUser, JiraIssue

class Command(BaseCommand):
    help = 'Populates the database with sample Jira data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Jira data...')

        # Limpa os dados antigos para garantir um novo começo
        self.stdout.write('Deleting old Jira data...')
        JiraIssue.objects.all().delete()
        JiraProject.objects.all().delete()
        JiraUser.objects.all().delete()

        # 1. Criar um Projeto de Amostra
        project = JiraProject.objects.create(
            id='10001',
            key='PROJ',
            name='Sample Project',
            simplified=False,
            projectTypeKey='software'
        )
        self.stdout.write(f'Sample project "{project.name}" created.')

        # 2. Criar Usuários de Amostra
        users = []
        for i in range(5):
            user = JiraUser.objects.create(
                accountId=f'user-id-{i+1}',
                displayName=f'Jira User {i+1}',
                emailAddress=f'jira.user{i+1}@example.com',
                active=True,
                timeZone='America/Sao_Paulo',
                accountType='atlassian'
            )
            users.append(user)
        self.stdout.write(f'{len(users)} sample Jira users created.')
        
        # 3. Criar Issues de Amostra
        for i in range(20): # Vamos criar 20 issues
            JiraIssue.objects.create(
                issue_id=f'2000{i}',
                issue_key=f'PROJ-{i+1}',
                project=project,
                created=timezone.now() - timedelta(days=20-i),
                updated=timezone.now(),
                status=random.choice(['To Do', 'In Progress', 'Done']),
                priority=random.choice(['High', 'Medium', 'Low']),
                creator=random.choice(users),
                reporter=random.choice(users),
                assignee=random.choice(users),
                summary=f'Fix bug in login screen #{i+1}',
                description='User is unable to log in when using a password with special characters.'
            )
        self.stdout.write('20 sample Jira issues created.')

        self.stdout.write(self.style.SUCCESS('Successfully seeded Jira data!'))
# Em github/management/commands/seed_github_data.py

import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

# --- IMPORTS CORRIGIDOS ---
# Importa os modelos com os nomes corretos
from github.models import GitHubMetadata, GitHubAuthor, GitHubCommit, GitHubIssue
from utils.models import Repository

class Command(BaseCommand):
    help = 'Populates the database with sample GitHub data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding GitHub data...')

        # Limpa os dados antigos para garantir um novo começo
        self.stdout.write('Deleting old GitHub data...')
        GitHubCommit.objects.all().delete()
        GitHubIssue.objects.all().delete()
        GitHubMetadata.objects.all().delete()
        GitHubAuthor.objects.all().delete()
        Repository.objects.filter(platform='github').delete()
        # 1. Criar um Repositório de Amostra
        # Primeiro, o registro genérico em 'utils.Repository'
        base_repo = Repository.objects.create(
            name='sample-github-repo',
            owner='test-owner',
            platform='github' # <-- Correção para 'platform'
        )
                
        # Depois, os metadados específicos do GitHub (usando GitHubMetadata)
        GitHubMetadata.objects.create(
            repository=base_repo,
            owner='test-owner',
            stars_count=random.randint(100, 5000),
            forks_count=random.randint(10, 500),
            open_issues_count=random.randint(5, 50),
            html_url=f'https://github.com/test-owner/sample-github-repo',
            created_at=timezone.now() - timedelta(days=365),
            updated_at=timezone.now(),
        )
        self.stdout.write(f'Sample repository "{base_repo.name}" created.')

        # 2. Criar Autores (Usuários) de Amostra
        authors = []
        for i in range(5):
            author = GitHubAuthor.objects.create(
                name=f'Dev {i+1}',
                email=f'dev{i+1}@example.com'
            )
            authors.append(author)
        self.stdout.write(f'{len(authors)} sample authors created.')
        
        # 3. Criar Commits de Amostra
        for i in range(30):
            GitHubCommit.objects.create(
                repository=base_repo, # Usa o objeto 'base_repo'
                sha=f'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1{i:02d}',
                message=f'feat: Implement feature #{i}',
                date=timezone.now() - timedelta(days=30-i),
                author=random.choice(authors),
                insertions=random.randint(0, 200),
                deletions=random.randint(0, 100),
                files_changed=random.randint(1, 5)
            )
        self.stdout.write('30 sample commits created.')

        # 4. Criar Issues de Amostra
        for i in range(10):
            GitHubIssue.objects.create(
                repository=base_repo, # Usa o objeto 'base_repo'
                issue_id=2000 + i,
                number=i + 1,
                title=f'Bug when clicking button #{i}',
                state=random.choice(['open', 'closed']),
                creator=random.choice(authors),
                created_at=timezone.now() - timedelta(days=10-i),
                updated_at=timezone.now()
            )
        self.stdout.write('10 sample issues created.')

        self.stdout.write(self.style.SUCCESS('Successfully seeded GitHub data!'))
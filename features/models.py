from django.db import models

class FeatureMining(models.Model):
    # Caminho para o repositório local
    repo_path = models.CharField(max_length=500)

    # Switches para ativar/desativar a mineração de diferentes tipos de dados
    mine_commits = models.BooleanField(default=False)
    mine_docs = models.BooleanField(default=False)
    mine_code = models.BooleanField(default=False)

    # Status da mineração (para rastrear se a mineração está em progresso, completa, etc.)
    status = models.CharField(max_length=50, default='pending')

    # Data e hora em que a mineração foi iniciada
    started_at = models.DateTimeField(auto_now_add=True)

    # Data e hora em que a mineração foi concluída
    finished_at = models.DateTimeField(null=True, blank=True)

    # Resultado da mineração (por exemplo, armazenar um resumo dos dados minerados)
    mining_result = models.TextField(null=True, blank=True)

    # Identificador para o processo de mineração
    process_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Mineração de Features em {self.repo_path}"
    
    from django.db import models

class Repositorio(models.Model):
    nome = models.CharField(max_length=255)
    ssh_url = models.CharField(max_length=255)
    tipo_mineracao = models.CharField(max_length=50)
    dados = models.JSONField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    tamanho = models.BigIntegerField()
    ultima_atualizacao = models.DateTimeField(auto_now=True)
    num_commits = models.IntegerField()

    class Meta:
        db_table = 'repositorios'  # Usa a tabela já criada
        managed = False  # Impede o Django de tentar criar ou modificar a tabela
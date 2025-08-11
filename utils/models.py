from django.db import models


class Repository(models.Model):
    """
    Modelo central para representar repositórios de diferentes plataformas
    """
    PLATFORM_CHOICES = [
        ('github', 'GitHub'),
        ('jira', 'Jira'),
    ]
    
    full_name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Nome completo do repositório (ex: 'owner/repo' para GitHub, 'project-key' para Jira)"
    )
    owner = models.CharField(max_length=255, help_text="Proprietário ou organização")
    name = models.CharField(max_length=255, help_text="Nome do repositório")
    platform = models.CharField(
        max_length=20, 
        choices=PLATFORM_CHOICES,
        help_text="Plataforma onde o repositório está hospedado"
    )
    url = models.URLField(null=True, blank=True, help_text="URL do repositório")
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Repository"
        verbose_name_plural = "Repositories"
        ordering = ['platform', 'full_name']
        indexes = [
            models.Index(fields=['platform', 'full_name']),
            models.Index(fields=['owner']),
        ]
    
    def __str__(self):
        return f"{self.platform.upper()}: {self.full_name}"
    
    @property
    def is_github(self):
        return self.platform == 'github'
    
    @property 
    def is_jira(self):
        return self.platform == 'jira'
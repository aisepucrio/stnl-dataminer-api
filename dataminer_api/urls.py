from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("Bem-vindo à página inicial do DataMiner API!!!!!!!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('github.urls')),
    path('jira/', include('jira.urls')),
    path('jobs/', include('jobs.urls')),
    path('', home),  # Adiciona uma página inicial para a URL raiz
]

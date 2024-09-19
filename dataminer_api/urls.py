from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from features import views as features_views 

def home(request):
    return HttpResponse("Bem-vindo à página inicial do DataMiner API!!!!!!!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('github.urls')),
    path('jira/', include('jira.urls')),
    path('', home),  # Adiciona uma página inicial para a URL raiz
    path('minerar/', features_views.minerar_features_view, name='minerar_features'),
]

from django.shortcuts import render
from django.http import JsonResponse
import features_mining_rust as mining
import os

# Função que faz a mineração de código a partir de uma view Django
def minerar_codigo_view(request):
    if request.method == "POST":
        repositorio_path = request.POST.get('repositorio_path')
        regex_file_path = request.POST.get('regex_file_path')

        if os.path.exists(repositorio_path) and os.path.exists(regex_file_path):
            mining.run_search_in_files(repositorio_path, regex_file_path)

            return JsonResponse({"status": "Mineração concluída"})
        else:
            return JsonResponse({"error": "Caminhos inválidos"}, status=400)

    return JsonResponse({"error": "Método inválido"}, status=405)

def minerar_features_view(request):
    if request.method == "POST":
        repositorio_path = request.POST.get('repositorio_path')
        regex_file_path = request.POST.get('regex_file_path')
        tipos_mineracao = request.POST.getlist('tipos_mineracao')

        if not os.path.exists(repositorio_path):
            return JsonResponse({"error": "Caminho do repositório inválido"}, status=400)
        if not os.path.exists(regex_file_path):
            return JsonResponse({"error": "Caminho do arquivo de regex inválido"}, status=400)

        # Processar cada tipo de mineração selecionado
        for tipo in tipos_mineracao:
            if tipo == 'codigo':
                mining.run_search_in_files(repositorio_path, regex_file_path)
            elif tipo == 'commits':
                # Aqui você chamaria sua função Rust para minerar commits
                mining.run_search_in_commits(repositorio_path, regex_file_path)
            elif tipo == 'doc':
                mining.run_search_in_files(repositorio_path, regex_file_path)

        return JsonResponse({"status": "Mineração concluída com sucesso!"})

    return render(request, 'mining_form.html')
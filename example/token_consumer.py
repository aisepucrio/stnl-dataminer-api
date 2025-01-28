import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def frenetic_github_requests():
    token = os.getenv("GITHUB_TOKENS")
    
    if not token:
        raise ValueError("Token não encontrado no .env")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    request_count = 0
    url = "https://api.github.com/user"  # Altere para o endpoint desejado
    
    while True:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            request_count += 1
            
            # Captura os limites de taxa da resposta
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            
            # Calcula tempo até o reset do limite
            current_time = time.time()
            time_until_reset = reset_time - current_time
            
            print(f"Requisição #{request_count}")
            print(f"Status: {response.status_code}")
            print(f"Restantes: {remaining}")
            print(f"Reset em: {time_until_reset:.0f} segundos")
            print("-" * 40)
            
            # Para quando atingir o limite
            if remaining <= 0:
                print("⚠️ Rate limit atingido! Pare de fazer requisições.")
                break
            
            # Intervalo entre requisições (ajuste conforme necessário)
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {str(e)}")
            break

# Execute a função
frenetic_github_requests()
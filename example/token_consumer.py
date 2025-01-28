import os
import requests
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import multiprocessing

load_dotenv()

def make_github_request(headers, request_number, print_lock):
    url = "https://api.github.com/user"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        with print_lock:
            print(f"Requisição #{request_number}")
            print(f"Status: {response.status_code}")
            print(f"Restantes: {response.headers.get('X-RateLimit-Remaining', 0)}")
            print("-" * 40)
            
        return int(response.headers.get("X-RateLimit-Remaining", 0))
    
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(f"Erro na requisição {request_number}: {str(e)}")
        return 0

def frenetic_github_requests():
    token = os.getenv("GITHUB_TOKENS")

    tokens = token.split(",")

    token = tokens[1]
    
    if not token:
        raise ValueError("Token não encontrado no .env")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print_lock = Lock()
    
    # Calcula o número máximo de threads
    max_workers = min(32, (multiprocessing.cpu_count() * 4))  # Limitando a 32 para segurança
    print(f"Iniciando com {max_workers} threads simultâneas")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        request_number = 0
        futures = []
        
        while True:
            # Cria várias requisições de uma vez
            for _ in range(max_workers):
                request_number += 1
                future = executor.submit(make_github_request, headers, request_number, print_lock)
                futures.append(future)
            
            # Verifica os resultados completados
            for completed_future in [f for f in futures if f.done()]:
                remaining = completed_future.result()
                if remaining <= 0:
                    print("⚠️ Rate limit atingido! Parando todas as threads...")
                    executor._threads.clear()
                    return
            
            # Remove futures completados da lista
            futures = [f for f in futures if not f.done()]
            
            # Reduz o intervalo entre batches de requisições
            time.sleep(0.5)

# Execute a função
if __name__ == "__main__":
    frenetic_github_requests()
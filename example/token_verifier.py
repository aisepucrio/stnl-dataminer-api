import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import argparse

load_dotenv()

def verificar_token_github(token):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get('https://api.github.com/rate_limit', headers=headers)
    
    if response.status_code == 200:
        dados = response.json()
        rate = dados['rate']
        
        limite_total = rate['limit']
        restantes = rate['remaining']
        reset_time = datetime.fromtimestamp(rate['reset'])
        
        print(f"Status do Token GitHub:")
        print(f"Limite total de requisições: {limite_total}")
        print(f"Requisições restantes: {restantes}")
        print(f"Limite será resetado em: {reset_time}")
        
        return restantes
    else:
        print(f"Erro ao verificar token. Status code: {response.status_code}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verifica o status de um token do GitHub')
    parser.add_argument('-i', '--index', type=int, default=0,
                       help='Índice do token a ser verificado (começando em 0)')
    
    args = parser.parse_args()
    
    token = os.getenv('GITHUB_TOKENS')
    token = token.split(',')
    
    if args.index >= len(token):
        print(f"Erro: índice {args.index} é maior que o número de tokens disponíveis ({len(token)})")
        exit(1)
        
    token = token[args.index]
    verificar_token_github(token)

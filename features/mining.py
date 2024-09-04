import features_mining_rust as mining
import os
import psycopg2
from psycopg2 import sql
import json

# Função para conectar ao banco de dados PostgreSQL
def conectar_banco():
    return psycopg2.connect(
        dbname="seu_banco",
        user="seu_usuario",
        password="sua_senha",
        host="localhost"
    )

# Função para inserir resultados na partição específica da tabela
def inserir_resultados_no_banco(tipo_mineracao, resultados):
    conn = conectar_banco()
    cur = conn.cursor()

    query = sql.SQL("""
        INSERT INTO {particao} (nome_repositorio, feature, caminho, linha, commit_hash, autor, data, commit_message, branch, minerado_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    """).format(particao=sql.Identifier(f'repositorios_{tipo_mineracao}'))

    for resultado in resultados:
        cur.execute(query, (
            resultado['feature'], resultado['path'], resultado['line'], resultado['commit_hash'],
            resultado['author'], resultado['date'], resultado['commit_message'], resultado['branch']
        ))

    conn.commit()
    cur.close()
    conn.close()

# Função para minerar features em código-fonte
def minerar_codigo(repositorio_path, regex_file_path):
    print("Iniciando mineração no código-fonte...")
    mining.run_search_in_files(repositorio_path, regex_file_path)

    # Carregar os resultados da mineração salvos em 'results.json'
    with open('results.json', 'r') as file:
        resultados = json.load(file)

    # Inserir os resultados no banco de dados na partição 'repositorios_codigo'
    inserir_resultados_no_banco('codigo', resultados)
    print("Mineração de código concluída e resultados armazenados.")

# Função para minerar features em commits
def minerar_commits(repositorio_path, regex_file_path):
    print("Iniciando mineração nos commits...")
    # Aqui você pode usar a API `git2` no código Rust para minerar os commits
    # Vamos chamar a função Rust que você precisaria implementar para minerar nos commits
    mining.run_search_in_commits(repositorio_path, regex_file_path)

    # Carregar os resultados da mineração salvos em 'results.json'
    with open('results.json', 'r') as file:
        resultados = json.load(file)

    # Inserir os resultados no banco de dados na partição 'repositorios_commits'
    inserir_resultados_no_banco('commits', resultados)
    print("Mineração de commits concluída e resultados armazenados.")

# Função para minerar features em documentação
def minerar_documentacao(repositorio_path, regex_file_path):
    print("Iniciando mineração em documentação...")
    mining.run_search_in_files(repositorio_path, regex_file_path)

    # Carregar os resultados da mineração salvos em 'results.json'
    with open('results.json', 'r') as file:
        resultados = json.load(file)

    # Inserir os resultados no banco de dados na partição 'repositorios_doc'
    inserir_resultados_no_banco('doc', resultados)
    print("Mineração de documentação concluída e resultados armazenados.")

# Função principal que orquestra a mineração
def executar_mineracao(tipo_mineracao, repositorio_path, regex_file_path):
    if tipo_mineracao == 'codigo':
        minerar_codigo(repositorio_path, regex_file_path)
    elif tipo_mineracao == 'commits':
        minerar_commits(repositorio_path, regex_file_path)
    elif tipo_mineracao == 'doc':
        minerar_documentacao(repositorio_path, regex_file_path)
    else:
        print("Tipo de mineração não reconhecido.")


# Exemplo de execução de mineração a partir da interface
def interface_usuario():
    # Simulação de interface web onde o usuário escolhe o tipo de mineração e o caminho do repositório
    tipo_mineracao = input("Digite o tipo de mineração (codigo, commits, doc): ")
    repositorio_path = input("Digite o caminho para o repositório: ")
    regex_file_path = input("Digite o caminho para o arquivo de regex: ")

    # Executar mineração com os dados fornecidos pelo usuário
    executar_mineracao(tipo_mineracao, repositorio_path, regex_file_path)

if __name__ == "__main__":
    # Chamando a interface para interação
    interface_usuario()

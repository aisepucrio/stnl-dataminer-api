import ollama 
import sys
import pandas as pd
import json
import os
from datetime import datetime
import textwrap

class DataReader:
    def __init__(self, file_path):
        self.file_path = file_path
        print(f"\n[INFO] [DataReader] Inicializando com arquivo: {file_path}")

    def read_csv(self):
        print(f"[INFO] [DataReader] Tentando ler arquivo CSV: {self.file_path}")
        
        if not os.path.exists(self.file_path):
            print(f"[ERRO] [DataReader] Arquivo não encontrado: {self.file_path}")
            return None
            
        try:
            df = pd.read_csv(self.file_path)
            print(f"[INFO] [DataReader] Arquivo CSV lido com sucesso. Colunas: {df.columns.tolist()}")
            print(f"[INFO] [DataReader] Número de registros: {len(df)}")
            return df
        except Exception as e:
            print(f"[ERRO] [DataReader] Falha ao ler CSV: {str(e)}")
            return None
    
    @property
    def comments_data(self):
        print(f"[INFO] [DataReader] Extraindo dados de comentários para: {self.file_path}")
        
        df = self.read_csv()
        if df is None:
            print("[ERRO] [DataReader] Não foi possível ler o arquivo CSV")
            return None
            
        try:
            if self.file_path.endswith('commits.csv'):
                print("[INFO] [DataReader] Processando arquivo de commits")
                data = df['message']
                print(f"[INFO] [DataReader] Dados extraídos com {len(data)} registros")
                return data
            
            elif self.file_path.endswith('jira.csv'):
                print("[INFO] [DataReader] Processando arquivo de jira")
                data = df[['commits', 'issuetype_description', 'summary', 'description']]
                print(f"[INFO] [DataReader] Dados extraídos com {len(data)} registros")
                return data
            
            elif self.file_path.endswith('Issues&PRs.csv'):
                print("[INFO] [DataReader] Processando arquivo de Issues&PRs")
                data = df[['comments', 'title', 'body', 'reactions']]
                print(f"[INFO] [DataReader] Dados extraídos com {len(data)} registros")
                return data
            else:
                print(f"[ERRO] [DataReader] Tipo de arquivo não reconhecido: {self.file_path}")
                return None
        except KeyError as e:
            print(f"[ERRO] [DataReader] Coluna não encontrada: {str(e)}")
            print(f"[INFO] [DataReader] Colunas disponíveis: {df.columns.tolist()}")
            return None
        except Exception as e:
            print(f"[ERRO] [DataReader] Erro ao extrair dados: {str(e)}")
            return None
    
class LLMRunner:
    def __init__(self, model_name):
        self.model_name = model_name
        print(f"\n[INFO] [LLMRunner] Inicializando com modelo: {model_name}")
        try:
            self.client = ollama.Client(host='http://localhost:11434')
            print("[INFO] [LLMRunner] Cliente Ollama inicializado com sucesso")
        except Exception as e:
            print(f"[ERRO] [LLMRunner] Falha ao inicializar cliente Ollama: {str(e)}")
        self._prompt = None

    def read_prompt(self, prompt_name):
        print(f"[INFO] [LLMRunner] Lendo arquivo de prompt: {prompt_name}")
        
        prompt_path = f"analysis/prompts/{prompt_name}.txt"
        if not os.path.exists(prompt_path):
            print(f"[ERRO] [LLMRunner] Arquivo de prompt não encontrado: {prompt_path}")
            return None
            
        try:
            with open(prompt_path, encoding="utf-8") as f:
                content = f.read()
                if not content:
                    print("[ERRO] [LLMRunner] Arquivo de prompt está vazio")
                    sys.exit(1)
                else:
                    print(f"[INFO] [LLMRunner] Prompt carregado com {len(content)} caracteres")
                    return content
        except UnicodeDecodeError as e:
            print(f"[ERRO] [LLMRunner] Erro de decodificação de caracteres: {str(e)}")
            print("[INFO] [LLMRunner] Tentando com diferentes codificações...")
            
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(prompt_path, encoding=encoding) as f:
                        content = f.read()
                        print(f"[INFO] [LLMRunner] Prompt carregado com codificação {encoding}")
                        return content
                except:
                    pass
            
            print("[ERRO] [LLMRunner] Não foi possível ler o arquivo de prompt com nenhuma codificação")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRO] [LLMRunner] Erro ao ler arquivo de prompt: {str(e)}")
            sys.exit(1)
    
    @property
    def prompt(self):
        return self._prompt
    
    @prompt.setter
    def prompt(self, data_type):
        print(f"[INFO] [LLMRunner] Configurando prompt para tipo de dados: {data_type}")
        
        if data_type == 'jira':
            self._prompt = self.read_prompt('jira')
            
        elif data_type == 'commits':
            self._prompt = self.read_prompt('commits')

        elif data_type == 'Issues&PRs':
            self._prompt = self.read_prompt('Issues&PRs')
        
        else:
            print(f"[AVISO] [LLMRunner] Tipo de dados desconhecido: {data_type}")
            self._prompt = None
            
        if self._prompt is None:
            print("[ERRO] [LLMRunner] Não foi possível configurar o prompt")
        else:
            print("[INFO] [LLMRunner] Prompt configurado com sucesso")

    def run_llm(self, data_type):
        print(f"\n[INFO] [LLMRunner] Iniciando processamento para: {data_type}")
        print(f"[INFO] [LLMRunner] Data e hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.prompt = data_type
        self.type = data_type  

        file_path = f'analysis/data/{data_type}.csv'
        print(f"[INFO] [LLMRunner] Caminho do arquivo: {file_path} (existe: {os.path.exists(file_path)})")
        
        data = DataReader(file_path)
        self.comments_data = data.comments_data
        
        if self.comments_data is None:
            print("[ERRO] [LLMRunner] Não foi possível obter dados de comentários")
            return []
            
        if len(self.comments_data) == 0:
            print("[AVISO] [LLMRunner] Nenhum comentário encontrado para processar")
            return []
            
        print(f"[INFO] [LLMRunner] Processando {len(self.comments_data)} comentários")
        
        results = []  

        for index, row in enumerate(self.comments_data.iterrows()):
            print(f"\n[INFO] [LLMRunner] Processando item {index+1}/{len(self.comments_data)}")
            
            try:
                idx, row_data = row  # row é uma tupla (índice, dados)
                
                if self.type == 'jira':
                    details = textwrap.dedent(f"""
                        ## Resumo
                        {row_data['summary']}
                        
                        ## Descrição
                        {row_data['description']}
                        
                        ## Commits
                        {row_data['commits']}
                        
                        ## Tipo de Issue
                        {row_data['issuetype_description']}
                    """).strip()
                
                elif self.type == 'commits':
                    details = str(row_data).strip()
                
                elif self.type == 'Issues&PRs':
                    details = textwrap.dedent(f"""
                        ## Título
                        {row_data['title']}
                        
                        ## Corpo
                        {row_data['body']}
                        
                        ## Comentários
                        {row_data['comments']}
                        
                        ## Reações
                        {row_data['reactions']}
                    """).strip()
                
                print(f"[INFO] [LLMRunner] Enviando prompt para o modelo com {len(details)} caracteres")

                prompt = textwrap.dedent(f"""
                    Read the following message (in triple quotes, formatted as markdown):

                    \"\"\"
                    {details}
                    \"\"\"

                    {self.prompt}
                """)

                print(f"\n\n[INFO] [LLMRunner] Prompt: {prompt}\n\n")
                
                try:
                    response = self.client.generate(
                        model=self.model_name,
                        format="json",
                        options={
                            "temperature": 1,
                            "num_ctx": 8192,
                            "num_predict": -1
                        },
                        stream=False,
                        prompt=prompt
                    )
                    print(f"[INFO] [LLMRunner] Resposta recebida do modelo: {len(str(response))} caracteres")
                    
                    # Extrai o conteúdo da resposta em formato serializável
                    try:
                        # Tenta acessar o conteúdo da resposta (pode variar dependendo da API)
                        if hasattr(response, 'response'):
                            serializable_response = {"response": response.response}
                        elif hasattr(response, 'content'):
                            serializable_response = {"content": response.content}
                        elif hasattr(response, 'text'):
                            serializable_response = {"text": response.text}
                        else:
                            # Se não conseguir acessar diretamente, converte para string
                            print("[AVISO] [LLMRunner] Usando método alternativo para serializar resposta")
                            serializable_response = {"raw_response": str(response)}
                        
                        # Adicione mais informações úteis se disponíveis
                        if hasattr(response, 'model'):
                            serializable_response["model"] = response.model
                        if hasattr(response, 'created_at'):
                            serializable_response["created_at"] = response.created_at
                        
                        # Adiciona metadados sobre o item sendo processado
                        serializable_response["item_index"] = index
                        
                        results.append(serializable_response)
                        print(f"[INFO] [LLMRunner] Resposta serializada com sucesso")
                        
                    except Exception as e:
                        print(f"[ERRO] [LLMRunner] Falha ao serializar resposta: {str(e)}")
                        print("[AVISO] [LLMRunner] Salvando representação em string da resposta")
                        results.append({"error": str(e), "raw_response": str(response)})
                    
                except Exception as e:
                    print(f"[ERRO] [LLMRunner] Falha ao gerar resposta do modelo: {str(e)}")
                
            except Exception as e:
                print(f"[ERRO] [LLMRunner] Erro ao processar item {index}: {str(e)}")
        
        print(f"\n[INFO] [LLMRunner] Processamento concluído. Total de {len(results)} resultados")
        
        output_path = f'analysis/data/{data_type}_results.json'
        print(f"[INFO] [LLMRunner] Salvando resultados em: {output_path}")
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"[INFO] [LLMRunner] Resultados salvos com sucesso")
        except Exception as e:
            print(f"[ERRO] [LLMRunner] Falha ao salvar resultados: {str(e)}")

        return results  

if __name__ == '__main__':
    print("\n" + "="*80)
    print(f"INICIANDO PROCESSAMENTO DE SENTIMENTOS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    llm = LLMRunner('mistral-small:24b')
    results = llm.run_llm('Issues&PRs')
    
    print("\n" + "="*80)
    print(f"PROCESSAMENTO CONCLUÍDO - Total de resultados: {len(results)}")
    print("="*80 + "\n")

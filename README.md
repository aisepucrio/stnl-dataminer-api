# API de Mineração de Dados de Desenvolvimento

## Descrição

Esta é uma API desenvolvida em Django para realizar mineração e análise de dados de desenvolvimento de software, permitindo extrair informações valiosas de repositórios GitHub e Jira. A ferramenta possibilita o acompanhamento detalhado do ciclo de vida de projetos, incluindo análise de commits, pull requests, issues e branches, fornecendo insights importantes sobre o processo de desenvolvimento.

## Funcionalidades

1. **Mineração do GitHub**: Extração de dados de commits, pull requests, issues e branches
2. **Integração com Jira**: Coleta de dados de tickets e sprints
3. **Análise Temporal**: Acompanhamento da evolução do projeto ao longo do tempo
4. **API Documentada**: Endpoints documentados usando DRF Spectacular

## Requisitos

Antes de começar, você precisará instalar:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/downloads)

## Instalação e Configuração

1. **Clone o Repositório**
   ```bash
   git clone https://github.com/seu_usuario/dataminer-api.git
   cd dataminer-api
   ```

2. **Configure o Arquivo .env**
   
   Crie um arquivo `.env` na raiz do projeto com as seguintes informações:
   ```
   GITHUB_TOKENS=seu_token_github
   POSTGRES_DB=nome_do_banco
   POSTGRES_USER=usuario_postgres
   POSTGRES_PASSWORD=senha_postgres
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   ```

3. **Verifique o Formato do Arquivo start.sh**
   
   Abra o arquivo `start.sh` em sua IDE e confirme que o formato de linha está como LF (isso geralmente é visível no canto inferior direito da IDE). Se estiver como CRLF, altere para LF.

4. **Inicie os Containers**
   ```bash
   docker-compose up --build
   ```

## Utilizando a API

A API oferece diversos endpoints para mineração de dados. Os exemplos abaixo utilizam o repositório esp8266/Arduino como demonstração, mas você pode substituir por qualquer repositório público do GitHub alterando o parâmetro `repo_name`. Da mesma forma, o intervalo de datas (`start_date` e `end_date`) pode ser ajustado conforme sua necessidade.

### 1. Mineração de Commits
```
GET http://localhost:8000/api/github/commits/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 2. Mineração de Issues
```
GET http://localhost:8000/api/github/issues/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 3. Mineração de Pull Requests
```
GET http://localhost:8000/api/github/pull-requests/?repo_name=esp8266/Arduino&start_date=2022-11-01T00:00:00Z&end_date=2023-12-29T00:00:00Z
```

### 4. Mineração de Branches
```
GET http://localhost:8000/api/github/branches/?repo_name=esp8266/Arduino
```

## Armazenamento dos Dados

Após a conclusão da mineração, os dados são:

1. **Salvos no PostgreSQL**: Você pode acessar os dados localmente usando as mesmas credenciais configuradas no arquivo `.env`. Por exemplo:
   ```bash
   psql -h localhost -U seu_usuario -d nome_do_banco
   ```

2. **Retornados como JSON**: Uma resposta JSON é fornecida imediatamente após a mineração para visualização dos dados coletados.

## Configuração do Token GitHub

### Como Gerar um Token GitHub:

1. Acesse [GitHub Settings > Developer Settings > Personal Access Tokens > Tokens (classic)](https://github.com/settings/tokens)
2. Clique em "Generate new token (classic)"
3. Selecione os seguintes escopos:
   - `repo` (acesso completo aos repositórios)
   - `read:org` (leitura de dados da organização)
   - `read:user` (leitura de dados do usuário)
4. Gere o token e copie-o imediatamente

### Configurando Múltiplos Tokens:

Para evitar limitações de taxa da API do GitHub, você pode configurar múltiplos tokens. No arquivo `.env`, adicione-os separados por vírgulas:

```
GITHUB_TOKENS='token1,token2,token3'
```

A API automaticamente alternará entre os tokens quando um deles atingir o limite de requisições.

## Testando a API

Para fazer um teste rápido da API, você pode utilizar o script `user_test.py` fornecido no repositório:

```bash
python user_test.py
```

Este script realizará uma série de requisições de teste para verificar o funcionamento da mineração de dados.

## Observações Importantes

- Certifique-se de que seu token do GitHub possui as permissões necessárias para acessar os repositórios desejados
- O PostgreSQL deve estar rodando na porta padrão 5432
- Todos os timestamps devem estar no formato ISO 8601 (YYYY-MM-DDTHH:mm:ssZ)

# API de Mineração de Features

## Descrição

Esta é uma API desenvolvida em Django para realizar a mineração de features em repositórios de código local. A API suporta a mineração de commits, documentação e código, e utiliza um subprocesso para executar um código Rust que realiza a mineração propriamente dita. Os resultados da mineração são armazenados em um banco de dados PostgreSQL.

## Funcionalidades

1. Mineração de Commits, Documentação e Código: Escolha quais aspectos do repositório deseja minerar.
2. Integração com Rust: A mineração de features é realizada por um código Rust executado via subprocesso.
3. Persistência de Dados: Os resultados da mineração são armazenados em um banco de dados PostgreSQL.
4. API Modular e Documentada: Todos os endpoints são documentados usando DRF Spectacular.

## Requisitos

- Python 3.10+
- Django 4.x
- PostgreSQL 12+
- Rust (para compilar o minerador de features)
- Git

## Instalação

1. Clonar o Repositório

```bash
Copy code
git clone https://github.com/seu_usuario/dataminer-api.git
cd dataminer-api
```

2. Criar e Ativar o Ambiente Virtual

```bash
Copy code
python -m venv venv-api
source venv-api/bin/activate  # No Windows: venv-api\Scripts\activate
```

3. Instalar as Dependências

```bash
Copy code
pip install -r requirements.txt
```

4. Configurar o Banco de Dados

Edite o arquivo settings.py na seção DATABASES para incluir as credenciais do seu banco de dados PostgreSQL:

```python
Copy code
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mining_db',
        'USER': 'seu_usuario',
        'PASSWORD': 'sua_senha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. Aplicar as Migrações
```bash
Copy code
python manage.py makemigrations
python manage.py migrate
```

6. Compilar o Código Rust

Certifique-se de que o Rust está instalado e depois compile o código de mineração:

```bash
Copy code
cd caminho/para/o/projeto/rust
cargo build --release
```

O binário resultante deve ser movido para o diretório do projeto Django ou acessível via PATH.

7. Rodar o Servidor Django

```bash
python manage.py runserver
```

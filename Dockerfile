# DOCKERFILE: Script que define como criar a IMAGEM de um docker
# DOCKER-COMPOSE.yaml: Arq. de config. que define, gerencia e orquestra multiplos CONTAINERS (instâncias de imagens).

FROM python:3.12.5-slim

RUN apt-get update && apt-get install -y git

# Instale o Redis
RUN apt-get update && apt-get install -y redis-server

# Instale o Celery
RUN pip install celery redis

# Definir o diretório de trabalho no contêiner
WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt
# pip freeze > requirements.txt

# Copia o código do projeto para o diretório de trabalho
COPY . /app

# Expoe a porta que o Django usa, basicamente documenta a porta que o django ouvirá do container
# e a pora que o redis irá usar
EXPOSE 8000
EXPOSE 6379

# Roda o servidor de desenvolvimento Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# Exponha a porta do Redis (opcional, caso o Redis esteja sendo executado no mesmo contêiner)

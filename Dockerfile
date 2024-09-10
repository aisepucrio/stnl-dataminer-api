# DOCKERFILE: Script que define como criar a IMAGEM de um docker
# DOCKER-COMPOSE.yaml: Arq. de config. que define, gerencia e orquestra multiplos CONTAINERS (instâncias de imagens).

FROM python:3.12.5-slim

RUN apt-get update && apt-get install -y git

# Definir o diretório de trabalho no contêiner
WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

# Copia o código do projeto para o diretório de trabalho
COPY . /app

RUN chmod +x start.sh
CMD ["/bin/bash", "start.sh"]

FROM python:3.12.5-slim

# Instalar dependências do sistema, incluindo o cliente PostgreSQL
RUN apt-get update && apt-get install -y \
    git \
    curl \
    netcat-openbsd \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho no contêiner
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia o código do projeto para o diretório de trabalho
COPY . /app

RUN chmod +x start.sh

CMD ["/bin/bash", "start.sh"]

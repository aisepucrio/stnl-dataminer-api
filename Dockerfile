FROM python:3.12.5-slim

# Instalar dependências do sistema, incluindo netcat-openbsd
RUN apt-get update && apt-get install -y \
    git \
    curl \
    netcat-openbsd \
    && apt-get clean

# Definir o diretório de trabalho no contêiner
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia o código do projeto para o diretório de trabalho
COPY . /app

RUN chmod +x start.sh

CMD ["/bin/bash", "start.sh"]

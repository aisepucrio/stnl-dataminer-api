FROM python:3.12.5-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    netcat-openbsd \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

RUN chmod +x start.sh

CMD ["/bin/bash", "start.sh"]
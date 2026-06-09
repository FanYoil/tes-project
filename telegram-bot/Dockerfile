FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    nano \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/telegram-shell data

ENV PYTHONUNBUFFERED=1
ENV TERMINAL_WORKING_DIR=/tmp/telegram-shell

CMD ["python", "bot.py"]

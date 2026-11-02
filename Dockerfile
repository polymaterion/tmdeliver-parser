FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && apt-get purge -y build-essential && apt-get autoremove -y
COPY app ./app
COPY migrations ./migrations
COPY locales ./locales
COPY rules ./rules
COPY config ./config
RUN useradd -m -u 10001 appuser && mkdir -p /secrets && chown appuser /secrets
USER appuser

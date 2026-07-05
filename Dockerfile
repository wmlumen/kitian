FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system libs for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Build deps
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# App files (copia todo lo del repo Git)
COPY . /app

EXPOSE 8080
ENV KITIAN_PORT=8080

CMD ["python", "/app/server.py"]

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

# App files
COPY kitian_http_standalone_real.py /app/kitian_http_standalone_real.py
COPY server.py /app/server.py
COPY kitian /app/kitian
COPY nebula_web.html /app/nebula_web.html
COPY kitian_health_dashboard.html /app/kitian_health_dashboard.html
COPY kitian_health.json /app/kitian_health.json
COPY kitian_config.json /app/kitian_config.json

EXPOSE 8080
ENV KITIAN_PORT=8080

CMD ["python", "/app/server.py"]

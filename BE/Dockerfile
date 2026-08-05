FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir -e .

# Railway injects PORT (often 8080). EXPOSE is informational; always bind $PORT.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "echo \"Starting uvicorn on 0.0.0.0:${PORT:-8080}\" && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]

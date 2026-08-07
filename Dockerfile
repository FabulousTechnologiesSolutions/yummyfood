FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 6060

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "conf.asgi:application", "--host", "0.0.0.0", "--port", "6060", "--proxy-headers", "--forwarded-allow-ips", "*"]

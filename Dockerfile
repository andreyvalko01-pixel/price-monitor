FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY price_monitor ./price_monitor
CMD ["python", "-m", "price_monitor", "--config", "/app/config.toml"]

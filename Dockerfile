FROM python:3.11-slim

WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 libgtk-3-0 libxshmfence1 \
    fonts-liberation libcurl4 wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install chromium && rm -rf /root/.cache/ms-playwright/chromium-*/ffmpeg*

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]


FROM python:3.10

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y wget curl unzip xvfb libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 libdrm2 libgbm1 libasound2 libxcomposite1 libxdamage1 libxrandr2 libgtk-3-0

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]

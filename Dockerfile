FROM python:3.10

WORKDIR /app

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgtk-3-0 \
    fonts-unifont \
    libgdk-pixbuf-xlib-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browser dependencies
RUN python -m playwright install --with-deps

# Default port is 8000 unless overridden by Render
ENV PORT=8000

# Use shell form CMD so $PORT resolves at runtime
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]

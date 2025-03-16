FROM python:3.9-slim

WORKDIR /app

# 安裝編譯工具和依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 設置環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 複製並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 直接使用 CMD 運行應用
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
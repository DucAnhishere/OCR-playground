# ==========================================
# GIAI ĐOẠN 1: BUILDER
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /build

# Cài đặt các công cụ biên dịch (rất nặng nhưng cần thiết để cài đặt thư viện)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    python3-dev \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Tạo môi trường ảo (venv) để cách ly toàn bộ thư viện cài đặt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# GIAI ĐOẠN 2: RUNNER
# ==========================================
FROM python:3.10-slim AS runner

# Chỉ cài đặt các thư viện hệ thống cần thiết lúc chạy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy thư mục môi trường ảo đã cài xong xuôi từ Stage 1 sang
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

EXPOSE 8003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]

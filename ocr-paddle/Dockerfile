# ==========================================
# GIAI ĐOẠN 1: BUILDER
# ==========================================
# Dùng CUDA 12.2 + cuDNN8 runtime (PaddlePaddle GPU 3.x yêu cầu cuDNN)
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04 AS builder

# Cài Python 3.10 + công cụ build
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    gcc \
    g++ \
    make \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Đặt python3.10 là mặc định
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

WORKDIR /build

# Tạo môi trường ảo (venv) để cách ly toàn bộ thư viện cài đặt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Cài PaddlePaddle GPU 3.x từ index URL chính thức của PaddlePaddle
# (PyPI chỉ có paddlepaddle-gpu đến bản 2.6.2, từ 3.x phải dùng server riêng)
# cu118 = tương thích CUDA 11.8+ (hoạt động với CUDA 12.x)
RUN pip install --no-cache-dir paddlepaddle-gpu==3.0.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# GIAI ĐOẠN 2: RUNNER
# ==========================================
# Runner cũng cần CUDA + cuDNN runtime để chạy GPU ops
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04 AS runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

WORKDIR /app

# Copy thư mục môi trường ảo đã cài xong xuôi từ Stage 1 sang
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

EXPOSE 8003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]

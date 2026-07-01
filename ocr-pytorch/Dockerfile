FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và quá trình build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ocr-pytorch/requirements.txt .

# Cài đặt thư viện Python (đã comment torch/torchvision trong requirements.txt)
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY ocr-pytorch/ .
COPY shared/ ./shared/

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]

# ==========================================
# GIAI ĐOẠN 1: BUILDER
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY image-processor/requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# ==========================================
# GIAI ĐOẠN 2: RUNNER
# ==========================================
FROM python:3.10-slim AS runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY image-processor/ .
COPY shared/ ./shared/

EXPOSE 8004

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]

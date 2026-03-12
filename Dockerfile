FROM python:3.12-slim

WORKDIR /app

# Install system deps needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Run as non-root
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Cloud Run injects PORT env var
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]

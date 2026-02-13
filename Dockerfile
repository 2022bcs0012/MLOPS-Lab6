FROM python:3.9-slim

# Prevent python buffering + bytecode
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps required by sklearn/pandas
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python deps first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY app ./app
COPY data ./data

# Ensure artifacts directory exists
RUN mkdir -p app/artifacts

# Run training
CMD ["python", "app/train.py"]

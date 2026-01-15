# Multi-stage build for smaller image size
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a symbolic link for python3 to python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .

# Create directories for input/output
RUN mkdir -p /app/videos /app/output /app/cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TORCH_HOME=/app/cache
ENV HF_HOME=/app/cache
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Expose port for potential web interface (future)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import whisper; print('Whisper OK')" || exit 1

# Run the application
CMD ["python", "main.py"]

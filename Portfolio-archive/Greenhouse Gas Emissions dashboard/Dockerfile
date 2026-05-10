# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn and Gevent
RUN pip install gunicorn==20.1.0 gevent==22.10.2

# Copy application code
COPY . .

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8050

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DASH_DEBUG_MODE=False \
    PYTHONMALLOC=malloc \
    MALLOC_TRIM_THRESHOLD_=100000

# Run the application with Gunicorn using explicit values
CMD ["gunicorn", \
     "--workers", "4", \
     "--threads", "2", \
     "--max-requests", "1000", \
     "--timeout", "30", \
     "--worker-class", "gevent", \
     "--bind", "0.0.0.0:8050", \
     "app:server"]
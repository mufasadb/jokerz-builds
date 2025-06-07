FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY templates/ ./templates/
COPY main.py .
COPY web_dashboard.py .
COPY discord_bot_interface.py .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV DB_PATH=/app/data/ladder_snapshots.db
ENV COLLECTION_TIME=02:00
ENV CLEANUP_TIME=03:00
ENV CLEANUP_DAYS=90
ENV LOG_LEVEL=INFO

# Expose ports
EXPOSE 5000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "from src.storage.database import DatabaseManager; db = DatabaseManager(); print('OK')" || exit 1

# Default command runs the daily collector
CMD ["python", "-m", "src.scheduler.daily_collector"]
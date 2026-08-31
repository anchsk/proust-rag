FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir \
    torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port and default command to run FastAPI with uvicorn
EXPOSE 8000

# Default command runs uvicorn on the module `main:app`
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
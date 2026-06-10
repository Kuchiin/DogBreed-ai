# Use an official Python runtime with a slim footprint
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies that might be needed for image processing (Pillow) or numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files (including the main.py script and local checkpoint weights if present)
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Start the application using python main.py
CMD ["python", "main.py"]

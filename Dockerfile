# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application
COPY . .

# Expose the dynamic port
EXPOSE 5001

# Run with Gunicorn, listening on the port provided by Render
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5001} app:app"]

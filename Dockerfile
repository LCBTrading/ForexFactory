# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    libgconf-2-4 \
    libnss3 \
    libx11-6 \
    libx11-dev \
    libxkbcommon0 \
    libxss1 \
    libasound2 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft repository and install Microsoft Edge
RUN wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add - && \
    echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list && \
    apt-get update && apt-get install -y microsoft-edge-stable

# Set a fixed version for msedgedriver (update as needed)
ENV EDGE_DRIVER_VERSION=133.0.3065.69

# Download and install msedgedriver
RUN wget -q "https://msedgedriver.azureedge.net/${EDGE_DRIVER_VERSION}/edgedriver_linux64.zip" -O edgedriver.zip && \
    unzip edgedriver.zip && \
    rm edgedriver.zip && \
    mv msedgedriver /usr/bin/ && \
    chmod +x /usr/bin/msedgedriver

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Start the application with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]

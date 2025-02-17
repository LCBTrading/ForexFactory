# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install dependencies required for Edge
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
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft Edge
RUN wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add - && \
    echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list && \
    apt-get update && apt-get install -y microsoft-edge-stable

# Install msedgedriver (if available via apt)
RUN apt-get install -y msedgedriver

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Start the application with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]

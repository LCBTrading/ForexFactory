# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code (including data.csv and app.py)
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Start the application with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]

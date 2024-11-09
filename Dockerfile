# Use the official Python image from the Docker Hub
FROM python:3.11.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose the port the app runs on
EXPOSE 8090

# Define the command to run the application
CMD ["python3", "app.py", "--host=0.0.0.0"]
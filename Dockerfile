# Use an official Python runtime as a parent image
FROM python:3.13-alpine@sha256:a94caf6aab428e086bc398beaf64a6b7a0fad4589573462f52362fd760e64cc9

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Also install Gunicorn, a Python WSGI HTTP Server for UNIX
RUN pip install --no-cache-dir -r requirements.txt \
	&& pip install --no-cache-dir gunicorn

# Copy your application code
COPY . .

# Make port 5000 available to the world outside this container
# Gunicorn will bind to this port
EXPOSE 5000

# Run Gunicorn as the production server
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "server:app"]

# Use a slim and official Python base image
FROM python:3.11-slim-bullseye

# Install openssl for certificate generation
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and scripts
COPY requirements.txt .
COPY flaresolverr_proxy.py .
COPY entrypoint.sh .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the proxy will run on
EXPOSE 8888

# Use the entrypoint script to start the container
ENTRYPOINT ["/app/entrypoint.sh"]

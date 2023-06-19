# Base image
FROM python:3.10

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file to container
COPY requirements.txt .

# Install dependencies

RUN pip install --no-cache-dir -r requirements.txt
# Copy app files to container
COPY . .

# Start command
CMD ["python", "run.py", "--expensive"]

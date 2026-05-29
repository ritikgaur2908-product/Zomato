# Use a combined build to get both Node and Python
FROM node:20-slim AS node-base
FROM python:3.11-slim

# Install Node.js from the node-base image
COPY --from=node-base /usr/local /usr/local

WORKDIR /app

# Install system dependencies needed for Python libraries (like pandas/numpy)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend packages and install
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

# Copy the rest of the application
WORKDIR /app
COPY . .

# Pre-download and cache the Zomato dataset into the container image during build time
RUN python -c "from data.loader import DatasetLoader; DatasetLoader().load(force_refresh=True)"

# Build the Next.js frontend
WORKDIR /app/frontend
RUN npm run build

# Expose port and start Next.js
EXPOSE 3000
ENV PORT=3000
ENV NODE_ENV=production

# Start Next.js server
CMD ["npm", "start"]

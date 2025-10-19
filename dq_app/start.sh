#!/bin/bash

# Start script for DQ Self-Service Portal

echo "🚀 Starting Data Quality Self-Service Portal..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cp env.example .env
    echo "📝 Please edit .env with your Databricks credentials before continuing."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check required environment variables
if [ -z "$DATABRICKS_SERVER_HOSTNAME" ] || [ -z "$DATABRICKS_HTTP_PATH" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ Missing required environment variables. Please configure .env file."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "✅ Environment ready"
echo "🌐 Starting app on http://localhost:8080"
echo ""

# Start the app
python app.py


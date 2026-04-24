#!/bin/bash

# Bloomy Backend Startup Script

echo "╔═════════════════════════════════════════╗"
echo "║        🌿 Bloomy API Server 🌿          ║"
echo "║      Smart Habit Tracking App            ║"
echo "╚═════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment found"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "📋 Creating .env from template..."
    cp .env.example .env
    echo "✓ .env created - please update with your Firebase credentials"
    echo ""
    echo "📝 Don't forget to:"
    echo "   1. Get Firebase service account key from console.firebase.google.com"
    echo "   2. Update FIREBASE_SERVICE_ACCOUNT_KEY path in .env"
    echo "   3. Add your OpenAI and Vision API keys if needed"
    echo ""
fi

# Check for Firebase config
if grep -q "path/to/serviceAccountKey.json" .env; then
    echo "⚠️  Firebase configuration still pointing to example path!"
    echo "❌ Please update FIREBASE_SERVICE_ACCOUNT_KEY in .env"
    exit 1
fi

# Start the server
echo ""
echo "🚀 Starting Bloomy API Server..."
echo "📍 Server will run on http://localhost:5000"
echo "📚 API Docs available at http://localhost:5000/api/docs"
echo "🏥 Health check at http://localhost:5000/api/health"
echo ""
python app.py

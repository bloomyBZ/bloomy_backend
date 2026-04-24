@echo off
REM Bloomy Backend Startup Script for Windows

echo.
echo ╔═════════════════════════════════════════╗
echo ║        🌿 Bloomy API Server 🌿          ║
echo ║      Smart Habit Tracking App            ║
echo ╚═════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment found
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt > nul 2>&1
echo ✓ Dependencies installed

REM Check for .env file
if not exist ".env" (
    echo.
    echo ⚠️  .env file not found!
    echo 📋 Creating .env from template...
    copy .env.example .env
    echo ✓ .env created - please update with your Firebase credentials
    echo.
    echo 📝 Don't forget to:
    echo    1. Get Firebase service account key from console.firebase.google.com
    echo    2. Update FIREBASE_SERVICE_ACCOUNT_KEY path in .env
    echo    3. Add your OpenAI and Vision API keys if needed
    echo.
)

REM Check for Firebase config
findstr /M "path/to/serviceAccountKey.json" .env > nul
if %errorlevel% equ 0 (
    echo ⚠️  Firebase configuration still pointing to example path!
    echo ❌ Please update FIREBASE_SERVICE_ACCOUNT_KEY in .env
    pause
    exit /b 1
)

REM Start the server
echo.
echo 🚀 Starting Bloomy API Server...
echo 📍 Server will run on http://localhost:5000
echo 📚 API Docs available at http://localhost:5000/api/docs
echo 🏥 Health check at http://localhost:5000/api/health
echo.
python app.py

pause
